"""Provider adapters. HTTP streams stay in Python; no secrets enter the web UI."""
import json
from urllib.parse import urlparse

import requests


def endpoint_url(settings, suffix):
    endpoint = settings['endpoint'].strip().rstrip('/')
    parsed = urlparse(endpoint)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('请输入有效的 HTTP(S) API Endpoint')
    if parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('远程模型服务需要 HTTPS；本地服务可使用 HTTP')
    return endpoint + suffix


def request_config(settings, key, messages):
    if not settings['model'].strip():
        raise ValueError('请先在设置中填写模型 ID')
    if not key and settings['provider'] != 'Local':
        raise ValueError('请先在设置中保存 API Key')
    body = {'model': settings['model'].strip(), 'messages': messages,
            'stream': True, 'temperature': settings['temperature'],
            'max_tokens': settings['maxTokens']}
    headers = {'Content-Type': 'application/json'}
    if settings['provider'] == 'Claude':
        headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
        body['system'] = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
        body['messages'] = [m for m in messages if m['role'] != 'system']
        return endpoint_url(settings, '/messages'), headers, body
    if key:
        headers['Authorization'] = f'Bearer {key}'
    if settings['provider'] == 'OpenAI':
        body['max_completion_tokens'] = body.pop('max_tokens')
        if settings['model'].lower().startswith(('gpt-5', 'o1', 'o3', 'o4')):
            body.pop('temperature', None)
    return endpoint_url(settings, '/chat/completions'), headers, body


def stream(settings, key, messages, cancel, on_response=None):
    url, headers, body = request_config(settings, key, messages)
    # No retries on generation: retries can duplicate paid requests.
    with requests.post(url, headers=headers, json=body, stream=True, timeout=(10, 60)) as response:
        if on_response:
            on_response(response)
        if cancel.is_set():
            return
        if not response.ok:
            raise ValueError(f'模型服务返回 HTTP {response.status_code}，请检查模型 ID、密钥与额度')
        response.encoding = 'utf-8'
        for line in response.iter_lines(chunk_size=1, decode_unicode=True):
            if cancel.is_set():
                return
            if not line or not line.startswith('data:'):
                continue
            raw = line[5:].strip()
            if raw == '[DONE]':
                return
            event = json.loads(raw)
            if event.get('error') or event.get('type') == 'error':
                raise ValueError('模型服务在生成过程中返回错误，请稍后重试')
            if settings['provider'] == 'Claude':
                delta = event.get('delta', {})
                if delta.get('type') == 'text_delta':
                    yield delta.get('text', '')
            else:
                choices = event.get('choices') or []
                if choices:
                    yield choices[0].get('delta', {}).get('content') or ''


def test_connection(settings, key):
    # Tiny real generation verifies the selected model, not just endpoint availability.
    import threading
    probe = settings | {'maxTokens': 128}
    for text in stream(probe, key, [{'role': 'user', 'content': 'Reply OK.'}], threading.Event()):
        if text:
            return {'connected': True, 'model': settings['model']}
    raise ValueError('连接已建立，但模型未返回文本')
