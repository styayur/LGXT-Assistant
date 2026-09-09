# -*- coding: utf-8 -*-
"""UI LAYOUT 2.0：Developer Workbench 主窗口。

结构：Header(品牌/面包屑/连接态) · Sidebar(188) · PageHeader · CommandBar ·
Content(可含 Inspector) · 内嵌 TaskPanel · StatusBar。

线程安全：worker 只向 queue 投事件，主线程 after() 轮询更新 UI。
"""
import io
import os
import queue
import threading
import time
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
SIDEBAR_W = 188
PAD = 24          # 内容左右边距
GAP = 10          # 按钮组内间距
GROUP = 20        # 按钮组间间距


def mono(parent, text, fg=theme.MUTED, size=9, bg=theme.BG):
    return tk.Label(parent, text=text, bg=bg, fg=fg,
                    font=('Consolas', size), anchor='w')


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(SERVICE)
        self.root.minsize(1200, 800)
        self.root.configure(bg=theme.BG)
        self.style = ttk.Style('darkly')
        theme.apply_theme(self.style)

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

        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
        self.settings = config.Settings(self.config_file)
        self.export_path = self.settings.export_path
        self.export_word_var = tk.BooleanVar(value=self.settings.export_word)
        self.export_word_include_answers_var = tk.BooleanVar(value=self.settings.export_word_include_answers)
        self.export_pdf_var = tk.BooleanVar(value=self.settings.export_pdf)
        self.export_pdf_include_answers_var = tk.BooleanVar(value=self.settings.export_pdf_include_answers)

        self._token = 0
        self._task_tag = 0
        self.queue = queue.Queue()
        self.progress_window = None      # 兼容旧适配器（现为内嵌面板）
        self._task_panel = None
        self.status_label = None
        self.progress_bar = None

        self._sel_work = None            # Works 页当前选中作业
        self._sel_qidx = None            # Questions 页当前选中题号
        self._last_sync = None           # 页面最近一次同步时刻（真实值）

        self.setup_ui()
        self.set_state('STANDBY')
        self.set_page('AUTH')
        self.show_login()
        self.root.after(60, self._poll_queue)

    # ---------- 窗口框架（LAYOUT 2.0 Shell） ----------

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=YES)

        # Header：品牌 | breadcrumb | ● 连接态
        header = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=46)
        header.pack(side=TOP, fill=X)
        header.pack_propagate(False)
        tk.Label(header, text='LGXT::ASSISTANT', bg=theme.BG_RAISED, fg=theme.PRIMARY,
                 font=('Consolas', 12, 'bold')).pack(side=LEFT, padx=(24, 0))
        tk.Frame(header, bg=theme.BORDER, width=1).pack(side=LEFT, fill=Y, padx=20, pady=12)
        self.page_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.MUTED,
                                   font=('Consolas', 11))
        self.page_label.pack(side=LEFT)
        self.state_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.DIM,
                                    font=('Consolas', 9, 'bold'))
        self.state_label.pack(side=RIGHT, padx=24)
        tk.Frame(self.main_frame, bg=theme.BORDER, height=1).pack(side=TOP, fill=X)

        # StatusBar：左日志 / 右版本（API/AUTH 细节移入设置页系统信息）
        tk.Frame(self.main_frame, bg=theme.BORDER, height=1).pack(side=BOTTOM, fill=X)
        statusbar = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=24)
        statusbar.pack(side=BOTTOM, fill=X)
        statusbar.pack_propagate(False)
        self.log_label = tk.Label(statusbar, text='> SYSTEM READY', bg=theme.BG_RAISED,
                                  fg=theme.DIM, font=('Consolas', 8), anchor='w')
        self.log_label.pack(side=LEFT, fill=X, expand=YES, padx=12)
        tk.Label(statusbar, text='v3.0 · GPL-3.0', bg=theme.BG_RAISED, fg=theme.DIM,
                 font=('Consolas', 8)).pack(side=RIGHT, padx=12)

        body = tk.Frame(self.main_frame, bg=theme.BG)
        body.pack(side=TOP, fill=BOTH, expand=YES)
        self.create_sidebar(body)
        tk.Frame(body, bg=theme.BORDER, width=1).pack(side=LEFT, fill=Y)
        self.content_frame = ttk.Frame(body, padding=(PAD, 16, PAD, 16))
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=YES)

    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=theme.SURFACE, width=SIDEBAR_W)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text='LGXT', bg=theme.SURFACE, fg=theme.PRIMARY,
                 font=('Consolas', 13, 'bold'), anchor='w').pack(fill=X, padx=16, pady=(18, 0))
        tk.Label(sidebar, text='理工学堂助手', bg=theme.SURFACE, fg=theme.FG,
                 font=('Microsoft YaHei', 10, 'bold'), anchor='w').pack(fill=X, padx=16)
        tk.Frame(sidebar, bg=theme.BORDER, height=1).pack(fill=X, padx=12, pady=12)

        def section(text):
            tk.Label(sidebar, text=text, bg=theme.SURFACE, fg=theme.DIM, anchor='w',
                     font=('Consolas', 8, 'bold')).pack(fill=X, padx=16, pady=(0, 4))

        def item(text, command, indent=True):
            lbl = tk.Label(sidebar, text=('  ' + text if indent else text), bg=theme.SURFACE,
                           fg=theme.MUTED, anchor='w', font=theme.FONT_UI, cursor='hand2',
                           padx=8, pady=6)
            lbl.pack(fill=X, padx=(8, 4))
            lbl.bind('<Enter>', lambda e: lbl.configure(bg=theme.HOVER, fg=theme.FG))
            lbl.bind('<Leave>', lambda e: lbl.configure(bg=theme.SURFACE, fg=theme.MUTED))
            lbl.bind('<Button-1>', lambda e: command())
            return lbl

        section('WORKSPACE')
        item('课程列表', self.show_courses)
        section('SYSTEM')
        item('设置', self.show_settings)
        item('帮助', self.show_help)
        item('退出', self.root.quit)

        tk.Frame(sidebar, bg=theme.BORDER, height=1).pack(side=BOTTOM, fill=X)
        tk.Label(sidebar, text='v3.0.0', bg=theme.SURFACE, fg=theme.FG,
                 font=('Consolas', 8), anchor='w').pack(side=BOTTOM, fill=X, padx=16, pady=(0, 14))

    # ---------- 页面骨架（PageHeader / CommandBar / 面板） ----------

    def page_header(self, title, subtitle='', back=None):
        """标准 Page Header：标题 + 可选 meta + 可选返回，返回容器供页面加右侧动作。"""
        bar = tk.Frame(self.content_frame, bg=theme.BG)
        bar.pack(fill=X, pady=(0, 8))
        left = tk.Frame(bar, bg=theme.BG)
        left.pack(side=LEFT)
        if back:
            tk.Button(left, text='‹ ' + back, command=self._go(back), relief='flat', bd=0,
                      bg=theme.BG, fg=theme.SECONDARY, activebackground=theme.HOVER,
                      activeforeground=theme.SECONDARY, font=('Consolas', 9), cursor='hand2'
                      ).pack(side=LEFT, padx=(0, 16), pady=4)
        tk.Label(left, text=title, bg=theme.BG, fg=theme.FG,
                 font=('Microsoft YaHei', 17, 'bold')).pack(side=LEFT)
        if subtitle:
            mono(left, '  ' + subtitle, fg=theme.DIM, size=9).pack(side=LEFT, pady=(6, 0))
        return bar

    def command_bar(self):
        """Command Bar 容器：页面在返回的 frame 上自由放置左/右分组按钮。"""
        bar = tk.Frame(self.content_frame, bg=theme.BG_RAISED, height=44)
        bar.pack(fill=X, pady=(0, 14))
        bar.pack_propagate(False)
        return bar

    def btn(self, parent, text, command, kind='primary'):
        style = {'primary': 'primary', 'secondary': 'secondary', 'info': 'info',
                 'warning': 'warning', 'danger': 'danger', 'ghost': 'secondary'}[kind]
        return ttk.Button(parent, text=text, command=command, bootstyle=style, cursor='hand2')

    def _go(self, page):
        return {'课程列表': self.show_courses,
                '作业列表': self.show_works,
                '返回课程列表': self.show_courses}[page]

    # ---------- 状态 / 导航辅助 ----------

    def set_page(self, text):
        self.page_label.configure(text=f':: {text}')

    def set_state(self, text):
        colors = {'STANDBY': theme.DIM, 'READY': theme.PRIMARY, 'CONNECTED': theme.PRIMARY,
                  'PROCESSING': theme.WARNING, 'ERROR': theme.ERROR, 'OFFLINE': theme.DIM}
        label = '● ' + text if text in ('READY', 'CONNECTED', 'PROCESSING') else '○ ' + text
        self.state_label.configure(text=label, fg=colors.get(text, theme.DIM))

    def log(self, text):
        self._write_log(text)

    def _write_log(self, text):
        text = str(text).replace('\n', ' | ').strip()
        if self.log_label is not None and self.log_label.winfo_exists():
            self.log_label.configure(text=f'> {text[:130]}')

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self._task_panel = None
        self.status_label = None
        self.progress_bar = None

    def begin_nav(self):
        self._token += 1
        self.clear_content()

    def fetch(self, job, on_done):
        token = self._token

        def work():
            try:
                result = job()
            except Exception as exc:
                result = (False, f'网络错误：{exc}')
            self.queue.put(('deliver', token, on_done, result))

        threading.Thread(target=work, daemon=True).start()

    # ---------- queue 轮询（主线程唯一更新点） ----------

    def _poll_queue(self):
        try:
            while True:
                self._handle_event(self.queue.get_nowait())
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
            pass

    # ---------- 任务面板（内嵌 Task Panel，替代独立弹窗） ----------

    def _destroy_progress(self):
        if self._task_panel is not None and self._task_panel.winfo_exists():
            self._task_panel.destroy()
        if self.progress_window is not None and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        self._task_panel = None
        self.progress_window = None
        self.status_label = None
        self.progress_bar = None
        self.set_state('CONNECTED' if self.username else 'OFFLINE')

    def open_progress(self, title, mode='determinate', status='', start=False):
        """在当前页面底部创建内嵌 Task Panel（不再弹独立小窗）。"""
        panel = tk.Frame(self.content_frame, bg=theme.SURFACE, highlightthickness=1,
                         highlightbackground=theme.BORDER)
        panel.pack(side=BOTTOM, fill=X, pady=(0, 0))
        tk.Label(panel, text=f'> {title}', bg=theme.SURFACE, fg=theme.PRIMARY,
                 font=('Consolas', 9, 'bold'), anchor='w').pack(fill=X, padx=12, pady=(8, 0))
        self.status_label = tk.Label(panel, text=status, bg=theme.SURFACE, fg=theme.MUTED,
                                     font=('Consolas', 9), anchor='w')
        self.status_label.pack(fill=X, padx=12, pady=(4, 4))
        self.progress_bar = ttk.Progressbar(panel, mode=mode, length=200)
        self.progress_bar.pack(fill=X, padx=12, pady=(0, 10))
        if start:
            self.progress_bar.start()
        self._task_panel = panel
        self.progress_window = None
        self.set_state('PROCESSING')
        self.log(f'任务开始 :: {title}')
        return panel

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
        """主线程读取导出开关，生成 worker 只读快照。"""
        return ExportOptions(self.export_path,
                             self.export_word_var.get(),
                             self.export_word_include_answers_var.get(),
                             self.export_pdf_var.get(),
                             self.export_pdf_include_answers_var.get())

    # ---------- 登录 ----------

    def show_login(self):
        self.begin_nav()
        self.set_page('AUTH')
        self.set_state('OFFLINE')
        self.log('AUTH required')

        panel = tk.Frame(self.content_frame, bg=theme.SURFACE, highlightthickness=1,
                         highlightbackground=theme.BORDER)
        panel.pack(expand=YES)
        tk.Label(panel, text='AUTHENTICATION', bg=theme.SURFACE, fg=theme.PRIMARY,
                 font=('Consolas', 15, 'bold')).pack(anchor='w', padx=32, pady=(28, 2))
        tk.Label(panel, text='输入理工学堂账号以建立会话。', bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_UI).pack(anchor='w', padx=32, pady=(0, 20))

        form = tk.Frame(panel, bg=theme.SURFACE)
        form.pack(anchor='w', padx=32, pady=(0, 8))
        tk.Label(form, text='USERNAME', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 9)).grid(row=0, column=0, sticky='w', pady=4)
        self.username_entry = ttk.Entry(form, width=40)
        self.username_entry.grid(row=0, column=1, padx=(16, 0), pady=4)
        tk.Label(form, text='PASSWORD', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 9)).grid(row=1, column=0, sticky='w', pady=4)
        self.password_entry = ttk.Entry(form, width=40, show='*')
        self.password_entry.grid(row=1, column=1, padx=(16, 0), pady=4)

        self.remember_var = tk.BooleanVar()
        ttk.Checkbutton(panel, text='记住密码（本地凭据库）', variable=self.remember_var,
                        bootstyle='round-toggle').pack(anchor='w', padx=32, pady=(4, 14))
        self.login_button = ttk.Button(panel, text='LOGIN ▸ 登录', command=self.login,
                                       bootstyle='primary', width=24)
        self.login_button.pack(anchor='w', padx=32, pady=(0, 28))

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
                self.set_state('CONNECTED')
                self.log('AUTH ok')
                self.show_courses()
            else:
                self.set_state('ERROR')
                self.log('AUTH failed')
                Messagebox.show_error(message=msg, title='登录失败')

        self.fetch(lambda: self.api.login(self.username, self.password), on_done)

    # ---------- 课程（Courses Workspace） ----------

    def show_courses(self):
        if not self.username or not self.password:
            Messagebox.show_error(title='错误', message='请先登录')
            self.show_login()
            return
        self.begin_nav()
        self.set_page('COURSES')
        self.log('LOADING courses...')
        self.fetch(self.api.get_my_courses, self._render_courses)

    def _render_courses(self, result):
        ok, data = result
        self.begin_nav()
        self.set_page('COURSES')
        bar = self.page_header('COURSES')
        if ok:
            self.courses = data
            self._last_sync = time.strftime('%H:%M:%S')
            subtitle = f'{len(data)} courses · synced {self._last_sync}'
        else:
            self.set_state('ERROR')
            subtitle = 'sync failed · 请检查网络后重试'
        mono(bar, '  ' + subtitle, fg=theme.DIM, size=9).pack(side=LEFT, pady=(10, 0))

        cmd = self.command_bar()
        actions = tk.Frame(cmd, bg=theme.BG_RAISED)
        actions.pack(side=RIGHT)
        self.btn(actions, 'REFRESH', self.show_courses, 'secondary').pack(side=LEFT, padx=(0, GAP))
        self.btn(actions, 'EXPORT ALL', self.export_all_courses, 'info').pack(side=LEFT, padx=(0, GAP))
        self.btn(actions, 'SUBMIT ALL 100', self.submit_all_courses_100, 'warning').pack(side=LEFT)

        frame = ScrolledFrame(self.content_frame, autohide=True)
        frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(frame, bg=theme.BG)
        lst.pack(fill=BOTH, expand=YES)
        if not ok:
            empty = tk.Frame(lst, bg=theme.SURFACE, highlightthickness=1,
                             highlightbackground=theme.BORDER)
            empty.pack(fill=X, pady=(0, GAP))
            mono(empty, '> ERROR', fg=theme.ERROR, size=10).pack(anchor='w', padx=12, pady=(8, 0))
            tk.Label(empty, text='获取课程列表失败 · 请检查网络后重试', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_UI, anchor='w').pack(anchor='w', padx=12, pady=(0, 8))
            return
        for course in self.courses:
            self._course_row(lst, course)

    def _course_row(self, parent, course):
        row = tk.Frame(parent, bg=theme.SURFACE, highlightthickness=1,
                       highlightbackground=theme.BORDER)
        row.pack(fill=X, pady=(0, GAP - 2))
        self.btn(row, 'OPEN', lambda c=course: self.select_course(c), 'primary'
                 ).pack(side=RIGHT, padx=12, pady=10)
        mono(row, f'#{course["courseId"]}', fg=theme.DIM, size=9, bg=theme.SURFACE).pack(side=RIGHT, padx=(0, 4))
        name = course['courseName']
        tk.Label(row, text=name, bg=theme.SURFACE, fg=theme.FG, anchor='w',
                 font=('Microsoft YaHei', 11, 'bold')).pack(side=LEFT, fill=X, expand=YES,
                                                            padx=12, pady=11)

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

    # ---------- 作业（List + Inspector） ----------

    def show_works(self):
        self.begin_nav()
        self._sel_work = self.works[0] if self.works else None
        self.set_page(f'{self.selected_course_name} :: WORKS')
        bar = self.page_header('ASSIGNMENTS',
                               f'{self.selected_course_name} · {len(self.works)} works',
                               back='返回课程列表')
        self._build_works_page()

    def refresh_works(self):
        course = {'courseId': self.selected_course_id, 'courseName': self.selected_course_name}
        self.select_course(course)

    def _build_works_page(self):
        # Command Bar（批量动作）
        cmd = self.command_bar()
        right = tk.Frame(cmd, bg=theme.BG_RAISED)
        right.pack(side=RIGHT)
        self.btn(right, 'REFRESH', self.refresh_works, 'secondary').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'EXPORT ALL', self.export_all_works, 'info').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'SUBMIT ALL 100', self.submit_all_works_100, 'warning').pack(side=LEFT)

        # 左：作业列表；右：Inspector
        body = tk.Frame(self.content_frame, bg=theme.BG)
        body.pack(fill=BOTH, expand=YES)
        list_box = tk.Frame(body, bg=theme.BG, width=420)
        list_box.pack(side=LEFT, fill=BOTH, expand=YES)
        list_box.pack_propagate(False)

        head = tk.Frame(list_box, bg=theme.BG)
        head.pack(fill=X, pady=(0, 8))
        mono(head, 'ASSIGNMENTS', fg=theme.DIM, size=9, bg=theme.BG).pack(side=LEFT)

        frame = ScrolledFrame(list_box, autohide=True)
        frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(frame, bg=theme.BG)
        lst.pack(fill=BOTH, expand=YES)

        if not self.works:
            empty = tk.Frame(lst, bg=theme.SURFACE, highlightthickness=1,
                             highlightbackground=theme.BORDER)
            empty.pack(fill=X)
            mono(empty, '> NO WORKSPACE DATA', fg=theme.PRIMARY, size=9,
                 bg=theme.SURFACE).pack(anchor='w', padx=12, pady=(8, 0))
            tk.Label(empty, text='该课程目前没有可用的作业。', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_UI, anchor='w').pack(anchor='w', padx=12, pady=(0, 8))
        else:
            for work in self.works:
                self._work_row(lst, work)

        self._inspector = tk.Frame(body, bg=theme.SURFACE, width=300,
                                   highlightthickness=1, highlightbackground=theme.BORDER)
        self._inspector.pack(side=RIGHT, fill=Y, padx=(16, 0))
        self._inspector.pack_propagate(False)
        self._render_work_inspector()

    def _work_row(self, parent, work):
        selected = (work is self._sel_work)
        bg = theme.HOVER if selected else theme.SURFACE
        row = tk.Frame(parent, bg=bg, highlightthickness=1,
                       highlightbackground=theme.PRIMARY if selected else theme.BORDER)
        row.pack(fill=X, pady=(0, 6))
        row.bind('<Button-1>', lambda e, w=work: self._select_work(w))
        row.bind('<Double-Button-1>', lambda e, w=work: self._open_work(w))
        name = work['workName']
        name_lbl = tk.Label(row, text=name, bg=bg, fg=theme.FG, anchor='w',
                            font=('Microsoft YaHei', 10, 'bold'))
        name_lbl.pack(fill=X, padx=12, pady=(8, 0))
        line = tk.Frame(row, bg=bg)
        line.pack(fill=X, padx=12, pady=(2, 8))
        times_used = work.get('times', 0)
        try_times = work.get('tryTimes', 0)
        remaining = max(0, try_times - times_used)
        if remaining <= 0:
            chips = [mono(line, f'#{work["workId"]}', fg=theme.DIM, size=9, bg=bg),
                     mono(line, '已用完所有机会', fg=theme.ERROR, size=9, bg=bg)]
        elif remaining == 1:
            chips = [mono(line, f'#{work["workId"]}', fg=theme.DIM, size=9, bg=bg),
                     mono(line, f'Last chance! {remaining}/{try_times}', fg=theme.WARNING, size=9, bg=bg)]
        else:
            chips = [mono(line, f'#{work["workId"]}', fg=theme.DIM, size=9, bg=bg),
                     mono(line, f'TRY {remaining}/{try_times}', fg=theme.PRIMARY, size=9, bg=bg)]
        for c in chips:
            c.pack(side=LEFT, padx=(0, 12))
        # 整行可点选/双击打开
        for w in [row, name_lbl, line] + chips:
            w.bind('<Button-1>', lambda e, wk=work: self._select_work(wk))
            w.bind('<Double-Button-1>', lambda e, wk=work: self._open_work(wk))

    def _select_work(self, work):
        self._sel_work = work
        self.clear_content()
        self._build_works_page()

    def _render_work_inspector(self):
        work = self._sel_work
        head = tk.Label(self._inspector, text='INSPECTOR', bg=theme.SURFACE, fg=theme.DIM,
                        font=('Consolas', 8, 'bold'), anchor='w')
        head.pack(fill=X, padx=12, pady=(10, 2))
        body = tk.Frame(self._inspector, bg=theme.SURFACE)
        body.pack(fill=X, padx=12)
        if work is None:
            tk.Label(body, text='未选择作业', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.FONT_UI, anchor='w').pack(anchor='w', pady=12)
            return
        mono(body, work['workName'], fg=theme.FG, size=10, bg=theme.SURFACE).pack(anchor='w', pady=(2, 0))

        def field(k, label):
            rowf = tk.Frame(body, bg=theme.SURFACE)
            rowf.pack(fill=X, pady=3)
            tk.Label(rowf, text=label, bg=theme.SURFACE, fg=theme.DIM,
                     font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
            val = work.get(k)
            shown = str(val) if val not in (None, '') else '—'
            mono(rowf, shown, fg=theme.MUTED, size=9, bg=theme.SURFACE).pack(side=LEFT)

        field('workId', 'ID')
        field('chapterName', 'CHAPTER')
        field('expireTime', 'DUE')
        if work.get('grade') is not None:
            field('grade', 'SCORE')

        acts = tk.Frame(self._inspector, bg=theme.SURFACE)
        acts.pack(fill=X, padx=12, pady=(8, 12))
        self.btn(acts, 'OPEN ▸ 题目', lambda: self._open_work(work), 'primary'
                 ).pack(fill=X, pady=(0, 8))
        self.btn(acts, 'EXPORT 题目', lambda: self.collect_work(work), 'info').pack(fill=X)

    def _open_work(self, work):
        self.select_work(work)

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

    # ---------- 题目（List + View + Inspector） ----------

    def show_questions(self):
        self.begin_nav()
        self._sel_qidx = 0 if self.questions else None
        self.set_page(f'{self.selected_work_name} :: QUESTIONS')
        self._layout_questions()

    def _layout_questions(self):
        self.clear_content()
        bar = self.page_header('QUESTIONS', f'{self.selected_work_name} · {len(self.questions)} 题')
        back = tk.Button(bar, text='‹ 返回作业列表', command=self.show_works, relief='flat', bd=0,
                         bg=theme.BG, fg=theme.SECONDARY, activebackground=theme.HOVER,
                         activeforeground=theme.SECONDARY, font=('Consolas', 9), cursor='hand2')
        back.pack(side=RIGHT, pady=8)

        body = tk.Frame(self.content_frame, bg=theme.BG)
        body.pack(fill=BOTH, expand=YES)

        # 左：题目列表
        lst_pane = tk.Frame(body, bg=theme.BG, width=230)
        lst_pane.pack(side=LEFT, fill=Y)
        lst_pane.pack_propagate(False)
        head = tk.Frame(lst_pane, bg=theme.BG)
        head.pack(fill=X, pady=(0, 8))
        mono(head, 'QUESTIONS', fg=theme.DIM, size=9, bg=theme.BG).pack(side=LEFT)
        lst_frame = ScrolledFrame(lst_pane, autohide=True)
        lst_frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(lst_frame, bg=theme.BG)
        lst.pack(fill=BOTH, expand=YES)
        for idx, q in enumerate(self.questions):
            self._qlist_row(lst, idx, q)

        # 中：题目视图
        view = tk.Frame(body, bg=theme.SURFACE, highlightthickness=1,
                        highlightbackground=theme.BORDER)
        view.pack(side=LEFT, fill=BOTH, expand=YES, padx=16)
        self._view = view
        self._view_image_holder = None

        # 右：Inspector
        inspector = tk.Frame(body, bg=theme.SURFACE, width=280,
                             highlightthickness=1, highlightbackground=theme.BORDER)
        inspector.pack(side=RIGHT, fill=Y)
        inspector.pack_propagate(False)
        self._inspector_q = inspector
        self._render_question_views()

    def _qlist_row(self, parent, idx, q):
        selected = (idx == self._sel_qidx)
        bg = theme.HOVER if selected else theme.SURFACE
        row = tk.Frame(parent, bg=bg, highlightthickness=1,
                       highlightbackground=theme.PRIMARY if selected else theme.BORDER)
        row.pack(fill=X, pady=(0, 5))
        id_lbl = tk.Label(row, text=f'Q{idx + 1:02d}', bg=bg,
                          fg=theme.PRIMARY if selected else theme.MUTED,
                          font=('Consolas', 9, 'bold'))
        id_lbl.pack(side=LEFT, padx=(10, 8), pady=9)
        name_lbl = tk.Label(row, text=q.get('name', 'N/A'), bg=bg, fg=theme.FG, anchor='w',
                            font=theme.FONT_UI)
        name_lbl.pack(side=LEFT, fill=X, expand=YES, pady=9)
        for w in (row, id_lbl, name_lbl):
            w.bind('<Button-1>', lambda e, i=idx: self._select_question(i))

    def _select_question(self, idx):
        if idx == self._sel_qidx:
            return
        self._sel_qidx = idx
        self._layout_questions()

    def _current_q(self):
        if self.questions and self._sel_qidx is not None:
            return self.questions[self._sel_qidx]
        return None

    def _render_question_views(self):
        q = self._current_q()
        # 中央视图
        view = self._view
        tk.Label(view, text='QUESTION', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8, 'bold'), anchor='w').pack(fill=X, padx=16, pady=(10, 0))
        nav = tk.Frame(view, bg=theme.SURFACE)
        nav.pack(fill=X, padx=16, pady=(6, 2))
        tk.Button(nav, text='‹', command=lambda: self._step_q(-1), relief='flat', bd=0,
                  bg=theme.SURFACE, fg=theme.SECONDARY, cursor='hand2',
                  font=('Consolas', 12, 'bold')).pack(side=LEFT)
        tk.Label(nav, text=f'Q{self._sel_qidx + 1} / {len(self.questions)}'
                 if q else '', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 9)).pack(side=LEFT, padx=12)
        tk.Button(nav, text='›', command=lambda: self._step_q(1), relief='flat', bd=0,
                  bg=theme.SURFACE, fg=theme.SECONDARY, cursor='hand2',
                  font=('Consolas', 12, 'bold')).pack(side=LEFT)

        if q is None:
            mono(view, '> NO QUESTIONS', fg=theme.PRIMARY, size=10,
                 bg=theme.SURFACE).pack(anchor='w', padx=16, pady=24)
            return

        tk.Label(view, text=q.get('name', 'N/A'), bg=theme.SURFACE, fg=theme.FG, anchor='w',
                 font=('Microsoft YaHei', 12, 'bold')).pack(anchor='w', padx=16, pady=(6, 0))
        mono(view, f'ID {q.get("id", "N/A")}', fg=theme.DIM, size=9,
             bg=theme.SURFACE).pack(anchor='w', padx=16, pady=(2, 0))
        # 题面图片区
        img_area = tk.Frame(view, bg=theme.SURFACE)
        img_area.pack(anchor='w', padx=16, pady=(10, 0))
        imgurl = q.get('imgurl', 'N/A')
        if imgurl and imgurl != 'N/A':
            holder = tk.Label(img_area, text='> FETCHING IMAGE...', bg=theme.SURFACE,
                              fg=theme.DIM, font=('Consolas', 9), anchor='w')
            holder.pack()
            self._view_image_holder = holder
            self._load_image_async(holder, imgurl)
        else:
            mono(img_area, '[ NO IMAGE ]', fg=theme.DIM, size=9,
                 bg=theme.SURFACE).pack()

        # 右侧 Inspector
        ins = self._inspector_q
        tk.Label(ins, text='INSPECTOR', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8, 'bold'), anchor='w').pack(fill=X, padx=14, pady=(10, 0))
        body = tk.Frame(ins, bg=theme.SURFACE)
        body.pack(fill=X, padx=14)
        row = tk.Frame(body, bg=theme.SURFACE)
        row.pack(fill=X, pady=3)
        tk.Label(row, text='ANSWER', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
        ans = q.get('answer', 'N/A')
        tk.Label(body, text=str(ans), bg=theme.SURFACE, fg=theme.WARNING, anchor='w',
                 font=('Consolas', 10), justify='left', wraplength=220).pack(fill=X, pady=(0, 8))

        score = tk.Frame(ins, bg=theme.SURFACE)
        score.pack(fill=X, padx=14, pady=(4, 0))
        tk.Label(score, text='SCORE', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
        self.grade_entry = ttk.Entry(score, width=8)
        self.grade_entry.pack(side=LEFT)
        tk.Label(ins, text='提交成绩（0-100）', bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.FONT_UI).pack(anchor='w', padx=14, pady=(6, 0))
        self.submit_grade_button = self.btn(ins, 'SUBMIT', self.submit_grade, 'primary')
        self.submit_grade_button.pack(fill=X, padx=14, pady=(10, 14))

    def _step_q(self, delta):
        n = len(self.questions)
        if n == 0:
            return
        self._sel_qidx = (self._sel_qidx + delta) % n
        self._layout_questions()

    def _load_image_async(self, holder, imgurl):
        cache = getattr(self, '_img_bytes', None)
        if cache is None:
            cache = {}
            self._img_bytes = cache
        if imgurl in cache:
            self.queue.put(('image_bytes', holder, cache[imgurl], None))
            return

        def work():
            try:
                data = self.api.fetch_image(imgurl)
                cache[imgurl] = data
                self.queue.put(('image_bytes', holder, data, None))
            except Exception as exc:
                self.queue.put(('image_bytes', holder, None, str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _render_image(self, holder, data, error):
        if holder is None or not holder.winfo_exists():
            return
        parent = holder.master
        if error is not None:
            holder.config(text=f'[ IMAGE ERROR ] {error}', fg=theme.ERROR)
            return
        try:
            image = Image.open(io.BytesIO(data))
            image.thumbnail((460, 340))
            photo = ImageTk.PhotoImage(image)
        except Exception as exc:
            holder.config(text=f'[ IMAGE ERROR ] {exc}', fg=theme.ERROR)
            return
        holder.destroy()
        label = tk.Label(parent, image=photo, bg=theme.SURFACE)
        label.image = photo
        self.images.append(photo)
        label.pack()

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
        self.set_page('SETTINGS')
        self.page_header('SETTINGS')

        body = tk.Frame(self.content_frame, bg=theme.BG)
        body.pack(fill=BOTH, expand=YES)

        left = tk.Frame(body, bg=theme.BG)
        left.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 24))

        export_frame = ttk.Labelframe(left, text='EXPORT', padding=16)
        export_frame.pack(fill=X)
        opts = ttk.Frame(export_frame)
        opts.pack(fill=X)
        self.export_word_check = ttk.Checkbutton(opts, text='Word (.docx)', variable=self.export_word_var,
                                                 command=self.toggle_word_options)
        self.export_word_check.grid(row=0, column=0, sticky='w', padx=(0, 48), pady=5)
        self.export_word_answers_check = ttk.Checkbutton(opts, text='含答案', variable=self.export_word_include_answers_var)
        self.export_word_answers_check.grid(row=1, column=0, sticky='w', padx=(24, 48), pady=5)
        self.export_pdf_check = ttk.Checkbutton(opts, text='PDF (.pdf)', variable=self.export_pdf_var,
                                                command=self.toggle_pdf_options)
        self.export_pdf_check.grid(row=0, column=1, sticky='w', pady=5)
        self.export_pdf_answers_check = ttk.Checkbutton(opts, text='含答案', variable=self.export_pdf_include_answers_var)
        self.export_pdf_answers_check.grid(row=1, column=1, sticky='w', padx=(24, 0), pady=5)
        self.toggle_word_options()
        self.toggle_pdf_options()

        path_frame = ttk.Labelframe(left, text='PATH', padding=16)
        path_frame.pack(fill=X, pady=(16, 0))
        path_row = ttk.Frame(path_frame)
        path_row.pack(fill=X)
        ttk.Label(path_row, text='导出路径').pack(side=LEFT)
        self.path_entry = ttk.Entry(path_row)
        self.path_entry.pack(side=LEFT, fill=X, expand=YES, padx=12)
        self.path_entry.insert(0, self.export_path)
        self.btn(path_row, 'BROWSE', self.choose_export_path, 'secondary').pack(side=LEFT)

        btns = tk.Frame(left, bg=theme.BG)
        btns.pack(fill=X, pady=(20, 0))
        self.btn(btns, 'SAVE', self.save_settings, 'primary').pack(side=LEFT, padx=(0, GAP))
        self.btn(btns, 'USER INFO', self.view_user_info, 'info').pack(side=LEFT)

        # 右侧系统信息面板（真实静态信息，非伪造指标）
        sys_panel = tk.Frame(body, bg=theme.SURFACE, width=300, highlightthickness=1,
                             highlightbackground=theme.BORDER)
        sys_panel.pack(side=RIGHT, fill=Y)
        sys_panel.pack_propagate(False)
        tk.Label(sys_panel, text='SYSTEM', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8, 'bold'), anchor='w').pack(fill=X, padx=16, pady=(12, 2))
        info = tk.Frame(sys_panel, bg=theme.SURFACE)
        info.pack(fill=X, padx=16)

        def sysrow(label, value):
            r = tk.Frame(info, bg=theme.SURFACE)
            r.pack(fill=X, pady=3)
            tk.Label(r, text=label, bg=theme.SURFACE, fg=theme.DIM,
                     font=('Consolas', 8), width=10, anchor='w').pack(side=LEFT)
            mono(r, value, fg=theme.MUTED, size=9, bg=theme.SURFACE).pack(side=LEFT)

        sysrow('API', self.api.base_url)
        sysrow('VERSION', '3.0')
        sysrow('LICENSE', 'GPL-3.0')
        sysrow('AUTH', 'token' if self.username else 'none')

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
                  foreground=theme.PRIMARY).pack(anchor='w', padx=24, pady=(16, 4))
        ttk.Label(content, text='LGXT Assistant · 理工学堂助手',
                  font=('Microsoft YaHei', 15, 'bold'), foreground=theme.FG).pack(anchor='w', padx=24)

        def head(text):
            ttk.Label(content, text=f'> {text}', font=('Consolas', 11, 'bold'),
                      foreground=theme.SECONDARY).pack(anchor='w', padx=24, pady=(12, 4))

        def line(text):
            ttk.Label(content, text=text, font=theme.FONT_UI, foreground=theme.MUTED,
                      justify='left').pack(anchor='w', padx=40, pady=1)

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
                   bootstyle='danger').pack(anchor='w', padx=40, pady=(20, 28))

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
