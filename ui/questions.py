# -*- coding: utf-8 -*-
"""题目工作区（List + View + Inspector）。"""
import io
import threading
import tkinter as tk
from tkinter.constants import *

import ttkbootstrap as ttk
from PIL import Image, ImageTk

import theme
from .widgets import ScrolledFrame, mono


class QuestionsMixin:
    def _render_questions(self, result):
        ok, data = result
        if not ok:
            self.msg_error(title='错误', message=data)
            return
        self.questions = data
        self.show_questions()

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
            self.msg_error(title='错误', message='请输入有效的成绩（0-100）。')
            return
        self.submit_grade_button.state(['disabled'])

        def on_done(result):
            self.submit_grade_button.state(['!disabled'])
            ok, data = result
            if ok:
                self.msg_info(title='提示', message=data)
            else:
                self.msg_error(title='错误', message=data)

        self.fetch(lambda: self.api.submit_answer(self.selected_work_id, grade), on_done)

