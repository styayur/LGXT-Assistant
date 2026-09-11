# -*- coding: utf-8 -*-
"""作业工作区（List + Inspector）。"""
import tkinter as tk
from tkinter.constants import *

import ttkbootstrap as ttk

import theme
from .widgets import ScrolledFrame, mono, GAP


class WorksMixin:
    def _render_works(self, result):
        ok, data = result
        if not ok:
            self.msg_error(title='错误', message=data)
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

