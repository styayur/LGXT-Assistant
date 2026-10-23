"""LGXT transport: finite read retries, no automatic write replay."""
import io
from collections import OrderedDict
import ipaddress
import os
import secrets
import socket
import threading
import time
import warnings
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter

# The official HTTP endpoint responds; HTTPS could not be verified. Fail closed.
BASE_URL = os.environ.get('LGXT_API_BASE', 'http://lgxt.wutp.com.cn/api')
TIMEOUT = (5, 10)
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
INSECURE_WARNING = '不安全兼容模式：账号、密码、题目和成绩通过明文 HTTP 传输，可能被窃取或篡改；不会保存登录凭据。'
READ_ENDPOINTS = frozenset(('userInfo', 'myCourses', 'myCourseWorks', 'showQuestions'))
TRANSIENT = frozenset((429, 500, 502, 503, 504))


def validate_image(data):
    from PIL import Image
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError('图片为空或超过 8 MB')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('PNG', 'JPEG', 'WEBP'):
                    raise ValueError('仅支持 PNG、JPEG、WebP 图片')
                if image.width * image.height > MAX_IMAGE_PIXELS or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('图片像素或帧数超过限制')
                mime = Image.MIME[image.format]
                image.verify()
        return mime
    except Exception as exc:
        raise ValueError('图片格式无效或超过解码限制') from exc


class APIClient:
    def __init__(self, base_url=BASE_URL, *, allow_insecure=False, retries=2):
        parsed = urlsplit(base_url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError('无效的平台 API 地址')
        default_port = 80 if parsed.scheme == 'http' else 443
        if parsed.port is not None:
            if parsed.port != default_port:
                raise ValueError('不支持的平台端口')
        self.base_url = base_url.rstrip('/')
        self.allow_insecure = bool(allow_insecure)
        self.insecure = parsed.scheme == 'http'
        self.retries = max(0, min(3, int(retries)))
        self.headers = {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
        self.session = requests.Session()
        self.session.trust_env = False
        adapter = HTTPAdapter(pool_connections=2, pool_maxsize=2, max_retries=0)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self._lock = threading.RLock()
        self._cache = {}
        self._image_cache = OrderedDict()

    def logout(self):
        with self._lock:
            self.headers.pop('Authorization', None)
            self.session.headers.pop('Authorization', None)
            self.session.cookies.clear()
            self._cache.clear()
            self._image_cache.clear()

    def _delay(self, attempt, response=None):
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timezone
        delay = min(4, 0.25 * 2 ** attempt + secrets.SystemRandom().uniform(0, 0.25))
        if response is not None:
            value = response.headers.get('Retry-After', '')
            try:
                seconds = float(value)
            except (ValueError, TypeError):
                try:
                    seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    seconds = 0
            if seconds > 10:
                return False  # Never retry earlier than a long Retry-After.
            delay = max(delay, seconds)
        time.sleep(delay)
        return True

    def _post(self, endpoint, data=None, fail_msg='请求失败'):
        if self.insecure and not self.allow_insecure:
            return False, '已阻止明文 HTTP。平台 HTTPS 尚未验证；请阅读风险并明确启用不安全兼容模式。'
        readonly = endpoint in READ_ENDPOINTS
        key = (endpoint, repr(data))
        with self._lock:
            cached = self._cache.get(key)
            if readonly and endpoint != 'showQuestions' and cached and cached[0] > time.monotonic():
                return cached[1]
            for attempt in range((self.retries if readonly else 0) + 1):
                response = None
                try:
                    response = self.session.post(self.base_url + '/' + endpoint, headers=self.headers,
                                                 data=data, timeout=TIMEOUT, allow_redirects=False)
                    status = response.status_code
                    if readonly and status in TRANSIENT and attempt < self.retries:
                        if self._delay(attempt, response):
                            continue
                    if endpoint == 'submitAnswer' and (status >= 500 or 300 <= status < 400):
                        return False, '结果待核实：服务器未给出可靠确认；请在平台检查，勿直接重试。'
                    if 300 <= status < 400:
                        return False, '已阻止平台重定向，请检查 API 配置'
                    response.raise_for_status()
                    result = response.json()
                except requests.exceptions.RequestException:
                    if response is not None and 400 <= response.status_code < 500:
                        return False, f'{fail_msg}：HTTP {response.status_code}（未自动重试）'
                    if readonly and attempt < self.retries and self._delay(attempt):
                        continue
                    if endpoint == 'submitAnswer':
                        return False, '结果待核实：连接中断或超时，服务器可能已提交；请在平台检查。'
                    return False, '网络错误：连接失败或超时，请检查网络与 TLS 证书'
                except ValueError:
                    return False, ('结果待核实：服务器返回非 JSON 响应' if endpoint == 'submitAnswer'
                                   else fail_msg + '：服务器返回了非 JSON 响应')
                finally:
                    if response is not None:
                        response.close()
                if not isinstance(result, dict) or 'code' not in result:
                    return False, ('结果待核实：响应缺少必要字段' if endpoint == 'submitAnswer'
                                   else fail_msg + '：响应缺少必要字段')
                if result['code'] == 0 and 'data' in result:
                    answer = (True, result['data'])
                    if readonly and endpoint != 'showQuestions':
                        self._cache[key] = (time.monotonic() + 10, answer)
                    return answer
                return False, fail_msg + '：平台拒绝请求，请检查账号或作业状态'

    def login(self, username, password):
        self.logout()
        ok, data = self._post('login', {'loginName': username, 'password': password}, '登录失败')
        if ok and isinstance(data, str) and data:
            self.headers['Authorization'] = data
            return True, '欢迎回来！'
        return False, data if not ok else '登录失败：无效的登录响应'

    def get_user_info(self):
        return self._post('userInfo', fail_msg='获取用户信息失败')

    def get_my_courses(self):
        return self._post('myCourses', fail_msg='获取课程列表失败')

    def get_course_works(self, course_id):
        return self._post('myCourseWorks', {'courseId': course_id}, '获取课程作业失败')

    def get_questions(self, work_id):
        return self._post('showQuestions', {'workId': work_id}, '获取题目失败')

    def submit_answer(self, work_id, grade):
        if not str(grade).isdigit() or not 0 <= int(grade) <= 100:
            return False, '成绩必须是 0–100 的整数'
        with self._lock:
            self._cache.clear()
            ok, data = self._post('submitAnswer', {'grade': grade, 'workId': work_id}, '答案提交失败')
        if ok:
            return True, f'平台已确认提交，成绩：{grade}；未独立核验最终成绩。'
        return False, data

    def _image_url(self, url):
        try:
            parsed, origin = urlsplit(url), urlsplit(self.base_url)
            if (parsed.scheme not in ('http', 'https') or parsed.hostname != origin.hostname
                    or parsed.username or parsed.password or parsed.fragment
                    or (parsed.port is not None and parsed.port not in (80, 443))
                    or (parsed.scheme == 'http' and not self.allow_insecure)):
                raise ValueError()
            default_port = 443 if parsed.scheme == 'https' else 80
            if parsed.port is not None:
                if parsed.port != default_port:
                    raise ValueError()
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                raise ValueError()
        except (ValueError, OSError):
            raise ValueError('已阻止不受信任的图片地址（仅允许平台同源公共地址）') from None

    def fetch_image(self, url):
        # Four verified images, max 32 MB, shared by simultaneous UI consumers.
        with self._lock:
            cached = self._image_cache.get(url)
            if cached and cached[0] > time.monotonic():
                self._image_cache.move_to_end(url)
                return cached[1]
            raw = self._fetch_image(url)
            self._image_cache[url] = (time.monotonic() + 60, raw)
            self._image_cache.move_to_end(url)
            while len(self._image_cache) > 4:
                self._image_cache.popitem(last=False)
            return raw

    def _fetch_image(self, url):
        self._image_url(url)
        # Isolated session: no Authorization, cookies, netrc or ambient proxy.
        with requests.Session() as images:
            images.trust_env = False
            for attempt in range(self.retries + 1):
                try:
                    with images.get(url, timeout=TIMEOUT, stream=True, allow_redirects=False) as response:
                        if response.status_code in TRANSIENT and attempt < self.retries and self._delay(attempt, response):
                            continue
                        if 300 <= response.status_code < 400:
                            raise ValueError('已阻止图片重定向')
                        response.raise_for_status()
                        if response.headers.get('Content-Type', '').split(';')[0].lower() not in ('image/png', 'image/jpeg', 'image/webp'):
                            raise ValueError('响应不是支持的图片')
                        if int(response.headers.get('Content-Length', '0')) > MAX_IMAGE_BYTES:
                            raise ValueError('图片超过 8 MB')
                        data = bytearray()
                        for block in response.iter_content(64 * 1024):
                            data.extend(block)
                            if len(data) > MAX_IMAGE_BYTES:
                                raise ValueError('图片超过 8 MB')
                        validate_image(data)
                        return bytes(data)
                except requests.exceptions.RequestException:
                    if attempt == self.retries:
                        raise ValueError('图片下载失败，请检查网络与证书') from None
                    self._delay(attempt)


client = APIClient()
