"""Narrow desktop bridge. pywebview executes calls off the UI thread."""
import base64
import hashlib
import json
import mimetypes
import threading
import time
import uuid
from pathlib import Path

import keyring

import api
import config
import exporter
import tasks
from . import models
from .storage import Store


class TaskProgress:
    def __init__(self, job, lock):
        self.job, self.lock = job, lock

    def status(self, text):
        with self.lock:
            self.job['status'] = text

    def progress(self, value):
        with self.lock:
            self.job['progress'] = value

    def maximum(self, value):
        with self.lock:
            self.job['maximum'] = value

    def stop_and_close(self, _delay):
        pass


def prepare_messages(settings, messages):
    selected = messages[-settings['contextMessages']:]
    # Truncation must start with a user turn (required by some providers).
    while selected and selected[0]['role'] != 'user':
        selected = selected[1:]
    result = []
    if settings['memoryEnabled'] and settings['memory'].strip():
        result.append({'role': 'system', 'content': settings['memory'][:16000]})
    for message in selected:
        role = message.get('role')
        if role not in ('user', 'assistant'):
            continue
        content = str(message.get('content', ''))
        images = []
        for attachment in message.get('attachments', []):
            if attachment.get('text') is not None:
                content += f"\n\n文件引用：{attachment['name']}\n{attachment['text']}"
            elif attachment.get('data', '').startswith('data:image/'):
                images.append(attachment['data'])
        if images and role == 'user':
            blocks = [{'type': 'text', 'text': content or '请分析附件图片。'}]
            for data in images:
                if settings['provider'] == 'Claude':
                    head, encoded = data.split(',', 1)
                    blocks.append({'type': 'image', 'source': {'type': 'base64',
                                   'media_type': head[5:].split(';')[0], 'data': encoded}})
                else:
                    blocks.append({'type': 'image_url', 'image_url': {'url': data}})
            content = blocks
        if content:
            result.append({'role': role, 'content': content})
    return result


class Bridge:
    def __init__(self, directory=None, client=None, legacy_settings=None):
        self._store = Store(directory or Path(config.default_config_path()).parent / 'desktop')
        self._client = client or api.APIClient()
        self._legacy = legacy_settings or config.Settings(legacy_path=config.legacy_config_path(str(Path(__file__).resolve().parents[1])))
        self._window = None
        self._username = ''
        self._jobs = {}
        self._lock = threading.RLock()
        self._login_attempt = None
        self._cancelled_logins = set()

    def _key_id(self, settings):
        endpoint = settings['endpoint'].strip().rstrip('/')
        return settings['provider'] + ':' + hashlib.sha256(endpoint.encode()).hexdigest()[:24]

    def _key(self, settings):
        try:
            return keyring.get_password('LGXT-Assistant-AI', self._key_id(settings)) or ''
        except Exception:
            return ''

    def bootstrap(self):
        settings = self._store.settings()
        return {'settings': settings, 'hasKey': False,
                'conversations': self._store.conversations(), 'prompts': self._store.prompts(),
                'workspace': self._store.workspace(),
                'username': self._username, 'savedUsername': '',
                'warnings': self._store.warnings,
                'export': {k: getattr(self._legacy, k) for k in (
                    'export_path', 'export_word', 'export_pdf', 'export_word_include_answers',
                    'export_pdf_include_answers')}, 'api': self._client.base_url}

    def credential_status(self):
        # Credential backends can block on an OS prompt; never hold up bootstrap.
        return {'hasKey': bool(self._key(self._store.settings())),
                'savedUsername': config.get_saved_username() or ''}

    def save_settings(self, values, api_key=None, export_values=None):
        # Validate before touching the credential store or existing settings.
        models.endpoint_url(values, '')
        if api_key is not None and api_key.strip():
            try:
                keyring.set_password('LGXT-Assistant-AI', self._key_id(values), api_key.strip())
            except Exception as exc:
                raise ValueError('无法写入系统凭据库；设置未保存，请检查凭据管理器') from exc
        settings = self._store.save_settings(values)
        if export_values:
            for key in ('export_path', 'export_word', 'export_pdf', 'export_word_include_answers', 'export_pdf_include_answers'):
                if key in export_values:
                    setattr(self._legacy, key, export_values[key])
            if not self._legacy.save():
                raise ValueError('导出设置保存失败，请检查配置目录权限')
        return {'settings': settings, 'hasKey': bool(self._key(settings))}

    def remove_key(self):
        settings = self._store.settings()
        if self._key(settings):
            keyring.delete_password('LGXT-Assistant-AI', self._key_id(settings))
        return True

    def test_model(self):
        settings = self._store.settings()
        return models.test_connection(settings, self._key(settings))

    def conversation(self, cid):
        return self._store.conversation(cid)

    def save_conversation(self, conversation):
        return self._store.save_conversation(conversation)

    def delete_conversation(self, cid):
        self._store.delete_conversation(cid)

    def save_prompts(self, prompts):
        self._store.save_prompts(prompts)

    def save_workspace(self, workspace):
        self._store.save_workspace(workspace)

    def toggle_fullscreen(self):
        self._window.toggle_fullscreen()

    def login(self, username, password, remember=False, attempt_id=None):
        username = username.strip()
        attempt_id = attempt_id or str(uuid.uuid4())
        with self._lock:
            if attempt_id in self._cancelled_logins:
                raise ValueError('本次登录已取消')
            self._login_attempt = attempt_id
        password = password or config.get_saved_password(username) or ''
        if not username or not password:
            raise ValueError('请输入账号和密码')
        candidate = api.APIClient(self._client.base_url)
        ok, data = candidate.login(username, password)
        if not ok:
            candidate.session.close()
            raise ValueError(data)
        with self._lock:
            if attempt_id != self._login_attempt or attempt_id in self._cancelled_logins:
                candidate.session.close()
                raise ValueError('本次登录已取消，请重新登录')
        warning = ''
        if remember:
            if not config.save_credentials(username, password):
                warning = '已登录，但凭据保存失败'
        else:
            config.delete_saved_credentials()
        # A slow credential backend must not authenticate a cancelled request.
        with self._lock:
            if attempt_id != self._login_attempt or attempt_id in self._cancelled_logins:
                candidate.session.close()
                raise ValueError('本次登录已取消，请重新登录')
            self._client = candidate
            self._username = username
        return {'username': username, 'warning': warning}

    def cancel_login(self, attempt_id):
        with self._lock:
            if len(self._cancelled_logins) >= 100:
                self._cancelled_logins.clear()
            self._cancelled_logins.add(attempt_id)
            if self._login_attempt == attempt_id:
                self._login_attempt = None
        return True

    def logout(self):
        self._login_attempt = None
        self._client.headers.pop('Authorization', None)
        self._client.session.headers.pop('Authorization', None)
        self._username = ''

    def _authenticated(self):
        if not self._username:
            raise ValueError('请先登录理工学堂')

    def _result(self, result):
        ok, data = result
        if not ok:
            raise ValueError(data)
        return data

    def courses(self):
        self._authenticated()
        return self._result(self._client.get_my_courses())

    def dashboard(self):
        self._authenticated()
        from ui.dashboard import DashboardMixin
        from types import SimpleNamespace
        courses = self._result(self._client.get_my_courses())
        return DashboardMixin._collect_dashboard(SimpleNamespace(api=self._client), courses)

    def works(self, course_id):
        self._authenticated()
        return self._result(self._client.get_course_works(course_id))

    def questions(self, work_id):
        self._authenticated()
        return self._result(self._client.get_questions(work_id))

    def question_image(self, url):
        self._authenticated()
        raw = self._client.fetch_image(url)
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(raw))
        mime = Image.MIME.get(image.format, 'image/png')
        return 'data:' + mime + ';base64,' + base64.b64encode(raw).decode()

    def submit_grade(self, work_id, grade):
        self._authenticated()
        if not str(grade).isdigit() or not 0 <= int(grade) <= 100:
            raise ValueError('成绩必须是 0–100 的整数')
        return self._result(self._client.submit_answer(work_id, str(grade)))

    def user_info(self):
        self._authenticated()
        return self._result(self._client.get_user_info())

    def _new_job(self, kind):
        with self._lock:
            if any(not j['done'] for j in self._jobs.values()):
                raise ValueError('请等待当前任务完成，或停止当前生成')
            for jid in list(self._jobs):
                if self._jobs[jid]['done']:
                    del self._jobs[jid]
            job = {'id': str(uuid.uuid4()), 'kind': kind, 'text': '', 'status': '正在连接…',
                   'done': False, 'error': '', 'progress': 0, 'maximum': 100,
                   'cancel': threading.Event(), 'response': None}
            self._jobs[job['id']] = job
            return job

    def start_chat(self, messages):
        settings = self._store.settings()
        key = self._key(settings)
        prepared = prepare_messages(settings, messages)
        models.request_config(settings, key, prepared)
        job = self._new_job('chat')

        def response_ready(response):
            with self._lock:
                job['response'] = response

        def work():
            try:
                for text in models.stream(settings, key, prepared, job['cancel'], response_ready):
                    with self._lock:
                        job['text'] += text
                        job['status'] = '正在生成' if text else '等待模型输出'
                        if len(job['text']) > 500000:
                            raise ValueError('回复超过显示上限，请缩短问题后重试')
                if not job['text'] and not job['cancel'].is_set():
                    raise ValueError('模型未返回文本；请检查模型类型和服务配置')
            except Exception as exc:
                with self._lock:
                    if not job['cancel'].is_set():
                        job['error'] = str(exc)
            finally:
                with self._lock:
                    job['done'] = True
                    job['response'] = None
                    job['status'] = '已停止' if job['cancel'].is_set() else ('生成失败' if job['error'] else '已完成')
        threading.Thread(target=work, daemon=True).start()
        return job['id']

    def poll_job(self, jid, offset=0):
        with self._lock:
            job = self._jobs[jid]
            return {k: job[k] for k in ('id', 'kind', 'status', 'done', 'error', 'progress', 'maximum')} | {
                'delta': job['text'][int(offset):], 'offset': len(job['text'])}

    def stop_chat(self, jid):
        with self._lock:
            job = self._jobs.get(jid)
            if not job or job['kind'] != 'chat':
                return False
            job['cancel'].set()
            response = job['response']
        if response is not None:
            threading.Thread(target=response.close, daemon=True).start()
        return True

    def start_task(self, action, course=None, work=None):
        self._authenticated()
        if action not in ('export_work', 'export_course', 'export_all', 'submit_course', 'submit_all'):
            raise ValueError('未知任务')
        s = self._legacy
        if action.startswith('export') and not (s.export_word or s.export_pdf):
            raise ValueError('请先在设置中选择 Word 或 PDF 导出格式')
        opts = exporter.ExportOptions(s.export_path, s.export_word, s.export_word_include_answers,
                                      s.export_pdf, s.export_pdf_include_answers)
        job = self._new_job('task')
        adapter = TaskProgress(job, self._lock)

        def run():
            try:
                if action == 'export_work':
                    result = tasks.collect_single(adapter, self._client, work['workId'], work['workName'],
                                                  course['courseName'], course['courseId'], opts)
                    if result is None:
                        raise ValueError(job['status'])
                    text = f'已导出 {len(result)} 道题目至 {opts.export_path}'
                elif action.endswith('course'):
                    works = self._result(self._client.get_course_works(course['courseId']))
                    if action == 'export_course':
                        result = tasks.export_all_works(adapter, self._client, works, course['courseId'], course['courseName'], opts)
                    else:
                        result = tasks.submit_all_works(adapter, self._client, works)
                    text = result['text']
                else:
                    courses = self._result(self._client.get_my_courses())
                    fn = tasks.export_all_courses if action == 'export_all' else tasks.submit_all_courses
                    result = fn(adapter, self._client, courses, opts) if action == 'export_all' else fn(adapter, self._client, courses)
                    text = result['text']
                with self._lock:
                    job['text'] = text
                    job['status'] = '任务结束，请查看结果'
            except Exception as exc:
                with self._lock:
                    job['error'] = str(exc)
                    job['status'] = '任务失败'
            finally:
                with self._lock:
                    job['done'] = True
        threading.Thread(target=run, daemon=True).start()
        return job['id']

    def choose_files(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True,
                    file_types=('上下文文件 (*.txt;*.md;*.py;*.js;*.ts;*.json;*.csv;*.png;*.jpg;*.jpeg;*.webp)',))
        result = []
        for raw in (paths or [])[:8]:
            path = Path(raw)
            if path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError(f'{path.name} 超过 2 MB，请选取较小文件')
            mime = mimetypes.guess_type(path.name)[0] or ''
            item = {'id': str(uuid.uuid4()), 'name': path.name, 'size': path.stat().st_size}
            if mime in ('image/png', 'image/jpeg', 'image/webp'):
                item['data'] = f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()
            else:
                item['text'] = path.read_text(encoding='utf-8')[:60000]
            result.append(item)
        return result

    def choose_directory(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return paths[0] if paths else None

    def export_chat(self, title, markdown):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.SAVE,
                    save_filename=exporter.clean_name(title) + '.md', file_types=('Markdown (*.md)',))
        if not paths:
            return False
        path = Path(paths if isinstance(paths, str) else paths[0])
        path.write_text(markdown, encoding='utf-8')
        return True
