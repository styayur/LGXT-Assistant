# -*- coding: utf-8 -*-
"""API 客户端：统一的 session / 超时 / 错误处理 / 鉴权。返回 (ok, data)。"""
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = os.environ.get('LGXT_API_BASE', 'http://lgxt.wutp.com.cn/api')
TIMEOUT = 5
MAX_IMAGE_BYTES = 8 * 1024 * 1024   # 单张题目图片上限


class APIClient:
    """理工学堂平台 API 客户端。UI / 任务 / 导出共享同一个实例。"""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=Retry(
            total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504],
            allowed_methods=['POST', 'GET']))
        self.session = requests.Session()
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _post(self, endpoint, data=None, fail_msg='请求失败'):
        try:
            response = self.session.post(f'{self.base_url}/{endpoint}', headers=self.headers,
                                         data=data, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return False, f'网络错误：{e}'
        try:
            result = response.json()
        except ValueError:
            return False, f'{fail_msg}：服务器返回了非 JSON 响应'
        try:
            if result['code'] == 0:
                return True, result['data']
            return False, f'{fail_msg}：{result["msg"]}'
        except KeyError:
            return False, f'{fail_msg}：响应缺少必要字段'

    def login(self, username, password):
        ok, data = self._post('login', {'loginName': username, 'password': password}, '登录失败')
        if ok:
            self.headers['Authorization'] = data
            self.session.headers.update({'Authorization': data})
            return True, '欢迎回来！'
        return False, data

    def get_user_info(self):
        return self._post('userInfo', fail_msg='获取用户信息失败')

    def get_my_courses(self):
        return self._post('myCourses', fail_msg='获取课程列表失败')

    def get_course_works(self, course_id):
        return self._post('myCourseWorks', {'courseId': course_id}, '获取课程作业失败')

    def get_questions(self, work_id):
        return self._post('showQuestions', {'workId': work_id}, '获取题目失败')

    def submit_answer(self, work_id, grade):
        ok, data = self._post('submitAnswer', {'grade': grade, 'workId': work_id}, '答案提交失败')
        if ok:
            return True, f'答案提交成功，成绩：{grade}\n返回信息：{data}'
        return False, data

    def fetch_image(self, url):
        """下载图片字节；做基础校验，失败抛异常由调用方呈现为 IMAGE ERROR。"""
        response = self.session.get(url, headers=self.headers, timeout=TIMEOUT)
        response.raise_for_status()
        ctype = response.headers.get('Content-Type', '')
        if ctype and not ctype.lower().startswith('image/'):
            raise ValueError(f'响应不是图片（{ctype}）')
        data = response.content
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError(f'图片过大（{len(data)} bytes）')
        if not data:
            raise ValueError('图片内容为空')
        return data


# 默认实例：全应用共享（登录态/会话集中于此处）
client = APIClient()
