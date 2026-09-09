import configparser
import io
import os
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog
from tkinter.constants import *

import keyring
import requests
import ttkbootstrap as ttk
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, RGBColor
from PIL import Image, ImageTk
from reportlab.lib import colors
from reportlab.lib.units import inch
from requests.adapters import HTTPAdapter
from ttkbootstrap.dialogs import Messagebox
from urllib3.util.retry import Retry

try:  # ttkbootstrap < 2
    from ttkbootstrap.scrolled import ScrolledFrame
except ImportError:  # ttkbootstrap >= 2 exports ScrolledFrame at top level
    from ttkbootstrap import ScrolledFrame

base_url = "http://lgxt.wutp.com.cn/api"
headers = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
}

adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=Retry(
    total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["POST", "GET"]))
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)

DEFAULT_TIMEOUT = 5
SERVICE_NAME = '理工学堂'


def api_post(endpoint, data=None, fail_msg='请求失败'):
    """POST 到 API 并解包响应；成功返回 (True, data)，失败返回 (False, 错误信息)。"""
    try:
        response = session.post(f'{base_url}/{endpoint}', headers=headers,
                                data=data, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        if result['code'] == 0:
            return True, result['data']
        return False, f'{fail_msg}：{result["msg"]}'
    except requests.exceptions.RequestException as e:
        return False, f'网络错误：{e}'


def login(username, password):
    ok, data = api_post('login', {'loginName': username, 'password': password}, '登录失败')
    if ok:
        headers['Authorization'] = data
        session.headers.update({'Authorization': data})
        return True, '欢迎回来！'
    return False, data


def get_user_info():
    return api_post('userInfo', fail_msg='获取用户信息失败')


def get_my_courses():
    return api_post('myCourses', fail_msg='获取课程列表失败')


def get_course_works(course_id):
    return api_post('myCourseWorks', {'courseId': course_id}, '获取课程作业失败')


def get_questions(work_id):
    return api_post('showQuestions', {'workId': work_id}, '获取题目失败')


def submit_answer(work_id, grade):
    ok, data = api_post('submitAnswer', {'grade': grade, 'workId': work_id}, '答案提交失败')
    if ok:
        return True, f'答案提交成功，成绩：{grade}\n返回信息：{data}'
    return False, data


def clean_name(name):
    return ''.join(c for c in name if c not in r'<>:"/\|?*')

# ---- UI design tokens ----
BG = '#0B0D10'
BG_RAISED = '#0D1117'
SURFACE = '#11161D'
HOVER = '#18212B'
BORDER = '#232C37'
FG = '#D7E0EA'
MUTED = '#8B98A5'
DIM = '#5C6672'
PRIMARY = '#34D399'
SECONDARY = '#22D3EE'
WARNING = '#FBBF24'
ERROR = '#F87171'
FONT_UI = ('Microsoft YaHei', 10)
FONT_MONO = ('Consolas', 10)

class ModernApp:
    def __init__(self, main_window):
        self.root = main_window
        self.root.title('理工学堂助手')
        self.root.minsize(1100, 800)
        self.root.configure(bg=BG)
        self.style = ttk.Style('darkly')

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

        self.export_path = os.getcwd()
        self.export_word_var = tk.BooleanVar(value=True)
        self.export_word_include_answers_var = tk.BooleanVar(value=True)
        self.export_pdf_var = tk.BooleanVar(value=False)
        self.export_pdf_include_answers_var = tk.BooleanVar(value=True)

        self.config = configparser.ConfigParser()
        self.config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
        self.load_config()

        self.setup_ui()
        self.set_state('STANDBY')
        self.set_page('未连接')
    def setup_ui(self):
        self.apply_theme()
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=YES)

        # ---- header ----
        header = tk.Frame(self.main_frame, bg=BG_RAISED, height=42)
        header.pack(side=TOP, fill=X)
        header.pack_propagate(False)
        tk.Label(header, text='LGXT::ASSISTANT', bg=BG_RAISED, fg=PRIMARY,
                 font=('Consolas', 11, 'bold')).pack(side=LEFT, padx=(16, 0))
        tk.Frame(header, bg=BORDER, width=1).pack(side=LEFT, fill=Y, padx=14, pady=9)
        self.page_label = tk.Label(header, text='', bg=BG_RAISED, fg=MUTED, font=('Consolas', 10))
        self.page_label.pack(side=LEFT)
        self.state_label = tk.Label(header, text='', bg=BG_RAISED, fg=DIM, font=('Consolas', 10, 'bold'))
        self.state_label.pack(side=RIGHT, padx=16)
        tk.Frame(self.main_frame, bg=BORDER, height=1).pack(side=TOP, fill=X)

        # ---- status bar ----
        tk.Frame(self.main_frame, bg=BORDER, height=1).pack(side=BOTTOM, fill=X)
        statusbar = tk.Frame(self.main_frame, bg=BG_RAISED, height=24)
        statusbar.pack(side=BOTTOM, fill=X)
        statusbar.pack_propagate(False)
        tk.Label(statusbar, text='v3.0.0  ·  GPL-3.0  ·  Styayur', bg=BG_RAISED, fg=DIM,
                 font=('Consolas', 8)).pack(side=LEFT, padx=10)
        self.auth_label = tk.Label(statusbar, text='AUTH none', bg=BG_RAISED, fg=DIM,
                                   font=('Consolas', 8))
        self.auth_label.pack(side=RIGHT, padx=10)
        tk.Label(statusbar, text='API http://lgxt.wutp.com.cn/api', bg=BG_RAISED, fg=DIM,
                 font=('Consolas', 8)).pack(side=RIGHT, padx=10)

        # ---- body ----
        body = tk.Frame(self.main_frame, bg=BG)
        body.pack(side=TOP, fill=BOTH, expand=YES)
        self.create_sidebar(body)
        tk.Frame(body, bg=BORDER, width=1).pack(side=LEFT, fill=Y)
        self.content_frame = ttk.Frame(body, padding=(18, 14))
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=YES)

    def apply_theme(self):
        self.style.configure('TFrame', background=BG)
        self.style.configure('TLabel', background=BG, foreground=FG)
        self.style.configure('TButton', font=FONT_UI)
        self.style.configure('TLabelframe', background=BG, bordercolor=BORDER, relief='solid', borderwidth=1)
        self.style.configure('TLabelframe.Label', background=BG, foreground=MUTED, font=FONT_UI)
        self.style.configure('TEntry', fieldbackground=SURFACE, foreground=FG,
                             insertcolor=PRIMARY, bordercolor=BORDER)
        self.style.configure('TCheckbutton', background=BG, foreground=FG, font=FONT_UI)
        self.style.configure('TProgressbar', background=PRIMARY, troughcolor=SURFACE, bordercolor=BORDER)
        self.style.configure('Horizontal.TProgressbar', background=PRIMARY, troughcolor=SURFACE, bordercolor=BORDER)

        schemes = {
            'primary':   ('#143D31', '#A7F3D0', '#1B5A47', '#0C241C'),
            'secondary': ('#232C37', '#C9D4DE', '#303C49', '#1A212A'),
            'info':      ('#103A4C', '#A5F3FC', '#15566E', '#0A2834'),
            'warning':   ('#3A2A0B', '#FDE68A', '#54400F', '#2A1E07'),
            'danger':    ('#421515', '#FCA5A5', '#5E1F1F', '#330F0F'),
        }
        for name, (bg, fg, active, pressed) in schemes.items():
            self.style.configure(f'{name}.TButton', background=bg, foreground=fg)
            self.style.map(f'{name}.TButton',
                           background=[('pressed', '!disabled', pressed), ('active', active)],
                           foreground=[('pressed', fg), ('disabled', '#5C6672')])
    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=SURFACE, width=216)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text='理工学堂助手', bg=SURFACE, fg=FG,
                 font=('Microsoft YaHei', 13, 'bold'), anchor='w').pack(fill=X, padx=14, pady=(16, 2))
        tk.Label(sidebar, text='developer workbench', bg=SURFACE, fg=DIM,
                 font=('Consolas', 8)).pack(fill=X, padx=14)

        def nav_section(text):
            tk.Label(sidebar, text=text, bg=SURFACE, fg=DIM, anchor='w',
                     font=('Consolas', 8, 'bold')).pack(fill=X, padx=14, pady=(14, 4))

        def nav_item(text, command):
            item = tk.Label(sidebar, text=text, bg=SURFACE, fg=MUTED, anchor='w',
                            font=FONT_UI, cursor='hand2', padx=10, pady=6)
            item.pack(fill=X, padx=8)
            item.bind('<Enter>', lambda e: item.configure(bg=HOVER, fg=FG))
            item.bind('<Leave>', lambda e: item.configure(bg=SURFACE, fg=MUTED))
            item.bind('<Button-1>', lambda e: command())
            return item

        nav_section('WORKSPACE')
        nav_item('  课程列表', self.show_courses_page)
        nav_section('SYSTEM')
        nav_item('  设置', self.show_settings_page)
        nav_item('  帮助', self.show_help)
        nav_item('  退出', self.root.quit)

        tk.Frame(sidebar, bg=BORDER, height=1).pack(side=BOTTOM, fill=X)
        info = tk.Frame(sidebar, bg=SURFACE)
        info.pack(side=BOTTOM, fill=X, pady=8)
        for line, color in [('v3.0.0', FG), ('GPL-3.0', DIM), ('by Styayur', DIM)]:
            tk.Label(info, text=line, bg=SURFACE, fg=color,
                     font=('Consolas', 8), anchor='w').pack(fill=X, padx=14)

    def set_page(self, text):
        self.page_label.configure(text=f':: {text}')

    def set_state(self, text):
        colors = {'STANDBY': DIM, 'READY': PRIMARY, 'PROCESSING': WARNING, 'ERROR': ERROR}
        self.state_label.configure(text=f'[ {text} ]', fg=colors.get(text, DIM))

    def set_auth(self, ok):
        self.auth_label.configure(text='AUTH token' if ok else 'AUTH none',
                                  fg=PRIMARY if ok else DIM)
    def show_help(self):
        help_window = ttk.Toplevel(self.root)
        help_window.title('帮助')
        help_window.geometry('980x760')
        help_window.minsize(720, 520)

        content = ScrolledFrame(help_window, autohide=True)
        content.pack(fill=BOTH, expand=YES)

        ttk.Label(content, text='MANUAL :: 使用说明', font=('Consolas', 13, 'bold'),
                  foreground=PRIMARY).pack(anchor='w', padx=18, pady=(14, 4))
        ttk.Label(content, text='LGXT Assistant · 理工学堂助手', font=('Microsoft YaHei', 15, 'bold'),
                  foreground=FG).pack(anchor='w', padx=18)

        def head(text):
            ttk.Label(content, text=f'> {text}', font=('Consolas', 11, 'bold'),
                      foreground=SECONDARY).pack(anchor='w', padx=18, pady=(12, 4))

        def line(text):
            ttk.Label(content, text=text, font=FONT_UI, foreground=MUTED,
                      justify='left').pack(anchor='w', padx=30, pady=1)

        head('功能介绍')
        for t in [
            '1. 登录：输入用户名和密码进行登录。',
            '2. 课程列表：查看所有课程并选择查看作业。',
            '3. 作业列表：查看选定课程的所有作业。',
            '4. 题目列表：查看选定作业的所有题目。',
            '5. 设置：配置导出路径和格式。',
            '6. 帮助：查看本帮助信息。',
        ]:
            line(t)

        head('操作指南')
        for t in [
            '1. 登录后，点击课程列表查看所有课程。',
            '2. 在课程列表中，点击查看作业查看该课程的所有作业。',
            '3. 在作业列表中，点击查看题目查看该作业的所有题目。',
            '4. 在题目列表中，可以导出题目或提交成绩。',
            '5. 在设置页面，可以配置导出路径和格式。',
        ]:
            line(t)

        head('声明 · LICENSE')
        for t in [
            '本工具仅限学习交流使用，请勿转卖或用于商业用途。',
            'LGXT v3.0 · Author: Styayur · License: GPL-3.0',
        ]:
            line(t)

        ttk.Button(content, text='关闭', command=help_window.destroy,
                   bootstyle='danger').pack(anchor='w', padx=30, pady=(18, 24))
    def show_login_page(self):
        self.clear_content()
        self.set_page('AUTH · 登录')
        self.set_state('STANDBY')
        self.set_auth(False)

        panel = ttk.Frame(self.content_frame)
        panel.pack(expand=YES)
        ttk.Label(panel, text='$ connect lgxt', font=('Consolas', 14, 'bold'),
                  foreground=PRIMARY).pack(anchor='w')
        ttk.Label(panel, text='输入理工学堂账号以建立会话。', font=FONT_UI,
                  foreground=MUTED).pack(anchor='w', pady=(2, 16))

        user_row = ttk.Frame(panel)
        user_row.pack(fill=X, pady=3)
        ttk.Label(user_row, text='USERNAME', font=('Consolas', 9), width=10,
                  foreground=DIM).pack(side=LEFT)
        self.username_entry = ttk.Entry(user_row, width=34)
        self.username_entry.pack(side=LEFT)

        pass_row = ttk.Frame(panel)
        pass_row.pack(fill=X, pady=3)
        ttk.Label(pass_row, text='PASSWORD', font=('Consolas', 9), width=10,
                  foreground=DIM).pack(side=LEFT)
        self.password_entry = ttk.Entry(pass_row, width=34, show='*')
        self.password_entry.pack(side=LEFT)

        self.remember_var = tk.BooleanVar()
        ttk.Checkbutton(panel, text='记住密码（本地凭据库）', variable=self.remember_var,
                        bootstyle='round-toggle').pack(anchor='w', pady=(8, 4))
        ttk.Button(panel, text='LOGIN ▸ 登录', command=self.login,
                   bootstyle='primary', width=22).pack(anchor='w', pady=(6, 0))

        saved_username = self.get_saved_username()
        saved_password = None
        if saved_username:
            self.username_entry.insert(0, saved_username)
            saved_password = self.get_saved_password(saved_username)
            if saved_password:
                self.password_entry.insert(0, saved_password)
        self.remember_var.set(bool(saved_username and saved_password))
    def login(self):
        self.username = self.username_entry.get()
        self.password = self.password_entry.get()
        ok, msg = login(self.username, self.password)
        if ok:
            if self.remember_var.get():
                self.save_credentials(self.username, self.password)
            else:
                self.delete_saved_credentials()
            self.set_state('READY')
            self.set_auth(True)
            self.show_courses_page()
        else:
            self.set_state('ERROR')
            Messagebox.show_error(message=msg, title='登录失败')
    def show_courses_page(self):
        if not self.username or not self.password:
            Messagebox.show_error(title='错误', message='请先登录')
            self.show_login_page()
            return

        self.clear_content()
        self.set_page('课程列表')
        ttk.Label(self.content_frame, text='WORKSPACE :: 课程列表', font=('Consolas', 12, 'bold'),
                  foreground=FG).pack(anchor='w', pady=(2, 10))

        ok, data = get_my_courses()
        body_frame = ttk.Frame(self.content_frame)
        body_frame.pack(fill=BOTH, expand=YES)

        if ok:
            self.courses = data
            ttk.Label(body_frame, text=f'[ {len(data)} COURSES ]', font=('Consolas', 9),
                      foreground=DIM).pack(anchor='w', pady=(0, 6))
            frame = ScrolledFrame(body_frame, autohide=True)
            frame.pack(fill=BOTH, expand=YES)
            lst = tk.Frame(frame, bg=BG)
            lst.pack(fill=BOTH, expand=YES)
            for course in self.courses:
                self.create_course_card(lst, course)
        else:
            self.set_state('ERROR')
            panel = tk.Frame(body_frame, bg=SURFACE)
            panel.pack(fill=X, pady=6)
            tk.Label(panel, text='> ERROR', bg=SURFACE, fg=ERROR,
                     font=('Consolas', 10, 'bold'), anchor='w').pack(fill=X, padx=12, pady=(8, 0))
            tk.Label(panel, text='获取课程列表失败 · 请检查网络后重试', bg=SURFACE, fg=MUTED,
                     font=FONT_UI, anchor='w').pack(fill=X, padx=12, pady=(0, 8))

        actions = ttk.Frame(self.content_frame)
        actions.pack(fill=X, pady=(10, 0))
        ttk.Button(actions, text='提交全部作业100分', command=self.submit_all_courses_100,
                   bootstyle='warning').pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text='导出所有课程的作业', command=self.export_all_courses_assignments,
                   bootstyle='info').pack(side=LEFT)
    def create_course_card(self, parent, course):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill=X, pady=(0, 5))
        ttk.Button(row, text='查看', bootstyle='primary', cursor='hand2',
                   command=lambda: self.select_course(course['courseId'], course['courseName'])
                   ).pack(side=RIGHT, padx=10, pady=7)
        tk.Label(row, text=f'#{course["courseId"]}', bg=SURFACE, fg=DIM,
                 font=('Consolas', 9)).pack(side=RIGHT)
        tk.Label(row, text=course['courseName'], bg=SURFACE, fg=FG, anchor='w',
                 font=('Microsoft YaHei', 11, 'bold')).pack(side=LEFT, fill=X, expand=YES, padx=12, pady=9)
    def select_course(self, course_id, course_name):
        self.selected_course_id = course_id
        self.selected_course_name = course_name
        ok, data = get_course_works(course_id)
        if ok:
            self.works = data
            self.create_works_page()
        else:
            Messagebox.show_error(title='错误', message=data)

    def create_works_page(self):
        self.clear_content()
        self.set_page(f'{self.selected_course_name} · 作业')
        ttk.Label(self.content_frame, text=f'WORKSPACE :: {self.selected_course_name} :: 作业列表',
                  font=('Consolas', 12, 'bold'), foreground=FG).pack(anchor='w', pady=(2, 10))

        body_frame = ttk.Frame(self.content_frame)
        body_frame.pack(fill=BOTH, expand=YES)
        frame = ScrolledFrame(body_frame, autohide=True)
        frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(frame, bg=BG)
        lst.pack(fill=BOTH, expand=YES)

        if not self.works:
            panel = tk.Frame(lst, bg=SURFACE)
            panel.pack(fill=X, pady=6)
            tk.Label(panel, text='> NO WORKSPACE DATA', bg=SURFACE, fg=PRIMARY,
                     font=('Consolas', 10, 'bold'), anchor='w').pack(fill=X, padx=12, pady=(8, 0))
            tk.Label(panel, text='该课程目前没有可用的作业。', bg=SURFACE, fg=MUTED,
                     font=FONT_UI, anchor='w').pack(fill=X, padx=12, pady=(0, 8))
        else:
            ttk.Label(lst, text=f'[ {len(self.works)} WORKS ]', font=('Consolas', 9),
                      foreground=DIM).pack(anchor='w', pady=(0, 6))
            for work in self.works:
                self.create_work_card(lst, work)

        actions = ttk.Frame(self.content_frame)
        actions.pack(fill=X, pady=(10, 0))
        ttk.Button(actions, text='提交当前课程作业100分', command=self.submit_all_works_100,
                   bootstyle='warning').pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text='导出当前课程的所有作业', command=self.export_all_works_of_current_course,
                   bootstyle='info').pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text='返回课程列表', command=self.show_courses_page,
                   bootstyle='secondary').pack(side=LEFT)
    def create_work_card(self, parent, work):
        times_used = work.get('times', 0)
        try_times = work.get('tryTimes', 0)
        remaining = max(0, try_times - times_used)
        if remaining <= 0:
            status_text, status_color = '已用完所有机会', ERROR
        elif remaining == 1:
            status_text, status_color = f'Last chance! 剩余 {remaining}/{try_times} 次', WARNING
        else:
            status_text, status_color = f'剩余 {remaining}/{try_times} 次', PRIMARY

        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill=X, pady=(0, 5))
        head = tk.Frame(row, bg=SURFACE)
        head.pack(fill=X)
        ttk.Button(head, text='导出所有题目', bootstyle='info', cursor='hand2',
                   command=lambda: self.start_collecting_questions(work['workId'], work['workName'], self.selected_course_name)
                   ).pack(side=RIGHT, padx=(4, 10), pady=7)
        ttk.Button(head, text='查看题目', bootstyle='primary', cursor='hand2',
                   command=lambda: self.select_work(work['workId'], work['workName'])
                   ).pack(side=RIGHT, padx=4, pady=7)
        tk.Label(head, text=work['workName'], bg=SURFACE, fg=FG, anchor='w',
                 font=('Microsoft YaHei', 11, 'bold')).pack(side=LEFT, fill=X, expand=YES, padx=12, pady=9)

        detail = tk.Frame(row, bg=SURFACE)
        detail.pack(fill=X, padx=12, pady=(0, 8))
        tk.Label(detail, text=f'#{work["workId"]}', bg=SURFACE, fg=DIM,
                 font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        tk.Label(detail, text=status_text, bg=SURFACE, fg=status_color,
                 font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        if work.get('expireTime', 'N/A') != 'N/A':
            tk.Label(detail, text=f'DUE {work["expireTime"]}', bg=SURFACE, fg=MUTED,
                     font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        if work.get('chapterName'):
            tk.Label(detail, text=f'CH {work["chapterName"]}', bg=SURFACE, fg=MUTED,
                     font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
        if work.get('grade') is not None:
            tk.Label(detail, text=f'SCORE {work["grade"]}', bg=SURFACE, fg=SECONDARY,
                     font=('Consolas', 9)).pack(side=LEFT, padx=(0, 12))
    def select_work(self, work_id, work_name):
        self.selected_work_id = work_id
        self.selected_work_name = work_name
        ok, data = get_questions(work_id)
        if ok:
            self.questions = data
            self.create_questions_page()
        else:
            Messagebox.show_error(title='错误', message=data)

    def create_questions_page(self):
        self.clear_content()
        self.set_page(f'{self.selected_work_name} · 题目')
        ttk.Label(self.content_frame, text=f'QUESTIONS :: {self.selected_work_name}',
                  font=('Consolas', 12, 'bold'), foreground=FG).pack(anchor='w', pady=(2, 10))

        body_frame = ttk.Frame(self.content_frame)
        body_frame.pack(fill=BOTH, expand=YES)
        frame = ScrolledFrame(body_frame, autohide=True)
        frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(frame, bg=BG)
        lst.pack(fill=BOTH, expand=YES)
        ttk.Label(lst, text=f'[ {len(self.questions)} QUESTIONS ]', font=('Consolas', 9),
                  foreground=DIM).pack(anchor='w', pady=(0, 6))

        self.images = []
        for idx, question in enumerate(self.questions):
            self.create_question_card(lst, idx, question)

        bottom = ttk.Frame(self.content_frame)
        bottom.pack(fill=X, pady=(10, 0))
        ttk.Label(bottom, text='提交成绩（0-100）：', font=FONT_UI, foreground=MUTED).pack(side=LEFT)
        self.grade_entry = ttk.Entry(bottom, width=8)
        self.grade_entry.pack(side=LEFT, padx=6)
        ttk.Button(bottom, text='提交', command=self.submit_grade,
                   bootstyle='primary').pack(side=LEFT, padx=(0, 12))
        ttk.Button(bottom, text='返回作业列表', command=self.create_works_page,
                   bootstyle='secondary').pack(side=LEFT)
    def create_question_card(self, parent, idx, question):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill=X, pady=(0, 6))
        head = tk.Frame(row, bg=SURFACE)
        head.pack(fill=X)
        tk.Label(head, text=f'Q{idx + 1}', bg=SURFACE, fg=PRIMARY,
                 font=('Consolas', 11, 'bold')).pack(side=LEFT, padx=(12, 10), pady=8)
        tk.Label(head, text=question.get('name', 'N/A'), bg=SURFACE, fg=FG, anchor='w',
                 font=('Microsoft YaHei', 11)).pack(side=LEFT, fill=X, expand=YES, pady=8)
        tk.Label(head, text=f'ID {question.get("id", "N/A")}', bg=SURFACE, fg=DIM,
                 font=('Consolas', 9)).pack(side=RIGHT, padx=12)

        content = tk.Frame(row, bg=SURFACE)
        content.pack(fill=X, padx=12, pady=(0, 8))
        imgurl = question.get('imgurl', 'N/A')
        if imgurl and imgurl != 'N/A':
            self.load_and_display_image(content, imgurl)
        else:
            tk.Label(content, text='[ NO IMAGE ]', bg=SURFACE, fg=DIM,
                     font=('Consolas', 9), anchor='w').pack(fill=X)
        tk.Label(content, text=f'答案: {question.get("answer", "N/A")}', bg=SURFACE,
                 fg=WARNING, font=('Consolas', 10), anchor='w').pack(fill=X, pady=(4, 6))
    def load_and_display_image(self, parent, imgurl):
        try:
            response = session.get(imgurl)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            image.thumbnail((400, 300))
            photo = ImageTk.PhotoImage(image)
            self.images.append(photo)  # 保持引用，防止被回收
            tk.Label(parent, image=photo, bg=SURFACE).pack(anchor='w', pady=(4, 0))
        except Exception as e:
            tk.Label(parent, text=f'[ IMAGE ERROR ] {e}', bg=SURFACE, fg=ERROR,
                     font=('Consolas', 9), anchor='w').pack(fill=X)
    def submit_grade(self):
        grade = self.grade_entry.get()
        if grade.isdigit() and 0 <= int(grade) <= 100:
            ok, data = submit_answer(self.selected_work_id, grade)
            if ok:
                Messagebox.show_info(title='提示', message=data)
            else:
                Messagebox.show_error(title='错误', message=data)
        else:
            Messagebox.show_error(title='错误', message='请输入有效的成绩（0-100）。')

    def show_settings_page(self):
        self.clear_content()
        self.set_page('设置 · CONFIG')

        ttk.Label(self.content_frame, text='CONFIG :: 设置', font=('Consolas', 12, 'bold'),
                  foreground=FG).pack(anchor='w', pady=(2, 10))

        col = ttk.Frame(self.content_frame)
        col.pack(fill=X)

        export_frame = ttk.Labelframe(col, text='EXPORT :: 导出设置', padding=12)
        export_frame.pack(fill=X)
        opts = ttk.Frame(export_frame)
        opts.pack(fill=X)
        self.export_word_check = ttk.Checkbutton(opts, text='导出为 Word (.docx)', variable=self.export_word_var,
                                                 command=self.toggle_word_options)
        self.export_word_check.grid(row=0, column=0, sticky='w', padx=(0, 30), pady=3)
        self.export_word_answers_check = ttk.Checkbutton(opts, text='含答案', variable=self.export_word_include_answers_var)
        self.export_word_answers_check.grid(row=1, column=0, sticky='w', padx=(22, 30), pady=3)
        self.export_pdf_check = ttk.Checkbutton(opts, text='导出为 PDF (.pdf)', variable=self.export_pdf_var,
                                                command=self.toggle_pdf_options)
        self.export_pdf_check.grid(row=0, column=1, sticky='w', pady=3)
        self.export_pdf_answers_check = ttk.Checkbutton(opts, text='含答案', variable=self.export_pdf_include_answers_var)
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
        self.export_word_answers_check.state(['!disabled' if self.export_word_var.get() else 'disabled'])

    def toggle_pdf_options(self):
        self.export_pdf_answers_check.state(['!disabled' if self.export_pdf_var.get() else 'disabled'])

    def choose_export_path(self):
        path = filedialog.askdirectory(initialdir=self.export_path)
        if path:
            self.path_entry.delete(0, END)
            self.path_entry.insert(0, path)
            self.export_path = path

    def save_settings(self):
        self.export_path = self.path_entry.get()
        self.save_config()
        Messagebox.show_info(title='提示', message='设置已保存')

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.save_config()
            return
        self.config.read(self.config_file, encoding='utf-8')
        if 'Settings' in self.config:
            s = self.config['Settings']
            self.export_path = s.get('export_path', self.export_path)
            self.export_word_var.set(s.getboolean('export_word', True))
            self.export_word_include_answers_var.set(s.getboolean('export_word_include_answers', True))
            self.export_pdf_var.set(s.getboolean('export_pdf', False))
            self.export_pdf_include_answers_var.set(s.getboolean('export_pdf_include_answers', True))

    def save_config(self):
        self.config['Settings'] = {
            'export_path': self.export_path,
            'export_word': str(self.export_word_var.get()),
            'export_word_include_answers': str(self.export_word_include_answers_var.get()),
            'export_pdf': str(self.export_pdf_var.get()),
            'export_pdf_include_answers': str(self.export_pdf_include_answers_var.get()),
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)

    @staticmethod
    def save_credentials(username, password):
        keyring.set_password(SERVICE_NAME, 'username', username)
        keyring.set_password(SERVICE_NAME, username, password)

    @staticmethod
    def get_saved_username():
        return keyring.get_password(SERVICE_NAME, 'username')

    @staticmethod
    def get_saved_password(username):
        return keyring.get_password(SERVICE_NAME, username)

    def delete_saved_credentials(self):
        saved_username = self.get_saved_username()
        if saved_username:
            keyring.delete_password(SERVICE_NAME, saved_username)
        keyring.delete_password(SERVICE_NAME, 'username')

    @staticmethod
    def view_user_info():
        ok, data = get_user_info()
        if ok:
            def field(name):
                return data.get(name) or 'N/A'
            Messagebox.show_info(title='用户信息', message=(
                f'姓名：{field("userName")}\n'
                f'邮箱：{field("email")}\n'
                f'学号：{field("studentNo")}\n'
                f'学院：{field("schoolName")}\n'
                f'班级：{field("deptName")}\n'
                f'电话号码：{field("phonenumber")}'
            ))
        else:
            Messagebox.show_error(title='错误', message=data)

    def open_progress(self, title, mode='determinate', status='', start=False):
        win = ttk.Toplevel(self.root)
        win.title(title)
        win.resizable(False, False)
        win.configure(bg=BG_RAISED)
        body = tk.Frame(win, bg=BG_RAISED)
        body.pack(expand=True, fill='both')
        self.set_state('PROCESSING')
        tk.Label(body, text=f'> {title}', bg=BG_RAISED, fg=PRIMARY,
                 font=('Consolas', 11, 'bold'), anchor='w').pack(fill=X, padx=22, pady=(18, 0))
        self.status_label = tk.Label(body, text=status, bg=BG_RAISED, fg=MUTED,
                                     font=('Consolas', 10), anchor='w')
        self.status_label.pack(fill=X, padx=22, pady=(10, 8))
        self.progress_bar = ttk.Progressbar(body, mode=mode, length=340)
        self.progress_bar.pack(fill=X, padx=22, pady=(0, 18))
        if start:
            self.progress_bar.start()
        self.progress_window = win
        win.bind('<Destroy>', lambda e: self._on_progress_closed(e, win))
        return win

    def _on_progress_closed(self, event, win):
        if event.widget is win:
            self.set_state('READY' if self.username else 'STANDBY')
    def update_status(self, text):
        self.root.after(0, self.status_label.config, {'text': text})

    def set_progress(self, value):
        self.root.after(0, self.progress_bar.config, {'value': value})

    def run_batch(self, title, job):
        self.open_progress(title)
        threading.Thread(target=job).start()

    def show_result(self, title, message):
        self.root.after(0, lambda: Messagebox.show_info(title=title, message=message))

    def start_collecting_questions(self, work_id, work_name, course_name):
        work_name = clean_name(work_name)
        course_name = clean_name(course_name)
        self.open_progress(f'收集作业 {work_name} 的题目', mode='indeterminate',
                           status='开始收集题目，请稍候...', start=True)

        def job():
            if self.collect_all_questions(work_id, work_name, course_name, 100) is None:
                self.progress_window.after(1000, lambda: Messagebox.show_error(
                    title='导出失败',
                    message=f"作业 '{work_name}' 导出失败，可能是网络错误或该作业没有题目"))

        threading.Thread(target=job).start()

    def collect_all_questions(self, work_id, work_name, course_name, max_iterations=200):
        """并行翻页收集：一次性并发 max_iterations 次请求，去重直到结果稳定。"""
        collected = {}
        self.update_status('开始收集题目...')
        self.root.after(0, self.progress_bar.start)
        start_time = time.time()
        api_errors = 0
        no_new = 0

        def fail(text):
            self.update_status(text)
            self.root.after(0, self.progress_bar.stop)
            self.root.after(3000, self.progress_window.destroy)
            return None

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(get_questions, work_id) for _ in range(max_iterations)]
            total = len(futures)
            processed = 0
            for future in as_completed(futures):
                processed += 1
                self.update_status(f'正在收集题目...({processed}/{total}) - {int(processed / total * 100)}% - 已找到 {len(collected)} 道题目')
                self.set_progress(int(processed / total * 100))
                try:
                    ok, questions = future.result()
                    if ok:
                        api_errors = 0
                        new_found = False
                        for q in questions:
                            qid = q.get('id')
                            if qid and qid not in collected:
                                collected[qid] = q
                                new_found = True
                        if not new_found:
                            no_new += 1
                            if processed >= 30 and no_new >= 10:
                                break
                        else:
                            no_new = 0
                    else:
                        api_errors += 1
                        err = f'API错误: {questions}'
                        self.update_status(f'获取题目时发生错误: {err}\n重试中... ({api_errors}/3)')
                        if api_errors >= 3:
                            return fail('获取题目失败: 多次请求失败')
                except Exception as exc:
                    return fail(f'处理题目时出现错误: {exc}')

            if not collected:
                return fail('没有找到任何题目，可能是API错误或作业中没有题目')

            self.save_collected_questions(collected, work_name, course_name, work_id,
                                          self.selected_course_id, work_name)
            self.update_status(f'收集完成，共收集到 {len(collected)} 道题目。用时: {time.time() - start_time:.2f}秒')
            self.root.after(0, self.progress_bar.stop)
            self.root.after(1000, self.progress_window.destroy)
            return collected

    def batch_collect_questions_with_progress(self, work_id, course_name, work_name):
        """串行翻页收集，供批量导出使用；返回 (collected, None) 或 ({}, 错误信息)。"""
        collected = {}
        no_new = 0
        processed = 0
        api_errors = 0
        for _ in range(200):
            processed += 1
            try:
                ok, questions = get_questions(work_id)
                if ok:
                    api_errors = 0
                    new_found = False
                    for q in questions:
                        qid = q.get('id')
                        if qid and qid not in collected:
                            collected[qid] = q
                            new_found = True
                    self.update_status(f'正在导出课程：{course_name}\n作业：{work_name}\n'
                                       f'已获取题目数量：{len(collected)}\n迭代次数：{processed}/200')
                    if not new_found:
                        no_new += 1
                        if processed >= 30 and no_new >= 10:
                            break
                    else:
                        no_new = 0
                else:
                    api_errors += 1
                    err = f'API错误: {questions}'
                    self.update_status(f'导出课程时发生错误: {err}\n重试中... ({api_errors}/3)')
                    if api_errors >= 3:
                        return None, err
            except Exception as e:
                err = f'导出题目时出现异常: {str(e)}'
                self.update_status(err)
                return None, err
        if collected:
            return collected, None
        return {}, '没有找到任何题目'

    def save_collected_questions(self, collected_questions, work_name, course_name,
                                 work_id, course_id, chapter_name):
        work_name = clean_name(work_name)
        course_name = clean_name(course_name)
        assignment_folder = os.path.join(self.export_path, '作业',
                                         f'{course_name} (ID_{course_id})', f'{work_name} (ID_{work_id})')
        os.makedirs(assignment_folder, exist_ok=True)
        for question in collected_questions.values():
            self.save_question(question, assignment_folder)
        if self.export_word_var.get():
            self.save_questions_to_word(collected_questions, assignment_folder, chapter_name,
                                        export_answers=self.export_word_include_answers_var.get())
        if self.export_pdf_var.get():
            self.save_questions_to_pdf(collected_questions, assignment_folder, chapter_name,
                                       export_answers=self.export_pdf_include_answers_var.get())

    def load_all_works(self, messages):
        """拉取所有课程的作业，失败信息写入 messages；返回 (作业列表, 拉取失败课程数)。"""
        works = []
        fetch_fail = 0
        for course in self.courses:
            ok, data = get_course_works(course['courseId'])
            if ok:
                works.extend((course['courseId'], course['courseName'], w['workId'], w['workName']) for w in data)
            else:
                fetch_fail += 1
                messages.append(f"获取课程 '{course['courseName']}' 的作业失败：{data}")
        return works, fetch_fail

    def export_all_courses_assignments(self):
        self.run_batch('正在导出所有课程的作业，请稍候...', self._export_all_courses_assignments)

    def _export_all_courses_assignments(self):
        messages = []
        works, _ = self.load_all_works(messages)
        total_courses = len(self.courses)
        total_works = len(works)
        if total_works == 0:
            self.root.after(0, self.progress_window.destroy)
            self.show_result('导出结果', f'共处理 {total_courses} 门课程，{total_works} 个作业。\n\n' + '\n'.join(messages))
            return

        self.root.after(0, self.progress_bar.config, {'maximum': total_works})
        for processed, (course_id, course_name, work_id, work_name) in enumerate(works, 1):
            self.update_status(f'正在导出课程：{course_name}\n作业：{work_name}')
            collected, err = self.batch_collect_questions_with_progress(work_id, course_name, work_name)
            if collected:
                self.save_collected_questions(collected, work_name, course_name, work_id, course_id, work_name)
                messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 导出成功，共 {len(collected)} 道题目。")
            else:
                messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 导出失败: {err}")
            self.set_progress(processed)

        self.root.after(0, self.progress_window.destroy)
        self.show_result('导出结果', f'共处理 {total_courses} 门课程，{total_works} 个作业。\n\n' + '\n'.join(messages))

    def submit_all_courses_100(self):
        self.run_batch('正在批量提交所有课程作业，请稍候...', self._submit_all_courses_100)

    def _submit_all_courses_100(self):
        messages = []
        works, fetch_fail = self.load_all_works(messages)
        total_courses = len(self.courses)
        total_works = len(works)
        success_count = fail_count = 0

        self.root.after(0, self.progress_bar.config, {'maximum': total_works})
        for processed, (course_id, course_name, work_id, work_name) in enumerate(works, 1):
            self.update_status(f'正在提交课程：{course_name}\n作业：{work_name}')
            ok, data = submit_answer(work_id, '100')
            if ok:
                success_count += 1
                messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 提交成功。")
            else:
                fail_count += 1
                messages.append(f"课程 '{course_name}' 的作业 '{work_name}' 提交失败：{data}")
            self.set_progress(processed)

        self.root.after(0, self.progress_window.destroy)
        self.show_result('提交结果',
                         f'共处理 {total_courses} 门课程，{total_works} 个作业。\n'
                         f'成功提交 {success_count} 个作业，提交失败 {fail_count} 个作业。\n'
                         f'有 {fetch_fail} 门课程的作业获取失败。\n\n' + '\n'.join(messages))

    def submit_all_works_100(self):
        self.run_batch('正在批量提交所有作业，请稍候...', self._submit_all_works_100)

    def _submit_all_works_100(self):
        total = len(self.works)
        success_count = fail_count = 0
        messages = []
        self.root.after(0, self.progress_bar.config, {'maximum': total})

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(submit_answer, work['workId'], '100'): work for work in self.works}
            completed = 0
            for future in as_completed(futures):
                completed += 1
                work_name = futures[future]['workName']
                try:
                    ok, data = future.result()
                    if ok:
                        success_count += 1
                        messages.append(f"作业 '{work_name}' 提交成功。")
                    else:
                        fail_count += 1
                        messages.append(f"作业 '{work_name}' 提交失败：{data}")
                except Exception as e:
                    fail_count += 1
                    messages.append(f"作业 '{work_name}' 提交时出现错误：{str(e)}")
                self.set_progress(int(completed / total * 100))
                self.update_status(f'正在提交作业 ({completed}/{total})...')

        self.root.after(0, self.progress_window.destroy)
        self.show_result('提交结果',
                         f'成功提交 {success_count} 个作业，失败 {fail_count} 个作业。\n\n' + '\n'.join(messages))

    def export_all_works_of_current_course(self):
        self.run_batch('正在导出当前课程的所有作业，请稍候...', self._export_all_works_of_current_course)

    def _export_all_works_of_current_course(self):
        total_works = len(self.works)
        success_count = fail_count = 0
        messages = []
        course_id = self.selected_course_id
        course_name = self.selected_course_name

        self.root.after(0, self.progress_bar.config, {'maximum': total_works})
        for processed, work in enumerate(self.works, 1):
            work_id = work['workId']
            work_name = work['workName']
            self.update_status(f'正在导出作业：{work_name}')
            collected, err = self.batch_collect_questions_with_progress(work_id, course_name, work_name)
            if collected:
                self.save_collected_questions(collected, work_name, course_name, work_id, course_id, work_name)
                messages.append(f"作业 '{work_name}' 导出成功，共 {len(collected)} 道题目")
                success_count += 1
            else:
                messages.append(f"作业 '{work_name}' 导出失败: {err}")
                fail_count += 1
            self.set_progress(processed)

        self.root.after(0, self.progress_window.destroy)
        self.show_result('导出结果',
                         f'共处理 {total_works} 个作业。\n成功导出: {success_count} 个\n导出失败: {fail_count} 个\n\n' + '\n'.join(messages))

    @staticmethod
    def save_question(question, assignment_folder):
        question_id = question.get('id', 'N/A')
        imgurl = question.get('imgurl', 'N/A')
        images_folder = os.path.join(assignment_folder, '题目图片')
        os.makedirs(images_folder, exist_ok=True)
        if not imgurl or imgurl == 'N/A':
            return
        try:
            response = session.get(imgurl)
            response.raise_for_status()
            with open(os.path.join(images_folder, f'{question_id}.png'), 'wb') as f:
                f.write(response.content)
        except Exception as e:
            print(f'无法下载题目 {question_id} 的图片：{e}')

    @staticmethod
    def save_questions_to_word(collected_questions, assignment_folder, work_name, export_answers=True):
        document = Document()
        style = document.styles['Normal']
        style.font.name = '宋体'
        style.font.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        document.add_heading(work_name, 0)

        images_folder = os.path.join(assignment_folder, '题目图片')
        for idx, question_id in enumerate(sorted(collected_questions, key=int)):
            question = collected_questions[question_id]
            document.add_heading(f'题目 {idx + 1}: {question.get("name", "N/A")}', level=2)
            image_path = os.path.join(images_folder, f'{question_id}.png')
            if os.path.exists(image_path):
                document.add_picture(image_path, width=Inches(5))
            else:
                document.add_paragraph('（无图片）')
            if export_answers:
                run = document.add_paragraph('答案：').add_run(question.get('answer', 'N/A'))
                run.font.color.rgb = RGBColor(255, 0, 0)

        document.save(os.path.join(assignment_folder, f'{work_name}.docx'))

    @staticmethod
    def save_questions_to_pdf(collected_questions, assignment_folder, work_name, export_answers=True):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import (BaseDocTemplate, Frame, Image as RLImage,
                                        PageTemplate, Paragraph, Spacer)

        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        styles = getSampleStyleSheet()
        for name, parent, size, leading, color in [
            ('ChineseTitle', 'Title', 20, 24, '#333333'),
            ('ChineseHeading1', 'Heading1', 16, 20, '#555555'),
            ('Chinese', 'Normal', 12, 18, '#000000'),
        ]:
            styles.add(ParagraphStyle(name=name, parent=styles[parent], fontName='STSong-Light',
                                      fontSize=size, leading=leading,
                                      alignment=1 if name == 'ChineseTitle' else 0,
                                      textColor=colors.HexColor(color)))
        normal_style = styles['Chinese']

        def add_page_number(canvas, _doc):
            canvas.setFont('STSong-Light', 9)
            canvas.drawRightString(A4[0] - 50, 15, f'第 {canvas.getPageNumber()} 页')

        doc = BaseDocTemplate(os.path.join(assignment_folder, f'{work_name}.pdf'), pagesize=A4,
                              rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=60)
        frame = Frame(40, 60, doc.width, doc.height, id='normal')
        doc.addPageTemplates([PageTemplate(id='test', frames=frame, onPage=add_page_number)])

        elements = [Paragraph(work_name, styles['ChineseTitle']), Spacer(1, 0.3 * inch)]
        images_folder = os.path.join(assignment_folder, '题目图片')
        for idx, question_id in enumerate(sorted(collected_questions, key=int)):
            question = collected_questions[question_id]
            elements.append(Paragraph(f'题目 {idx + 1}: {question.get("name", "N/A")}', styles['ChineseHeading1']))
            elements.append(Spacer(1, 0.1 * inch))
            image_path = os.path.join(images_folder, f'{question_id}.png')
            if os.path.exists(image_path):
                img = ImageReader(image_path)
                width, height = img.getSize()
                display_width = doc.width * 0.8
                elements.append(RLImage(image_path, width=display_width,
                                        height=display_width * height / float(width)))
            else:
                elements.append(Paragraph('（无图片）', normal_style))
            if export_answers:
                elements.append(Paragraph(f"答案：<font color='red'>{question.get('answer', 'N/A')}</font>", normal_style))
            elements.append(Spacer(1, 0.2 * inch))

        doc.build(elements)



if __name__ == '__main__':
    root = ttk.Window()
    ModernApp(root)
    root.mainloop()

