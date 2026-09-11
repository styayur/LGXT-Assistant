# -*- coding: utf-8 -*-
"""课程树（科目 → 作业 懒加载展开）。"""
import time
import tkinter as tk
from tkinter.constants import *

import ttkbootstrap as ttk

import theme
from .widgets import ScrolledFrame, mono, GAP


class CoursesMixin:
    def show_courses(self):
        if not self.username or not self.password:
            self.msg_error(title='错误', message='请先登录')
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

