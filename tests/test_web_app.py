import threading

import pytest
import requests

from web_app import BrowserServer


class FakeBridge:
    def bootstrap(self):
        return {'username': '测试用户'}

    def login(self, username, password):
        raise ValueError('登录失败')


@pytest.fixture
def server(tmp_path):
    (tmp_path / 'index.html').write_text('<html lang="zh"><body>LGXT</body></html>')
    (tmp_path / 'asset.js').write_text('export default 1')
    instance = BrowserServer(tmp_path, FakeBridge())
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance
    instance.shutdown()
    instance.server_close()
    thread.join()


def invoke(server, method='bootstrap', args=None, **headers):
    return requests.post(server.origin + '/api/call',
                         headers={'Origin': server.origin, 'X-LGXT-Token': server.token, **headers},
                         json={'method': method, 'args': args or []}, timeout=5)


def test_browser_entry_and_static_boundary(server):
    response = requests.get(server.origin, timeout=5)
    assert 'data-browser="true"' in response.text
    assert server.token not in response.text
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert requests.get(server.origin + '/asset.js', timeout=5).headers['Content-Type'] == 'text/javascript'
    assert requests.get(server.origin + '/%2e%2e/config.py', timeout=5).status_code == 404
    assert requests.get(server.origin, headers={'Host': 'evil.example'}, timeout=5).status_code == 403


def test_authenticated_rpc_and_failures(server):
    assert invoke(server).json()['result']['username'] == '测试用户'
    assert invoke(server, 'login', ['user', 'pass']).json()['error'] == '登录失败'
    assert invoke(server, '_key').status_code == 400
    assert invoke(server, 'choose_files').status_code == 400


@pytest.mark.parametrize('headers', [
    {'Origin': 'https://evil.example'}, {'Origin': ''},
    {'X-LGXT-Token': ''}, {'X-LGXT-Token': 'incorrect'}, {'Host': 'evil.example'},
])
def test_cross_origin_and_unauthorized_requests_rejected(server, headers):
    assert invoke(server, **headers).status_code == 403


def test_oversize_request_rejected(server):
    response = requests.post(server.origin + '/api/call', headers={
        'Origin': server.origin, 'X-LGXT-Token': server.token,
        'Content-Length': str(25 * 1024 * 1024)}, timeout=5)
    assert response.status_code == 413
