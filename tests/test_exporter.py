# -*- coding: utf-8 -*-
import base64
import os

import pytest

import exporter


PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')


class FakeClient:
    def __init__(self):
        self.calls = 0

    def fetch_image(self, url):
        self.calls += 1
        return PNG_1PX


QUESTIONS = {
    '1': {'id': '1', 'name': '题目一', 'answer': 'A', 'imgurl': ''},
    '2': {'id': '2', 'name': '题目二', 'answer': 'B', 'imgurl': 'http://example/img.png'},
}


def test_clean_name_rules():
    assert exporter.clean_name('a<b>c:d/e\\f|g?h*i') == 'abcdefghi'
    assert exporter.clean_name('name. ') == 'name'
    assert exporter.clean_name('CON').startswith('_CON')
    assert len(exporter.clean_name('x' * 500)) == 120
    assert exporter.clean_name('') == 'unnamed'


def test_save_collected_creates_word_and_pdf(tmp_path):
    client = FakeClient()
    exporter.save_collected(client, QUESTIONS, '作业一', '高等数学', 201, 101, '作业一',
                            exporter.ExportOptions(str(tmp_path), True, True, True, True))
    folder = exporter.assignment_folder(str(tmp_path), '高等数学', 101, '作业一', 201)
    assert os.path.exists(os.path.join(folder, '作业一.docx'))
    assert os.path.exists(os.path.join(folder, '作业一.pdf'))
    assert os.path.exists(os.path.join(folder, exporter.IMAGE_DIR, '2.png'))
    assert client.calls == 1


def test_image_cache_skips_existing_file(tmp_path):
    client = FakeClient()
    folder = tmp_path / 'wk'
    folder.mkdir()
    images = folder / exporter.IMAGE_DIR
    images.mkdir()
    target = images / '2.png'
    target.write_bytes(b'cached')
    exporter.save_question(client, QUESTIONS['2'], str(folder))
    assert client.calls == 0                      # 命中缓存不再下载
    target.write_bytes(b'')                       # 空文件视为损坏
    exporter.save_question(client, QUESTIONS['2'], str(folder))
    assert client.calls == 1
