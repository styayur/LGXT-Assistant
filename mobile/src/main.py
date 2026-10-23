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

        if api.insecure and api.allow_insecure:
            controls = [ft.Text(INSECURE_WARNING, color=ERR, size=12)] + list(controls)
        header = ft.Container(
            content=ft.Row(header_left, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=SURFACE, padding=ft.Padding.only(left=8, right=16, top=10, bottom=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, LINE)))

        column_controls = [header, ft.Container(ft.Column(controls, scroll=ft.ScrollMode.AUTO,
                                                          spacing=10, expand=True),
                                                expand=True, padding=ft.Padding.only(
                                                    left=16, right=16, top=14, bottom=14))]
        nav = None
        if show_nav:
            nav = ft.NavigationBar(
                selected_index=nav_index, bgcolor=SURFACE, indicator_color=SURFACE_2,
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
                                  on_click=lambda e: (cancel_login(), do_login())),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ]
        show(make_view('/login', '登录', 'CONNECTING ...', connecting))
        username = user_field.value.strip()
        password = pass_field.value

        def work():
            try:
                candidate = client_factory()
                candidate.allow_insecure = bool(insecure_opt.value)
                ok, msg = candidate.login(username, password)
            except Exception as exc:              # 理论不会发生，兜底
                ok, msg = False, f'登录异常：{exc}'
            if not state.get('login_pending') or state.get('login_id') != login_id:
                candidate.logout()
                return                            # 用户已取消
            state['login_pending'] = False
            if ok:
                api.logout()
                api.headers.update(candidate.headers)
                state['username'] = username
                try:
                    local_store.set('lgxt.user', username)
                    local_store.remove('lgxt.pass')
                except Exception:
                    logging.warning('Local mobile storage unavailable')
                ui(show_dashboard)
            else:
                ui(show_login, msg)

        threading.Thread(target=work, daemon=True).start()

        def watchdog():
            time.sleep(LOGIN_TIMEOUT)
            if state.get('login_pending') and state.get('login_id') == login_id:
                state['login_pending'] = False
                ui(show_login, f'登录超时（{LOGIN_TIMEOUT}s）：请检查网络或服务器状态后重试')

        threading.Thread(target=watchdog, daemon=True).start()

    def cancel_login():
        state['login_id'] = None
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

        threading.Thread(target=work_fn, daemon=True).start()

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
            threading.Thread(target=fetch_image, daemon=True).start()
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

        def submit(_e):
            value = (grade_field.value or '').strip()
            if not (value.isdigit() and 0 <= int(value) <= 100):
                snack('请输入 0-100 的成绩', WARN)
                return

            def work():
                ok, msg = api.submit_answer(state['work']['workId'], value)
                ui(snack, msg, PRIMARY if ok else ERR)

            def confirmed(_):
                page.pop_dialog()
                threading.Thread(target=work, daemon=True).start()
            dialog = ft.AlertDialog(title=ft.Text('确认提交成绩'), content=ft.Text(f'本作业提交 {value} 分，会修改服务器记录并可能消耗提交次数。超时需到平台核实，不自动重试。'),
                                    actions=[ft.TextButton('取消', on_click=lambda e: page.pop_dialog()), ft.TextButton('确认提交', on_click=confirmed)])
            page.show_dialog(dialog)

        controls.append(card(ft.Row([grade_field,
                                     ft.Button('提交成绩', bgcolor=PRIMARY,
                                                       color='#FFFFFF', height=52,
                                                       on_click=submit)], spacing=12)))
        push(make_view('/questions', state['work'].get('workName', ''), 'QUESTIONS · 题目',
                       controls, show_back=True, on_back=lambda: back_to('/works')))

    ai_fields = {
        'endpoint': ft.TextField(label='模型 HTTPS Endpoint（兼容接口）', value='https://api.openai.com/v1'),
        'model': ft.TextField(label='模型 ID'),
        'key': ft.TextField(label='API Key（仅本次会话）', password=True, can_reveal_password=True),
    }
    vision = ft.Checkbox(label='我已核实此模型支持图片', value=False)

    def open_question_document(q):
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
        def save(_=None):
            d.update(correctedMarkdown=corrected.value or '', solutionMarkdown=solution.value or '')
            value = question_documents.validate_document(d)
            prior = local_store.get(key)
            if prior:
                local_store.set(key + '.previous', prior)
            local_store.set(key, value)
            snack('已保存到本机')
        def run_ai(recognize):
            if state.get('ai_pending'):
                snack('请先结束当前生成', WARN); return
            try:
                save()
                image = d.get('originalImage')
                if not vision.value:
                    raise ValueError('请先核实模型视觉能力；纯文字分析请在 Windows 使用')
                if not image:
                    raise ValueError('请等待原图加载，返回后重新打开此题')
                settings = {'provider':'OpenAI','endpoint':ai_fields['endpoint'].value,'model':ai_fields['model'].value,
                            'temperature':0.3,'maxTokens':4096,'visionEnabled':True}
                prompt = ('Return only JSON with exactly two string fields text and latex. Recognize printed text and mathematical LaTeX, do not solve.' if recognize else question_input.value)
                messages = question_documents.context_messages(d, prompt, image)
                # Same provider-specific attachment serialization, with no secret persistence.
                content = messages[0]['content'] + '\n' + '\n'.join(a.get('text','') for a in messages[0]['attachments'])
                prepared = [{'role':'user','content':[{'type':'text','text':content},{'type':'image_url','image_url':{'url':image}}]}]
                model_transport.request_config(settings, ai_fields['key'].value, prepared)
            except Exception as exc:
                snack(str(exc), ERR); return
            state['ai_pending'] = True
            cancel.clear()
            def generate():
                text = ''
                try:
                    for chunk in model_transport.stream(settings, ai_fields['key'].value, prepared, cancel):
                        text += chunk
                        if len(text) > 64000:
                            raise ValueError('输出超过限制')
                    if recognize:
                        parsed = question_documents.parse_recognition(text)
                        latex.value = parsed['latex']
                        output.value = parsed['text']
                    else:
                        output.value = text
                except Exception:
                    output.value = '模型请求失败或输出无效；已有文档已保留，请检查配置与能力。'
                finally:
                    state['ai_pending'] = False
                    ui(page.update)
            threading.Thread(target=generate, daemon=True).start()
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
                         ft.ExpansionTile(title=ft.Text('模型设置（密钥仅本次会话）'), controls=[*ai_fields.values(),vision]),
                         question_input, ft.Button('使用 AI 分析此题', on_click=lambda e: run_ai(False)),
                         ft.TextButton('图片转 LaTeX', on_click=lambda e: run_ai(True)),
                         ft.TextButton('停止生成', on_click=lambda e: cancel.set()), output, latex,
                         ft.TextButton('应用校正结果到题面', on_click=apply_recognition),
                         ft.TextButton('将回复加入解答', on_click=lambda e: (setattr(solution,'value',(solution.value or '')+'\n'+output.value), page.update())),
                         ft.Button('保存学习材料', on_click=save)])
        push(make_view('/question-document', '题目与解答', '可缩放原图 · 校正 · 分析', controls, show_back=True))

    # ---------------- 设置 ----------------
    def show_settings():
        def logout(_e):
            api.logout()
            api.allow_insecure = False
            ai_fields['key'].value = ''
            pass_field.value = ''
            insecure_opt.value = False
            state.update({'username': ''})
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
                       show_nav=True, nav_index=2))

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
