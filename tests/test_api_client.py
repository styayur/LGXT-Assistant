# -*- coding: utf-8 -*-
import pytest

import api


class FakeResponse:
    def __init__(self, payload=None, *, ctype='image/png', content=b'x', raise_json=False):
        self._payload = payload
        self.headers = {'Content-Type': ctype}
        self.content = content
        self._raise_json = raise_json

    def raise_for_status(self):
        return None

    def json(self):
        if self._raise_json:
            raise ValueError('not json')
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.headers = {}
        self.calls = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.calls.append((url, data, timeout))
        return self.response

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, timeout))
        return self.response


def client_with(response):
    c = api.APIClient()
    c.session = FakeSession(response)
    return c


def test_login_ok_sets_authorization():
    c = client_with(FakeResponse({'code': 0, 'data': 'TOKEN'}))
    ok, msg = c.login('u', 'p')
    assert ok and msg == '欢迎回来！'
    assert c.headers['Authorization'] == 'TOKEN'
    assert c.session.headers['Authorization'] == 'TOKEN'


def test_business_error_keeps_prefix():
    c = client_with(FakeResponse({'code': 1, 'msg': '拒绝'}))
    ok, msg = c.get_my_courses()
    assert not ok and msg == '获取课程列表失败：拒绝'


def test_non_json_response_is_reported():
    c = client_with(FakeResponse(None, raise_json=True))
    ok, msg = c.get_user_info()
    assert not ok and '非 JSON' in msg


def test_missing_field_is_reported():
    c = client_with(FakeResponse({'msg': 'x'}))
    ok, msg = c.get_my_courses()
    assert not ok and '缺少必要字段' in msg


def test_submit_answer_success_message():
    c = client_with(FakeResponse({'code': 0, 'data': 'OK'}))
    ok, msg = c.submit_answer(7, '100')
    assert ok and '成绩：100' in msg and 'OK' in msg


def test_fetch_image_rejects_non_image():
    c = client_with(FakeResponse(ctype='text/html', content=b'<html>'))
    with pytest.raises(ValueError):
        c.fetch_image('http://example/x')


def test_fetch_image_rejects_empty_and_oversize():
    with pytest.raises(ValueError):
        client_with(FakeResponse(content=b'')).fetch_image('http://example/x')
    with pytest.raises(ValueError):
        client_with(FakeResponse(content=b'x' * (api.MAX_IMAGE_BYTES + 1))).fetch_image('http://example/x')
