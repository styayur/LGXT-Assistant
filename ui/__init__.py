# -*- coding: utf-8 -*-
"""LGXT Assistant UI 包：按职责拆分为 shell / widgets / 页面 mixin。"""
from .actions import TasksMixin
from .base import AppBase, PAD, SIDEBAR_W
from .courses import CoursesMixin
from .login import LoginMixin
from .questions import QuestionsMixin
from .settings import SettingsMixin
from .widgets import WidgetsMixin
from .works import WorksMixin


class App(LoginMixin, CoursesMixin, WorksMixin, QuestionsMixin, SettingsMixin,
          TasksMixin, WidgetsMixin, AppBase):
    """完整应用：由各职责 mixin 组合而成（方法体与拆分前一致）。"""


__all__ = ['App', 'SIDEBAR_W', 'PAD']
