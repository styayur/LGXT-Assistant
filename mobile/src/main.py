# -*- coding: utf-8 -*-
"""LGXT Assistant · Android (Flet)

移动端实现：登录 / 仪表盘 / 课程 → 作业 → 题目 / 提交成绩 / 设置。
与桌面版共用同一套 API 语义：(ok, data) 返回结构、相同 endpoint 与参数。

说明：Android 无 tkinter/keyring/winsound，故 UI 使用 Flet(Flutter)；
题目导出（docx/pdf）在移动端 v1 未包含，改为复制/分享题目文本。
"""
import os
import threading
import time

import flet as ft
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = os.environ.get('LGXT_API_BASE', 'http://lgxt.wutp.com.cn/api')
TIMEOUT = 8

COLORS = getattr(ft, 'Colors', None) or getattr(ft, 'colors')
ICONS = getattr(ft, 'Icons', None) or getattr(ft, 'icons')

BG = '#080A0D'
SURFACE = '#0F141B'
SURFACE_2 = '#151C25'
FG = '#D7E0EA'
MUTED = '#8B98A5'
DIM = '#5C6672'
PRIMARY = '#34D399'
CYAN = '#22D3EE'
WARN = '#FBBF24'
ERR = '#F87171'


class ApiClient:
    """与桌面版 APIClient 相同的返回结构与错误文案。"""

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(
            total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504],
            allowed_methods=['POST', 'GET']))
        self.session = requests.Session()
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _post(self, endpoint, data=None, fail_msg='请求失败'):
        try:
            r = self.session.post(f'{self.base_url}/{endpoint}', headers=self.headers,
                                  data=data, timeout=TIMEOUT)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            return False, f'网络错误：{e}'
        try:
            result = r.json()
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


def make_page():
    page = ft.Page
    return page


def main(page):
    page.title = 'LGXT Assistant'
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0
    page.window_width = 420
    page.window_height = 900

    api = ApiClient()
    state = {'username': '', 'password': '', 'courses': [], 'works': [],
             'questions': [], 'work': None, 'course': None}

    def ui(fn, *args):
        """后台线程里更新 UI：Flet 允许 handler 在工作线程中修改控件。"""
        try:
            page.run_task(fn, *args)
        except Exception:
            threading.Thread(target=fn, args=args, daemon=True).start()

    def snack(msg, color=CYAN):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=FG), bgcolor=SURFACE_2, show_close_icon=True)
        try:
            page.snack_bar.open = True
        except Exception:
            pass
        page.update()

    def card(content, padding=14, bg=SURFACE):
        return ft.Container(content=content, bgcolor=bg, padding=padding,
                            border_radius=8,
                            border=ft.border.all(1, '#1E2833'),
                            margin=ft.margin.only(bottom=10))

    def loading(text='SYNCING ...'):
        return ft.Column([ft.ProgressRing(width=22, height=22, color=PRIMARY),
                          ft.Text(text, color=MUTED, size=12)],
                         horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=8)
    header = ft.Container(
        content=ft.Row([ft.Text('LGXT::ASSISTANT', color=PRIMARY, weight=ft.FontWeight.BOLD,
                                font_family='monospace'),
                        ft.Text('', color=DIM, size=11)], spacing=10),
        bgcolor='#0D1117', padding=ft.padding.symmetric(12, 14),
        border=ft.border.only(bottom=ft.BorderSide(1, '#1E2833')))
    nav = ft.NavigationBar(
        bgcolor='#0D1117', indicator_color=SURFACE_2,
        destinations=[
            ft.NavigationBarDestination(icon=ICONS.DASHBOARD_OUTLINED, label='仪表盘'),
            ft.NavigationBarDestination(icon=ICONS.SCHOOL_OUTLINED, label='课程'),
            ft.NavigationBarDestination(icon=ICONS.SETTINGS_OUTLINED, label='设置'),
        ], on_change=lambda e: show_tab(int(e.control.selected_index)))

    # ---------------- 登录 ----------------
    user_field = ft.TextField(label='用户名', bgcolor=SURFACE, border_color='#243040',
                              text_size=14, color=FG)
    pass_field = ft.TextField(label='密码', password=True, can_reveal_password=True,
                              bgcolor=SURFACE, border_color='#243040', text_size=14, color=FG)
    remember = ft.Checkbox(label='记住账号密码（保存在本机 App 存储）', value=False, label_style=ft.TextStyle(color=MUTED, size=12))

    def do_login(_e=None):
        if not user_field.value or not pass_field.value:
            snack('请输入用户名和密码', WARN)
            return
        body.controls = [ft.Container(loading('CONNECTING ...'), padding=40)]
        page.update()

        def work():
            ok, msg = api.login(user_field.value.strip(), pass_field.value)
            if ok:
                state['username'] = user_field.value.strip()
                state['password'] = pass_field.value
                try:
                    page.client_storage.set('lgxt.user', state['username'])
                    if remember.value:
                        page.client_storage.set('lgxt.pass', state['password'])
                    else:
                        page.client_storage.remove('lgxt.pass')
                except Exception:
                    pass
                ui(after_login)
            else:
                ui(show_login, msg)

        threading.Thread(target=work, daemon=True).start()

    def show_login(err=''):
        header.content.controls[1].value = 'AUTH'
        controls = [
            ft.Text('AUTHENTICATION', color=PRIMARY, size=20, weight=ft.FontWeight.BOLD,
                    font_family='monospace'),
            ft.Text('输入理工学堂账号以建立会话', color=MUTED, size=12),
            card(ft.Column([user_field, pass_field, remember,
                            ft.ElevatedButton('LOGIN ▸ 登录', on_click=do_login,
                                              bgcolor=PRIMARY, color='#062018',
                                              width=400, height=44)], spacing=12)),
        ]
        if err:
            controls.append(ft.Text(err, color=ERR, size=12))
        body.controls = [ft.Container(ft.Column(controls, spacing=14), padding=20)]
        try:
            user_field.value = page.client_storage.get('lgxt.user') or ''
            pass_field.value = page.client_storage.get('lgxt.pass') or ''
            remember.value = bool(pass_field.value)
        except Exception:
            pass
        page.update()

    # ---------------- 仪表盘 ----------------
    def after_login(_e=None):
        header.content.controls[1].value = 'CONNECTED'
        show_dashboard()

    def show_dashboard():
        body.controls = [ft.Container(loading('LOADING DASHBOARD ...'), padding=40)]
        page.update()

        def work():
            ok, data = api.get_my_courses()
            if not ok:
                ui(snack, data, ERR)
                ui(show_login, data)
                return
            state['courses'] = data
            pending = done = 0
            scores = []
            for course in data:
                cok, works = api.get_course_works(course['courseId'])
                if not cok:
                    continue
                for w in works:
                    grade = w.get('grade')
                    if grade is not None:
                        done += 1
                        try:
                            scores.append(float(grade))
                        except (TypeError, ValueError):
                            pass
                    elif max(0, w.get('tryTimes', 0) - w.get('times', 0)) > 0:
                        pending += 1
            avg = sum(scores) / len(scores) if scores else 0
            ui(render_dashboard, pending, done, avg, len(data))

        threading.Thread(target=work, daemon=True).start()

    def render_dashboard(pending, done, avg, courses):
        def stat(title, value, color):
            return ft.Container(
                content=ft.Column([ft.Text(title, color=DIM, size=11, font_family='monospace'),
                                   ft.Text(str(value), color=color, size=30,
                                           weight=ft.FontWeight.BOLD, font_family='monospace')],
                                  spacing=4),
                bgcolor=SURFACE, padding=14, border_radius=8, expand=True,
                border=ft.border.all(1, '#1E2833'))
        body.controls = [
            ft.Container(ft.Column([
                ft.Text('DASHBOARD', color=FG, size=20, weight=ft.FontWeight.BOLD,
                        font_family='monospace'),
                ft.Text(f'{courses} 门课程 · 数据来自服务器实时统计', color=MUTED, size=12),
                ft.Row([stat('待激活 PENDING', pending, WARN),
                        stat('已完成 DONE', done, CYAN),
                        stat('平均分 AVG', f'{avg:.1f}', PRIMARY)], spacing=10),
                ft.Row([ft.ElevatedButton('REFRESH', on_click=lambda e: show_dashboard(),
                                          bgcolor=SURFACE_2, color=FG)], spacing=10),
                ft.Text('提示：单击底部「课程」进入课程列表', color=DIM, size=11),
            ], spacing=12), padding=16),
        ]
        page.update()

    # ---------------- 课程 / 作业 / 题目 ----------------
    def show_courses():
        header.content.controls[1].value = 'COURSES'
        body.controls = [ft.Container(loading('LOADING COURSES ...'), padding=40)]
        page.update()

        def work():
            ok, data = api.get_my_courses()
            if not ok:
                ui(render_courses, None, data)
            else:
                state['courses'] = data
                ui(render_courses, data, '')

        threading.Thread(target=work, daemon=True).start()

    def render_courses(courses, err):
        controls = [ft.Text('COURSES', color=FG, size=20, weight=ft.FontWeight.BOLD,
                            font_family='monospace')]
        if err:
            controls.append(ft.Text(err, color=ERR, size=12))
        if courses:
            for course in courses:
                def open_course(_e, c=course):
                    open_course_works(c)
                controls.append(card(ft.Row([
                    ft.Column([ft.Text(course.get('courseName', ''), color=FG, size=15),
                               ft.Text(f"#{course.get('courseId')}", color=DIM, size=11,
                                       font_family='monospace')], spacing=2, expand=True),
                    ft.IconButton(icon=ICONS.CHEVRON_RIGHT, icon_color=CYAN,
                                  on_click=open_course),
                ])))
        elif not err:
            controls.append(ft.Text('没有课程数据', color=MUTED, size=13))
        body.controls = [ft.Container(ft.Column(controls, spacing=8), padding=16)]
        page.update()

    def open_course_works(course):
        state['course'] = course
        header.content.controls[1].value = course.get('courseName', '')
        body.controls = [ft.Container(loading('LOADING WORKS ...'), padding=40)]
        page.update()

        def work():
            ok, data = api.get_course_works(course['courseId'])
            if not ok:
                ui(snack, data, ERR)
                ui(show_courses)
                return
            state['works'] = data
            ui(render_works, data)

        threading.Thread(target=work, daemon=True).start()

    def render_works(works):
        controls = [ft.Row([ft.IconButton(icon=ICONS.ARROW_BACK, icon_color=CYAN,
                                          on_click=lambda e: show_courses()),
                            ft.Text('ASSIGNMENTS', color=FG, size=18,
                                    weight=ft.FontWeight.BOLD, font_family='monospace')], spacing=4)]
        if not works:
            controls.append(ft.Text('该课程暂无作业', color=MUTED, size=13))
        for work in works:
            grade = work.get('grade')
            remaining = max(0, work.get('tryTimes', 0) - work.get('times', 0))
            if grade is not None:
                status, color = f'DONE · {grade}', CYAN
            elif remaining <= 0:
                status, color = 'EXHAUSTED', ERR
            elif remaining == 1:
                status, color = 'LAST CHANCE', WARN
            else:
                status, color = f'TRY {remaining}/{work.get("tryTimes", 0)}', PRIMARY
            controls.append(card(ft.Column([
                ft.Text(work.get('workName', ''), color=FG, size=14),
                ft.Text(f"{status}   ·   DUE {work.get('expireTime', 'N/A')}", color=color,
                        size=11, font_family='monospace'),
                ft.Row([ft.ElevatedButton('查看题目', bgcolor=PRIMARY, color='#062018',
                                          on_click=lambda e, w=work: open_questions(w))], spacing=8),
            ], spacing=6)))
        body.controls = [ft.Container(ft.Column(controls, spacing=8), padding=16)]
        page.update()

    def open_questions(work):
        state['work'] = work
        header.content.controls[1].value = work.get('workName', '')
        body.controls = [ft.Container(loading('LOADING QUESTIONS ...'), padding=40)]
        page.update()

        def fetch():
            ok, data = api.get_questions(work['workId'])
            if not ok:
                ui(snack, data, ERR)
                ui(render_works, state['works'])
                return
            state['questions'] = data
            ui(render_questions, data)

        threading.Thread(target=fetch, daemon=True).start()

    def render_questions(questions):
        controls = [ft.Row([ft.IconButton(icon=ICONS.ARROW_BACK, icon_color=CYAN,
                                          on_click=lambda e: render_works(state['works'])),
                            ft.Text(f'QUESTIONS · {len(questions)}', color=FG, size=18,
                                    weight=ft.FontWeight.BOLD, font_family='monospace')], spacing=4)]
        for idx, q in enumerate(questions):
            img = (ft.Image(src=q.get('imgurl'), height=180, fit=ft.ImageFit.CONTAIN)
                   if q.get('imgurl') and q.get('imgurl') != 'N/A' else
                   ft.Text('[ NO IMAGE ]', color=DIM, size=11, font_family='monospace'))
            controls.append(card(ft.Column([
                ft.Text(f"Q{idx + 1} · {q.get('name', 'N/A')}", color=FG, size=14),
                ft.Text(f"ID {q.get('id', 'N/A')}", color=DIM, size=11, font_family='monospace'),
                img,
                ft.Text(f"答案：{q.get('answer', 'N/A')}", color=WARN, size=12),
            ], spacing=6)))

        grade_field = ft.TextField(label='成绩 0-100', value='100', width=140,
                                   bgcolor=SURFACE, border_color='#243040', color=FG)

        def submit(_e):
            value = (grade_field.value or '').strip()
            if not (value.isdigit() and 0 <= int(value) <= 100):
                snack('请输入 0-100 的成绩', WARN)
                return

            def work():
                ok, msg = api.submit_answer(state['work']['workId'], value)
                ui(snack, msg, PRIMARY if ok else ERR)

            threading.Thread(target=work, daemon=True).start()

        controls.append(card(ft.Row([grade_field,
                                     ft.ElevatedButton('SUBMIT', bgcolor=PRIMARY, color='#062018',
                                                       on_click=submit)], spacing=10)))
        body.controls = [ft.Container(ft.Column(controls, spacing=8), padding=16)]
        page.update()

    # ---------------- 设置 ----------------
    def show_settings():
        header.content.controls[1].value = 'SETTINGS'

        def logout(_e):
            state.update({'username': '', 'password': ''})
            try:
                page.client_storage.remove('lgxt.pass')
            except Exception:
                pass
            show_login()

        body.controls = [ft.Container(ft.Column([
            ft.Text('SETTINGS', color=FG, size=20, weight=ft.FontWeight.BOLD,
                    font_family='monospace'),
            card(ft.Column([
                ft.Text('SYSTEM', color=DIM, size=11, font_family='monospace'),
                ft.Text(f'API  {BASE_URL}', color=MUTED, size=12, selectable=True),
                ft.Text('VERSION  3.1.0-android', color=MUTED, size=12),
                ft.Text('LICENSE  GPL-3.0-or-later · Styayur', color=MUTED, size=12),
                ft.Text('AUTH  ' + ('token' if state['username'] else 'none'),
                        color=MUTED, size=12),
            ], spacing=6)),
            card(ft.Column([
                ft.Text('说明', color=DIM, size=11, font_family='monospace'),
                ft.Text('Android 版支持：登录、仪表盘统计、课程/作业/题目浏览、'
                        '图片查看与成绩提交。', color=MUTED, size=12),
                ft.Text('题目导出（Word/PDF）请在桌面版使用；移动端 v1 未包含。',
                        color=MUTED, size=12),
            ], spacing=6)),
            ft.ElevatedButton('LOGOUT', bgcolor=SURFACE_2, color=FG, on_click=logout),
        ], spacing=12), padding=16)]
        page.update()

    def show_tab(index):
        nav.selected_index = index
        if index == 0:
            show_dashboard()
        elif index == 1:
            show_courses()
        else:
            show_settings()

    # ---------------- 启动 ----------------
    root = ft.Column([header, ft.Container(body, expand=True, padding=0), nav], expand=True,
                     spacing=0)
    page.add(root)
    show_login()


run = getattr(ft, 'run', None) or getattr(ft, 'app', None)
if __name__ == '__main__':
    run(main)
