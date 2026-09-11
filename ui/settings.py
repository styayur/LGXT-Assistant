# -*- coding: utf-8 -*-
"""设置与帮助。"""
import tkinter as tk
from tkinter import filedialog
from tkinter.constants import *

import ttkbootstrap as ttk

import theme
from .widgets import ScrolledFrame, mono, GAP


class SettingsMixin:
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
        sys_panel = tk.Frame(body, bg=theme.SURFACE, width=300, highlightthickness=0)
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
        self.msg_info(title='提示', message='设置已保存')

    def view_user_info(self):
        self.fetch(self.api.get_user_info, self._show_user_info)

    def _show_user_info(self, result):
        ok, data = result
        if not ok:
            self.msg_error(title='错误', message=data)
            return

        def field(name):
            return data.get(name) or 'N/A'

        self.msg_info(title='用户信息', message=(
            f'姓名：{field("userName")}\n'
            f'邮箱：{field("email")}\n'
            f'学号：{field("studentNo")}\n'
            f'学院：{field("schoolName")}\n'
            f'班级：{field("deptName")}\n'
            f'电话号码：{field("phonenumber")}'))

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
            ttk.Label(content, text=text, font=theme.ui(10), foreground=theme.MUTED,
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

