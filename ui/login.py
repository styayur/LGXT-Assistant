# -*- coding: utf-8 -*-
"""登录页。"""
import tkinter as tk
from tkinter.constants import *

import ttkbootstrap as ttk

import config
import theme


class LoginMixin:
    def show_login(self):
        self.begin_nav()
        self.set_page('AUTH')
        self.set_active_nav(None)
        self.set_state('OFFLINE')
        self.log('AUTH required')

        panel = tk.Frame(self.content_frame, bg=theme.SURFACE, highlightthickness=0)
        panel.pack(expand=YES)
        tk.Label(panel, text='AUTHENTICATION', bg=theme.SURFACE, fg=theme.PRIMARY,
                 font=('Consolas', 15, 'bold')).pack(anchor='w', padx=32, pady=(28, 2))
        tk.Label(panel, text='输入理工学堂账号以建立会话。', bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.ui(10)).pack(anchor='w', padx=32, pady=(0, 20))

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
        self.login_button = self.btn(panel, 'LOGIN ▸ 登录', self.login, 'primary')
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
                self.msg_error(message=msg, title='登录失败')

        self.fetch(lambda: self.api.login(self.username, self.password), on_done)

