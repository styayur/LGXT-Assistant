"""Encrypted-store boundary, restart validation, cancellation and offline recovery."""
import asyncio
import json
from types import SimpleNamespace

import flet as ft
import pytest
import requests

from mobile.src.lgxt_transport import APIClient
from mobile.src.main import main
from mobile.src.session_state import SESSION_KEY, MAX_AGE, SessionVault, encode_session, restore_session
from mobile.src.study_overview import overview
from test_mobile import Page, Storage, FixtureClient, find, wait_for


def authenticated():
    client = APIClient('https://platform.example/api')
    client.headers['Authorization'] = 'synthetic-token'
    client.session.cookies.set('sid', 'synthetic-cookie', domain='platform.example', path='/api', secure=True)
    return client


def test_session_roundtrip_is_origin_bound_and_bounded():
    source = authenticated()
    raw = encode_session(source, 'synthetic-user', now=100)
    target = APIClient(source.base_url)
    assert restore_session(target, raw, now=101) == 'synthetic-user'
    assert target.headers['Authorization'] == 'synthetic-token'
    cookie = next(iter(target.session.cookies))
    assert (cookie.name, cookie.value, cookie.domain, cookie.path, cookie.secure) == (
        'sid', 'synthetic-cookie', 'platform.example', '/api', True)
    assert 'password' not in raw
    for delta in ({'baseUrl': 'https://other.example/api'}, {'expiresAt': 100},
                  {'savedAt': 200}, {'expiresAt': 100 + MAX_AGE + 1}, {'token': 'bad\r\nheader'},
                  {'cookies': [{'name': 'x'}]}, {'cookies': [dict(json.loads(raw)['cookies'][0], domain='evil.example')]}):
        with pytest.raises(ValueError):
            restore_session(APIClient(source.base_url), json.dumps(json.loads(raw) | delta), now=101)
    with pytest.raises(ValueError):
        restore_session(target, 'x' * 65537)


def test_logout_serializes_after_inflight_secure_write():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        class Slow:
            value = None
            async def set(self, key, value):
                entered.set()
                await release.wait()
                self.value = value
            async def remove(self, key):
                self.value = None
        store = Slow()
        vault = SessionVault(store)
        writing = asyncio.create_task(vault.save('synthetic'))
        await entered.wait()
        forgetting = asyncio.create_task(vault.forget())
        release.set()
        await asyncio.gather(writing, forgetting)
        assert store.value is None
    asyncio.run(scenario())


class SecureStore:
    def __init__(self, value): self.value = value
    async def get(self, key): assert key == SESSION_KEY; return self.value
    async def set(self, key, value): assert key == SESSION_KEY; self.value = value
    async def remove(self, key): assert key == SESSION_KEY; self.value = None


class AsyncPage(Page):
    def run_task(self, callback, *args): return asyncio.run(callback(*args))


@pytest.mark.parametrize('result,rejected,restored,retained', [
    (True, False, True, True), (False, True, False, False), (False, False, False, True)])
def test_restart_checks_server_and_distinguishes_expiry_from_offline(result, rejected, restored, retained):
    instances = []
    class Client(FixtureClient):
        base_url = 'https://platform.example/api'
        def __init__(self):
            super().__init__()
            self.session = requests.Session()
            self.authentication_rejected = rejected
            instances.append(self)
        def get_user_info(self):
            assert self.headers['Authorization'] == 'synthetic-token'
            assert self.session.cookies.get('sid') == 'synthetic-cookie'
            return result, {} if result else 'synthetic rejection'
    secure = SecureStore(encode_session(authenticated(), 'synthetic-user'))
    page, notes = AsyncPage(), Storage()
    main(page, Client, notes, secure)
    if restored:
        wait_for(lambda: page.views[-1].route == '/dashboard')
        nav = find(page, ft.NavigationBar)
        nav.selected_index = 3
        nav.on_change(SimpleNamespace(control=nav))
        find(page, ft.Button, text='退出登录并清除设备会话').on_click(None)
        assert secure.value is None and page.views[-1].route == '/login'
    else:
        assert page.views[-1].route == '/login'
        assert bool(secure.value) is retained
    assert 'synthetic-token' not in json.dumps(notes.data)


def test_corrupt_secure_store_keeps_offline_notes_available():
    page, notes, secure = AsyncPage(), Storage(), SecureStore('{broken')
    main(page, FixtureClient, notes, secure)
    assert page.views[-1].route == '/login'
    find(page, ft.TextButton, text='离线打开本地资料').on_click(None)
    assert page.views[-1].route == '/library'


def test_overview_orders_deadlines_without_dropping_exhausted_or_unknown_attempts():
    courses = [{'courseId': 1}, {'courseId': 2}]
    works = [
        {'workId': 'unknown', 'grade': None},
        {'workId': 'later', 'grade': None, 'expireTime': '2026-12-01'},
        {'workId': 'exhausted', 'grade': None, 'tryTimes': 1, 'times': 1, 'expireTime': '2026-11-20'},
        {'workId': 'done', 'grade': 0},
    ]
    result = overview(courses, lambda cid: (True, works) if cid == 1 else (False, 'offline'))
    assert [w['workId'] for _, w in result['pending']] == ['exhausted', 'later', 'unknown']
    assert result['done'] == 1 and result['total'] == 4 and result['failed'] == 1
