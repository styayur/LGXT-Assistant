# -*- coding: utf-8 -*-
"""LGXT Assistant · Android (Flet)

移动端 v3.2.0：
- SafeArea 顶栏：不遮挡系统状态栏/刘海，顶栏加高、触控友好
- 视图栈导航：手机返回键返回上一级菜单；在根级菜单双击返回才退出
- 与桌面版共用同一套 API 语义（相同 endpoint/参数与 (ok, data) 结构）
"""
import os
import logging
import threading
import time

import flet as ft
import base64
import json
import uuid
try:
    from .lgxt_transport import APIClient as ApiClient, BASE_URL, INSECURE_WARNING
    from . import model_transport, question_documents
    from .local_store import LocalStore
except ImportError:
    from lgxt_transport import APIClient as ApiClient, BASE_URL, INSECURE_WARNING
    import model_transport
    import question_documents
    from local_store import LocalStore

LOGIN_TIMEOUT = 20
APP_VERSION = '3.3.0'

COLORS = getattr(ft, 'Colors', None) or getattr(ft, 'colors')
ICONS = getattr(ft, 'Icons', None) or getattr(ft, 'icons')

BG = '#F2F5F9'
SURFACE = '#FFFFFF'
SURFACE_2 = '#E5EDF6'
LINE = '#CFDCE9'
FG = '#172D46'
MUTED = '#4D637C'
DIM = '#526A83'
PRIMARY = '#2563A6'
CYAN = '#2563A6'
WARN = '#9C5600'
ERR = '#B42336'


def main(page, client_factory=ApiClient, storage=None):
    local_store = storage if storage is not None else LocalStore()
    page.title = 'LGXT Assistant'
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=PRIMARY)
    page.padding = 0
    page.spacing = 0

    api = client_factory()
    state = {'username': '', 'courses': [], 'works': [],
             'questions': [], 'course': None, 'work': None}
    last_back = {'at': 0.0}
    workers = threading.local()
    state.update(epoch=0, view_epoch=0, ai_cancel=None, ai_response=None, ai_pending=False)

    def stop_ai(_=None):
        if state.get('ai_cancel'):
            state['ai_cancel'].set()
        response = state.get('ai_response')
        if response:
            threading.Thread(target=response.close, daemon=True).start()

    def start_work(fn):
        epoch, view_epoch = state['epoch'], state['view_epoch']
        def guarded():
            workers.epoch, workers.view_epoch = epoch, view_epoch
            fn()
        threading.Thread(target=guarded, daemon=True).start()

    def leave_view():
        stop_ai()
        state['view_epoch'] += 1

    def lifecycle(event):
        if event.state in (ft.AppLifecycleState.PAUSED, ft.AppLifecycleState.HIDDEN, ft.AppLifecycleState.DETACHED):
            stop_ai()
    page.on_app_lifecycle_state_change = lifecycle

    def snack(msg, color=CYAN):
        notice = ft.SnackBar(
            content=ft.Text(msg, color=FG), bgcolor=SURFACE_2,
            behavior=ft.SnackBarBehavior.FLOATING, show_close_icon=True)
        page.show_dialog(notice)
        page.update()

    def ui(fn, *args, **kwargs):
        """从后台线程安全更新 UI。

        Flet 允许从任意线程调用控件方法与 page.update()；
        注意：不能用 ui(同步函数)（Flet 断言只接受协程函数，
        会抛 AssertionError 并导致界面停在 CONNECTING）。
        """
        if (getattr(workers, 'epoch', state['epoch']) != state['epoch'] or
                getattr(workers, 'view_epoch', state['view_epoch']) != state['view_epoch']):
            return
        try:
            fn(*args, **kwargs)
        except Exception as exc:      # 兜底：任何 UI 异常都不能让界面卡死
            logging.warning('Mobile UI update failed')
            try:
                page.update()
            except Exception:
                logging.warning('Mobile UI/storage operation unavailable')

    def card(content, padding=14, bg=SURFACE):
        return ft.Container(
            content=content, bgcolor=bg, padding=padding, border_radius=8,
            border=ft.Border.all(1, LINE), margin=ft.Margin.only(bottom=10))

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
                logging.info('Native window close method unavailable')
        os._exit(0)

    def pop_view(_e=None):
        """返回上一级菜单；根级菜单双击返回才退出。"""
        if len(page.views) > 1:
            leave_view()
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
            ft.Text('理工学堂 · 作业助手', color=PRIMARY, size=13, weight=ft.FontWeight.BOLD),
            ft.Text(title, color=FG, size=17, weight=ft.FontWeight.BOLD),
            ft.Text(subtitle, color=DIM, size=11) if subtitle else ft.Container(height=0),
        ], spacing=1, expand=True))

        warning = ft.Text(INSECURE_WARNING, color=ERR, size=12) if api.insecure and api.allow_insecure else None
        header = ft.Container(
            content=ft.Row(header_left, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=SURFACE, padding=ft.Padding.only(left=8, right=16, top=10, bottom=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, LINE)))

        column_controls = [header]
        if warning:
            column_controls.append(ft.Container(warning, padding=ft.Padding.symmetric(horizontal=16, vertical=6), bgcolor='#FFF0ED'))
        column_controls.append(ft.Container(ft.Column(controls, scroll=ft.ScrollMode.AUTO,
                                                          spacing=10, expand=True),
                                                expand=True, padding=ft.Padding.only(
                                                    left=16, right=16, top=14, bottom=14)))
        nav = None
        if show_nav:
            nav = ft.NavigationBar(
                selected_index=nav_index, bgcolor=SURFACE, indicator_color=SURFACE_2,
                destinations=[
                    ft.NavigationBarDestination(icon=ICONS.DASHBOARD_OUTLINED, label='仪表盘'),
                    ft.NavigationBarDestination(icon=ICONS.SCHOOL_OUTLINED, label='课程'),
                    ft.NavigationBarDestination(icon=ICONS.FOLDER_OUTLINED, label='本地资料'),
                    ft.NavigationBarDestination(icon=ICONS.SETTINGS_OUTLINED, label='设置'),
                ], on_change=lambda e: switch_tab(int(e.control.selected_index)))
            column_controls.append(nav)

        body = ft.Column(column_controls, spacing=0, expand=True)
        # SafeArea：自动避让手机状态栏/刘海，顶栏不会被遮挡
        safe = ft.SafeArea(content=body, expand=True)
        return ft.View(route=route, controls=[safe], padding=0, bgcolor=BG)

    def show(view):
        """根级切换：清空视图栈，仅保留当前根视图。"""
        leave_view()
        page.views.clear()
        page.views.append(view)
        page.update()

    def push(view):
        """进入下一级：压栈，手机返回键可回到上一级。"""
        leave_view()
        # Loading and loaded controls describe the same screen, not two back steps.
        if page.views and page.views[-1].route == view.route:
            page.views.pop()
        page.views.append(view)
        page.update()

    def switch_tab(index):
        if index == 0:
            show_dashboard()
        elif index == 1:
            show_courses()
        elif index == 2:
            show_library()
        else:
            show_settings()

    def back_to(route):
        """返回到栈中最近的指定 route（不存在则回根菜单）。"""
        for i in range(len(page.views) - 1, -1, -1):
            if page.views[i].route == route:
                leave_view()
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
    insecure_opt = ft.Checkbox(label='理解风险，本次允许明文 HTTP', value=False)

    def show_login(err=''):
        try:
            if not user_field.value:
                user_field.value = local_store.get('lgxt.user') or ''
            local_store.remove('lgxt.pass')
        except Exception:
            logging.warning('Local mobile storage unavailable')
        controls = [
            ft.Text('从当前作业开始', color=FG, size=26, weight=ft.FontWeight.BOLD),
            ft.Text('输入理工学堂账号以建立会话', color=MUTED, size=13),
            ft.Text('平台 HTTPS 尚未验证。默认阻止明文登录；兼容模式会暴露账号、密码和成绩传输。', color=ERR, size=13),
            card(ft.Column([user_field, pass_field, insecure_opt,
                            ft.Button('登录理工学堂', on_click=do_login,
                                              bgcolor=PRIMARY, color='#FFFFFF',
                                              height=52)], spacing=14)),
            ft.Text(err, color=ERR, size=12) if err else ft.Container(height=0),
            ft.Text(getattr(local_store, 'warning', ''), color=ERR, size=12),
            ft.TextButton('离线打开本地资料', on_click=lambda e: show_library()),
        ]
        show(make_view('/login', '登录', 'AUTH · 建立会话', controls))

    def do_login(_e=None):
        api.allow_insecure = bool(insecure_opt.value)
        if state.get('login_pending'):
            return
        if not user_field.value or not pass_field.value:
            snack('请输入用户名和密码', WARN)
            return
        login_id = uuid.uuid4().hex
        state['login_id'] = login_id
        state['login_pending'] = True
        state['login_started'] = time.time()
        connecting = [
            loading('CONNECTING ...'),
            ft.Text('正在连接理工学堂服务器，请稍候', color=MUTED, size=12),
            ft.Row([
                ft.Button('取消', bgcolor=SURFACE_2, color=FG,
                                  on_click=lambda e: cancel_login()),
                ft.Button('重试', bgcolor=PRIMARY, color='#FFFFFF',
                                  on_click=lambda e: cancel_login()),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ]
        show(make_view('/login', '登录', 'CONNECTING ...', connecting))
        username = user_field.value.strip()
        password = pass_field.value
        pass_field.value = ''
        insecure_login = bool(insecure_opt.value)

        def work():
            candidate = None
            try:
                candidate = client_factory()
                candidate.allow_insecure = insecure_login
                ok, msg = candidate.login(username, password)
            except Exception:
                ok, msg = False, '登录失败，请检查网络与配置'
            if not state.get('login_pending') or state.get('login_id') != login_id:
                if candidate: candidate.logout()
                return                            # 用户已取消
            state['login_pending'] = False
            if ok:
                api.logout()
                api.headers.update(candidate.headers)
                state['username'] = username
                try:
                    if not api.insecure: local_store.set('lgxt.user', username)
                    else: local_store.remove('lgxt.user')
                    local_store.remove('lgxt.pass')
                except Exception:
                    logging.warning('Local mobile storage unavailable')
                ui(show_dashboard)
            else:
                ui(show_login, msg)

        start_work(work)

        def watchdog():
            time.sleep(LOGIN_TIMEOUT)
            if state.get('login_pending') and state.get('login_id') == login_id:
                state['login_pending'] = False
                ui(show_login, f'登录超时（{LOGIN_TIMEOUT}s）：请检查网络或服务器状态后重试')

        threading.Thread(target=watchdog, daemon=True).start()

    def cancel_login():
        state['login_id'] = None
        state['login_pending'] = False
        show_login('已取消登录；重试时请重新输入密码')

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
                    elif max(0, (w.get('tryTimes') or 0) - (w.get('times') or 0)) > 0:
                        pending += 1
            avg = sum(scores) / len(scores) if scores else 0
            ui(render_dashboard, pending, done, avg, len(data))

        start_work(work)

    def render_dashboard(pending, done, avg, courses):
        def stat(title, value, color):
            return ft.Container(
                content=ft.Column([ft.Text(title, color=DIM, size=11, font_family='monospace'),
                                   ft.Text(str(value), color=color, size=30,
                                           weight=ft.FontWeight.BOLD, font_family='monospace')],
                                  spacing=4),
                bgcolor=SURFACE, padding=14, border_radius=8, expand=True,
                border=ft.Border.all(1, LINE))
        controls = [
            ft.Text(f'{courses} 门课程 · 数据来自服务器实时统计', color=MUTED, size=12),
            ft.Row([stat('待激活', pending, WARN), stat('已完成', done, CYAN),
                    stat('平均分', f'{avg:.1f}', PRIMARY)], spacing=10),
            ft.Button('刷新作业状态', on_click=lambda e: show_dashboard(),
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

        start_work(work)

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

        start_work(work)

    def render_works(works):
        controls = []
        if not works:
            controls.append(ft.Text('该课程暂无作业', color=MUTED, size=13))
        for work in works:
            grade = work.get('grade')
            remaining = max(0, (work.get('tryTimes') or 0) - (work.get('times') or 0))
            if work.get('tryTimes') is None or work.get('times') is None:
                status, color = '提交次数未知', MUTED
            elif grade is not None:
                status, color = f'已完成 · {grade}', CYAN
            elif remaining <= 0:
                status, color = '次数已用完', ERR
            elif remaining == 1:
                status, color = '最后一次', WARN
            else:
                status, color = f'剩余 {remaining}/{work.get("tryTimes", 0)} 次', PRIMARY
            controls.append(card(ft.Column([
                ft.Text(work.get('workName', ''), color=FG, size=15),
                ft.Text(f"{status} · DUE {work.get('expireTime', 'N/A')}", color=color,
                        size=11, font_family='monospace'),
                ft.Button('查看题目', bgcolor=PRIMARY, color='#FFFFFF', height=46,
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

        start_work(work_fn)

    def render_questions(questions):
        controls = [ft.Text(f'共 {len(questions)} 题', color=MUTED, size=12)]
        for idx, q in enumerate(questions):
            image_holder = ft.Container(content=ft.Text('图片待加载', color=MUTED), on_click=lambda e, q=q: open_question_document(q))
            def fetch_image(q=q, holder=image_holder):
                try:
                    raw = api.fetch_image(q.get('imgurl', ''))
                    encoded = base64.b64encode(raw).decode()
                    q['_image'] = 'data:' + question_documents.api.validate_image(raw) + ';base64,' + encoded
                    holder.content = ft.Image(src=base64.b64decode(encoded), height=200, fit=ft.BoxFit.CONTAIN)
                except Exception:
                    holder.content = ft.Text('图片不可用，点击查看题面与错误处理', color=ERR)
                ui(page.update)
            # Started after the new view is mounted, so navigation invalidation
            # does not invalidate the initial image request.
            image_holder.data = fetch_image
            img = image_holder
            controls.append(card(ft.Column([
                ft.Text(f"Q{idx + 1} · {q.get('name', 'N/A')}", color=FG, size=15),
                ft.Text(f"ID {q.get('id', 'N/A')}", color=DIM, size=11, font_family='monospace'),
                img,
                ft.TextButton('查看原图 / 识别公式 / AI 分析', on_click=lambda e, q=q: open_question_document(q)),
                ft.Text(f"答案：{q.get('answer', 'N/A')}", color=WARN, size=13),
            ], spacing=8)))

        grade_field = ft.TextField(label='成绩 0-100', value='100', width=150, height=52,
                                   bgcolor=SURFACE, border_color='#243040', color=FG)

        submitting = threading.Event()
        work_id = state['work']['workId']
        def submit(_e):
            if submitting.is_set():
                snack('已有提交请求，请等待结果并核实', WARN); return
            value = (grade_field.value or '').strip()
            if not (value.isdigit() and 0 <= int(value) <= 100):
                snack('请输入 0-100 的成绩', WARN)
                return

            def work():
                try:
                    ok, msg = api.submit_answer(work_id, value)
                    ui(snack, msg, WARN if '待核实' in msg else PRIMARY if ok else ERR)
                finally:
                    submitting.clear()

            def confirmed(_):
                if state['epoch'] != confirmation_epoch or state['view_epoch'] != confirmation_view:
                    page.pop_dialog();snack('页面或会话已改变，请重新预览提交', WARN); return
                if submitting.is_set(): return
                submitting.set()
                page.pop_dialog()
                start_work(work)
            confirmation_epoch, confirmation_view = state['epoch'], state['view_epoch']
            dialog = ft.AlertDialog(title=ft.Text('确认提交成绩'), content=ft.Text(f'本作业提交 {value} 分，会修改服务器记录并可能消耗提交次数。超时需到平台核实，不自动重试。'),
                                    actions=[ft.TextButton('取消', on_click=lambda e: page.pop_dialog()), ft.TextButton('确认提交', on_click=confirmed)])
            page.show_dialog(dialog)

        controls.append(card(ft.Row([grade_field,
                                     ft.Button('提交成绩', bgcolor=PRIMARY,
                                                       color='#FFFFFF', height=52,
                                                       on_click=submit)], spacing=12, wrap=True)))
        push(make_view('/questions', state['work'].get('workName', ''), 'QUESTIONS · 题目',
                       controls, show_back=True, on_back=lambda: back_to('/works')))
        for control in controls[:-1]:
            if isinstance(control, ft.Container):
                for item in control.content.controls:
                    if isinstance(item, ft.Container) and callable(item.data):
                        start_work(item.data)

    ai_fields = {
        'endpoint': ft.TextField(label='模型 HTTPS Endpoint（兼容接口）', value='https://api.openai.com/v1'),
        'model': ft.TextField(label='模型 ID'),
        'key': ft.TextField(label='API Key（仅本次会话）', password=True, can_reveal_password=True),
    }
    vision = ft.Checkbox(label='我已核实此模型支持图片', value=False)
    attach_image = ft.Checkbox(label='发送当前题目原图（可关闭，仅发送文字）', value=True)
    for field_name in ('endpoint', 'model'):
        ai_fields[field_name].on_change = lambda e: setattr(vision, 'value', False)

    async def export_backup(_=None):
        try:
            await ft.FilePicker().save_file(file_name='LGXT-study-notes.json', src_bytes=local_store.export_backup())
        except Exception:
            snack('备份未完成；请检查本地资料与文件选择器', ERR)

    async def import_backup(_=None):
        try:
            files = await ft.FilePicker().pick_files(allow_multiple=False, with_data=True)
            if not files: return
            file = files[0]
            if file.size > 32 * 1024 * 1024: raise ValueError('备份超过 32 MB')
            raw = file.bytes
            if raw is None: raise ValueError('文件不可读取')
            # A confirmation is necessary because matching document IDs replace
            # current content (the prior revision is retained atomically).
            def confirmed(_):
                page.pop_dialog()
                try:
                    count = local_store.import_backup(raw)
                    show_library();snack(f'已恢复 {count} 份资料，旧内容已保留为前一版本')
                except Exception:
                    snack('备份无效、版本未知或保存失败；原数据已保留', ERR)
            page.show_dialog(ft.AlertDialog(title=ft.Text('导入本地备份'),
                content=ft.Text('同一题目的内容将替换为备份内容，并保留前一版本。备份可能包含私人笔记，请核对来源。'),
                actions=[ft.TextButton('取消', on_click=lambda e: page.pop_dialog()), ft.TextButton('确认导入', on_click=confirmed)]))
        except Exception:
            snack('备份未读取，请选择不超过 32 MB 的有效 JSON 备份', ERR)

    def show_library():
        documents = local_store.documents() if hasattr(local_store, 'documents') else {}
        controls = [ft.Text('本机保存的题目与笔记，断网也可阅读。卸载前请导出备份。', color=MUTED),
                    ft.Text(getattr(local_store, 'warning', ''), color=ERR),
                    ft.Row([ft.TextButton('导出备份', on_click=export_backup), ft.TextButton('导入备份 / 恢复', on_click=import_backup)], wrap=True)]
        for key, document in documents.items():
            controls.append(card(ft.Column([
                ft.Text(document.get('title', '本地题目'), weight=ft.FontWeight.BOLD),
                ft.Text(document.get('workName', '') + ' · ' + document.get('updatedAt', ''), size=12, color=MUTED),
                ft.TextButton('打开本地笔记', on_click=lambda e, d=document: open_question_document(None, saved=d))])))
        if not documents: controls.append(ft.Text('尚无保存的资料', color=MUTED))
        if not state['username']:
            controls.append(ft.TextButton('返回登录', on_click=lambda e: show_login()))
        show(make_view('/library', '本地资料', '离线阅读 · 备份与恢复', controls, show_nav=bool(state['username']), nav_index=2))

    def open_question_document(q, saved=None):
        if saved:
            d = question_documents.validate_document(saved)
            key = 'question.' + question_documents.document_key(d['courseId'], d['workId'], d['questionId'])
        else:
            key = 'question.' + question_documents.document_key(state['course']['courseId'], state['work']['workId'], q['id'])
            d = local_store.get(key) or {
            'schemaVersion': 1, 'courseId': str(state['course']['courseId']), 'workId': str(state['work']['workId']),
            'questionId': str(q['id']), 'title': q.get('name', ''), 'courseName': state['course']['courseName'],
            'workName': state['work']['workName'], 'sourceText': q.get('text', q.get('name', '')),
            'correctedMarkdown': '', 'solutionMarkdown': '', 'originalImage': q.get('_image', ''), 'sources': []}
        corrected = ft.TextField(label='校正题面 / LaTeX 源码', value=d.get('correctedMarkdown', ''), multiline=True, min_lines=3, max_lines=8)
        solution = ft.TextField(label='解答笔记（Markdown）', value=d.get('solutionMarkdown', ''), multiline=True, min_lines=4, max_lines=10)
        question_input = ft.TextField(label='围绕此题追问', value='请逐步推导并说明公式适用条件', multiline=True)
        output = ft.Text('', selectable=True, color=FG)
        latex = ft.TextField(label='识别 LaTeX（机器生成，请核对后应用）', multiline=True, min_lines=2)
        cancel = threading.Event()
        save_status = ft.Text('本地内容已载入；编辑后请保存', color=MUTED, size=12)
        def save(_=None):
            try:
                d.update(correctedMarkdown=corrected.value or '', solutionMarkdown=solution.value or '')
                value = question_documents.validate_document(d)
                if hasattr(local_store, 'save_document'): local_store.save_document(key, value)
                else: local_store.set(key, value)
                save_status.value = '已保存到本机 · ' + value['updatedAt']
                page.update()
                return True
            except Exception:
                save_status.value = '保存失败；编辑内容仍在此页，请备份后重试'
                snack(save_status.value, ERR)
                return False
        def edited(_):
            save_status.value = '有未保存的修改'
            page.update()
        corrected.on_change = solution.on_change = edited
        def run_ai(recognize):
            if state.get('ai_pending'):
                snack('请先结束当前生成', WARN); return
            try:
                if not save(): return
                image = d.get('originalImage') if (recognize or attach_image.value) else None
                if recognize and not image:
                    raise ValueError('请等待原图加载，返回后重新打开此题')
                settings = {'provider':'OpenAI','endpoint':ai_fields['endpoint'].value,'model':ai_fields['model'].value,
                            'temperature':0.3,'maxTokens':4096,'visionEnabled':bool(vision.value)}
                prompt = ('Return only JSON with exactly two string fields text and latex. Recognize printed text and mathematical LaTeX, do not solve.' if recognize else question_input.value)
                messages = question_documents.context_messages(d, prompt, image)
                # Same provider-specific attachment serialization, with no secret persistence.
                content = messages[0]['content'] + '\n' + '\n'.join(a.get('text','') for a in messages[0]['attachments'])
                blocks = [{'type':'text','text':content}]
                if image: blocks.append({'type':'image_url','image_url':{'url':image}})
                prepared = [{'role':'user','content':blocks}]
                request_key = ai_fields['key'].value
                model_transport.request_config(settings, request_key, prepared)
            except Exception as exc:
                snack(str(exc), ERR); return
            state['ai_pending'] = True
            state['ai_cancel'] = cancel
            request_id = uuid.uuid4().hex
            state['ai_request_id'] = request_id
            cancel.clear()
            output.value = '正在生成；停止或离开页面将取消本地接收，不保证服务端停止计费。'
            page.update()
            def generate():
                text = ''
                try:
                    def response_ready(response):
                        state['ai_response'] = response
                        if cancel.is_set(): response.close()
                    for chunk in model_transport.stream(settings, request_key, prepared, cancel, response_ready):
                        text += chunk
                        if len(text) > 64000:
                            raise ValueError('输出超过限制')
                    if cancel.is_set(): return
                    if recognize:
                        parsed = question_documents.parse_recognition(text)
                        latex.value = parsed['latex']
                        output.value = parsed['text']
                    else:
                        output.value = text
                except Exception:
                    output.value = '模型请求失败或输出无效；已有文档已保留，请检查配置与能力。'
                finally:
                    if state.get('ai_request_id') == request_id:
                        state['ai_pending'] = False
                        state['ai_response'] = None
                    ui(page.update)
            start_work(generate)
        def apply_recognition(_):
            d['latex'] = latex.value or ''
            d['recognizedText'] = output.value
            corrected.value = output.value + '\n\n$$\n' + (latex.value or '') + '\n$$'
            page.update()
        controls = [ft.Text('来源：' + d['courseName'] + ' / ' + d['workName'], color=MUTED),
                    ft.Text('原图为来源；识别与解答可能有误。点击 AI 操作将题图、编辑内容发送到所配模型服务。', color=WARN, size=12)]
        if d.get('originalImage'):
            controls.append(ft.Container(ft.InteractiveViewer(content=ft.Image(src=base64.b64decode(d['originalImage'].split(',',1)[1]), fit=ft.BoxFit.CONTAIN), min_scale=0.5, max_scale=5), height=260))
        controls.extend([corrected, ft.Markdown(corrected.value or '', selectable=True), solution,
                         ft.ExpansionTile(title=ft.Text('模型设置（密钥仅本次会话）'), controls=[*ai_fields.values(),vision,attach_image]),
                         question_input, ft.Button('使用 AI 分析此题', on_click=lambda e: run_ai(False)),
                         ft.TextButton('图片转 LaTeX', on_click=lambda e: run_ai(True)),
                         ft.TextButton('停止生成', on_click=stop_ai), output, latex,
                         ft.TextButton('应用校正结果到题面', on_click=apply_recognition),
                         ft.TextButton('将回复加入解答', on_click=lambda e: (setattr(solution,'value',(solution.value or '')+'\n'+output.value), page.update())),
                         save_status, ft.Button('保存学习材料', on_click=save)])
        push(make_view('/question-document', '题目与解答', '可缩放原图 · 校正 · 分析', controls, show_back=True))

    # ---------------- 设置 ----------------
    def show_settings():
        def logout(_e):
            nonlocal api
            state['epoch'] += 1
            state['login_pending'] = False
            stop_ai()
            previous_api = api
            api = client_factory()
            threading.Thread(target=previous_api.logout, daemon=True).start()
            ai_fields['key'].value = ''
            pass_field.value = ''
            insecure_opt.value = False
            state.update(username='', courses=[], works=[], questions=[], course=None, work=None)
            try:
                local_store.remove('lgxt.pass')
            except Exception:
                logging.warning('Mobile UI/storage operation unavailable')
            show_login()

        controls = [
            card(ft.Column([
                ft.Text('SYSTEM', color=DIM, size=11, font_family='monospace'),
                ft.Text(f'API  {BASE_URL}', color=MUTED, size=12, selectable=True),
                ft.Text(f'VERSION  {APP_VERSION}-android', color=MUTED, size=12),
                ft.Text('LICENSE  AGPL-3.0-only · Styayur', color=MUTED, size=12),
                ft.Text('AUTH  ' + ('token' if state['username'] else 'none'),
                        color=MUTED, size=12),
            ], spacing=8)),
            card(ft.Column([
                ft.Text('使用说明', color=DIM, size=11, font_family='monospace'),
                ft.Text('· 课程 = 科目，作业 = 题目分组；点击课程进入作业，点击作业查看题目。',
                        color=MUTED, size=12),
                ft.Text('· 手机返回键：返回上一级菜单；根菜单连按两次返回退出。',
                        color=MUTED, size=12),
                ft.Text('· 支持课程作业、题图查看、公式校正和用户发起的 AI 分析；'
                        'Word、PDF 导出请在桌面版使用。', color=MUTED, size=12),
            ], spacing=8)),
            ft.Button('LOGOUT', bgcolor=SURFACE_2, color=FG, height=48,
                              on_click=logout),
        ]
        show(make_view('/settings', '设置', 'SETTINGS · 系统信息', controls,
                       show_nav=True, nav_index=3))

    # ---------------- 启动 ----------------
    show_login()
    if storage is None:
        async def migrate_legacy_login():
            try:
                preferences = ft.SharedPreferences()
                username = await preferences.get('lgxt.user')
                await preferences.remove('lgxt.pass')
                if username and not local_store.get('lgxt.user'):
                    local_store.set('lgxt.user', str(username))
                    if not user_field.value:
                        user_field.value = str(username)
                        page.update()
            except Exception:
                logging.warning('Legacy preference cleanup unavailable; old passwords will never be read')
        page.run_task(migrate_legacy_login)


run = getattr(ft, 'run', None) or getattr(ft, 'app', None)
if __name__ == '__main__':
    run(main)
