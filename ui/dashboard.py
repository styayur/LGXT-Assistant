# -*- coding: utf-8 -*-
"""仪表盘：待激活作业数、已完成作业数、平均分（数据来自真实 API，不伪造指标）。"""
import tkinter as tk
from tkinter.constants import *

import theme
from .widgets import AngularPanel, mono


class DashboardMixin:

    def show_dashboard(self):
        self.begin_nav()
        self.set_page('DASHBOARD')
        self.set_active_nav('dashboard')
        bar = self.page_header('DASHBOARD', '作业完成度与得分')
        self.btn(bar, 'REFRESH', self.refresh_dashboard, 'secondary').pack(side=RIGHT, pady=6)
        self._dash_body = tk.Frame(self.content_frame, bg=theme.BG)
        self._dash_body.pack(fill='both', expand=True)
        self._dash_nodes = []
        self._render_dashboard(None)
        self.refresh_dashboard()

    def refresh_dashboard(self):
        self.log('LOADING dashboard...')
        self._render_dashboard(None)
        self.fetch(self.api.get_my_courses, self._dash_after_courses)

    def _dash_after_courses(self, result):
        ok, data = result
        if not ok:
            self._render_dashboard({'error': data})
            return
        self.courses = data
        self.fetch(lambda: self._collect_dashboard(data), self._render_dashboard)

    def _collect_dashboard(self, courses):
        """worker 线程：汇总所有课程的作业统计（只读数据，不触碰 UI）。"""
        pending = completed = 0
        scores = []
        messages = []
        fetch_fail = 0
        total = 0
        for course in courses:
            ok, works = self.api.get_course_works(course['courseId'])
            if not ok:
                fetch_fail += 1
                messages.append(f"课程 '{course['courseName']}' 读取失败：{works}")
                continue
            for work in works:
                total += 1
                grade = work.get('grade')
                if grade is not None:
                    completed += 1
                    try:
                        scores.append(float(grade))
                    except (TypeError, ValueError):
                        pass
                elif max(0, work.get('tryTimes', 0) - work.get('times', 0)) > 0:
                    pending += 1
        return {'pending': pending, 'completed': completed,
                'average': (sum(scores) / len(scores)) if scores else 0.0,
                'total': total, 'fetch_fail': fetch_fail, 'messages': messages}

    def _render_dashboard(self, stats):
        for node in getattr(self, '_dash_nodes', []):
            node.destroy()
        self._dash_nodes = []
        body = getattr(self, '_dash_body', None)
        if body is None or not body.winfo_exists():
            return
        if stats is None:
            mono(body, '> SYNCING ...', fg=theme.PRIMARY, size=11).pack(anchor='w', pady=20)
            return
        if 'error' in stats:
            mono(body, '> ERROR', fg=theme.ERROR, size=11).pack(anchor='w', pady=(10, 0))
            tk.Label(body, text=str(stats['error']), bg=theme.BG, fg=theme.MUTED,
                     font=theme.ui(10)).pack(anchor='w')
            return

        cards = tk.Frame(body, bg=theme.BG)
        cards.pack(fill='x')
        for title, value, color in (('待激活 PENDING', str(stats['pending']), theme.WARNING),
                                    ('已完成 DONE', str(stats['completed']), theme.SECONDARY),
                                    ('平均分 AVG', f"{stats['average']:.1f}", theme.PRIMARY)):
            card = AngularPanel(cards, cut=14, padding=14, bg=theme.SURFACE, line=theme.METAL_LIGHT)
            card.configure(width=260, height=120)
            card.pack(side='left', padx=(0, 16))
            tk.Label(card.body, text=title, bg=theme.SURFACE, fg=theme.DIM,
                     font=('Consolas', 9, 'bold'), anchor='w').pack(fill='x')
            tk.Label(card.body, text=value, bg=theme.SURFACE, fg=color,
                     font=('Consolas', 26, 'bold'), anchor='w').pack(fill='x', pady=(6, 0))
            self._dash_nodes.append(card)

        summary = tk.Frame(body, bg=theme.BG)
        summary.pack(fill='x', pady=(16, 0))
        mono(summary, f"TOTAL {stats['total']} assignments · fetch failed courses: {stats['fetch_fail']}",
             fg=theme.MUTED, size=9).pack(anchor='w')
        for line in stats['messages'][:8]:
            mono(summary, '  - ' + line, fg=theme.ERROR, size=9).pack(anchor='w')
        self._dash_nodes.append(summary)
