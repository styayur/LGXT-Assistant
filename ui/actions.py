# -*- coding: utf-8 -*-
"""批量 / 收集任务入口（纯 UI 触发，实际工作在 tasks.py）。"""
import exporter
import tasks


class TasksMixin:
    def _preview_grade_batch(self, scope):
        from tkinter import messagebox
        def ready(plan):
            names = '\n'.join(str(w.get('workName', w['workId'])) for w in plan['works'])
            if not messagebox.askyesno('一键满分', f"范围：{scope}，共 {plan['count']} 个作业，目标 100 分。\n"
                                      f"读取失败课程：{plan['fetchFailed']}。会修改服务器记录，可能消耗次数。\n"
                                      "取消只停止后续请求；已提交更改不能撤销。超时结果需到平台核实。\n" + names):
                return
            from desktop.storage import Store
            import config
            from pathlib import Path
            audit = Store(Path(config.default_config_path()).parent / 'desktop').audit_batch
            self.run_task('一键满分', lambda ui: tasks.execute_batch(ui, self.api, plan['works'], audit=audit),
                          on_result=lambda r: self.show_result(r['title'], r['text']))
        course = {'courseId': self.selected_course_id} if scope != 'all' else None
        work = {'workId': self.selected_work_id} if scope == 'assignment' else None
        self.fetch(lambda: tasks.batch_plan(self.api, scope, course, work), ready)

    def submit_all_courses_100(self):
        self._preview_grade_batch('all')

    def submit_all_works_100(self):
        self._preview_grade_batch('course')

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

