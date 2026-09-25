"""Local, authenticated browser transport for the Windows application."""
import argparse
import json
import mimetypes
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from desktop.bridge import Bridge


METHODS = frozenset('bootstrap credential_status save_settings remove_key test_model '
                    'conversation save_conversation delete_conversation save_prompts '
                    'save_workspace login cancel_login logout courses dashboard works '
                    'questions question_image submit_grade user_info start_chat poll_job '
                    'stop_chat start_task'.split())
MAX_BODY = 24 * 1024 * 1024


class BrowserServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, root, bridge=None, port=0):
        self.root = Path(root).resolve()
        self.bridge = bridge if bridge is not None else Bridge()
        self.token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = f'http://127.0.0.1:{self.server_port}'

    @property
    def launch_url(self):
        return self.origin + '/#token=' + self.token


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        # Never log credential-bearing request URLs or bodies.
        pass

    def send(self, status, data, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get('Host') == self.server.origin.removeprefix('http://')

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, b'{}')
        name = unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
        path = (self.server.root / name).resolve()
        if not path.is_relative_to(self.server.root) or not path.is_file():
            return self.send(404, b'{}')
        data = path.read_bytes()
        if name == 'index.html':
            data = data.replace(b'<html ', b'<html data-browser="true" ')
        mime = {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html'}.get(
            path.suffix, mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send(200, data, mime)

    def do_POST(self):
        if (not self.valid_host() or self.headers.get('Origin') != self.server.origin
                or not secrets.compare_digest(self.headers.get('X-LGXT-Token', ''), self.server.token)):
            return self.send(403, b'{"error":"Unauthorized"}')
        if self.path != '/api/call':
            return self.send(404, b'{}')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size <= 0 or size > MAX_BODY:
                return self.send(413, b'{"error":"Request too large"}')
            payload = json.loads(self.rfile.read(size))
            method, args = payload['method'], payload.get('args', [])
            if method not in METHODS or not isinstance(args, list):
                raise ValueError('不支持的操作')
            result = getattr(self.server.bridge, method)(*args)
            self.send(200, json.dumps({'result': result}, ensure_ascii=False).encode())
        except Exception as exc:
            self.send(400, json.dumps({'error': str(exc)}, ensure_ascii=False).encode())


def main():
    parser = argparse.ArgumentParser(description='LGXT Assistant Windows 网页版')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    root = base / 'frontend' / 'dist'
    if not (root / 'index.html').is_file():
        raise SystemExit('缺少网页资源，请先在 frontend 运行 npm ci 和 npm run build。')
    with BrowserServer(root, port=args.port) as server:
        print('LGXT Assistant Windows 网页版\n请保留此窗口；退出请按 Ctrl+C。', flush=True)
        print('如果浏览器没有打开，请复制此本机链接（不要分享）：\n' + server.launch_url, flush=True)
        if not args.no_browser:
            webbrowser.open(server.launch_url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
