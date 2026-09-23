import json
import threading
import time
import uuid

import pytest

from desktop.storage import Store, DEFAULTS
from desktop.bridge import Bridge, prepare_messages
from desktop import models


def conversation():
    return {'id': str(uuid.uuid4()), 'title': '中文会话', 'updated': 123,
            'messages': [{'id': '1', 'role': 'user', 'content': '测试'}]}


def test_store_roundtrip_delete_and_memory_mode(tmp_path):
    store = Store(tmp_path)
    c = conversation()
    store.save_conversation(c)
    assert store.conversation(c['id']) == c
    assert 'messages' not in store.conversations()[0]
    store.save_settings({'storeConversations': False})
    assert store.save_conversation(c | {'title': '未保存'}) is False
    assert store.conversation(c['id'])['title'] == c['title']
    store.delete_conversation(c['id'])
    assert store.conversations() == []
    assert store.conversation(c['id']) is None


def test_store_refuses_path_traversal_and_preserves_corruption(tmp_path):
    store = Store(tmp_path)
    with pytest.raises(ValueError):
        store.conversation('../../credentials')
    path = tmp_path / 'index.json'
    path.write_text('broken')
    assert store.conversations() == []
    assert path.read_text() == 'broken'
    assert list(tmp_path.glob('index.json.recovery-*.bak'))
    assert store.warnings


def test_invalid_preferences_and_recent_conversation_do_not_block_bootstrap(tmp_path, monkeypatch):
    import config
    directory=tmp_path/'data'
    store=Store(directory)
    (directory/'preferences.json').write_text('{"provider":null,"theme":"unknown","contextMessages":"bad"}')
    assert store.settings()['provider']=='OpenAI'
    (directory/'index.json').write_text('[null,{"id":"bad"}]')
    monkeypatch.setattr(config,'get_saved_username',lambda:pytest.fail('bootstrap must not read credentials'))
    bridge=Bridge(directory,legacy_settings=config.Settings(str(tmp_path/'config.ini')))
    monkeypatch.setattr(bridge,'_key',lambda _:pytest.fail('bootstrap must not wait on keyring'))
    state=bridge.bootstrap()
    assert state['conversations']==[] and state['settings']['theme']=='dark'
    assert state['warnings']


@pytest.mark.parametrize('slow_credentials', [False, True])
def test_cancelled_login_cannot_authenticate_later(tmp_path, monkeypatch, slow_credentials):
    import config, api
    from types import SimpleNamespace
    bridge=Bridge(tmp_path/'data',legacy_settings=config.Settings(str(tmp_path/'config.ini')))
    started=threading.Event();release=threading.Event();errors=[]
    class Candidate:
        session=SimpleNamespace(close=lambda:None)
        def __init__(self,*args):pass
        def login(self,*args):
            if not slow_credentials:
                started.set();release.wait(2)
            return True,'ok'
    monkeypatch.setattr(api,'APIClient',Candidate)
    def save_credentials(*args):
        started.set();release.wait(2);return True
    monkeypatch.setattr(config,'save_credentials',save_credentials)
    def login():
        try:bridge.login(' user ','password',slow_credentials,'cancel-me')
        except ValueError as exc:errors.append(str(exc))
    t=threading.Thread(target=login);t.start();assert started.wait(1)
    bridge.cancel_login('cancel-me');release.set();t.join(2)
    assert bridge._username=='' and errors and '取消' in errors[0]


def test_missing_frontend_has_actionable_startup_error(tmp_path):
    from desktop.app import frontend_url, StartupError
    with pytest.raises(StartupError,match='完整解压'):
        frontend_url(tmp_path)


def test_concurrent_conversation_writes_keep_index(tmp_path):
    store = Store(tmp_path)
    threads = [threading.Thread(target=store.save_conversation, args=(conversation(),)) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(store.conversations()) == 12
    assert all(store.conversation(c['id']) for c in store.conversations())


def test_settings_never_persist_api_key(tmp_path):
    store = Store(tmp_path)
    store.save_settings({'api_key': 'secret', 'temperature': 5, 'contextMessages': 999})
    text = (tmp_path / 'preferences.json').read_text()
    assert 'secret' not in text
    assert store.settings()['temperature'] == 2
    assert store.settings()['contextMessages'] == 200


def test_workspace_and_provider_profiles_survive_restart(tmp_path):
    store = Store(tmp_path)
    store.save_workspace({'files':[{'id':'test','name':'note.md','text':'你好'}],'task':'study'})
    store.save_settings({'provider':'Local','endpoint':'http://localhost:11434/v1','model':'local-model'})
    store.save_settings({'provider':'Claude','endpoint':'https://api.anthropic.com/v1','model':'claude-model'})
    reloaded = Store(tmp_path)
    assert reloaded.workspace()['files'][0]['text'] == '你好'
    assert reloaded.settings()['profiles']['Local']['model'] == 'local-model'
    assert reloaded.settings()['profiles']['Claude']['model'] == 'claude-model'


def test_openai_reasoning_parameters():
    _, _, body = models.request_config(DEFAULTS | {'model':'gpt-5'}, 'key', [])
    assert 'max_completion_tokens' in body
    assert 'max_tokens' not in body and 'temperature' not in body


def test_provider_wire_formats_and_context():
    s = DEFAULTS | {'provider': 'Claude', 'endpoint': 'https://api.anthropic.com/v1',
                    'model': 'test-model', 'memoryEnabled': True, 'memory': 'Explain clearly'}
    messages = [{'role': 'assistant', 'content': 'old'}, {'role': 'user', 'content': 'look',
                 'attachments': [{'name': 'note.md', 'text': 'context'},
                                 {'name': 'image.png', 'data': 'data:image/png;base64,aA=='}]}]
    prepared = prepare_messages(s, messages)
    assert prepared[0]['role'] == 'system'
    assert prepared[1]['content'][0]['text'].endswith('context')
    assert prepared[1]['content'][1]['source']['media_type'] == 'image/png'
    url, headers, body = models.request_config(s, 'key', prepared)
    assert url.endswith('/v1/messages')
    assert headers['x-api-key'] == 'key'
    assert body['system'] == 'Explain clearly'
    assert body['messages'][0]['role'] == 'user'
    s = s | {'provider': 'Local', 'endpoint': 'http://localhost:11434/v1'}
    prepared = prepare_messages(s, messages)
    url, headers, body = models.request_config(s, '', prepared)
    assert url.endswith('/chat/completions')
    assert 'Authorization' not in headers
    assert prepared[1]['content'][1]['type'] == 'image_url'


@pytest.mark.parametrize('endpoint', ['file:///etc/passwd', 'http://remote.example/v1', 'https://user:pass@example.org'])
def test_invalid_endpoints(endpoint):
    with pytest.raises(ValueError):
        models.endpoint_url(DEFAULTS | {'endpoint': endpoint}, '')


class Response:
    ok = True
    status_code = 200
    def __init__(self, lines):
        self.lines = lines
        self.closed = False
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True
    def iter_lines(self, **kwargs): yield from self.lines


def test_stream_sse_unicode_error_and_close(monkeypatch):
    response = Response([': ping', '', 'data: ' + json.dumps({'choices': [{'delta': {'content': '你好'}}]}), 'data: [DONE]'])
    monkeypatch.setattr(models.requests, 'post', lambda *a, **kw: response)
    result = list(models.stream(DEFAULTS | {'model': 'test'}, 'key', [], threading.Event()))
    assert result == ['你好'] and response.closed
    response = Response(['data: {"error": {"message": "not copied to user"}}'])
    with pytest.raises(ValueError, match='生成过程中'):
        list(models.stream(DEFAULTS | {'model': 'test'}, 'key', [], threading.Event()))
    assert response.closed


def test_claude_stream(monkeypatch):
    response = Response(['event: content_block_delta', 'data: {"delta":{"type":"text_delta","text":"Hello"}}'])
    monkeypatch.setattr(models.requests, 'post', lambda *a, **kw: response)
    result = list(models.stream(DEFAULTS | {'provider': 'Claude', 'model': 'test'}, 'key', [], threading.Event()))
    assert result == ['Hello']


def test_stop_job_retains_partial_and_prevents_overlap(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, 'default_config_path', lambda: str(tmp_path / 'legacy.ini'))
    bridge = Bridge(tmp_path / 'data')
    bridge._store.save_settings({'provider': 'Local', 'endpoint': 'http://localhost:11434/v1', 'model': 'test'})
    started = threading.Event()
    def stream(settings, key, messages, cancel, response_ready):
        yield 'partial'
        started.set()
        cancel.wait(2)
    monkeypatch.setattr(models, 'stream', stream)
    jid = bridge.start_chat([{'role': 'user', 'content': 'test'}])
    assert started.wait(1)
    with pytest.raises(ValueError, match='当前任务'):
        bridge.start_chat([{'role': 'user', 'content': 'again'}])
    assert bridge.stop_chat(jid)
    deadline = time.monotonic() + 2
    while not bridge.poll_job(jid)['done'] and time.monotonic() < deadline:
        time.sleep(.01)
    result = bridge.poll_job(jid)
    assert result['done'] and result['delta'] == 'partial' and result['status'] == '已停止'
    assert bridge.poll_job(jid, len('partial'))['delta'] == ''


def test_auth_gate_and_grade_validation(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, 'default_config_path', lambda: str(tmp_path / 'legacy.ini'))
    bridge = Bridge(tmp_path / 'data')
    with pytest.raises(ValueError, match='登录'):
        bridge.courses()
    bridge._username = 'test'
    with pytest.raises(ValueError, match='整数'):
        bridge.submit_grade(1, 101)
    with pytest.raises(ValueError, match='整数'):
        bridge.submit_grade(1, 99.5)
