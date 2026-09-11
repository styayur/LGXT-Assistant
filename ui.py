# -*- coding: utf-8 -*-
"""UI LAYOUT 2.0：Developer Workbench 主窗口。

结构：Header(品牌/面包屑/连接态) · Sidebar(188) · PageHeader · CommandBar ·
Content(可含 Inspector) · 内嵌 TaskPanel · StatusBar。

线程安全：worker 只向 queue 投事件，主线程 after() 轮询更新 UI。
"""
import io
import logging
import os
import queue
import random
import tkinter.font as tkfont
import threading
import time
import tkinter as tk
import tkinter.ttk as tkttk
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
log = logging.getLogger(__name__)
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
        self._fullscreen = False
        self.scale = 1.0
        self._font_bases = {}
        self._font_pool = {}
        self._resize_job = None
        self._debounce_job = None
        self._inflight = 0
        self._placeholders = {}
        self._quitting = False

        self.setup_ui()
        self.set_state('STANDBY')
        self.set_page('AUTH')
        self.show_login()
        self.root.protocol('WM_DELETE_WINDOW', self.quit_app)
        self.root.bind('<F11>', lambda e: self._toggle_fullscreen())
        self.root.bind('<Configure>', self._on_configure)
        self.root.after(80, self._maximize)
        self.root.after(60, self._poll_queue)

    # ---------- 窗口框架（LAYOUT 2.0 Shell） ----------

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=YES)

        # Header：品牌 | breadcrumb | ● 连接态
        header = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=46)
        header.pack(side=TOP, fill=X)
        header.pack_propagate(False)
        self._header = header
        tk.Label(header, text='LGXT::ASSISTANT', bg=theme.BG_RAISED, fg=theme.PRIMARY,
                 font=('Consolas', 12, 'bold')).pack(side=LEFT, padx=(24, 0))
        tk.Frame(header, bg=theme.BORDER, width=1).pack(side=LEFT, fill=Y, padx=20, pady=12)
        self.page_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.MUTED,
                                   font=('Consolas', 11))
        self.page_label.pack(side=LEFT)
        self.state_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.DIM,
                                    font=('Consolas', 9, 'bold'))
        self.state_label.pack(side=RIGHT, padx=24)

        # StatusBar：左日志 / 右版本（API/AUTH 细节移入设置页系统信息）
        statusbar = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=24)
        statusbar.pack(side=BOTTOM, fill=X)
        statusbar.pack_propagate(False)
        self._statusbar = statusbar
        self.log_label = tk.Label(statusbar, text='> SYSTEM READY', bg=theme.BG_RAISED,
                                  fg=theme.DIM, font=('Consolas', 8), anchor='w')
        self.log_label.pack(side=LEFT, fill=X, expand=YES, padx=12)
        tk.Label(statusbar, text='v3.0 · GPL-3.0', bg=theme.BG_RAISED, fg=theme.DIM,
                 font=('Consolas', 8)).pack(side=RIGHT, padx=12)

        body = tk.Frame(self.main_frame, bg=theme.BG)
        body.pack(side=TOP, fill=BOTH, expand=YES)
        self.create_sidebar(body)
        self.content_frame = ttk.Frame(body, padding=(PAD, 16, PAD, 16))
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=YES)

    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=theme.SURFACE, width=SIDEBAR_W)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)
        self._sidebar = sidebar

        tk.Label(sidebar, text='LGXT', bg=theme.SURFACE, fg=theme.PRIMARY,
                 font=('Consolas', 13, 'bold'), anchor='w').pack(fill=X, padx=16, pady=(18, 0))
        tk.Label(sidebar, text='理工学堂助手', bg=theme.SURFACE, fg=theme.FG,
                 font=('Microsoft YaHei', 10, 'bold'), anchor='w').pack(fill=X, padx=16)
        tk.Frame(sidebar, bg=theme.SURFACE, height=10).pack(fill=X)

        def section(text):
            tk.Label(sidebar, text=text, bg=theme.SURFACE, fg=theme.DIM, anchor='w',
                     font=('Consolas', 8, 'bold')).pack(fill=X, padx=16, pady=(0, 4))

        def item(text, command, indent=True):
            lbl = tk.Label(sidebar, text=('  ' + text if indent else text), bg=theme.SURFACE,
                           fg=theme.MUTED, anchor='w', font=theme.ui(10), cursor='hand2',
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
        item('退出', self.quit_app)

        tk.Label(sidebar, text='v3.0.0', bg=theme.SURFACE, fg=theme.FG,
                 font=('Consolas', 8), anchor='w').pack(side=BOTTOM, fill=X, padx=16, pady=(0, 14))

    # ---------- 全屏 / 自适应字体 ----------

    def _maximize(self):
        try:
            self.root.state('zoomed')
        except tk.TclError:
            try:
                self.root.attributes('-fullscreen', True)
                self._fullscreen = True
            except tk.TclError:
                pass

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        try:
            self.root.attributes('-fullscreen', self._fullscreen)
        except tk.TclError:
            return
        if not self._fullscreen:
            self._maximize()

    def _on_configure(self, event):
        if event.widget is not self.root:
            return
        if self._resize_job:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                log.debug('after_cancel 失败（窗口可能已销毁）', exc_info=True)
        self._resize_job = self.root.after(150, self._apply_font_scale)

    def _apply_font_scale(self):
        self._resize_job = None
        width = self.root.winfo_width()
        if width < 200:
            return
        target = max(0.9, min(1.5, width / 1440.0))
        if abs(target - self.scale) < 0.04:
            return
        self.scale = target
        theme.set_scale(target)
        self._rescale_fonts()
        theme.apply_theme(self.style)
        self._apply_scale_geometry()

    def _rescale_fonts(self):
        """按 scale 调整 tk 控件字体（ttk 走 style，避免按控件改字体导致裁剪）。

        - 字体对象按 (family,size,weight) 复用，避免命名 Tk 字体泄漏；
        - _font_bases 每轮按存活控件重建，避免字典随页面销毁无限增长。
        """
        bases = {}
        for wdg in self._all_widgets(self.root):
            if isinstance(wdg, tkttk.Widget):
                continue
            try:
                current = wdg.cget('font')
                if not current:
                    continue
                f = tkfont.Font(root=self.root, font=current)
                family, size, weight = f.actual('family'), f.actual('size'), f.actual('weight')
            except Exception:
                continue
            key = str(wdg)
            base = self._font_bases.get(key, abs(size))
            bases[key] = base
            new_size = max(8, int(round(base * self.scale)))
            fkey = (family, new_size, weight)
            font = self._font_pool.get(fkey)
            if font is None:
                try:
                    font = tkfont.Font(root=self.root, family=family, size=new_size, weight=weight)
                except Exception:
                    continue
                self._font_pool[fkey] = font
            try:
                wdg.configure(font=font)
            except Exception:
                log.debug('字体应用失败: %s', wdg, exc_info=True)
        self._font_bases = bases

    def _apply_scale_geometry(self):
        """随字体同步调整固定尺寸容器/行高/列宽，避免文字被裁切。"""
        scale = self.scale
        for widget, base_height in ((getattr(self, '_header', None), 46),
                                    (getattr(self, '_statusbar', None), 24)):
            if widget is not None and widget.winfo_exists():
                try:
                    widget.configure(height=int(base_height * scale))
                except tk.TclError:
                    pass
        sidebar = getattr(self, '_sidebar', None)
        if sidebar is not None and sidebar.winfo_exists():
            try:
                sidebar.configure(width=int(SIDEBAR_W * scale))
            except tk.TclError:
                pass
        try:
            self.style.configure('Treeview', rowheight=int(26 * scale))
        except tk.TclError:
            pass
        tree = getattr(self, '_tree', None)
        if tree is not None and tree.winfo_exists():
            try:
                tree.column('#0', width=int(560 * scale))
                tree.column('id', width=int(90 * scale))
                tree.column('meta', width=int(220 * scale))
            except tk.TclError:
                pass
        for name, base_width in (('_works_listbox', 440), ('_works_inspector', 300),
                                 ('_q_list_pane', 240), ('_q_inspector', 280)):
            widget = getattr(self, name, None)
            if widget is not None and widget.winfo_exists():
                try:
                    widget.configure(width=int(base_width * scale))
                except tk.TclError:
                    pass
        try:
            self.root.minsize(max(1200, int(1200 * min(scale, 1.25))),
                              max(800, int(800 * min(scale, 1.25))))
        except tk.TclError:
            pass

    def _all_widgets(self, wdg):
        yield wdg
        for child in wdg.winfo_children():
            yield from self._all_widgets(child)

    # ---------- 关闭：黑客帝国代码雨 ----------

    def quit_app(self):
        if self._quitting:
            return
        self._quitting = True
        try:
            self._matrix_rain(self.root.destroy)
        except Exception:
            log.exception('代码雨播放失败，直接退出')
            self.root.destroy()

    def _matrix_rain(self, on_done, duration_ms=1800):
        rain = tk.Toplevel(self.root)
        rain.overrideredirect(True)
        rain.configure(bg='#000000')
        try:
            rain.attributes('-topmost', True)
        except tk.TclError:
            pass
        width = self.root.winfo_width() or 1280
        height = self.root.winfo_height() or 800
        rain.geometry(f'{width}x{height}+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}')
        canvas = tk.Canvas(rain, bg='#000000', highlightthickness=0, bd=0)
        canvas.pack(fill=BOTH, expand=YES)
        glyphs = 'アイウエオカキクケコサシスセソタチツテトナニヌネノ0123456789ABCDEFXYZ$#@%&*+-=/<>[]{}'
        col_w = max(12, int(13 * self.scale))
        cols = max(1, width // col_w)
        drops = [random.randint(-12, 0) for _ in range(cols)]
        palette = ['#00FF66', '#00D25A', '#00A94A', '#00803A', '#00592A', '#003D1E']
        fnt = ('Consolas', max(9, int(12 * self.scale)))
        end = time.time() + duration_ms / 1000.0

        def tick():
            if not rain.winfo_exists():
                return
            canvas.delete('all')
            for i in range(cols):
                y = drops[i] * col_w
                head = random.choice(glyphs)
                for k, color in enumerate(palette):
                    yy = y - k * col_w
                    if -col_w <= yy <= height:
                        canvas.create_text(i * col_w + col_w / 2, yy, fill=color,
                                           text=head if k == 0 else random.choice(glyphs),
                                           font=fnt)
                drops[i] += 1
                if drops[i] * col_w > height + 6 * col_w:
                    drops[i] = 0
            if time.time() < end:
                rain.after(45, tick)
            else:
                try:
                    rain.destroy()
                except tk.TclError:
                    pass
                on_done()

        tick()

    # ---------- 页面骨架（PageHeader / CommandBar / 面板） ----------

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
        if self._inflight >= 4:
            self.log('请求过于频繁，已忽略本次加载')
            return
        self._inflight += 1
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
        busy = False
        try:
            while True:
                self._handle_event(self.queue.get_nowait())
                busy = True
        except queue.Empty:
            pass
        try:
            self.root.after(15 if busy else 120, self._poll_queue)
        except (tk.TclError, RuntimeError):
            pass

    def _handle_event(self, event):
        kind = event[0]
        try:
            if kind == 'deliver':
                _, token, on_done, result = event
                self._inflight = max(0, self._inflight - 1)
                if token == self._token:
                    try:
                        on_done(result)
                    except Exception as exc:
                        log.exception('处理异步结果失败')
                        self._write_log(f'ERROR {exc}')
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
        except Exception as exc:
            log.exception('事件处理失败')
            self._write_log(f'ERROR {exc}')

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
        panel = tk.Frame(self.content_frame, bg=theme.SURFACE, highlightthickness=0)
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

            # ---------- 课程（Tree Workspace：科目 → 作业 树状展开） ----------

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

        bar2 = self.command_bar()
        left = tk.Frame(bar2, bg=theme.BG_RAISED)
        left.pack(side=LEFT)
        self._c_search = tk.StringVar()
        self._c_sort = tk.StringVar(value='默认')
        self.search_entry(left, self._c_search, '课程名 / ID')
        self.combo_box(left, self._c_sort, ['默认', '名称 A→Z', '名称 Z→A', 'ID ↑'])
        right = tk.Frame(bar2, bg=theme.BG_RAISED)
        right.pack(side=RIGHT)
        self._open_btn = self.btn(right, 'OPEN ▸ 作业', self._open_selected, 'primary')
        self._open_btn.pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'REFRESH', self.show_courses, 'secondary').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'EXPORT ALL', self.export_all_courses, 'info').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'SUBMIT ALL 100', self.submit_all_courses_100, 'warning').pack(side=LEFT)

        if not ok:
            empty = tk.Frame(self.content_frame, bg=theme.SURFACE)
            empty.pack(fill=X)
            mono(empty, '> ERROR', fg=theme.ERROR, size=10, bg=theme.SURFACE
                 ).pack(anchor='w', padx=12, pady=(8, 0))
            tk.Label(empty, text='获取课程列表失败 · 请检查网络后重试', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.ui(10), anchor='w').pack(anchor='w', padx=12, pady=(0, 8))
            return

        self._tree_courses = {}
        self._tree_works = {}
        self._loaded_courses = set()
        self._sel_tree_course = None
        self._sel_tree_work = None

        wrap = tk.Frame(self.content_frame, bg=theme.BG)
        wrap.pack(fill=BOTH, expand=YES)
        self._tree = ttk.Treeview(wrap, columns=('id', 'meta'), show='tree headings',
                                  selectmode='browse')
        self._tree.heading('#0', text='COURSE / ASSIGNMENT', anchor='w')
        self._tree.heading('id', text='ID', anchor='w')
        self._tree.heading('meta', text='STATUS', anchor='w')
        self._tree.column('#0', width=560, minwidth=260, stretch=True)
        self._tree.column('id', width=90, minwidth=70, stretch=False, anchor='w')
        self._tree.column('meta', width=220, minwidth=120, stretch=False, anchor='w')
        vs = ttk.Scrollbar(wrap, orient=VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vs.set)
        vs.pack(side=RIGHT, fill=Y)
        self._tree.pack(fill=BOTH, expand=YES)
        self._tree.bind('<<TreeviewOpen>>', self._on_tree_open)
        self._tree.bind('<Double-1>', self._on_tree_activate)
        self._tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self._c_search.trace_add('write', lambda *_: self._debounce(self._draw_courses_tree))
        self._c_sort.trace_add('write', lambda *_: self._draw_courses_tree())
        self._draw_courses_tree()

    def _filtered_courses(self):
        rows = list(self.courses)
        q = self._query_text(getattr(self, '_c_search', None)).lower() if hasattr(self, '_c_search') else ''
        if q:
            rows = [c for c in rows
                    if q in str(c.get('courseName', '')).lower() or q in str(c.get('courseId', ''))]
        srt = self._c_sort.get() if hasattr(self, '_c_sort') else '默认'
        if srt == '名称 A→Z':
            rows.sort(key=lambda c: str(c.get('courseName', '')))
        elif srt == '名称 Z→A':
            rows.sort(key=lambda c: str(c.get('courseName', '')), reverse=True)
        elif srt == 'ID ↑':
            rows.sort(key=lambda c: c.get('courseId', 0))
        return rows

    def _draw_courses_tree(self):
        if not hasattr(self, '_tree') or not self._tree.winfo_exists():
            return
        self._tree.delete(*self._tree.get_children())
        self._tree_courses = {}
        self._tree_works = {}
        self._loaded_courses = set()
        self._sel_tree_course = None
        self._sel_tree_work = None
        rows = self._filtered_courses()
        for course in rows:
            iid = f"c{course['courseId']}"
            self._tree_courses[iid] = course
            self._tree.insert('', 'end', iid=iid, text=self._short(course['courseName'], 42),
                              values=(course['courseId'], '展开查看作业'))
            self._tree.insert(iid, 'end', iid=iid + ':dummy', text='…', values=('', ''))
        if self._open_btn is not None and self._open_btn.winfo_exists():
            self._open_btn.configure(text='OPEN ▸ 作业')

    def _work_status(self, work):
        if work.get('grade') is not None:
            return 'DONE'
        remaining = max(0, work.get('tryTimes', 0) - work.get('times', 0))
        if remaining <= 0:
            return 'EXHAUSTED'
        return f'TRY {remaining}/{work.get("tryTimes", 0)}'

    def _on_tree_open(self, event=None):
        iid = self._tree.focus()
        course = self._tree_courses.get(iid)
        if course is None:
            return
        cid = course['courseId']
        if cid in self._loaded_courses:
            return
        self._loaded_courses.add(cid)
        self.log(f'LOADING works :: {course["courseName"]}')
        self.fetch(lambda: self.api.get_course_works(cid),
                   lambda res, c=course, i=iid: self._fill_course_works(c, i, res))

    def _fill_course_works(self, course, iid, result):
        if not self._tree.winfo_exists() or not self._tree.exists(iid):
            return
        ok, data = result
        for child in self._tree.get_children(iid):
            self._tree.delete(child)
        if not ok:
            self._loaded_courses.discard(course['courseId'])   # 允许重新展开重试
            self._tree.item(iid, values=(course['courseId'], 'load failed'))
            self._tree.insert(iid, 'end', iid=iid + ':err', text=str(data), values=('', 'ERR'))
            return
        self._tree.item(iid, values=(course['courseId'], f'{len(data)} works'))
        for work in data:
            wid = f"w{work['workId']}"
            self._tree_works[wid] = (course, work)
            self._tree.insert(iid, 'end', iid=wid, text=self._short(work['workName'], 42),
                              values=(work['workId'], self._work_status(work)))

    def _on_tree_select(self, event=None):
        iid = self._tree.focus()
        self._sel_tree_work = None
        self._sel_tree_course = self._tree_courses.get(iid)
        if iid in self._tree_works:
            course, work = self._tree_works[iid]
            self._sel_tree_course, self._sel_tree_work = course, work
        if self._open_btn is not None and self._open_btn.winfo_exists():
            self._open_btn.configure(text='OPEN ▸ 题目' if self._sel_tree_work else 'OPEN ▸ 作业')

    def _on_tree_activate(self, event=None):
        iid = self._tree.focus()
        if iid in self._tree_works:
            course, work = self._tree_works[iid]
            self.selected_course_id = course['courseId']
            self.selected_course_name = course['courseName']
            self.select_work(work)
        else:
            course = self._tree_courses.get(iid)
            if course:
                self.select_course(course)

    def _open_selected(self):
        if self._sel_tree_work:
            course = self._sel_tree_course
            self.selected_course_id = course['courseId']
            self.selected_course_name = course['courseName']
            self.select_work(self._sel_tree_work)
        elif self._sel_tree_course:
            self.select_course(self._sel_tree_course)

    def select_course(self, course):
        self.selected_course_id = course['courseId']
        self.selected_course_name = course['courseName']
        self.log(f'LOADING works :: {course["courseName"]}')
        self.fetch(lambda: self.api.get_course_works(course['courseId']), self._render_works)

# ---------- 作业（List + Inspector + 搜索/筛选/排序） ----------

    def _render_works(self, result):
        ok, data = result
        if not ok:
            Messagebox.show_error(title='错误', message=data)
            return
        self.works = data
        self.show_works()

    def show_works(self):
        self.begin_nav()
        self._sel_work = self.works[0] if self.works else None
        self.set_page(f'{self.selected_course_name} :: WORKS')
        self.page_header('ASSIGNMENTS', f'{self.selected_course_name} · {len(self.works)} works',
                         back='返回课程列表')
        self._build_works_page()

    def refresh_works(self):
        course = {'courseId': self.selected_course_id, 'courseName': self.selected_course_name}
        self.select_course(course)

    def _build_works_page(self):
        bar2 = self.command_bar()
        left = tk.Frame(bar2, bg=theme.BG_RAISED)
        left.pack(side=LEFT)
        self._w_search = tk.StringVar()
        self._w_status = tk.StringVar(value='全部')
        self._w_sort = tk.StringVar(value='默认')
        self.search_entry(left, self._w_search, '作业名 / 章节 / ID')
        self.combo_box(left, self._w_status, ['全部', '可提交', '已用完'], width=8)
        self.combo_box(left, self._w_sort, ['默认', '截止时间 ↑', '剩余 ↑', '名称 A→Z'], width=10)
        right = tk.Frame(bar2, bg=theme.BG_RAISED)
        right.pack(side=RIGHT)
        self.btn(right, 'REFRESH', self.refresh_works, 'secondary').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'EXPORT ALL', self.export_all_works, 'info').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'SUBMIT ALL 100', self.submit_all_works_100, 'warning').pack(side=LEFT)
        self._w_search.trace_add('write', lambda *_: self._debounce(self._draw_works))
        self._w_status.trace_add('write', lambda *_: self._debounce(self._draw_works, 60))
        self._w_sort.trace_add('write', lambda *_: self._debounce(self._draw_works, 60))

        body = tk.Frame(self.content_frame, bg=theme.BG)
        body.pack(fill=BOTH, expand=YES)
        list_box = tk.Frame(body, bg=theme.BG, width=440)
        list_box.pack(side=LEFT, fill=BOTH, expand=YES)
        list_box.pack_propagate(False)
        self._works_listbox = list_box
        head = tk.Frame(list_box, bg=theme.BG)
        head.pack(fill=X, pady=(0, 8))
        mono(head, 'ASSIGNMENTS', fg=theme.DIM, size=9, bg=theme.BG).pack(side=LEFT)
        self._w_count = mono(head, '', fg=theme.DIM, size=9, bg=theme.BG)
        self._w_count.pack(side=RIGHT)
        frame = ScrolledFrame(list_box, autohide=True)
        frame.pack(fill=BOTH, expand=YES)
        self._w_lst = tk.Frame(frame, bg=theme.BG)
        self._w_lst.pack(fill=BOTH, expand=YES)

        self._inspector = tk.Frame(body, bg=theme.SURFACE, width=300)
        self._inspector.pack(side=RIGHT, fill=Y, padx=(16, 0))
        self._inspector.pack_propagate(False)
        self._draw_works()

    def _remaining(self, work):
        return max(0, work.get('tryTimes', 0) - work.get('times', 0))

    def _filtered_works(self):
        rows = list(self.works)
        q = self._query_text(getattr(self, '_w_search', None)).lower() if hasattr(self, '_w_search') else ''
        st = self._w_status.get() if hasattr(self, '_w_status') else '全部'
        srt = self._w_sort.get() if hasattr(self, '_w_sort') else '默认'
        if q:
            rows = [w for w in rows if q in str(w.get('workName', '')).lower()
                    or q in str(w.get('chapterName', '')).lower()
                    or q in str(w.get('workId', ''))]
        if st == '可提交':
            rows = [w for w in rows if self._remaining(w) > 0]
        elif st == '已用完':
            rows = [w for w in rows if self._remaining(w) <= 0]
        if srt == '截止时间 ↑':
            rows.sort(key=lambda w: (w.get('expireTime') or '9999'))
        elif srt == '剩余 ↑':
            rows.sort(key=lambda w: (-self._remaining(w), str(w.get('workName', ''))))
        elif srt == '名称 A→Z':
            rows.sort(key=lambda w: str(w.get('workName', '')))
        return rows

    def _draw_works(self):
        for w in self._w_lst.winfo_children():
            w.destroy()
        rows = self._filtered_works()
        if self._w_count is not None and self._w_count.winfo_exists():
            self._w_count.config(text=f'{len(rows)}/{len(self.works)}')
        if self._sel_work not in rows:
            self._sel_work = rows[0] if rows else None
        if not rows:
            empty = tk.Frame(self._w_lst, bg=theme.SURFACE, highlightthickness=0)
            empty.pack(fill=X)
            mono(empty, '> NO MATCH', fg=theme.PRIMARY, size=9, bg=theme.SURFACE
                 ).pack(anchor='w', padx=12, pady=(8, 0))
            tk.Label(empty, text='该课程目前没有可用的作业。', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.ui(10), anchor='w').pack(anchor='w', padx=12, pady=(0, 8))
        else:
            for work in rows:
                self._work_row(self._w_lst, work)
        self._render_work_inspector()

    def _work_row(self, parent, work):
        selected = (work is self._sel_work)
        bg = theme.HOVER if selected else theme.SURFACE
        row = tk.Frame(parent, bg=bg, highlightthickness=0)
        row.pack(fill=X, pady=(0, 6))
        name_lbl = tk.Label(row, text=self._short(work['workName'], 34), bg=bg, fg=theme.FG, anchor='w',
                            font=('Microsoft YaHei', 10, 'bold'))
        name_lbl.pack(fill=X, padx=12, pady=(8, 0))
        line = tk.Frame(row, bg=bg)
        line.pack(fill=X, padx=12, pady=(2, 8))
        remaining = self._remaining(work)
        if remaining <= 0:
            chips = [mono(line, f'#{work["workId"]}', fg=theme.DIM, size=9, bg=bg),
                     mono(line, '已用完所有机会', fg=theme.ERROR, size=9, bg=bg)]
        elif remaining == 1:
            chips = [mono(line, f'#{work["workId"]}', fg=theme.DIM, size=9, bg=bg),
                     mono(line, f'Last chance! {remaining}/{work.get("tryTimes", 0)}',
                          fg=theme.WARNING, size=9, bg=bg)]
        else:
            chips = [mono(line, f'#{work["workId"]}', fg=theme.DIM, size=9, bg=bg),
                     mono(line, f'TRY {remaining}/{work.get("tryTimes", 0)}', fg=theme.PRIMARY,
                          size=9, bg=bg)]
        for c in chips:
            c.pack(side=LEFT, padx=(0, 12))
        for wd in [row, name_lbl, line] + chips:
            wd.bind('<Button-1>', lambda e, wk=work: self._select_work(wk))
            wd.bind('<Double-Button-1>', lambda e, wk=work: self._open_work(wk))

    def _select_work(self, work):
        self._sel_work = work
        self.clear_content()
        self.page_header('ASSIGNMENTS', f'{self.selected_course_name} · {len(self.works)} works',
                         back='返回课程列表')
        self._build_works_page()

    def _render_work_inspector(self):
        for w in self._inspector.winfo_children():
            w.destroy()
        work = self._sel_work
        tk.Label(self._inspector, text='INSPECTOR', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8, 'bold'), anchor='w').pack(fill=X, padx=12, pady=(10, 2))
        body = tk.Frame(self._inspector, bg=theme.SURFACE)
        body.pack(fill=X, padx=12)
        if work is None:
            tk.Label(body, text='未选择作业', bg=theme.SURFACE, fg=theme.MUTED,
                     font=theme.ui(10), anchor='w').pack(anchor='w', pady=12)
            return
        mono(body, self._short(work['workName'], 24), fg=theme.FG, size=10, bg=theme.SURFACE).pack(anchor='w', pady=(2, 0))

        def field(k, label):
            rowf = tk.Frame(body, bg=theme.SURFACE)
            rowf.pack(fill=X, pady=3)
            tk.Label(rowf, text=label, bg=theme.SURFACE, fg=theme.DIM,
                     font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
            val = work.get(k)
            shown = str(val) if val not in (None, '') else '—'
            tk.Label(rowf, text=shown, bg=theme.SURFACE, fg=theme.MUTED, anchor='w',
                     justify='left', wraplength=int(170 * self.scale),
                     font=('Consolas', max(8, int(9 * self.scale)))).pack(side=LEFT)

        field('workId', 'ID')
        field('chapterName', 'CHAPTER')
        field('expireTime', 'DUE')
        if work.get('grade') is not None:
            field('grade', 'SCORE')
        field('tryTimes', 'ATTEMPTS')
        if work.get('grade') is not None:
            rowf = tk.Frame(body, bg=theme.SURFACE)
            rowf.pack(fill=X, pady=3)
            tk.Label(rowf, text='STATUS', bg=theme.SURFACE, fg=theme.DIM,
                     font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
            mono(rowf, 'DONE', fg=theme.PRIMARY, size=9, bg=theme.SURFACE).pack(side=LEFT)
        elif self._remaining(work) <= 0:
            rowf = tk.Frame(body, bg=theme.SURFACE)
            rowf.pack(fill=X, pady=3)
            tk.Label(rowf, text='STATUS', bg=theme.SURFACE, fg=theme.DIM,
                     font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
            mono(rowf, 'EXHAUSTED', fg=theme.ERROR, size=9, bg=theme.SURFACE).pack(side=LEFT)

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

    # ---------- 题目（List + View + Inspector + 搜索/筛选/排序） ----------

    def show_questions(self):
        self.begin_nav()
        self._q_search = tk.StringVar()
        self._q_filter = tk.StringVar(value='全部')
        self._q_sort = tk.StringVar(value='默认')
        self._q_pos = 0
        self.images = []          # 重新进入题目页时释放上一轮的 PhotoImage 引用
        self._q_search.trace_add('write', lambda *_: self._q_trace(220))
        self._q_filter.trace_add('write', lambda *_: self._q_trace(60))
        self._q_sort.trace_add('write', lambda *_: self._q_trace(60))
        self.set_page(f'{self.selected_work_name} :: QUESTIONS')
        self._layout_questions()

    def _q_trace(self, delay):
        if getattr(self, '_building', False):
            return  # 重建控件（Combobox 回写变量）时忽略
        self._debounce(self._layout_questions, delay)

    def _layout_questions(self):
        self._building = True
        try:
            self._layout_questions_inner()
        finally:
            self._building = False

    def _layout_questions_inner(self):
        self.clear_content()
        self._qrows = self._filtered_questions()
        if self._q_pos >= len(self._qrows):
            self._q_pos = 0
        self._sel_qidx = self._q_pos

        bar = self.page_header('QUESTIONS', f'{self.selected_work_name} · {len(self.questions)} 题')
        back = tk.Button(bar, text='‹ 返回作业列表', command=self.show_works, relief='flat', bd=0, highlightthickness=0,
                         bg=theme.BG, fg=theme.SECONDARY, activebackground=theme.HOVER,
                         activeforeground=theme.SECONDARY, font=('Consolas', 9), cursor='hand2')
        back.pack(side=RIGHT, pady=8)

        # 工具栏：搜索 / 筛选 / 排序（全部本地执行）
        bar2 = self.command_bar()
        left = tk.Frame(bar2, bg=theme.BG_RAISED)
        left.pack(side=LEFT)
        self.search_entry(left, self._q_search, '题名 / 答案 / ID')
        self.combo_box(left, self._q_filter, ['全部', '有答案', '无图片'], width=8)
        self.combo_box(left, self._q_sort, ['默认', '编号 ↑', '名称 A→Z'], width=10)
        right = tk.Frame(bar2, bg=theme.BG_RAISED)
        right.pack(side=RIGHT)
        mono(right, f'{len(self._qrows)}/{len(self.questions)} SHOWN', fg=theme.DIM, size=9,
             bg=theme.BG_RAISED).pack(side=RIGHT)

        body = tk.Frame(self.content_frame, bg=theme.BG)
        body.pack(fill=BOTH, expand=YES)

        lst_pane = tk.Frame(body, bg=theme.BG, width=240)
        lst_pane.pack(side=LEFT, fill=Y)
        lst_pane.pack_propagate(False)
        self._q_list_pane = lst_pane
        mono(lst_pane, 'QUESTIONS', fg=theme.DIM, size=9, bg=theme.BG).pack(anchor='w', pady=(0, 8))
        lst_frame = ScrolledFrame(lst_pane, autohide=True)
        lst_frame.pack(fill=BOTH, expand=YES)
        lst = tk.Frame(lst_frame, bg=theme.BG)
        lst.pack(fill=BOTH, expand=YES)
        if not self._qrows:
            mono(lst, '> NO MATCH', fg=theme.PRIMARY, size=9).pack(anchor='w', padx=4, pady=8)
        else:
            for pos, q in enumerate(self._qrows):
                self._qlist_row(lst, pos, q)

        self._view = tk.Frame(body, bg=theme.SURFACE, highlightthickness=0)
        self._view.pack(side=LEFT, fill=BOTH, expand=YES, padx=16)
        self._view_image_holder = None

        self._inspector = tk.Frame(body, bg=theme.SURFACE, width=280)
        self._inspector.pack(side=RIGHT, fill=Y)
        self._inspector.pack_propagate(False)
        self._render_question_views()

    def _filtered_questions(self):
        rows = list(self.questions)
        q = self._query_text(getattr(self, '_q_search', None)).lower() if hasattr(self, '_q_search') else ''
        flt = self._q_filter.get() if hasattr(self, '_q_filter') else '全部'
        srt = self._q_sort.get() if hasattr(self, '_q_sort') else '默认'
        if q:
            rows = [x for x in rows if q in str(x.get('name', '')).lower()
                    or q in str(x.get('answer', '')).lower()
                    or q in str(x.get('id', ''))]
        if flt == '有答案':
            rows = [x for x in rows if x.get('answer') not in (None, '')]
        elif flt == '无图片':
            rows = [x for x in rows if not x.get('imgurl') or x.get('imgurl') == 'N/A']
        if srt == '编号 ↑':
            rows.sort(key=self._question_id_key)
        elif srt == '名称 A→Z':
            rows.sort(key=lambda x: str(x.get('name', '')))
        return rows

    @staticmethod
    def _question_id_key(item):
        raw = item.get('id')
        try:
            return (0, int(raw), '')
        except (TypeError, ValueError):
            return (1, 0, str(raw))

    def _qlist_row(self, parent, pos, q):
        selected = (pos == self._q_pos)
        bg = theme.HOVER if selected else theme.SURFACE
        row = tk.Frame(parent, bg=bg, highlightthickness=0)
        row.pack(fill=X, pady=(0, 5))
        id_lbl = tk.Label(row, text=f'Q{pos + 1:02d}', bg=bg,
                          fg=theme.PRIMARY if selected else theme.MUTED,
                          font=('Consolas', 9, 'bold'))
        id_lbl.pack(side=LEFT, padx=(10, 8), pady=9)
        name_lbl = tk.Label(row, text=self._short(q.get('name', 'N/A'), 26), bg=bg, fg=theme.FG, anchor='w',
                            font=theme.ui(10))
        name_lbl.pack(side=LEFT, fill=X, expand=YES, pady=9)
        for wd in (row, id_lbl, name_lbl):
            wd.bind('<Button-1>', lambda e, p=pos: self._select_qpos(p))

    def _select_qpos(self, pos):
        if pos != self._q_pos:
            self._q_pos = pos
            self._layout_questions()

    def _current_q(self):
        if self._qrows and self._q_pos < len(self._qrows):
            return self._qrows[self._q_pos]
        return None

    def _render_question_views(self):
        q = self._current_q()
        tk.Label(self._view, text='QUESTION', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8, 'bold'), anchor='w').pack(fill=X, padx=16, pady=(10, 0))
        nav = tk.Frame(self._view, bg=theme.SURFACE)
        nav.pack(fill=X, padx=16, pady=(6, 2))
        tk.Button(nav, text='‹', command=lambda: self._step_q(-1), relief='flat', bd=0, highlightthickness=0,
                  bg=theme.SURFACE, fg=theme.SECONDARY, cursor='hand2',
                  font=('Consolas', 12, 'bold')).pack(side=LEFT)
        tk.Label(nav, text=f'{self._q_pos + 1} / {len(self._qrows)}' if q else '',
                 bg=theme.SURFACE, fg=theme.DIM, font=('Consolas', 9)).pack(side=LEFT, padx=12)
        tk.Button(nav, text='›', command=lambda: self._step_q(1), relief='flat', bd=0, highlightthickness=0,
                  bg=theme.SURFACE, fg=theme.SECONDARY, cursor='hand2',
                  font=('Consolas', 12, 'bold')).pack(side=LEFT)

        if q is None:
            mono(self._view, '> NO QUESTIONS', fg=theme.PRIMARY, size=10,
                 bg=theme.SURFACE).pack(anchor='w', padx=16, pady=24)
            return

        tk.Label(self._view, text=self._short(q.get('name', 'N/A'), 48), bg=theme.SURFACE,
                 fg=theme.FG, anchor='w', justify='left', wraplength=int(520 * self.scale),
                 font=('Microsoft YaHei', 12, 'bold')).pack(anchor='w', padx=16, pady=(6, 0))
        mono(self._view, f'ID {q.get("id", "N/A")}', fg=theme.DIM, size=9,
             bg=theme.SURFACE).pack(anchor='w', padx=16, pady=(2, 0))
        img_area = tk.Frame(self._view, bg=theme.SURFACE)
        img_area.pack(anchor='w', padx=16, pady=(10, 0))
        imgurl = q.get('imgurl', 'N/A')
        if imgurl and imgurl != 'N/A':
            holder = tk.Label(img_area, text='> FETCHING IMAGE...', bg=theme.SURFACE,
                              fg=theme.DIM, font=('Consolas', 9), anchor='w')
            holder.pack()
            self._view_image_holder = holder
            self._load_image_async(holder, imgurl)
        else:
            mono(img_area, '[ NO IMAGE ]', fg=theme.DIM, size=9, bg=theme.SURFACE).pack()

        for w in self._inspector.winfo_children():
            w.destroy()
        tk.Label(self._inspector, text='INSPECTOR', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8, 'bold'), anchor='w').pack(fill=X, padx=14, pady=(10, 0))
        body = tk.Frame(self._inspector, bg=theme.SURFACE)
        body.pack(fill=X, padx=14)
        rowf = tk.Frame(body, bg=theme.SURFACE)
        rowf.pack(fill=X, pady=3)
        tk.Label(rowf, text='ANSWER', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
        tk.Label(body, text=str(q.get('answer', 'N/A')), bg=theme.SURFACE, fg=theme.WARNING,
                 anchor='w', font=('Consolas', 10), justify='left',
                 wraplength=int(220 * self.scale)).pack(fill=X, pady=(0, 8))
        score = tk.Frame(self._inspector, bg=theme.SURFACE)
        score.pack(fill=X, padx=14, pady=(4, 0))
        tk.Label(score, text='SCORE', bg=theme.SURFACE, fg=theme.DIM,
                 font=('Consolas', 8), width=9, anchor='w').pack(side=LEFT)
        self.grade_entry = ttk.Entry(score, width=8)
        self.grade_entry.pack(side=LEFT)
        tk.Label(self._inspector, text='提交成绩（0-100）', bg=theme.SURFACE, fg=theme.MUTED,
                 font=theme.ui(10)).pack(anchor='w', padx=14, pady=(6, 0))
        self.submit_grade_button = self.btn(self._inspector, 'SUBMIT', self.submit_grade, 'primary')
        self.submit_grade_button.pack(fill=X, padx=14, pady=(10, 14))

    def _step_q(self, delta):
        if not self._qrows:
            return
        self._q_pos = (self._q_pos + delta) % len(self._qrows)
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
                while len(cache) > 40:      # 简单的图片字节上限，防内存增长
                    cache.pop(next(iter(cache)))
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
        while len(self.images) > 40:        # 只保留最近若干张，避免引用泄漏
            self.images.pop(0)
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
