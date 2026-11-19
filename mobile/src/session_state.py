"""Bounded session envelopes; only a platform secure-storage service persists them.

No passwords, note backups, ambient cookies or arbitrary session objects belong here.
"""
import json
import time
from urllib.parse import urlsplit

SESSION_KEY = 'lgxt.android.session.v1'
MAX_AGE = 7 * 24 * 60 * 60


def encode_session(client, username, now=None):
    now = time.time() if now is None else now
    origin = urlsplit(client.base_url).hostname
    token = client.headers.get('Authorization')
    if not isinstance(token, str) or not token or len(token) > 16384:
        raise ValueError('Invalid session token')
    cookies = []
    for cookie in client.session.cookies:
        if cookie.domain and cookie.domain.lstrip('.') != origin:
            continue
        cookies.append({
            'name': cookie.name, 'value': cookie.value, 'domain': cookie.domain,
            'path': cookie.path, 'secure': cookie.secure, 'expires': cookie.expires,
        })
    value = json.dumps({'schemaVersion': 1, 'baseUrl': client.base_url,
                        'username': username, 'token': token, 'cookies': cookies,
                        'savedAt': now, 'expiresAt': now + MAX_AGE})
    if len(cookies) > 32 or len(value.encode('utf-8')) > 65536:
        raise ValueError('Session exceeds limits')
    return value


def restore_session(client, raw, *, now=None):
    """Restore only to the same configured API, before a fresh server check."""
    import requests
    now = time.time() if now is None else now
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > 65536:
        raise ValueError('Invalid session envelope')
    value = json.loads(raw)
    if (not isinstance(value, dict) or value.get('schemaVersion') != 1
            or value.get('baseUrl') != client.base_url):
        raise ValueError('Session origin or version differs')
    saved, expires = value.get('savedAt'), value.get('expiresAt')
    if (type(saved) not in (int, float) or type(expires) not in (int, float)
            or not 0 <= now - saved <= MAX_AGE or not now < expires <= saved + MAX_AGE):
        raise ValueError('Session expired')
    token, username, cookies = value.get('token'), value.get('username'), value.get('cookies')
    if (not isinstance(token, str) or not token or len(token) > 16384
            or '\r' in token or '\n' in token or not isinstance(username, str)
            or not username or len(username) > 512 or not isinstance(cookies, list)
            or len(cookies) > 32):
        raise ValueError('Invalid session fields')
    origin = urlsplit(client.base_url).hostname
    jar = requests.cookies.RequestsCookieJar()
    for cookie in cookies:
        if not isinstance(cookie, dict) or set(cookie) != {'name', 'value', 'domain', 'path', 'secure', 'expires'}:
            raise ValueError('Invalid cookie fields')
        if (not all(isinstance(cookie[k], str) for k in ('name', 'value', 'domain', 'path'))
                or cookie['domain'].lstrip('.') not in ('', origin)
                or not cookie['path'].startswith('/') or type(cookie['secure']) is not bool
                or (cookie['expires'] is not None and type(cookie['expires']) is not int)):
            raise ValueError('Invalid cookie origin')
        if cookie['expires'] is None or cookie['expires'] > now:
            jar.set_cookie(requests.cookies.create_cookie(**cookie))
    client.logout()
    client.session.cookies.update(jar)
    client.headers['Authorization'] = token
    return username


class SessionVault:
    """Serializes save/forget so logout cannot race an outstanding secure write."""
    def __init__(self, storage):
        import asyncio
        self.storage = storage
        self.lock = asyncio.Lock()

    async def load(self):
        async with self.lock:
            return await self.storage.get(SESSION_KEY)

    async def save(self, raw):
        async with self.lock:
            await self.storage.set(SESSION_KEY, raw)

    async def forget(self):
        async with self.lock:
            await self.storage.remove(SESSION_KEY)
