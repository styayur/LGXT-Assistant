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


def cut_points(x1, y1, x2, y2, cut):
    """硬朗金属切角矩形的多边形顶点（左上/右下切角）。"""
    return [x1 + cut, y1, x2, y1, x2, y2 - cut, x2 - cut, y2, x1, y2, x1, y1 + cut]


def draw_metal(canvas, points, fill, light=theme.METAL_LIGHT, dark=theme.METAL_DARK, width=1):
    canvas.create_polygon(points, fill=fill, outline='')
    half = len(points) // 2
    canvas.create_line(points[:2] + [points[2], points[3]], fill=light, width=width)
    canvas.create_line(points[4:8], fill=dark, width=width)
    canvas.create_line([points[-2], points[-1], points[0], points[1]], fill=dark, width=width)


class AngularPanel(tk.Canvas):
    """金属切角面板：内部 body Frame 供业务放置内容。"""

    def __init__(self, parent, cut=16, padding=14, bg=theme.SURFACE, line=theme.METAL_LIGHT):
        parent_bg = theme.BG
        try:
            parent_bg = parent.cget('bg')
        except Exception:
            pass
        super().__init__(parent, bg=parent_bg, highlightthickness=0, bd=0)
        self._cut = cut
        self._padding = padding
        self._fill = bg
        self._line = line
        self.body = tk.Frame(self, bg=bg)
        self._win = self.create_window(padding, padding, anchor='nw', window=self.body)
        self.bind('<Configure>', lambda e: self._redraw())

    def _redraw(self):
        self.delete('metal')
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 8:
            return
        pts = cut_points(1, 1, w - 1, h - 1, self._cut)
        self.create_polygon(pts, fill=self._fill, outline='', tags='metal')
        # 顶部微高光带（现代玻璃质感，非线条）
        band_h = max(8, int(h * 0.30))
        band = [1 + self._cut, 1, w - 1, 1, w - 1, 1 + band_h, 1, 1 + band_h, 1, 1 + self._cut]
        self.create_polygon(band, fill='#151C25', outline='', tags='metal')
        self.create_line(pts[:4], fill=self._line, width=1, tags='metal')
        self.create_line(pts[-4:], fill=theme.METAL_DARK, width=1, tags='metal')
        self.tag_lower('metal')
        pad = self._padding
        self.itemconfigure(self._win, width=max(1, w - pad * 2), height=max(1, h - pad * 2))


class GlowButton(tk.Canvas):
    """深色透光切角按钮：hover 光效 + 音效（音效经 ui.audio 静默降级）。"""

    def __init__(self, parent, text='', command=None, kind='primary', width=None,
                 height=30, cut=9, font=None):
        self._text = text
        self._command = command
        self._kind = kind
        self._font = font or ('Microsoft YaHei', 10)
        self._disabled = False
        self._hover = False
        self._bg, self._fg, self._active, _pressed = theme.BUTTON_SCHEMES.get(kind, theme.BUTTON_SCHEMES['primary'])
        if kind == 'ghost':
            self._bg, self._fg = theme.BG_RAISED, theme.MUTED
        try:
            parent_bg = parent.cget('bg')
        except Exception:
            parent_bg = theme.BG
        w = width or self._measure() + 26
        super().__init__(parent, width=w, height=height, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor='hand2')
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
        self._draw()

    def _measure(self):
        import tkinter.font as tkfont
        return tkfont.Font(family=self._font[0], size=self._font[1]).measure(self._text)

    def _on_enter(self, _e=None):
        if self._disabled:
            return
        self._hover = True
        try:
            from . import audio
            audio.play('hover')
        except Exception:
            pass
        self._draw()

    def _on_leave(self, _e=None):
        self._hover = False
        self._draw()

    def _on_click(self, _e=None):
        if self._disabled:
            return
        try:
            from . import audio
            audio.play('click')
        except Exception:
            pass
        if self._command:
            self._command()

    def _draw(self):
        self.delete('all')
        w, h = int(self['width']), int(self['height'])
        pts = cut_points(1, 1, w - 1, h - 1, 9)
        shadow = []
        for i in range(0, len(pts), 2):
            shadow.extend((pts[i], pts[i + 1] + 2))
        self.create_polygon(shadow, fill='#070A0D', outline='')   # 轻投影
        fill = self._active if self._hover else self._bg
        self.create_polygon(pts, fill=fill, outline='')
        glow = theme.SECONDARY if self._kind in ('info', 'secondary', 'ghost') else theme.PRIMARY
        self.create_line(pts[:4], fill=glow if self._hover else theme.METAL_LIGHT, width=1)
        self.create_line(pts[-4:], fill=theme.METAL_DARK, width=1)
        fg = theme.DIM if self._disabled else self._fg
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)

    # ---- 兼容 ttk 风格调用 ----
    def configure(self, cnf=None, **kw):
        if 'text' in kw:
            self._text = kw.pop('text')
        if 'state' in kw:
            self.state(kw.pop('state'))
        return super().configure(cnf, **kw)

    config = configure

    def state(self, states):
        if isinstance(states, str):
            states = [states]
        for s in states:
            if s == 'disabled':
                self._disabled = True
            elif s == '!disabled':
                self._disabled = False
        self.configure(cursor='arrow' if self._disabled else 'hand2')
        self._draw()


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
        return GlowButton(parent, text=text, command=command, kind=kind)

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

