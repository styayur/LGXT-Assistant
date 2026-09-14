# -*- coding: utf-8 -*-
"""宇宙星链视图：代码绘制的星点背景、悬停光轨、恒星系（科目）与行星（习题）。"""
import math
import random
import tkinter as tk

import theme
from .widgets import cut_points

STATUS_COLORS = {
    'OPEN': theme.PRIMARY,
    'WARN': theme.WARNING,
    'DONE': theme.SECONDARY,
    'EXHAUSTED': theme.ERROR,
}


class GalaxyView(tk.Canvas):
    """课程星图：每个科目一颗恒星，展开后行星环绕（点击行星进入题目）。"""

    CELL_W = 300
    CELL_H = 260

    def __init__(self, parent, on_open_course, on_open_work):
        super().__init__(parent, bg=theme.BG, highlightthickness=0, bd=0)
        self._on_open_course = on_open_course
        self._on_open_work = on_open_work
        self._courses = []
        self._works = {}          # course_id -> [work,...]
        self._errors = {}         # course_id -> message
        self.expanded = set()
        self._nodes = {}          # tag -> (x, y, kind, payload)
        self._hover_tag = None
        self._bg_stars = []
        self._running = False
        self.bind('<Configure>', lambda e: self.redraw())
        self.bind('<Motion>', self._on_motion)
        self.bind('<Button-1>', self._on_click)
        self.bind('<Leave>', lambda e: self._set_hover(None))

    # ---------- 数据 ----------

    def set_courses(self, courses):
        self._courses = list(courses)
        self._works = {}
        self._errors = {}
        self.expanded = set()
        self.redraw()

    def course_ids(self):
        return [c['courseId'] for c in self._courses]

    def is_expanded(self, course_id):
        return course_id in self.expanded

    def set_works(self, course_id, works):
        self._works[course_id] = list(works)
        self._errors.pop(course_id, None)
        self.expanded.add(course_id)
        self.redraw()

    def collapse(self, course_id):
        self.expanded.discard(course_id)
        self.redraw()

    def set_error(self, course_id, message):
        self._errors[course_id] = str(message)
        self.expanded.discard(course_id)      # 允许再次点击重试
        self.redraw()

    def works_shown(self, course_id):
        return len(self._works.get(course_id, []))

    # ---------- 绘制 ----------

    def redraw(self):
        self.delete('all')
        width, height = self.winfo_width(), self.winfo_height()
        if width < 20 or height < 20:
            return
        self._draw_bg(width, height)
        self._nodes = {}
        cols = max(1, width // self.CELL_W)
        for idx, course in enumerate(self._courses):
            col, row = idx % cols, idx // cols
            x = col * self.CELL_W + self.CELL_W // 2
            y = row * self.CELL_H + 92
            self._draw_system(course, x, y)
        if not self._bg_stars:
            self._seed_bg(width, height)
        if not self._running:
            self._running = True
            self._animate()

    def _seed_bg(self, width, height):
        self._bg_stars = [{
            'x': random.uniform(0, width), 'y': random.uniform(0, height),
            'r': random.choice((1, 1, 2)), 'speed': random.uniform(0.05, 0.25),
            'phase': random.uniform(0, 6.28),
        } for _ in range(70)]

    def _draw_bg(self, width, height):
        if not self._bg_stars:
            self._seed_bg(width, height)
        mouse_x, mouse_y = self._mouse if hasattr(self, '_mouse') else (-999, -999)
        for star in self._bg_stars:
            star['y'] += star['speed']
            if star['y'] > height:
                star['y'] = 0
                star['x'] = random.uniform(0, width)
            x, y, r = star['x'], star['y'], star['r']
            dist = math.hypot(x - mouse_x, y - mouse_y)
            if 6 < dist < 150:                 # 悬停光轨：星点向光标汇聚
                nx = x + (mouse_x - x) * 0.22
                ny = y + (mouse_y - y) * 0.22
                color = theme.SECONDARY if dist < 80 else '#1B5E70'
                self.create_line(x, y, nx, ny, fill=color, width=1)
            self.create_oval(x - r, y - r, x + r, y + r, fill='#8FA6B8', outline='')

    def _draw_system(self, course, x, y):
        cid = course['courseId']
        expanded = cid in self.expanded
        glow = theme.STAR if expanded else '#9FD8FF'
        for radius, color in ((26, '#0E2233'), (18, '#12405A'), (11, glow)):
            self.create_oval(x - radius, y - radius, x + radius, y + radius,
                             fill=color, outline='')
        self.create_text(x, y + 40, text=self._ellipsis(course.get('courseName', '')), fill=theme.FG,
                         font=('Microsoft YaHei', 10, 'bold'))
        self.create_text(x, y + 58, text=f"#{cid}", fill=theme.DIM, font=('Consolas', 8))
        self._nodes[f'course:{cid}'] = (x, y, 'course', course)

        if cid in self._errors:
            self.create_text(x, y + 78, text='> LOAD FAILED · 点击重试', fill=theme.ERROR,
                             font=('Consolas', 8))
        for work in self._works.get(cid, []):
            wid = work['workId']
            works = self._works[cid]
            angle = (works.index(work) / max(1, len(works))) * 2 * math.pi
            px = x + math.cos(angle) * 78
            py = y + math.sin(angle) * 78
            state = self._work_state(work)
            color = STATUS_COLORS.get(state, theme.MUTED)
            self.create_oval(x - 78, y - 78, x + 78, y + 78, outline=theme.ORBIT, dash=(2, 4))
            self.create_oval(px - 8, py - 8, px + 8, py + 8, fill=color, outline='')
            self.create_text(px, py + 18, text=self._ellipsis(work.get('workName', ''), 14),
                             fill=theme.MUTED, font=('Microsoft YaHei', 8))
            self._nodes[f'work:{wid}'] = (px, py, 'work', (course, work))

        if self._hover_tag and self._hover_tag in self._nodes:
            hx, hy, kind, payload = self._nodes[self._hover_tag]
            pts = cut_points(hx - 16, hy - 16, hx + 16, hy + 16, 6)
            self.create_polygon(pts, outline=theme.SECONDARY, fill='', width=1)

    @staticmethod
    def _work_state(work):
        if work.get('grade') is not None:
            return 'DONE'
        remaining = max(0, work.get('tryTimes', 0) - work.get('times', 0))
        if remaining <= 0:
            return 'EXHAUSTED'
        return 'WARN' if remaining == 1 else 'OPEN'

    @staticmethod
    def _ellipsis(text, limit=18):
        text = str(text)
        return text if len(text) <= limit else text[:limit - 1] + '…'

    # ---------- 交互 ----------

    def _on_motion(self, event):
        self._mouse = (event.x, event.y)
        self._set_hover(self._nearest(event.x, event.y))

    def _set_hover(self, tag):
        if tag != self._hover_tag:
            self._hover_tag = tag
            self.redraw()

    def _nearest(self, x, y):
        best, dist = None, 26
        for tag, (nx, ny, _kind, _payload) in self._nodes.items():
            d = math.hypot(nx - x, ny - y)
            if d < dist:
                best, dist = tag, d
        return best

    def _on_click(self, event):
        tag = self._nearest(event.x, event.y)
        if not tag:
            return
        _x, _y, kind, payload = self._nodes[tag]
        if kind == 'course':
            self._on_open_course(payload)
        else:
            course, work = payload
            self._on_open_work(course, work)

    def _animate(self):
        if not self.winfo_exists():
            self._running = False
            return
        self.redraw()
        self.after(70, self._animate)
