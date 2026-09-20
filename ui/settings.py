# -*- coding: utf-8 -*-
"""设置与帮助。"""
import tkinter as tk
from tkinter import filedialog
from tkinter.constants import *

import ttkbootstrap as ttk

import theme
from . import audio
from .widgets import ScrolledFrame, mono, GAP


class SettingsMixin:
    def show_settings(self):
        self.begin_nav()
        self.set_page('SETTINGS')
        self.set_active_nav('settings')
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

        ui_frame = ttk.Labelframe(left, text='UI', padding=16)
        ui_frame.pack(fill=X, pady=(16, 0))
        self.sound_var = tk.BooleanVar(value=getattr(self.settings, 'ui_sound', True))
        ttk.Checkbutton(ui_frame, text='界面音效（悬停 / 点击）', variable=self.sound_var,
                        command=self.toggle_sound).pack(anchor='w')

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

    def toggle_sound(self):
        flag = bool(self.sound_var.get())
        audio.set_enabled(flag)
        self.settings.ui_sound = flag
        self.settings.save()

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
        self.settings.ui_sound = bool(getattr(self, 'sound_var', None).get()) if hasattr(self, 'sound_var') else True
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
        help_window.geometry('1000x780')
        help_window.minsize(760, 560)
        help_window.configure(bg=theme.BG)

        content = ScrolledFrame(help_window, autohide=True)
        content.pack(fill='both', expand=True)

        def head(text):
            ttk.Label(content, text=f'> {text}', font=('Consolas', 11, 'bold'),
                      foreground=theme.SECONDARY).pack(anchor='w', padx=24, pady=(14, 4))

        def line(text):
            ttk.Label(content, text=text, font=theme.ui(10), foreground=theme.MUTED,
                      justify='left', wraplength=900).pack(anchor='w', padx=40, pady=1)

        ttk.Label(content, text='MANUAL :: 使用手册', font=('Consolas', 13, 'bold'),
                  foreground=theme.PRIMARY).pack(anchor='w', padx=24, pady=(16, 2))
        ttk.Label(content, text='LGXT Assistant · 理工学堂助手',
                  font=('Microsoft YaHei', 15, 'bold'), foreground=theme.FG).pack(anchor='w', padx=24)

        head('界面与窗口')
        line('· 无边框工作台：标题栏可拖动，右下角三角可缩放窗口；')
        line('· ESC = 退出（播放代码雨后关闭）；F11 = 全屏/还原；')
        line('· 所有按钮为深色透光切角样式，悬停有光效与轻音效（可在设置中关闭）。')

        head('课程星图（科目 = 恒星系，习题 = 行星）')
        line('· 每颗恒星代表一门课程；单击展开/收起该课程的习题行星；')
        line('· 行星颜色：绿色=可提交，橙色=仅剩最后一次，红色=已用完，青色=已完成；')
        line('· 单击行星直接进入题目工作区；展开失败时可再次单击恒星重试；')
        line('· 顶部 SEARCH 按课程名/ID 过滤，SORT 支持名称与 ID 排序，REFRESH 重新同步。')

        head('仪表盘')
        line('· 待激活 PENDING：尚未提交且仍有剩余次数的作业数量；')
        line('· 已完成 DONE：已有成绩的作业数量；')
        line('· 平均分 AVG：已完成作业成绩的算术平均；')
        line('· 数据来自服务器真实返回，不做任何推测或伪造。')

        head('作业工作区与题目')
        line('· 作业列表：SEARCH/FILTER（全部·可提交·已用完）/SORT（截止时间·剩余·名称）；')
        line('· 选中作业后，右侧 INSPECTOR 显示章节、截止时间、成绩、尝试次数与状态；')
        line('· 题目三栏：左列表（搜索/筛选/排序）、中题面图片、右 Inspector（答案与成绩提交）；')
        line('· 数据加载与图片下载均在后台线程完成，界面保持响应。')

        head('导出与批量')
        line('· 单作业：INSPECTOR 内 EXPORT 题目；当前课程：EXPORT ALL；全部课程：星图页 EXPORT ALL；')
        line('· 导出目录：<导出路径>/作业/<课程>(ID_x)/<作业>(ID_y)/题目图片 + .docx/.pdf；')
        line('· 题目图片命中本地缓存会跳过下载；批量任务在页面底部 Task Panel 显示进度。')

        head('快捷键')
        line('ESC            退出（代码雨特效）')
        line('F11            全屏 / 还原')
        line('双击行星        打开题目')
        line('双击标题栏      最大化工作区')

        head('常见问题')
        line('1) 登录失败：检查账号密码；网络异常会给出具体原因（网络/响应格式/缺少字段）。')
        line('2) 星图展开失败：确认网络后再次单击该恒星重试。')
        line('3) 导出失败：检查导出路径是否可写；失败信息会出现在结果弹窗中。')
        line('4) 没有声音：设置页 UI 分组中可开启/关闭界面音效。')
        line('5) 配置位置：%APPDATA%\\LGXT-Assistant\\config.ini（旧版脚本目录配置会自动迁移）。')

        head('声明 · LICENSE')
        line('本工具仅限学习交流使用，请勿转卖或用于商业用途。')
        line('LGXT v3.2.1 · Author: Styayur · License: GPL-3.0-or-later')

        ttk.Button(content, text='关闭', command=help_window.destroy,
                   bootstyle='danger').pack(anchor='w', padx=40, pady=(20, 28))
