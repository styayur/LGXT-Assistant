# -*- coding: utf-8 -*-
"""App 外壳：窗口框架、状态、队列轮询、任务适配、字体缩放、退出特效。"""
import logging
import os
import queue
import random
import threading
import time
import tkinter as tk
import tkinter.ttk as tkttk
from tkinter.constants import *

import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox

import api
import config
import exporter
import tasks
import theme
from exporter import ExportOptions

SERVICE = '理工学堂助手'
SIDEBAR_W = 188
PAD = 24
log = logging.getLogger(__name__)


class AppBase:
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

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = config.default_config_path()
        self.settings = config.Settings(self.config_file,
                                        legacy_path=config.legacy_config_path(project_dir))
        from . import audio
        audio.set_enabled(getattr(self.settings, 'ui_sound', True))
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

        self.root.overrideredirect(True)          # 隐藏系统原生标题栏
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self._work_height = max(600, screen_h - 48)   # 预留任务栏
        self.root.geometry(f'{screen_w}x{self._work_height}+0+0')
        self._drag_offset = None
        self._resize_origin = None
        self._ambient_stars = []
        self._ambient_mouse = (0, 0)
        self._ambient_running = False

        self.setup_ui()
        self.set_state('STANDBY')
        self.set_page('AUTH')
        self.show_login()
        self.root.protocol('WM_DELETE_WINDOW', self.quit_app)
        self.root.bind('<F11>', lambda e: self._toggle_fullscreen())
        self.root.bind('<Configure>', self._on_configure)
        self.root.bind_all('<Escape>', lambda e: self.quit_app())
        self.root.after(120, self.root.focus_force)
        self.root.after(60, self._poll_queue)

    def setup_ui(self):
        # 星点背景 Canvas：主容器内缩 14px，四周可见浮动星点
        self.star_canvas = tk.Canvas(self.root, bg=theme.BG, highlightthickness=0, bd=0)
        self.star_canvas.pack(fill=BOTH, expand=YES)
        self.main_frame = tk.Frame(self.star_canvas, bg=theme.BG)
        self.main_frame.place(x=14, y=14, relwidth=1.0, relheight=1.0, width=-28, height=-28)
        self.star_canvas.bind('<Motion>', lambda e: setattr(self, '_ambient_mouse', (e.x, e.y)))
        self._init_ambient()
        self._ambient_running = True
        self.root.after(80, self._animate_ambient)

        # 自绘标题栏（无最小化/关闭按钮；ESC 退出）
        header = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=46)
        header.pack(side=TOP, fill=X)
        header.pack_propagate(False)
        self._header = header
        brand = tk.Label(header, text='LGXT::ASSISTANT', bg=theme.BG_RAISED, fg=theme.PRIMARY,
                         font=('Consolas', 12, 'bold'))
        brand.pack(side=LEFT, padx=(24, 0))
        self.page_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.MUTED,
                                   font=('Consolas', 11))
        self.page_label.pack(side=LEFT, padx=(24, 0))
        hint = tk.Label(header, text='[ ESC ] EXIT   [ F11 ] FULLSCREEN', bg=theme.BG_RAISED,
                        fg=theme.DIM, font=('Consolas', 8))
        hint.pack(side=RIGHT, padx=(0, 24))
        self.state_label = tk.Label(header, text='', bg=theme.BG_RAISED, fg=theme.DIM,
                                    font=('Consolas', 9, 'bold'))
        self.state_label.pack(side=RIGHT, padx=(0, 16))
        for widget in (header, brand, self.page_label, hint, self.state_label):
            self._bind_drag(widget)

        # 右下角自绘缩放把手（无原生边框时用来调整窗口）
        grip = tk.Canvas(self.star_canvas, width=18, height=18, bg=theme.BG,
                         highlightthickness=0, bd=0, cursor='size_nw_se')
        grip.place(relx=1.0, rely=1.0, anchor='se')
        grip.create_line(4, 14, 14, 4, fill=theme.METAL_LIGHT)
        grip.create_line(9, 15, 15, 9, fill=theme.METAL_DARK)
        grip.bind('<Button-1>', self._resize_start)
        grip.bind('<B1-Motion>', self._resize_drag)

        # StatusBar：左日志 / 右版本（API/AUTH 细节移入设置页系统信息）
        statusbar = tk.Frame(self.main_frame, bg=theme.BG_RAISED, height=24)
        statusbar.pack(side=BOTTOM, fill=X)
        statusbar.pack_propagate(False)
        self._statusbar = statusbar
        self.log_label = tk.Label(statusbar, text='> SYSTEM READY', bg=theme.BG_RAISED,
                                  fg=theme.DIM, font=('Consolas', 8), anchor='w')
        self.log_label.pack(side=LEFT, fill=X, expand=YES, padx=12)
        tk.Label(statusbar, text='v3.1.0 · GPL-3.0', bg=theme.BG_RAISED, fg=theme.DIM,
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
            def on_enter(_e, w=lbl):
                w.configure(bg=theme.HOVER, fg=theme.FG)
                try:
                    from . import audio
                    audio.play('hover')
                except Exception:
                    pass
            lbl.bind('<Enter>', on_enter)
            lbl.bind('<Leave>', lambda e: lbl.configure(bg=theme.SURFACE, fg=theme.MUTED))
            lbl.bind('<Button-1>', lambda e: command())
            return lbl

        section('WORKSPACE')
        item('仪表盘', self.show_dashboard)
        item('课程星图', self.show_courses)
        section('SYSTEM')
        item('设置', self.show_settings)
        item('帮助', self.show_help)
        item('退出', self.quit_app)

        tk.Label(sidebar, text='v3.1.0', bg=theme.SURFACE, fg=theme.FG,
                 font=('Consolas', 8), anchor='w').pack(side=BOTTOM, fill=X, padx=16, pady=(0, 14))

    def _maximize(self):
        """无边框窗口的“最大化”：铺满屏幕工作区（保留任务栏）。"""
        screen_w = self.root.winfo_screenwidth()
        self.root.geometry(f'{screen_w}x{self._work_height}+0+0')

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        try:
            self.root.attributes('-fullscreen', self._fullscreen)
        except tk.TclError:
            return
        if not self._fullscreen:
            self._maximize()

    # ---- 自绘标题栏拖拽 / 右下角缩放 ----

    def _bind_drag(self, widget):
        widget.bind('<Button-1>', self._drag_start)
        widget.bind('<B1-Motion>', self._drag_move)
        widget.bind('<Double-Button-1>', lambda e: self._maximize())

    def _drag_start(self, event):
        self._drag_offset = (event.x_root - self.root.winfo_x(),
                             event.y_root - self.root.winfo_y())

    def _drag_move(self, event):
        if not self._drag_offset:
            return
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        self.root.geometry(f'+{max(0, x)}+{max(0, y)}')

    def _resize_start(self, event):
        self._resize_origin = (event.x_root, event.y_root,
                               self.root.winfo_width(), self.root.winfo_height())

    def _resize_drag(self, event):
        if not self._resize_origin:
            return
        x0, y0, w0, h0 = self._resize_origin
        w = max(1200, w0 + (event.x_root - x0))
        h = max(800, h0 + (event.y_root - y0))
        self.root.geometry(f'{w}x{h}')

    # ---- 背景星点 / 悬停光轨 ----

    def _init_ambient(self):
        width = max(400, self.root.winfo_screenwidth())
        height = max(300, self._work_height)
        self._ambient_stars = [{
            'x': random.uniform(0, width),
            'y': random.uniform(0, height),
            'r': random.choice((1, 1, 1, 2)),
            'speed': random.uniform(0.10, 0.45),
            'phase': random.uniform(0, 6.28),
        } for _ in range(90)]

    def _animate_ambient(self):
        if self._quitting or not self.star_canvas.winfo_exists():
            self._ambient_running = False
            return
        canvas = self.star_canvas
        canvas.delete('star')
        width, height = canvas.winfo_width(), canvas.winfo_height()
        mx, my = self._ambient_mouse
        for star in self._ambient_stars:
            star['y'] += star['speed']
            if star['y'] > height + 2:
                star['y'] = -2
                star['x'] = random.uniform(0, max(1, width))
            star['phase'] += 0.08
            x, y, r = star['x'], star['y'], star['r']
            brightness = 0.55 + 0.45 * abs(random.random())
            color = theme.STAR if brightness > 0.8 else '#7C93A6'
            dist = ((x - mx) ** 2 + (y - my) ** 2) ** 0.5
            if dist < 140 and dist > 4:      # 悬停光轨：向鼠标方向汇聚
                nx = x + (mx - x) * 0.18
                ny = y + (my - y) * 0.18
                trail = theme.SECONDARY if dist < 70 else '#1C6B80'
                canvas.create_line(x, y, nx, ny, fill=trail, width=1, tags='star')
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline='', tags='star')
        canvas.tag_lower('star')
        self.root.after(50, self._animate_ambient)

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
                self.root.after(0, lambda: self.msg_info(title=event[1], message=event[2]))
            elif kind == 'error_after':
                self.root.after(event[1], lambda: self.msg_error(title=event[2], message=event[3]))
            elif kind == 'task_error':
                _, exc = event
                self.log(f'ERROR {exc}')
                self._destroy_progress()
                self.root.after(0, lambda: self.msg_error(title='错误', message=f'任务失败：{exc}'))
            elif kind == 'run_ok':
                _, on_result, result = event
                on_result(result)
            elif kind == 'run_none':
                _, ms, title, message = event
                self.root.after(ms, lambda: self.msg_error(title=title, message=message))
            elif kind == 'image_bytes':
                _, holder, data, error = event
                self._render_image(holder, data, error)
        except tk.TclError:
            pass
        except Exception as exc:
            log.exception('事件处理失败')
            self._write_log(f'ERROR {exc}')

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

    def msg_info(self, title, message):
        """单一弹窗出口：便于测试注入，避免各页面各自 import Messagebox。"""
        Messagebox.show_info(title=title, message=message)

    def msg_error(self, title, message):
        Messagebox.show_error(title=title, message=message)

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

