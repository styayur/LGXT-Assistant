# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest

import ui
from ui.questions import QuestionsMixin
from ui.widgets import WidgetsMixin


def test_question_id_sort_key_handles_non_numeric():
    a = QuestionsMixin._question_id_key({'id': 'A1'})
    b = QuestionsMixin._question_id_key({'id': '2'})
    c = QuestionsMixin._question_id_key({'id': None})
    assert b < a and c[0] == 1


def test_short_truncates_with_ellipsis():
    fake = SimpleNamespace(scale=1.0)
    out = WidgetsMixin._short(fake, 'x' * 100, 10)
    assert out.endswith('…') and len(out) <= 10


def test_app_is_composed_from_mixins():
    from ui import App
    for mixin in (ui.base.AppBase, ui.login.LoginMixin, ui.courses.CoursesMixin,
                  ui.works.WorksMixin, ui.questions.QuestionsMixin,
                  ui.settings.SettingsMixin, ui.actions.TasksMixin, ui.widgets.WidgetsMixin):
        assert issubclass(App, mixin)


def test_app_can_start_headless(monkeypatch):
    tk = pytest.importorskip('tkinter')
    import api, config
    monkeypatch.setattr(api.client, 'get_my_courses', lambda: (True, []))
    monkeypatch.setattr(api.client, 'login', lambda u, p: (True, 'ok'))
    monkeypatch.setattr(config, 'get_saved_username', lambda: None)
    try:
        import ttkbootstrap as ttk
        root = ttk.Window()
    except Exception as exc:                      # 无显示环境时跳过
        pytest.skip('no display: %s' % exc)
    root.withdraw()
    app = ui.App(root)
    assert app.username_entry is not None          # 登录页已构建
    root.destroy()
