# -*- coding: utf-8 -*-
import threading

import tasks
from exporter import ExportOptions


class FakeClient:
    """按序返回 answers；跑完后返回空列表（模拟“没有更多新题”）。"""

    def __init__(self, answers=None):
        self.answers = answers or []
        self.calls = 0
        self.lock = threading.Lock()

    def get_questions(self, work_id):
        with self.lock:
            self.calls += 1
            idx = self.calls - 1
        if idx >= len(self.answers):
            return (True, [])
        return (True, self.answers[idx])

    def submit_answer(self, work_id, grade):
        return (True, 'ok')


class FakeUI:
    def __init__(self):
        self.statuses = []
        self.closed = []

    def status(self, text):
        self.statuses.append(text)

    def progress(self, value):
        pass

    def maximum(self, value):
        pass

    def stop_and_close(self, ms):
        self.closed.append(ms)


def test_merge_questions_dedupes():
    collected = {}
    assert tasks._merge_questions(collected, [{'id': 1}, {'id': 2}]) is True
    assert tasks._merge_questions(collected, [{'id': 2}]) is False
    assert set(collected) == {1, 2}


def test_batch_collect_stops_after_threshold():
    client = FakeClient()
    ui = FakeUI()
    collected, err = tasks.batch_collect(ui, client, 1, 'c', 'w')
    assert collected == {} and err == '没有找到任何题目'
    assert client.calls == tasks.MIN_ITERATIONS   # 30 次后停止，而不是 200 次


def test_batch_collect_returns_questions():
    client = FakeClient(answers=[[{'id': 1, 'name': 'q'}]])
    collected, err = tasks.batch_collect(FakeUI(), client, 1, 'c', 'w')
    assert err is None and list(collected) == [1]


def test_cancel_pending_cancels_unfinished_futures():
    class FakeFuture:
        def __init__(self):
            self.cancelled = False

        def done(self):
            return False

        def cancel(self):
            self.cancelled = True

    futures = [FakeFuture(), FakeFuture()]
    tasks._cancel_pending(futures)
    assert all(f.cancelled for f in futures)


def test_collect_single_saves_and_bounds_requests(monkeypatch, tmp_path):
    saved = {}

    def fake_save(client, collected, *args, **kwargs):
        saved['collected'] = dict(collected)

    monkeypatch.setattr(tasks, 'save_collected', fake_save)
    client = FakeClient()
    ui = FakeUI()
    opts = ExportOptions(str(tmp_path), True, True, False, True)
    # 每次返回同一题：第一次新增，之后不再新增 → 30 次后提前结束
    client.answers = [[{'id': 1, 'name': 'q', 'answer': 'a', 'imgurl': ''}]]
    result = tasks.collect_single(ui, client, 1, 'w', 'c', 101, opts, max_iterations=100)
    assert result and list(result) == [1]
    assert saved['collected'] == result
    # 已提交的 future 可能已在执行，cancel 只能取消尚未开始的；
    # 集成断言只保证不超出提交上限，取消行为由 test_cancel_pending_* 单独覆盖
    assert client.calls <= 100
    assert 1000 in ui.closed
