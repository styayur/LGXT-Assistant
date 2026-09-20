# -*- coding: utf-8 -*-
"""课程星图：科目=恒星系，习题=行星；点击恒星展开/收起，点击行星进入题目。"""
import time
import tkinter as tk
from tkinter.constants import *

import theme
from .space import GalaxyView
from .widgets import mono, GAP


class CoursesMixin:

    def show_courses(self):
        if not self.username or not self.password:
            self.msg_error('错误', '请先登录')
            self.show_login()
            return
        self.begin_nav()
        self.set_page('COURSES')
        self.set_active_nav('courses')
        self.log('LOADING courses...')
        self.fetch(self.api.get_my_courses, self._render_courses)

    def _render_courses(self, result):
        ok, data = result
        self.begin_nav()
        self.set_page('COURSES')
        bar = self.page_header('STAR MAP', '科目 = 恒星系 · 习题 = 行星')
        if ok:
            self.courses = data
            self._last_sync = time.strftime('%H:%M:%S')
            mono(bar, f'  {len(data)} systems · synced {self._last_sync}',
                 fg=theme.DIM, size=9).pack(side=LEFT, pady=(10, 0))
        else:
            self.set_state('ERROR')
            mono(bar, '  sync failed · 请检查网络后重试', fg=theme.ERROR,
                 size=9).pack(side=LEFT, pady=(10, 0))

        bar2 = self.command_bar()
        left = tk.Frame(bar2, bg=theme.BG_RAISED)
        left.pack(side=LEFT)
        self._c_search = tk.StringVar()
        self._c_sort = tk.StringVar(value='默认')
        self.search_entry(left, self._c_search, '课程名 / ID')
        self.combo_box(left, self._c_sort, ['默认', '名称 A→Z', '名称 Z→A', 'ID ↑'])
        right = tk.Frame(bar2, bg=theme.BG_RAISED)
        right.pack(side=RIGHT)
        self.btn(right, 'REFRESH', self.show_courses, 'secondary').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'EXPORT ALL', self.export_all_courses, 'info').pack(side=LEFT, padx=(0, GAP))
        self.btn(right, 'SUBMIT ALL 100', self.submit_all_courses_100, 'warning').pack(side=LEFT)

        self._galaxy = GalaxyView(self.content_frame, self._galaxy_open_course,
                                  self._galaxy_open_work)
        self._galaxy.pack(fill='both', expand=True)
        if ok:
            self._c_search.trace_add('write', lambda *_: self._debounce(self._redraw_galaxy, 180))
            self._c_sort.trace_add('write', lambda *_: self._debounce(self._redraw_galaxy, 60))
            self._redraw_galaxy()
        else:
            self._galaxy.set_courses([])

    def _redraw_galaxy(self):
        if hasattr(self, '_galaxy') and self._galaxy.winfo_exists():
            self._galaxy.set_courses(self._filtered_courses())

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

    # ---- 星图交互 ----

    def _galaxy_open_course(self, course):
        cid = course['courseId']
        if self._galaxy.is_expanded(cid):
            self._galaxy.collapse(cid)
            return
        self.log(f'LOADING works :: {course["courseName"]}')
        self.fetch(lambda: self.api.get_course_works(cid),
                   lambda res, c=course: self._galaxy_fill(c, res))

    def _galaxy_fill(self, course, result):
        if not hasattr(self, '_galaxy') or not self._galaxy.winfo_exists():
            return
        ok, data = result
        if ok:
            self._galaxy.set_works(course['courseId'], data)
        else:
            self._galaxy.set_error(course['courseId'], data)

    def _galaxy_open_work(self, course, work):
        self.selected_course_id = course['courseId']
        self.selected_course_name = course['courseName']
        self.select_work(work)

    # ---- 兼容旧入口：直接进入某课程的作业工作区 ----

    def select_course(self, course):
        self.selected_course_id = course['courseId']
        self.selected_course_name = course['courseName']
        self.log(f'LOADING works :: {course["courseName"]}')
        self.fetch(lambda: self.api.get_course_works(course['courseId']), self._render_works)
