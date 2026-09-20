# -*- coding: utf-8 -*-
"""LGXT Assistant · Android (Flet)

移动端 v3.2.0：
- SafeArea 顶栏：不遮挡系统状态栏/刘海，顶栏加高、触控友好
- 视图栈导航：手机返回键返回上一级菜单；在根级菜单双击返回才退出
- 与桌面版共用同一套 API 语义（相同 endpoint/参数与 (ok, data) 结构）
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
LOGIN_TIMEOUT = 20
APP_VERSION = '3.2.1'

COLORS = getattr(ft, 'Colors', None) or getattr(ft, 'colors')
ICONS = getattr(ft, 'Icons', None) or getattr(ft, 'icons')

BG = '#080A0D'
SURFACE = '#0F141B'
SURFACE_2 = '#151C25'
LINE = '#1E2833'
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
            total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504],
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


def main(page):
    page.title = 'LGXT Assistant'
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    api = ApiClient()
    state = {'username': '', 'password': '', 'courses': [], 'works': [],
             'questions': [], 'course': None, 'work': None}
    last_back = {'at': 0.0}

    def snack(msg, color=CYAN):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=FG), bgcolor=SURFACE_2,
            behavior=ft.SnackBarBehavior.FLOATING, show_close_icon=True)
        page.snack_bar.open = True
        page.update()

    def ui(fn, *args, **kwargs):
        """从后台线程安全更新 UI。

        Flet 允许从任意线程调用控件方法与 page.update()；
        注意：不能用 ui(同步函数)（Flet 断言只接受协程函数，
        会抛 AssertionError 并导致界面停在 CONNECTING）。
        """
        try:
            fn(*args, **kwargs)
        except Exception as exc:      # 兜底：任何 UI 异常都不能让界面卡死
            print('ui error:', exc, flush=True)
            try:
                page.update()
            except Exception:
                pass

    def card(content, padding=14, bg=SURFACE):
        return ft.Container(
            content=content, bgcolor=bg, padding=padding, border_radius=8,
            border=ft.border.all(1, LINE), margin=ft.margin.only(bottom=10))

    def loading(text='SYNCING ...'):
        return ft.Column([ft.ProgressRing(width=22, height=22, color=PRIMARY),
                          ft.Text(text, color=MUTED, size=12)],
                         horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    def exit_app():
        for fn in ('window_destroy', 'window_close'):
            try:
                getattr(page, fn)()
                return
            except Exception:
                continue
        os._exit(0)

    def pop_view(_e=None):
        """返回上一级菜单；根级菜单双击返回才退出。"""
        if len(page.views) > 1:
            page.views.pop()
            page.update()
            return
        now = time.time()
        if now - last_back['at'] < 2.0:
            exit_app()
        else:
            last_back['at'] = now
            snack('再按一次返回退出应用', WARN)

    page.on_view_pop = pop_view

    def make_view(route, title, subtitle, controls, show_nav=False, show_back=False,
                  on_back=None, nav_index=0):
        def back_click(_e=None):
            if on_back:
                on_back()
            else:
                pop_view()

        header_left = []
        if show_back:
            header_left.append(ft.IconButton(icon=ICONS.ARROW_BACK, icon_color=CYAN,
                                             icon_size=26, on_click=back_click))
        header_left.append(ft.Column([
            ft.Text('LGXT::ASSISTANT', color=PRIMARY, size=13,
                    weight=ft.FontWeight.BOLD, font_family='monospace'),
            ft.Text(title, color=FG, size=17, weight=ft.FontWeight.BOLD),
            ft.Text(subtitle, color=DIM, size=11) if subtitle else ft.Container(height=0),
        ], spacing=1, expand=True))

        header = ft.Container(
            content=ft.Row(header_left, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor='#0D1117', padding=ft.padding.only(left=8, right=16, top=10, bottom=12),
            border=ft.border.only(bottom=ft.BorderSide(1, LINE)))

        column_controls = [header, ft.Container(ft.Column(controls, scroll=ft.ScrollMode.AUTO,
                                                          spacing=10, expand=True),
                                                expand=True, padding=ft.padding.only(
                                                    left=16, right=16, top=14, bottom=14))]
        nav = None
        if show_nav:
            nav = ft.NavigationBar(
                selected_index=nav_index, bgcolor='#0D1117', indicator_color=SURFACE_2,
                destinations=[
                    ft.NavigationBarDestination(icon=ICONS.DASHBOARD_OUTLINED, label='仪表盘'),
                    ft.NavigationBarDestination(icon=ICONS.SCHOOL_OUTLINED, label='课程'),
                    ft.NavigationBarDestination(icon=ICONS.SETTINGS_OUTLINED, label='设置'),
                ], on_change=lambda e: switch_tab(int(e.control.selected_index)))
            column_controls.append(nav)

        body = ft.Column(column_controls, spacing=0, expand=True)
        # SafeArea：自动避让手机状态栏/刘海，顶栏不会被遮挡
        safe = ft.SafeArea(content=body, expand=True)
        return ft.View(route=route, controls=[safe], padding=0, bgcolor=BG)

    def show(view):
        """根级切换：清空视图栈，仅保留当前根视图。"""
        page.views.clear()
        page.views.append(view)
        page.update()

    def push(view):
        """进入下一级：压栈，手机返回键可回到上一级。"""
        page.views.append(view)
        page.update()

    def switch_tab(index):
        if index == 0:
            show_dashboard()
        elif index == 1:
            show_courses()
        else:
            show_settings()

    def back_to(route):
        """返回到栈中最近的指定 route（不存在则回根菜单）。"""
        for i in range(len(page.views) - 1, -1, -1):
            if page.views[i].route == route:
                del page.views[i + 1:]
                page.update()
                return
        pop_view()

    # ---------------- 登录 ----------------
    user_field = ft.TextField(label='用户名', bgcolor=SURFACE, border_color='#243040',
                              text_size=15, color=FG, height=56)
    pass_field = ft.TextField(label='密码', password=True, can_reveal_password=True,
                              bgcolor=SURFACE, border_color='#243040', text_size=15,
                              color=FG, height=56)
    remember = ft.Checkbox(label='记住账号密码（保存在本机 App 存储）', value=False,
                           label_style=ft.TextStyle(color=MUTED, size=12))

    def show_login(err=''):
        try:
            if not user_field.value:
                user_field.value = page.client_storage.get('lgxt.user') or ''
            if not pass_field.value:
                saved = page.client_storage.get('lgxt.pass') or ''
                pass_field.value = saved
                remember.value = bool(saved)
        except Exception:
            pass
        controls = [
            ft.Text('AUTHENTICATION', color=PRIMARY, size=22, weight=ft.FontWeight.BOLD,
                    font_family='monospace'),
            ft.Text('输入理工学堂账号以建立会话', color=MUTED, size=13),
            card(ft.Column([user_field, pass_field, remember,
                            ft.ElevatedButton('LOGIN ▸ 登录', on_click=do_login,
                                              bgcolor=PRIMARY, color='#062018',
                                              height=52)], spacing=14)),
            ft.Text(err, color=ERR, size=12) if err else ft.Container(height=0),
        ]
        show(make_view('/login', '登录', 'AUTH · 建立会话', controls))

    def do_login(_e=None):
        if state.get('login_pending'):
            return
        if not user_field.value or not pass_field.value:
            snack('请输入用户名和密码', WARN)
            return
        state['login_pending'] = True
        state['login_started'] = time.time()
        connecting = [
            loading('CONNECTING ...'),
            ft.Text('正在连接理工学堂服务器，请稍候', color=MUTED, size=12),
            ft.Row([
                ft.ElevatedButton('取消', bgcolor=SURFACE_2, color=FG,
                                  on_click=lambda e: cancel_login()),
                ft.ElevatedButton('重试', bgcolor=PRIMARY, color='#062018',
                                  on_click=lambda e: (cancel_login(), do_login())),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ]
        show(make_view('/login', '登录', 'CONNECTING ...', connecting))
        username = user_field.value.strip()
        password = pass_field.value

        def work():
            try:
                ok, msg = api.login(username, password)
            except Exception as exc:              # 理论不会发生，兜底
                ok, msg = False, f'登录异常：{exc}'
            if not state.get('login_pending'):
                return                            # 用户已取消
            state['login_pending'] = False
            if ok:
                state['username'] = username
                state['password'] = password
                try:
                    page.client_storage.set('lgxt.user', username)
                    if remember.value:
                        page.client_storage.set('lgxt.pass', password)
                    else:
                        page.client_storage.remove('lgxt.pass')
                except Exception:
                    pass
                ui(show_dashboard)
            else:
                ui(show_login, msg)

        threading.Thread(target=work, daemon=True).start()

        def watchdog():
            time.sleep(LOGIN_TIMEOUT)
            if state.get('login_pending'):
                state['login_pending'] = False
                ui(show_login, f'登录超时（{LOGIN_TIMEOUT}s）：请检查网络或服务器状态后重试')

        threading.Thread(target=watchdog, daemon=True).start()

    def cancel_login():
        state['login_pending'] = False

    # ---------------- 仪表盘 ----------------
    def show_dashboard():
        show(make_view('/dashboard', '仪表盘', 'DASHBOARD · 作业完成度',
                       [loading('LOADING DASHBOARD ...')], show_nav=True, nav_index=0))

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
                border=ft.border.all(1, LINE))
        controls = [
            ft.Text(f'{courses} 门课程 · 数据来自服务器实时统计', color=MUTED, size=12),
            ft.Row([stat('待激活', pending, WARN), stat('已完成', done, CYAN),
                    stat('平均分', f'{avg:.1f}', PRIMARY)], spacing=10),
            ft.ElevatedButton('REFRESH', on_click=lambda e: show_dashboard(),
                              bgcolor=SURFACE_2, color=FG, height=48),
            ft.Text('提示：底部「课程」可进入课程 → 作业 → 题目', color=DIM, size=11),
        ]
        show(make_view('/dashboard', '仪表盘', 'DASHBOARD · 作业完成度', controls,
                       show_nav=True, nav_index=0))

    # ---------------- 课程 ----------------
    def show_courses():
        show(make_view('/courses', '课程', 'COURSES · 选择科目',
                       [loading('LOADING COURSES ...')], show_nav=True, nav_index=1))

        def work():
            ok, data = api.get_my_courses()
            if ok:
                state['courses'] = data
                ui(render_courses, data, '')
            else:
                ui(render_courses, [], data)

        threading.Thread(target=work, daemon=True).start()

    def render_courses(courses, err):
        controls = []
        if err:
            controls.append(ft.Text(err, color=ERR, size=12))
        for course in courses:
            controls.append(card(ft.Row([
                ft.Column([ft.Text(course.get('courseName', ''), color=FG, size=16),
                           ft.Text(f"#{course.get('courseId')}", color=DIM, size=11,
                                   font_family='monospace')], spacing=2, expand=True),
                ft.IconButton(icon=ICONS.CHEVRON_RIGHT, icon_color=CYAN, icon_size=26,
                              on_click=lambda e, c=course: open_course_works(c)),
            ])))
        if not courses and not err:
            controls.append(ft.Text('没有课程数据', color=MUTED, size=13))
        show(make_view('/courses', '课程', 'COURSES · 选择科目', controls,
                       show_nav=True, nav_index=1))

    def open_course_works(course):
        state['course'] = course
        push(make_view('/works', course.get('courseName', ''), 'ASSIGNMENTS · 作业列表',
                       [loading('LOADING WORKS ...')], show_back=True,
                       on_back=lambda: back_to('/courses')))

        def work():
            ok, data = api.get_course_works(course['courseId'])
            if not ok:
                ui(snack, data, ERR)
                ui(back_to, '/courses')
                return
            state['works'] = data
            ui(render_works, data)

        threading.Thread(target=work, daemon=True).start()

    def render_works(works):
        controls = []
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
                ft.Text(work.get('workName', ''), color=FG, size=15),
                ft.Text(f"{status} · DUE {work.get('expireTime', 'N/A')}", color=color,
                        size=11, font_family='monospace'),
                ft.ElevatedButton('查看题目', bgcolor=PRIMARY, color='#062018', height=46,
                                  on_click=lambda e, w=work: open_questions(w)),
            ], spacing=8)))
        push(make_view('/works', state['course'].get('courseName', ''),
                       'ASSIGNMENTS · 作业列表', controls, show_back=True,
                       on_back=lambda: back_to('/courses')))

    def open_questions(work):
        state['work'] = work
        push(make_view('/questions', work.get('workName', ''), 'QUESTIONS · 题目',
                       [loading('LOADING QUESTIONS ...')], show_back=True,
                       on_back=lambda: back_to('/works')))

        def work_fn():
            ok, data = api.get_questions(work['workId'])
            if not ok:
                ui(snack, data, ERR)
                ui(back_to, '/works')
                return
            state['questions'] = data
            ui(render_questions, data)

        threading.Thread(target=work_fn, daemon=True).start()

    def render_questions(questions):
        controls = [ft.Text(f'共 {len(questions)} 题', color=MUTED, size=12)]
        for idx, q in enumerate(questions):
            img = (ft.Image(src=q.get('imgurl'), height=190, fit=ft.ImageFit.CONTAIN)
                   if q.get('imgurl') and q.get('imgurl') != 'N/A' else
                   ft.Text('[ NO IMAGE ]', color=DIM, size=11, font_family='monospace'))
            controls.append(card(ft.Column([
                ft.Text(f"Q{idx + 1} · {q.get('name', 'N/A')}", color=FG, size=15),
                ft.Text(f"ID {q.get('id', 'N/A')}", color=DIM, size=11, font_family='monospace'),
                img,
                ft.Text(f"答案：{q.get('answer', 'N/A')}", color=WARN, size=13),
            ], spacing=8)))

        grade_field = ft.TextField(label='成绩 0-100', value='100', width=150, height=52,
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
                                     ft.ElevatedButton('SUBMIT', bgcolor=PRIMARY,
                                                       color='#062018', height=52,
                                                       on_click=submit)], spacing=12)))
        push(make_view('/questions', state['work'].get('workName', ''), 'QUESTIONS · 题目',
                       controls, show_back=True, on_back=lambda: back_to('/works')))

    # ---------------- 设置 ----------------
    def show_settings():
        def logout(_e):
            state.update({'username': '', 'password': ''})
            try:
                page.client_storage.remove('lgxt.pass')
            except Exception:
                pass
            show_login()

        controls = [
            card(ft.Column([
                ft.Text('SYSTEM', color=DIM, size=11, font_family='monospace'),
                ft.Text(f'API  {BASE_URL}', color=MUTED, size=12, selectable=True),
                ft.Text(f'VERSION  {APP_VERSION}-android', color=MUTED, size=12),
                ft.Text('LICENSE  GPL-3.0-or-later · Styayur', color=MUTED, size=12),
                ft.Text('AUTH  ' + ('token' if state['username'] else 'none'),
                        color=MUTED, size=12),
            ], spacing=8)),
            card(ft.Column([
                ft.Text('使用说明', color=DIM, size=11, font_family='monospace'),
                ft.Text('· 课程 = 科目，作业 = 题目分组；点击课程进入作业，点击作业查看题目。',
                        color=MUTED, size=12),
                ft.Text('· 手机返回键：返回上一级菜单；根菜单连按两次返回退出。',
                        color=MUTED, size=12),
                ft.Text('· 移动端 v3.2 支持登录 / 仪表盘 / 浏览 / 图片 / 提交成绩；'
                        'Word、PDF 导出请在桌面版使用。', color=MUTED, size=12),
            ], spacing=8)),
            ft.ElevatedButton('LOGOUT', bgcolor=SURFACE_2, color=FG, height=48,
                              on_click=logout),
        ]
        show(make_view('/settings', '设置', 'SETTINGS · 系统信息', controls,
                       show_nav=True, nav_index=2))

    # ---------------- 启动 ----------------
    show_login()


run = getattr(ft, 'run', None) or getattr(ft, 'app', None)
if __name__ == '__main__':
    run(main)
