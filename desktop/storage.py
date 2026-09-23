"""Atomic local state with isolated credentials and bounded, per-conversation files."""
import json
import os
import threading
import uuid
import shutil
import math
from pathlib import Path

DEFAULTS = {
    'theme': 'dark', 'language': 'zh', 'startup': 'last', 'reduceMotion': False,
    'provider': 'OpenAI', 'endpoint': 'https://api.openai.com/v1', 'model': '',
    'temperature': 0.7, 'contextMessages': 40, 'maxTokens': 4096,
    'storeConversations': True, 'memoryEnabled': False, 'memory': '', 'debug': False, 'profiles': {},
}


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / 'conversations').mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.warnings = []
        self._backups = set()

    def _read(self, path, fallback):
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
            if fallback is not None and not isinstance(value, type(fallback)):
                raise ValueError('Unexpected data type')
            return value
        except FileNotFoundError:
            return fallback
        except (ValueError, UnicodeError) as exc:
            if fallback is not None:
                self._backup(path)
                return fallback
            raise ValueError(f'本地数据损坏，原文件已保留：{path.name}') from exc

    def _backup(self, path):
        if path in self._backups:
            return
        backup = path.with_name(path.name + '.recovery-' + uuid.uuid4().hex[:8] + '.bak')
        shutil.copy2(path, backup)
        self._backups.add(path)
        self.warnings.append(f'{path.name} 中有无法读取的数据，已保留备份 {backup.name}，可以继续使用。')

    def _write(self, path, data):
        with self.lock:
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temp, path)

    def settings(self):
        with self.lock:
            path = self.directory / 'preferences.json'
            raw = self._read(path, {})
            data = dict(DEFAULTS)
            invalid = False
            for k, default in DEFAULTS.items():
                value = raw.get(k, default)
                valid = isinstance(value, type(default))
                if isinstance(default, float):
                    valid = isinstance(value, (int, float)) and math.isfinite(value)
                if valid:
                    data[k] = value
                else:
                    invalid = True
            for k, choices in {'theme': ('dark', 'light', 'system'), 'provider': ('OpenAI','Claude','Gemini','Local'),
                               'startup': ('last','new','courses'), 'language': ('zh','en')}.items():
                if data[k] not in choices:
                    data[k] = DEFAULTS[k]
                    invalid = True
            data['contextMessages'] = max(2, min(200, data['contextMessages']))
            data['maxTokens'] = max(128, min(32768, data['maxTokens']))
            data['temperature'] = max(0, min(2, data['temperature']))
            data['profiles'] = {k:v for k,v in data['profiles'].items() if k in ('OpenAI','Claude','Gemini','Local')
                                and isinstance(v, dict) and isinstance(v.get('model'), str) and isinstance(v.get('endpoint'), str)}
            if invalid and path.exists():
                self._backup(path)
            return data

    def save_settings(self, values):
        data = self.settings() | {k: v for k, v in values.items() if k in DEFAULTS}
        if data['theme'] not in ('dark', 'light', 'system'):
            raise ValueError('无效主题')
        if data['provider'] not in ('OpenAI', 'Claude', 'Gemini', 'Local'):
            raise ValueError('无效模型服务')
        data['temperature'] = max(0, min(2, float(data['temperature'])))
        data['contextMessages'] = max(2, min(200, int(data['contextMessages'])))
        data['maxTokens'] = max(128, min(32768, int(data['maxTokens'])))
        data['profiles'] = dict(data.get('profiles') or {})
        data['profiles'][data['provider']] = {k: data[k] for k in ('endpoint', 'model')}
        self._write(self.directory / 'preferences.json', data)
        return data

    def _conversation_path(self, cid):
        return self.directory / 'conversations' / f'{uuid.UUID(cid)}.json'

    def conversations(self):
        with self.lock:
            path = self.directory / 'index.json'
            rows = self._read(path, [])
            valid = []
            for c in rows:
                try:
                    uuid.UUID(c['id'])
                    if not isinstance(c.get('title'), str) or not isinstance(c.get('updated'), (int, float)):
                        raise ValueError('Invalid record')
                    valid.append(c)
                except (ValueError, TypeError, KeyError, AttributeError):
                    self._backup(path)
            return valid

    def conversation(self, cid):
        with self.lock:
            c = self._read(self._conversation_path(cid), None)
            if c is not None and (not isinstance(c, dict) or not isinstance(c.get('title'), str)
                or not isinstance(c.get('messages'), list) or any(not isinstance(m,dict)
                or m.get('role') not in ('user','assistant') or not isinstance(m.get('content'),str)
                for m in c.get('messages',[]))):
                raise ValueError('会话格式无效，原文件已保留，可先新建会话继续使用')
            return c

    def save_conversation(self, conversation):
        if not self.settings()['storeConversations']:
            return False
        path = self._conversation_path(conversation['id'])
        if len(conversation.get('messages', [])) > 10000:
            raise ValueError('单个会话最多保存 10000 条消息，请新建会话')
        with self.lock:
            self._write(path, conversation)
            index = [c for c in self.conversations() if c['id'] != conversation['id']]
            index.insert(0, {k: conversation[k] for k in ('id', 'title', 'updated')})
            self._write(self.directory / 'index.json', index)
        return True

    def delete_conversation(self, cid):
        with self.lock:
            self._conversation_path(cid).unlink(missing_ok=True)
            self._write(self.directory / 'index.json', [c for c in self.conversations() if c['id'] != cid])

    def prompts(self):
        with self.lock:
            path = self.directory / 'prompts.json'
            rows = self._read(path, [])
            valid = [p for p in rows if isinstance(p,dict) and all(isinstance(p.get(k),str) for k in ('id','title','text'))]
            if len(valid) != len(rows):
                self._backup(path)
            return valid

    def save_prompts(self, prompts):
        self._write(self.directory / 'prompts.json', prompts)

    def workspace(self):
        with self.lock:
            path = self.directory / 'workspace.json'
            data = self._read(path, {'files': [], 'task': ''})
            if not isinstance(data.get('files'),list) or not isinstance(data.get('task'),str):
                if path.exists(): self._backup(path)
                return {'files': [], 'task': ''}
            files = [f for f in data['files'] if isinstance(f,dict) and isinstance(f.get('id'),str)
                     and isinstance(f.get('name'),str) and (isinstance(f.get('text'),str) or isinstance(f.get('data'),str))]
            if len(files) != len(data['files']): self._backup(path)
            return {'files': files, 'task': data['task']}

    def save_workspace(self, workspace):
        if len(workspace.get('files', [])) > 80 or len(json.dumps(workspace).encode()) > 32 * 1024 * 1024:
            raise ValueError('工作区资料超过 32 MB 或 80 个文件，请移除不再使用的资料')
        self._write(self.directory / 'workspace.json', workspace)
