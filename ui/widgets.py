# -*- coding: utf-8 -*-
"""通用控件与页面骨架：PageHeader / CommandBar / 搜索框 / 下拉框 / 文本助手。"""
import tkinter as tk
from tkinter.constants import *

import ttkbootstrap as ttk

import theme

try:  # ttkbootstrap < 2
    from ttkbootstrap.scrolled import ScrolledFrame
except ImportError:  # ttkbootstrap >= 2
    from ttkbootstrap import ScrolledFrame

GAP = 10
GROUP = 20


def mono(parent, text, fg=theme.MUTED, size=9, bg=theme.BG):
    return tk.Label(parent, text=text, bg=bg, fg=fg,
                    font=('Consolas', size), anchor='w')


class WidgetsMixin:
    def page_header(self, title, subtitle='', back=None):
        """标准 Page Header：标题 + 可选 meta + 可选返回，返回容器供页面加右侧动作。"""
        bar = tk.Frame(self.content_frame, bg=theme.BG)
        bar.pack(fill=X, pady=(0, 8))
        left = tk.Frame(bar, bg=theme.BG)
        left.pack(side=LEFT)
        if back:
            tk.Button(left, text='‹ ' + back, command=self._go(back), relief='flat', bd=0, highlightthickness=0,
                      bg=theme.BG, fg=theme.SECONDARY, activebackground=theme.HOVER,
                      activeforeground=theme.SECONDARY, font=('Consolas', 9), cursor='hand2'
                      ).pack(side=LEFT, padx=(0, 16), pady=4)
        tk.Label(left, text=title, bg=theme.BG, fg=theme.FG,
                 font=('Microsoft YaHei', 17, 'bold')).pack(side=LEFT)
        if subtitle:
            mono(left, '  ' + subtitle, fg=theme.DIM, size=9).pack(side=LEFT, pady=(6, 0))
        return bar

    def command_bar(self):
        """Command Bar 容器（自动高度，按钮不会被裁切）。"""
        bar = tk.Frame(self.content_frame, bg=theme.BG_RAISED, padx=12, pady=6)
        bar.pack(fill=X, pady=(0, 14))
        return bar

    def search_entry(self, parent, var, placeholder):
        tk.Label(parent, text='SEARCH', bg=theme.BG_RAISED, fg=theme.DIM,
                 font=('Consolas', 8)).pack(side=LEFT, padx=(0, 6))
        entry = ttk.Entry(parent, textvariable=var, width=24)
        entry.pack(side=LEFT, padx=(0, GROUP))
        if placeholder:
            self._placeholders[str(var)] = placeholder
            if not var.get().strip():
                var.set(placeholder)

            def clear_placeholder(_event=None):
                if var.get() == placeholder:
                    var.set('')

            def restore_placeholder(_event=None):
                if not var.get().strip():
                    var.set(placeholder)

            entry.bind('<FocusIn>', clear_placeholder)
            entry.bind('<FocusOut>', restore_placeholder)
        return entry

    def _query_text(self, var):
        if var is None:
            return ''
        value = (var.get() or '').strip()
        return '' if value == self._placeholders.get(str(var)) else value

    def _short(self, text, limit):
        """按当前缩放截断过长文本，避免行内文字互相遮挡/被裁切。"""
        text = str(text)
        limit = max(6, int(limit * self.scale))
        return text if len(text) <= limit else text[:limit - 1] + '…' 

    def combo_box(self, parent, var, values, width=10):
        ttk.Combobox(parent, textvariable=var, values=values, state='readonly',
                     width=width).pack(side=LEFT, padx=(0, GROUP))
        return var

    def btn(self, parent, text, command, kind='primary'):
        style = {'primary': 'primary', 'secondary': 'secondary', 'info': 'info',
                 'warning': 'warning', 'danger': 'danger', 'ghost': 'secondary'}[kind]
        return ttk.Button(parent, text=text, command=command, bootstyle=style, cursor='hand2')

    def _debounce(self, job, delay=180):
        if self._debounce_job:
            try:
                self.root.after_cancel(self._debounce_job)
            except tk.TclError:
                pass
        self._debounce_job = self.root.after(delay, job)

    def _go(self, page):
        return self.show_courses

    def _all_widgets(self, wdg):
        yield wdg
        for child in wdg.winfo_children():
            yield from self._all_widgets(child)

