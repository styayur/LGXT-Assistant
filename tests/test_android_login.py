"""Regression for the v3.2.0/v3.2.1 Android login contract."""
import json
from pathlib import Path

import flet as ft
import pytest
import requests

import api
from mobile.src.main import main
from test_mobile import FixtureClient, Page, Storage, find, wait_for

ROOT = Path(__file__).resolve().parents[1]


class Response:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self.payload = {'code': 0, 'data': []} if payload is None else payload
        self.headers = headers or {}
        self.closed = False

    def close(self):
        self.closed = True

    def json(self):
        if self.payload is None:
            raise ValueError('not json')
        return self.payload


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.headers = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        self.cookies.set('sid', 'login-session')
        return value


def client(*responses, url='http://lgxt.wutp.com.cn/api'):
    value = api.APIClient(url, allow_insecure=url.startswith('http://'))
    value.session = Session(*responses)
    return value


def test_http_stays_blocked_until_explicit_and_matches_v321_request():
    blocked = api.APIClient('http://lgxt.wutp.com.cn/api')
    blocked.session = Session(Response(payload={'code': 0, 'data': 'TOKEN'}))
    assert blocked.login('user', 'secret') == (False, api.HTTP_BLOCKED)
    assert blocked.session.calls == []

    active = client(Response(payload={'code': 0, 'data': 'TOKEN'}))
    ok, message = active.login('user', 'secret')
    assert ok and message == '欢迎回来！'
    url, kwargs = active.session.calls[0]
    assert url == 'http://lgxt.wutp.com.cn/api/login'
    assert urlsplit_scheme(url) == 'http'
    assert kwargs['allow_redirects'] is False
    assert kwargs['verify'] is True
    assert kwargs['headers']['Accept'] == '*/*'
    assert kwargs['headers']['Accept-Language'] == 'zh-CN,zh;q=0.9'
    assert kwargs['headers']['Content-Type'] == 'application/x-www-form-urlencoded'
    assert kwargs['data'] == {'loginName': 'user', 'password': 'secret'}
    assert active.headers['Authorization'] == 'TOKEN'
    assert 'Authorization' not in active.session.headers
    assert active.session.cookies.get('sid') == 'login-session'
    assert 'secret' not in message


def urlsplit_scheme(url):
    return api.urlsplit(url).scheme


def test_platform_messages_are_visible_and_secrets_are_not():
    rejected = client(Response(payload={'code': 500, 'msg': '用户名密码错误!'}))
    ok, message = rejected.login('user', 'secret-password')
    assert not ok and message == '登录失败：用户名密码错误!'
    assert 'secret-password' not in message

    expired = client(Response(payload={'code': -1, 'msg': '账号登录信息已过期或失效 ，请重新登录!'}),
                     url='https://lgxt.wutp.com.cn/api')
    ok, message = expired.get_user_info()
    assert not ok and '请重新登录' in message and message.startswith('获取用户信息失败')


@pytest.mark.parametrize('code', [0, '0'])
def test_portal_numeric_or_string_success_code(code):
    active = client(Response(payload={'code': code, 'data': 'TOKEN'}))
    assert active.login('user', 'synthetic')[0]
    assert active.headers['Authorization'] == 'TOKEN'


@pytest.mark.parametrize('payload', [
    {'code': False, 'data': 'TOKEN'}, {'code': True, 'data': 'TOKEN'},
    {'code': 0.0, 'data': 'TOKEN'}, {'code': None, 'data': 'TOKEN'},
    {'code': [], 'data': 'TOKEN'}, {'code': {}, 'data': 'TOKEN'},
    {'code': '00', 'data': 'TOKEN'}, {'code': 'false', 'data': 'TOKEN'},
    {'code': '0'}, {'data': 'TOKEN'}, [], '0',
])
def test_malformed_login_schema_never_installs_authorization(payload):
    response = Response(payload=payload)
    active = client(response)
    assert not active.login('user', 'synthetic')[0]
    assert 'Authorization' not in active.headers and response.closed
    assert len(active.session.calls) == 1


@pytest.mark.parametrize('code', [-1, '-1'])
def test_portal_numeric_or_string_expiry_code(code):
    active = client(Response(payload={'code': code, 'msg': 'expired'}))
    assert not active.get_user_info()[0]
    assert active.authentication_rejected


def test_https_upgrade_redirect_is_not_called():
    active = client(Response(302, headers={'Location': 'https://lgxt.wutp.com.cn/api/login'}))
    ok, message = active.login('user', 'secret')
    assert not ok and message == api.HTTPS_UPGRADE_BLOCKED
    assert len(active.session.calls) == 1
    assert active.session.calls[0][0].startswith('http://')
    assert active.session.calls[0][1]['allow_redirects'] is False


def test_http_network_failure_does_not_blame_tls():
    active = client(requests.Timeout('secret-password'))
    ok, message = active.login('user', 'secret-password')
    assert not ok and 'TLS' not in message and 'secret-password' not in message

    secure = api.APIClient('https://lgxt.wutp.com.cn/api')
    secure.session = Session(*[requests.Timeout('secret')] * 3)
    ok, message = secure.get_user_info()
    assert not ok and 'TLS' in message and 'secret' not in message


def test_source_does_not_disable_tls_or_open_global_cleartext():
    transport = (ROOT / 'mobile/src/lgxt_transport.py').read_text(encoding='utf-8')
    project = (ROOT / 'mobile/pyproject.toml').read_text(encoding='utf-8')
    assert 'verify=False' not in transport and 'verify = False' not in transport
    assert 'usesCleartextTraffic =' not in project and 'usesCleartextTraffic=' not in project
    assert 'networkSecurityConfig' not in project


def test_android_login_keeps_the_authenticated_session():
    instances = []

    class Client(FixtureClient):
        def __init__(self):
            super().__init__()
            self.cookies = {}
            instances.append(self)

        def login(self, user, password):
            assert password == 'not-a-real-password'
            self.headers['Authorization'] = 'TOKEN'
            self.cookies['sid'] = 'session'
            return True, '欢迎回来！'

        def get_my_courses(self):
            assert self.headers.get('Authorization') == 'TOKEN'
            assert self.cookies.get('sid') == 'session'
            self.used = True
            return super().get_my_courses()

    page = Page()
    store = Storage()
    main(page, Client, store)
    find(page, ft.TextField, label='账号').value = 'account'
    find(page, ft.TextField, label='密码').value = 'not-a-real-password'
    find(page, ft.Button, text='登录理工学堂').on_click(None)
    wait_for(lambda: getattr(instances[-1], 'used', False))
    assert page.views[-1].route == '/dashboard'
    assert not getattr(instances[0], 'used', False)
    assert store.get('lgxt.user') == 'account'
    assert 'lgxt.pass' not in store.data
    assert 'TOKEN' not in json.dumps(store.data)
    assert 'not-a-real-password' not in json.dumps(store.data)


def test_http_authorization_is_one_confirmation_and_can_be_remembered():
    class HttpClient(FixtureClient):
        logins = []
        insecure = True

        def __init__(self):
            super().__init__()
            self.insecure = True

        def login(self, *args):
            type(self).logins.append(args)
            self.headers['Authorization'] = 'TOKEN'
            return True, '欢迎回来！'

    page = Page()
    store = Storage()
    store.data.pop('lgxt.pass', None)
    main(page, HttpClient, store)
    find(page, ft.TextField, label='账号').value = 'account'
    find(page, ft.TextField, label='密码').value = 'not-a-real-password'
    find(page, ft.Button, text='登录理工学堂').on_click(None)
    assert page.dialog and HttpClient.logins == []
    consent = page.dialog
    consent.actions[1].on_click(None)
    assert HttpClient.logins == []  # Flutter has not dismissed the route yet.
    consent.on_dismiss(None)
    wait_for(lambda: page.views[-1].route == '/dashboard')
    assert HttpClient.logins and store.get('lgxt.http_compat') is True
    assert 'lgxt.pass' not in store.data and 'TOKEN' not in json.dumps(store.data)

    HttpClient.logins.clear()
    restored = Page()
    main(restored, HttpClient, store)
    box = find(restored, ft.Checkbox)
    assert box.value is True
    find(restored, ft.TextField, label='账号').value = 'account'
    find(restored, ft.TextField, label='密码').value = 'not-a-real-password'
    find(restored, ft.Button, text='登录理工学堂').on_click(None)
    wait_for(lambda: restored.views[-1].route == '/dashboard')
    assert HttpClient.logins and restored.dialog is None
    box.value = False
    box.on_change(None)
    assert store.get('lgxt.http_compat') is None
