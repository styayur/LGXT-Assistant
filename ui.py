# -*- coding: utf-8 -*-
"""UI：Developer-Tool 风格主窗口、页面渲染与任务适配。

线程安全约定：
- 页面数据加载与图片下载在后台线程执行，结果经 root.after() 回主线程渲染；
- 批量/收集任务只通过本类的 status/progress/maximum/stop_and_close 等适配器
  更新界面（内部全部 root.after 调度），worker 不直接操作控件。
"""
import io
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter.constants import *

import ttkbootstrap as ttk
from PIL import Image, ImageTk
from ttkbootstrap.dialogs import Messagebox

import api
import config
import exporter
import tasks
import theme
from exporter import ExportOptions

try:  # ttkbootstrap < 2
    from ttkbootstrap.scrolled import ScrolledFrame
except ImportError:  # ttkbootstrap >= 2 exports ScrolledFrame at top level
    from ttkbootstrap import ScrolledFrame

SERVICE = '理工学堂助手'


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(SERVICE)
        self.root.minsize(1100, 800)
        self.root.configure(bg=theme.BG)
        self.style = ttk.Style('darkly')
        theme.apply_theme(self.style)

        # 共享工作区状态（对应服务器会话数据）
        self.api = api.client
        self.username = ''
        self.password = ''
        self.courses = []
        self.works = []
        self.questions = []
        self.images = []
        self.selected_course_id = None
        self.selected_course_name = ''
        self.selected_work_id = None
        self.selected_work_name = ''

        # 导出设置（运行期变量 + config.ini 持久化）
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
        self.settings = config.Settings(self.config_file)
        self.export_path = self.settings.export_path
        self.export_word_var = tk.BooleanVar(value=self.settings.export_word)
        self.export_word_include_answers_var = tk.BooleanVar(value=self.settings.export_word_include_answers)
        self.export_pdf_var = tk.BooleanVar(value=self.settings.export_pdf)
        self.export_pdf_include_answers_var = tk.BooleanVar(value=self.settings.export_pdf_include_answers)

        self._token = 0            # 导航令牌：只允许最新一次异步加载落地
        self.queue = queue.Queue()  # worker -> 主线程轮询（禁止跨线程操作控件）
        self.progress_window = None
        self.status_label = None
        self.progress_bar = None

        self.setup_ui()
        self.root.after(60, self._poll_queue)
        self.set_state('STANDBY')
        self.set_page('未连接')
        self.show_login()

    # ---------- 窗口框架 ----------

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=YES)

        header = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=42)
        header.pack(side=TOP, fill=X)
        header.pack_propagate(False)
        tk.Label(header, text='LGXT::ASSISTANT', bg=theme.BG_RAISED, fg=theme.PRIMARY,
                 font=('Consolas', 11, 'bold')).pack(side=LEFT, padx=(16, 0))
        tk.Frame(header, bg=theme.BORDER, width=1).pack(side=LEFT, fill=Y, padx=14, pady=9)
        self.page_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.MUTED,
                                   font=('Consolas', 10))
        self.page_label.pack(side=LEFT)
        self.state_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.DIM,
                                    font=('Consolas', 10, 'bold'))
        self.state_label.pack(side=RIGHT, padx=16)
        tk.Frame(self.main_frame, bg=theme.BORDER, height=1).pack(side=TOP, fill=X)

        tk.Frame(self.main_frame, bg=theme.BORDER, height=1).pack(side=BOTTOM, fill=X)
        statusbar = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=24)
        statusbar.pack(side=BOTTOM, fill=X)
        statusbar.pack_propagate(False)
        self.log_label = tk.Label(statusbar, text='> SYSTEM READY', bg=theme.BG_RAISED,
                                  fg=theme.DIM, font=('Consolas', 8), anchor='w')
        self.log_label.pack(side=LEFT, fill=X, expand=YES, padx=10)
        self.auth_label = tk.Label(statusbar, text='AUTH none', bg=theme.BG_RAISED, fg=theme.DIM,
                                   font=('Consolas', 8))
        self.auth_label.pack(side=RIGHT, padx=10)
        tk.Label(statusbar, text='API ' + self.api.base_url, bg=theme.BG_RAISED, fg=theme.DIM,
                 font=('Consolas', 8)).pack(side=RIGHT, padx=10)

        body = tk.Frame(self.main_frame, bg=theme.BG)
        body.pack(side=TOP, fill=BOTH, expand=YES)
        self.create_sidebar(body)
        tk.Frame(body, bg=theme.BORDER, width=1).pack(side=LEFT, fill=Y)
        self.content_frame = ttk.Frame(body, padding=(18, 14))
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=YES)

    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=theme.SURFACE, width=216)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text='理工学堂助手', bg=theme.SURFACE, fg=theme.FG,
                 font=('Microsoft YaHei', 13, 'bold'), anchor='w').pack(fill=X, padx=14, pady=(16, 2))
        tk.Label(sidebar, text='developer workbench', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8)).pack(fill=X, padx=14)

        def nav_section(text):
            tk.Label(sidebar, text=text, bg=theme.SURFACE, fg=theme.DIM, anchor='w',
                     font=('Consolas', 8, 'bold')).pack(fill=X, padx=14, pady=(14, 4))

        def nav_item(text, command):
            item = tk.Label(sidebar, text=text, bg=theme.SURFACE, fg=theme.MUTED, anchor='w',
                            font=theme.FONT_UI, cursor='hand2', padx=10, pady=6)
            item.pack(fill=X, padx=8)
            item.bind('<Enter>', lambda e: item.configure(bg=theme.HOVER, fg=theme.FG))
            item.bind('<Leave>', lambda e: item.configure(bg=theme.SURFACE, fg=theme.MUTED))
            item.bind('<Button-1>', lambda e: command())
            return item

        nav_section('WORKSPACE')
        nav_item('  课程列表', self.show_courses)
        nav_section('SYSTEM')
        nav_item('  设置', self.show_settings)
        nav_item('  帮助', self.show_help)
        nav_item('  退出', self.root.quit)

        tk.Frame(sidebar, bg=theme.BORDER, height=1).pack(side=BOTTOM, fill=X)
        info = tk.Frame(sidebar, bg=theme.SURFACE)
        info.pack(side=BOTTOM, fill=X, pady=8)
        for line, color in [('v3.0.0', theme.FG), ('GPL-3.0', theme.DIM), ('by Styayur', theme.DIM)]:
            tk.Label(info, text=line, bg=theme.SURFACE, fg=color,
                     font=('Consolas', 8), anchor='w').pack(fill=X, padx=14)

    # ---------- 状态 / 导航辅助 ----------

    def set_page(self, text):
        self.page_label.configure(text=f':: {text}')

    def set_state(self, text):
        colors = {'STANDBY': theme.DIM, 'READY': theme.PRIMARY,
                  'PROCESSING': theme.WARNING, 'ERROR': theme.ERROR}
        self.state_label.configure(text=f'[ {text} ]', fg=colors.get(text, theme.DIM))

    def set_auth(self, ok):
        self.auth_label.configure(text='AUTH token' if ok else 'AUTH none',
                                  fg=theme.PRIMARY if ok else theme.DIM)

    def log(self, text):
        self._write_log(text)

    def _write_log(self, text):
        text = str(text).replace('\n', ' | ').strip()
        if self.log_label is not None and self.log_label.winfo_exists():
            self.log_label.configure(text=f'> {text[:120]}')

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def begin_nav(self):
        """开启一次页面导航：作废旧的异步加载结果并清空内容区。"""
        self._token += 1
        self.clear_content()

    def fetch(self, job, on_done):
        """后台执行 job()；完成后入队，由主线程轮询回调 on_done(result)。"""
        token = self._token

        def work():
            try:
                result = job()
            except Exception as exc:
                result = (False, f'网络错误：{exc}')
            self.queue.put(('deliver', token, on_done, result))

        threading.Thread(target=work, daemon=True).start()

    def _poll_queue(self):
        """主线程轮询：把 worker 事件翻译为 UI 更新（唯一触碰控件的地方之一）。"""
        try:
            while True:
                event = self.queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        try:
            self.root.after(60, self._poll_queue)
        except (tk.TclError, RuntimeError):
            pass

    def _handle_event(self, event):
        kind = event[0]
        try:
            if kind == 'deliver':
                _, token, on_done, result = event
                if token == self._token:
                    on_done(result)
            elif kind == 'status':
                self._set_status(event[1])
            elif kind == 'progress':
                self._progress_config('value', event[1])
            elif kind == 'maximum':
                self._progress_config('maximum', event[1])
            elif kind == 'stop':
                self._progress_stop()
            elif kind == 'close':
                self.root.after(event[1], self._destroy_progress)
            elif kind == 'log':
                self._write_log(event[1])
            elif kind == 'result':
                self._destroy_progress()
                self.root.after(0, lambda: Messagebox.show_info(title=event[1], message=event[2]))
            elif kind == 'error_after':
                self.root.after(event[1], lambda: Messagebox.show_error(title=event[2], message=event[3]))
            elif kind == 'task_error':
                _, exc = event
                self.log(f'ERROR {exc}')
                self._destroy_progress()
                self.root.after(0, lambda: Messagebox.show_error(title='错误', message=f'任务失败：{exc}'))
            elif kind == 'run_ok':
                _, on_result, result = event
                on_result(result)
            elif kind == 'run_none':
                _, ms, title, message = event
                self.root.after(ms, lambda: Messagebox.show_error(title=title, message=message))
            elif kind == 'image_bytes':
                _, holder, data, error = event
                self._render_image(holder, data, error)
        except tk.TclError:
            pass  # 控件已随导航销毁

    def _destroy_progress(self):
        if self.progress_window is not None and self.progress_window.winfo_exists():
            self.progress_window.destroy()

    def _on_progress_closed(self, event, win):
        if event.widget is win:
            self.set_state('READY' if self.username else 'STANDBY')

    # ---------- 进度窗口适配器（worker 线程调用，仅入队，不触碰控件） ----------

    def open_progress(self, title, mode='determinate', status='', start=False):
        win = ttk.Toplevel(self.root)
        win.title(title)
        win.resizable(False, False)
        win.configure(bg=theme.BG_RAISED)
        body = tk.Frame(win, bg=theme.BG_RAISED)
        body.pack(expand=True, fill='both')
        self.set_state('PROCESSING')
        tk.Label(body, text=f'> {title}', bg=theme.BG_RAISED, fg=theme.PRIMARY,
                 font=('Consolas', 11, 'bold'), anchor='w').pack(fill=X, padx=22, pady=(18, 0))
        self.status_label = tk.Label(body, text=status, bg=theme.BG_RAISED, fg=theme.MUTED,
                                     font=('Consolas', 10), anchor='w')
        self.status_label.pack(fill=X, padx=22, pady=(10, 8))
        self.progress_bar = ttk.Progressbar(body, mode=mode, length=340)
        self.progress_bar.pack(fill=X, padx=22, pady=(0, 18))
        if start:
            self.progress_bar.start()
        self.progress_window = win
        win.bind('<Destroy>', lambda e: self._on_progress_closed(e, win))
        self.log(f'任务开始 :: {title}')
        return win

    def status(self, text):
        self.queue.put(('status', text))

    def _set_status(self, text):
        if self.status_label is not None and self.status_label.winfo_exists():
            self.status_label.config(text=text)
        self._write_log(text)

    def progress(self, value):
        self.queue.put(('progress', value))

    def maximum(self, value):
        self.queue.put(('maximum', value))

    def _progress_config(self, key, value):
        if self.progress_bar is not None and self.progress_bar.winfo_exists():
            self.progress_bar.config({key: value})

    def stop_and_close(self, ms):
        self.queue.put(('stop',))
        self.queue.put(('close', ms))

    def _progress_stop(self):
        if self.progress_bar is not None and self.progress_bar.winfo_exists():
            self.progress_bar.stop()

    def show_result(self, title, message):
        self.queue.put(('result', title, message))

    def error_after(self, ms, title, message):
        self.queue.put(('error_after', ms, title, message))

    def run_task(self, title, target, on_result, mode='determinate', status='', start=False,
                 error_after=None):
        """在后台线程执行 target(self)；结果事件回主线程处理。"""
        self.open_progress(title, mode=mode, status=status, start=start)

        def worker():
            try:
                result = target(self)
            except Exception as exc:
                self.queue.put(('task_error', exc))
                return
            if result is not None:
                self.queue.put(('run_ok', on_result, result))
            elif error_after is not None:
                self.queue.put(('run_none',) + tuple(error_after))

        threading.Thread(target=worker, daemon=True).start()

    def export_options(self):
        """主线程读取导出开关，生成 worker 只读快照（避免跨线程访问 Tk 变量）。"""
        return ExportOptions(self.export_path,
                             self.export_word_var.get(),
                             self.export_word_include_answers_var.get(),
                             self.export_pdf_var.get(),
                             self.export_pdf_include_answers_var.get())

    def export_options(self):
        """主线程读取导出开关，生成 worker 只读快照（避免跨线程访问 Tk 变量）。"""
        return ExportOptions(self.export_path,
                             self.export_word_var.get(),
                             self.export_word_include_answers_var.get(),
                             self.export_pdf_var.get(),
                             self.export_pdf_include_answers_var.get())

    # ---------- 登录 ----------

    def show_login(self):
        self.begin_nav()
        self.set_page('AUTH · 登录')
        self.set_state('STANDBY')
        self.set_auth(False)

        panel = ttk.Frame(self.content_frame)
        panel.pack(expand=YES)
        ttk.Label(panel, text='$ connect lgxt', font=('Consolas', 14, 'bold'),
                  foreground=theme.PRIMARY).pack(anchor='w')
        ttk.Label(panel, text='输入理工学堂账号以建立会话。', font=theme.FONT_UI,
                  foreground=theme.MUTED).pack(anchor='w', pady=(2, 16))

        user_row = ttk.Frame(panel)
        user_row.pack(fill=X, pady=3)
        ttk.Label(user_row, text='USERNAME', font=('Consolas', 9), width=10,
                  foreground=theme.DIM).pack(side=LEFT)
        self.username_entry = ttk.Entry(user_row, width=34)
        self.username_entry.pack(side=LEFT)

        pass_row = ttk.Frame(panel)
        pass_row.pack(fill=X, pady=3)
        ttk.Label(pass_row, text='PASSWORD', font=('Consolas', 9), width=10,
                  foreground=theme.DIM).pack(side=LEFT)
        self.password_entry = ttk.Entry(pass_row, width=34, show='*')
        self.password_entry.pack(side=LEFT)

        self.remember_var = tk.BooleanVar()
        ttk.Checkbutton(panel, text='记住密码（本地凭据库）', variable=self.remember_var,
                        bootstyle='round-toggle').pack(anchor='w', pady=(8, 4))
        self.login_button = ttk.Button(panel, text='LOGIN ▸ 登录', command=self.login,
                                       bootstyle='primary', width=22)
        self.login_button.pack(anchor='w', pady=(6, 0))

        saved_username = config.get_saved_username()
        saved_password = None
        if saved_username:
            self.username_entry.insert(0, saved_username)
            saved_password = config.get_saved_password(saved_username)
            if saved_password:
                self.password_entry.insert(0, saved_password)
        self.remember_var.set(bool(saved_username and saved_password))

    def login(self):
        if not hasattr(self, 'username_entry'):
            return
        self.username = self.username_entry.get()
        self.password = self.password_entry.get()
        self.login_button.state(['disabled'])
        self.set_state('PROCESSING')
        self.log('AUTH connecting...')

        def on_done(result):
            self.login_button.state(['!disabled'])
            ok, msg = result
            if ok:
                if self.remember_var.get():
                    config.save_credentials(self.username, self.password)
                else:
                    config.delete_saved_credentials()
                self.set_state('READY')
                self.set_auth(True)
                self.log('AUTH ok')
                self.show_courses()
            else:
                self.set_state('ERROR')
                self.log('AUTH failed')
                Messagebox.show_error(message=msg, title='登录失败')

        self.fetch(lambda: self.api.login(self.username, self.password), on_done)

    # ---------- 课程 ----------

    def show_courses(self):
        if not self.username or not self.password:
            Messagebox.show_error(title='错误', message='请先登录')
            self.show_login()
            return
        self.begin_nav()
        self.set_page('课程列表')
        ttk.Label(self.content_frame, text='WORKSPACE :: 课程列表', font=('Consolas', 12, 'bold'),
                  foreground=theme.FG).pack(anchor='w', pady=(2, 10))
        self.log('LOADING courses...')
        self.fetch(self.api.get_my_courses, self._render_courses)

    def _render_courses(self, result):
        ok, data = result
        self.clear_content()
        self.set_page('课程列表')
        ttk.Label(self.content_frame, text='WORKSPACE :: 课程列表', font=('Consolas', 12, 'bold'),
                  foreground=theme.FG).pack(anchor='w', pady=(2, 10))
        body_frame = ttk.Frame(self.content_frame)
        body_frame.pack(fill=BOTH, expand=YES)

        if ok:
            self.courses = data
            ttk.Label(body_frame, text=f'[ {len(data)} COURSES ]', font=('Consolas', 9),
                      foreground=theme.DIM).pack(anchor='w', pady=(0, 6))
            frame = ScrolledFrame(body_frame, autohide=True)
            frame.pack(fill=BOTH, expand=YES)
            lst = tk.Frame(frame, bg=theme.BG)
            lst.pack(fill=BOTH, expand=YES)
            for course in self.courses:
                self._course_row(lst, course)
            self.log(f'COURSES loaded ({len(data)})')
        else:
            self.set_state('ERROR')
            self.log('courses load failed')
            panel = tk.Frame(body_frame, bg=theme.SURFACE)
            panel.pack(fill=X, pady=6)
            tk.Label(panel, text='> ERROR', bg=theme.SURFACE, fg=theme.ERROR,
                     font=('Consolas', 10, 'bold'), anchor='w').pack(fill=X, padx=12, pady=(8, 0))
            tk.Label(panel, text='获取课程列表失败 · 请检查网络后重试', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_UI, anchor='w').pack(fill=X, padx=12, pady=(0, 8))

        actions = ttk.Frame(self.content_frame)
        actions.pack(fill=X, pady=(10, 0))
        ttk.Button(actions, text='提交全部作业100分', command=self.submit_all_courses_100,
                   bootstyle='warning').pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text='导出所有课程的作业', command=self.export_all_courses,
                   bootstyle='info').pack(side=LEFT)

    def _course_row(self, parent, course):
        row = tk.Frame(parent, bg=theme.SURFACE)
        row.pack(fill=X, pady=(0, 5))
        ttk.Button(row, text='查看', bootstyle='primary', cursor='hand2',
                   command=lambda: self.select_course(course)
                   ).pack(side=RIGHT, padx=10, pady=7)
        tk.Label(row, text=f'#{course["courseId"]}', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 9)).pack(side=RIGHT)
        tk.Label(row, text=course['courseName'], bg=theme.SURFACE, fg=theme.FG, anchor='w',
                 font=('Microsoft YaHei', 11, 'bold')).pack(side=LEFT, fill=X, expand=YES,
                                                            padx=12, pady=9)

    def select_course(self, course):
        self.selected_course_id = course['courseId']
        self.selected_course_name = course['courseName']
        self.log(f'LOADING works :: {course["courseName"]}')
        self.fetch(lambda: self.api.get_course_works(course['courseId']), self._render_works)

    def _render_works(self, result):
        ok, data = result
        if not ok:
            Messagebox.show_error(title='错误', message=data)
            return
        self.works = data
        self.show_works()

    # ---------- 作业 ----------

    def show_works(self):
        self.begin_nav()
        self.set_page(f'{self.selected_course_name} · 作业')
        ttk.Label(self.content_frame, text=f'WORKSPACE :: {self.selected_course_name} :: 作业列表',
                  font=('Consolas', 12, 'bold'), foreground=theme.FG).pack(anchor='w', pady=(2, 10))

        body_frame = ttk.Frame(self.content_frame)
        body_frame.pack(fill=BOTH, expand=YES)
        frame = ScrolledFrame(body_frame, autohide=True)
        frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(frame, bg=theme.BG)
        lst.pack(fill=BOTH, expand=YES)

        if not self.works:
            panel = tk.Frame(lst, bg=theme.SURFACE)
            panel.pack(fill=X, pady=6)
            tk.Label(panel, text='> NO WORKSPACE DATA', bg=theme.SURFACE, fg=theme.PRIMARY,
                     font=('Consolas', 10, 'bold'), anchor='w').pack(fill=X, padx=12, pady=(8, 0))
            tk.Label(panel, text='该课程目前没有可用的作业。', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_UI, anchor='w').pack(fill=X, padx=12, pady=(0, 8))
        else:
            ttk.Label(lst, text=f'[ {len(self.works)} WORKS ]', font=('Consolas', 9),
                      foreground=theme.DIM).pack(anchor='w', pady=(0, 6))
            for work in self.works:
                self._work_row(lst, work)

        actions = ttk.Frame(self.content_frame)
        actions.pack(fill=X, pady=(10, 0))
        ttk.Button(actions, text='提交当前课程作业100分', command=self.submit_all_works_100,
                   bootstyle='warning').pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text='导出当前课程的所有作业', command=self.export_all_works,
                   bootstyle='info').pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text='返回课程列表', command=self.show_courses,
                   bootstyle='secondary').pack(side=LEFT)

    def _work_row(self, parent, work):
        times_used = work.get('times', 0)
        try_times = work.get('tryTimes', 0)
        remaining = max(0, try_times - times_used)
        if remaining <= 0:
            status_text, status_color = '已用完所有机会', theme.ERROR
        elif remaining == 1:
            status_text, status_color = f'Last chance! 剩余 {remaining}/{try_times} 次', theme.WARNING
        else:
            status_text, status_color = f'剩余 {remaining}/{try_times} 次', theme.PRIMARY

        row = tk.Frame(parent, bg=theme.SURFACE)
        row.pack(fill=X, pady=(0, 5))
        head = tk.Frame(row, bg=theme.SURFACE)
        head.pack(fill=X)
        ttk.Button(head, text='导出所有题目', bootstyle='info', cursor='hand2',
                   command=lambda: self.collect_work(work)
                   ).pack(side=RIGHT, padx=(4, 10), pady=7)
        ttk.Button(head, text='查看题目', bootstyle='primary', cursor='hand2',
                   command=lambda: self.select_work(work)
                   ).pack(side=RIGHT, padx=4, pady=7)
        tk.Label(head, text=work['workName'], bg=theme.SURFACE, fg=theme.FG, anchor='w',
                 font=('Microsoft YaHei', 11, 'bold')).pack(side=LEFT, fill=X, expand=YES,
                                                            padx=12, pady=9)

        detail = tk.Frame(row, bg=theme.SURFACE)
        detail.pack(fill=X, padx=12, pady=(0, 8))
        tk.Label(detail, text=f'#{work["workId"]}', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        tk.Label(detail, text=status_text, bg=theme.SURFACE, fg=status_color,
                 font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        if work.get('expireTime', 'N/A') != 'N/A':
            tk.Label(detail, text=f'DUE {work["expireTime"]}', bg=theme.SURFACE, fg=theme.MUTED,
                     font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        if work.get('chapterName'):
            tk.Label(detail, text=f'CH {work["chapterName"]}', bg=theme.SURFACE, fg=theme.MUTED,
                     font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        if work.get('grade') is not None:
            tk.Label(detail, text=f'SCORE {work["grade"]}', bg=theme.SURFACE, fg=theme.SECONDARY,
                     font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))

    def select_work(self, work):
        self.selected_work_id = work['workId']
        self.selected_work_name = work['workName']
        self.log(f'LOADING questions :: {work["workName"]}')
        self.fetch(lambda: self.api.get_questions(work['workId']), self._render_questions)

    def _render_questions(self, result):
        ok, data = result
        if not ok:
            Messagebox.show_error(title='错误', message=data)
            return
        self.questions = data
        self.show_questions()

    # ---------- 题目 ----------

    def show_questions(self):
        self.begin_nav()
        self.set_page(f'{self.selected_work_name} · 题目')
        ttk.Label(self.content_frame, text=f'QUESTIONS :: {self.selected_work_name}',
                  font=('Consolas', 12, 'bold'), foreground=theme.FG).pack(anchor='w', pady=(2, 10))

        body_frame = ttk.Frame(self.content_frame)
        body_frame.pack(fill=BOTH, expand=YES)
        frame = ScrolledFrame(body_frame, autohide=True)
        frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(frame, bg=theme.BG)
        lst.pack(fill=BOTH, expand=YES)
        ttk.Label(lst, text=f'[ {len(self.questions)} QUESTIONS ]', font=('Consolas', 9),
                  foreground=theme.DIM).pack(anchor='w', pady=(0, 6))

        self.images = []
        for idx, question in enumerate(self.questions):
            self._question_card(lst, idx, question)

        bottom = ttk.Frame(self.content_frame)
        bottom.pack(fill=X, pady=(10, 0))
        ttk.Label(bottom, text='提交成绩（0-100）：', font=theme.FONT_UI,
                  foreground=theme.MUTED).pack(side=LEFT)
        self.grade_entry = ttk.Entry(bottom, width=8)
        self.grade_entry.pack(side=LEFT, padx=6)
        self.submit_grade_button = ttk.Button(bottom, text='提交', command=self.submit_grade,
                                              bootstyle='primary')
        self.submit_grade_button.pack(side=LEFT, padx=(0, 12))
        ttk.Button(bottom, text='返回作业列表', command=self.show_works,
                   bootstyle='secondary').pack(side=LEFT)

    def _question_card(self, parent, idx, question):
        row = tk.Frame(parent, bg=theme.SURFACE)
        row.pack(fill=X, pady=(0, 6))
        head = tk.Frame(row, bg=theme.SURFACE)
        head.pack(fill=X)
        tk.Label(head, text=f'Q{idx + 1}', bg=theme.SURFACE, fg=theme.PRIMARY,
                 font=('Consolas', 11, 'bold')).pack(side=LEFT, padx=(12, 10), pady=8)
        tk.Label(head, text=question.get('name', 'N/A'), bg=theme.SURFACE, fg=theme.FG,
                 anchor='w', font=('Microsoft YaHei', 11)).pack(side=LEFT, fill=X, expand=YES,
                                                                pady=8)
        tk.Label(head, text=f'ID {question.get("id", "N/A")}', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 9)).pack(side=RIGHT, padx=12)

        content = tk.Frame(row, bg=theme.SURFACE)
        content.pack(fill=X, padx=12, pady=(0, 8))
        imgurl = question.get('imgurl', 'N/A')
        img_holder = None
        if imgurl and imgurl != 'N/A':
            img_holder = tk.Label(content, text='> FETCHING IMAGE...', bg=theme.SURFACE,
                                  fg=theme.DIM, font=('Consolas', 9), anchor='w')
            img_holder.pack(fill=X, pady=(2, 0))
            self._load_image_async(content, imgurl, img_holder)
        else:
            tk.Label(content, text='[ NO IMAGE ]', bg=theme.SURFACE, fg=theme.DIM,
                     font=('Consolas', 9), anchor='w').pack(fill=X)
        tk.Label(content, text=f'答案: {question.get("answer", "N/A")}', bg=theme.SURFACE,
                 fg=theme.WARNING, font=('Consolas', 10), anchor='w').pack(fill=X, pady=(4, 6))

    def _load_image_async(self, parent, imgurl, holder):
        def work():
            try:
                data = self.api.fetch_image(imgurl)
                self.queue.put(('image_bytes', holder, data, None))
            except Exception as exc:
                self.queue.put(('image_bytes', holder, None, str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _render_image(self, holder, data, error):
        if not holder.winfo_exists():
            return
        if error is not None:
            holder.config(text=f'[ IMAGE ERROR ] {error}', fg=theme.ERROR)
            return
        try:
            image = Image.open(io.BytesIO(data))
            image.thumbnail((400, 300))
            photo = ImageTk.PhotoImage(image)
        except Exception as exc:
            holder.config(text=f'[ IMAGE ERROR ] {exc}', fg=theme.ERROR)
            return
        holder.destroy()
        label = tk.Label(holder.master, image=photo, bg=theme.SURFACE)
        label.image = photo
        self.images.append(photo)
        label.pack(anchor='w', pady=(4, 0))

# ---------- 成绩提交 ----------

    def submit_grade(self):
        grade = self.grade_entry.get()
        if not (grade.isdigit() and 0 <= int(grade) <= 100):
            Messagebox.show_error(title='错误', message='请输入有效的成绩（0-100）。')
            return
        self.submit_grade_button.state(['disabled'])

        def on_done(result):
            self.submit_grade_button.state(['!disabled'])
            ok, data = result
            if ok:
                Messagebox.show_info(title='提示', message=data)
            else:
                Messagebox.show_error(title='错误', message=data)

        self.fetch(lambda: self.api.submit_answer(self.selected_work_id, grade), on_done)

    # ---------- 设置 ----------

    def show_settings(self):
        self.begin_nav()
        self.set_page('设置 · CONFIG')
        ttk.Label(self.content_frame, text='CONFIG :: 设置', font=('Consolas', 12, 'bold'),
                  foreground=theme.FG).pack(anchor='w', pady=(2, 10))

        col = ttk.Frame(self.content_frame)
        col.pack(fill=X)

        export_frame = ttk.Labelframe(col, text='EXPORT :: 导出设置', padding=12)
        export_frame.pack(fill=X)
        opts = ttk.Frame(export_frame)
        opts.pack(fill=X)
        self.export_word_check = ttk.Checkbutton(opts, text='导出为 Word (.docx)',
                                                 variable=self.export_word_var,
                                                 command=self.toggle_word_options)
        self.export_word_check.grid(row=0, column=0, sticky='w', padx=(0, 30), pady=3)
        self.export_word_answers_check = ttk.Checkbutton(opts, text='含答案',
                                                         variable=self.export_word_include_answers_var)
        self.export_word_answers_check.grid(row=1, column=0, sticky='w', padx=(22, 30), pady=3)
        self.export_pdf_check = ttk.Checkbutton(opts, text='导出为 PDF (.pdf)',
                                                variable=self.export_pdf_var,
                                                command=self.toggle_pdf_options)
        self.export_pdf_check.grid(row=0, column=1, sticky='w', pady=3)
        self.export_pdf_answers_check = ttk.Checkbutton(opts, text='含答案',
                                                        variable=self.export_pdf_include_answers_var)
        self.export_pdf_answers_check.grid(row=1, column=1, sticky='w', padx=(22, 0), pady=3)
        self.toggle_word_options()
        self.toggle_pdf_options()

        path_frame = ttk.Labelframe(col, text='PATH :: 导出路径', padding=12)
        path_frame.pack(fill=X, pady=(10, 0))
        path_row = ttk.Frame(path_frame)
        path_row.pack(fill=X)
        ttk.Label(path_row, text='路径：').pack(side=LEFT)
        self.path_entry = ttk.Entry(path_row)
        self.path_entry.pack(side=LEFT, fill=X, expand=YES, padx=8)
        self.path_entry.insert(0, self.export_path)
        ttk.Button(path_row, text='浏览', command=self.choose_export_path,
                   bootstyle='secondary').pack(side=LEFT)

        btns = ttk.Frame(col)
        btns.pack(fill=X, pady=(14, 0))
        ttk.Button(btns, text='保存设置', command=self.save_settings,
                   bootstyle='primary').pack(side=LEFT, padx=(0, 8))
        ttk.Button(btns, text='查看用户信息', command=self.view_user_info,
                   bootstyle='info').pack(side=LEFT)

    def toggle_word_options(self):
        self.export_word_answers_check.state(
            ['!disabled' if self.export_word_var.get() else 'disabled'])

    def toggle_pdf_options(self):
        self.export_pdf_answers_check.state(
            ['!disabled' if self.export_pdf_var.get() else 'disabled'])

    def choose_export_path(self):
        path = filedialog.askdirectory(initialdir=self.export_path)
        if path:
            self.path_entry.delete(0, END)
            self.path_entry.insert(0, path)

    def save_settings(self):
        self.export_path = self.path_entry.get()
        self.settings.export_path = self.export_path
        self.settings.export_word = self.export_word_var.get()
        self.settings.export_word_include_answers = self.export_word_include_answers_var.get()
        self.settings.export_pdf = self.export_pdf_var.get()
        self.settings.export_pdf_include_answers = self.export_pdf_include_answers_var.get()
        self.settings.save()
        self.log('CONFIG saved')
        Messagebox.show_info(title='提示', message='设置已保存')

    def view_user_info(self):
        self.fetch(self.api.get_user_info, self._show_user_info)

    def _show_user_info(self, result):
        ok, data = result
        if not ok:
            Messagebox.show_error(title='错误', message=data)
            return

        def field(name):
            return data.get(name) or 'N/A'

        Messagebox.show_info(title='用户信息', message=(
            f'姓名：{field("userName")}\n'
            f'邮箱：{field("email")}\n'
            f'学号：{field("studentNo")}\n'
            f'学院：{field("schoolName")}\n'
            f'班级：{field("deptName")}\n'
            f'电话号码：{field("phonenumber")}'))

    # ---------- 帮助 ----------

    def show_help(self):
        help_window = ttk.Toplevel(self.root)
        help_window.title('帮助')
        help_window.geometry('980x760')
        help_window.minsize(720, 520)

        content = ScrolledFrame(help_window, autohide=True)
        content.pack(fill=BOTH, expand=YES)

        ttk.Label(content, text='MANUAL :: 使用说明', font=('Consolas', 13, 'bold'),
                  foreground=theme.PRIMARY).pack(anchor='w', padx=18, pady=(14, 4))
        ttk.Label(content, text='LGXT Assistant · 理工学堂助手',
                  font=('Microsoft YaHei', 15, 'bold'), foreground=theme.FG).pack(anchor='w', padx=18)

        def head(text):
            ttk.Label(content, text=f'> {text}', font=('Consolas', 11, 'bold'),
                      foreground=theme.SECONDARY).pack(anchor='w', padx=18, pady=(12, 4))

        def line(text):
            ttk.Label(content, text=text, font=theme.FONT_UI, foreground=theme.MUTED,
                      justify='left').pack(anchor='w', padx=30, pady=1)

        head('功能介绍')
        for t in ['1. 登录：输入用户名和密码进行登录。',
                  '2. 课程列表：查看所有课程并选择查看作业。',
                  '3. 作业列表：查看选定课程的所有作业。',
                  '4. 题目列表：查看选定作业的所有题目。',
                  '5. 设置：配置导出路径和格式。',
                  '6. 帮助：查看本帮助信息。']:
            line(t)

        head('操作指南')
        for t in ['1. 登录后，点击课程列表查看所有课程。',
                  '2. 在课程列表中，点击查看作业查看该课程的所有作业。',
                  '3. 在作业列表中，点击查看题目查看该作业的所有题目。',
                  '4. 在题目列表中，可以导出题目或提交成绩。',
                  '5. 在设置页面，可以配置导出路径和格式。']:
            line(t)

        head('声明 · LICENSE')
        for t in ['本工具仅限学习交流使用，请勿转卖或用于商业用途。',
                  'LGXT v3.0 · Author: Styayur · License: GPL-3.0']:
            line(t)

        ttk.Button(content, text='关闭', command=help_window.destroy,
                   bootstyle='danger').pack(anchor='w', padx=30, pady=(18, 24))

    # ---------- 批量 / 收集任务入口 ----------

    def submit_all_courses_100(self):
        self.run_task('正在批量提交所有课程作业，请稍候...',
                      lambda ui: tasks.submit_all_courses(ui, self.api, self.courses),
                      on_result=lambda r: self.show_result(r['title'], r['text']))

    def submit_all_works_100(self):
        self.run_task('正在批量提交所有作业，请稍候...',
                      lambda ui: tasks.submit_all_works(ui, self.api, self.works),
                      on_result=lambda r: self.show_result(r['title'], r['text']))

    def export_all_courses(self):
        opts = self.export_options()
        self.run_task('正在导出所有课程的作业，请稍候...',
                      lambda ui: tasks.export_all_courses(ui, self.api, self.courses, opts),
                      on_result=lambda r: self.show_result(r['title'], r['text']))

    def export_all_works(self):
        opts = self.export_options()
        self.run_task('正在导出当前课程的所有作业，请稍候...',
                      lambda ui: tasks.export_all_works(ui, self.api, self.works,
                                                        self.selected_course_id,
                                                        self.selected_course_name, opts),
                      on_result=lambda r: self.show_result(r['title'], r['text']))

    def collect_work(self, work):
        """单个作业“导出所有题目”。"""
        work_name = exporter.clean_name(work['workName'])
        course_name = exporter.clean_name(self.selected_course_name)
        opts = self.export_options()
        self.run_task(f'收集作业 {work_name} 的题目',
                      lambda ui: tasks.collect_single(ui, self.api, work['workId'], work_name,
                                                      course_name, self.selected_course_id,
                                                      opts, 100),
                      on_result=lambda r: None,
                      mode='indeterminate', status='开始收集题目，请稍候...', start=True,
                      error_after=(1000, '导出失败',
                                   f"作业 '{work_name}' 导出失败，可能是网络错误或该作业没有题目"))
