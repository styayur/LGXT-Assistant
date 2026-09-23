# -*- coding: utf-8 -*-
import os

import config


def test_settings_roundtrip(tmp_path):
    path = str(tmp_path / 'sub' / 'config.ini')
    s = config.Settings(path)
    s.export_path = r'D:\out'
    s.export_word = False
    s.export_pdf = True
    s.save()
    again = config.Settings(path)
    assert again.export_path == r'D:\out'
    assert again.export_word is False
    assert again.export_pdf is True


def test_legacy_config_migration(tmp_path):
    legacy = tmp_path / 'legacy.ini'
    legacy.write_text('[Settings]\nexport_path = D:\\old\nexport_word = False\n', encoding='utf-8')
    new = str(tmp_path / 'new' / 'config.ini')
    s = config.Settings(new, legacy_path=str(legacy))
    assert s.export_path == 'D:\\old' and s.export_word is False
    assert os.path.exists(new)          # 迁移后写入新位置


def test_keyring_failures_do_not_raise(monkeypatch):
    class BadKeyring:
        @staticmethod
        def get_password(*_a):
            raise RuntimeError('no backend')

        @staticmethod
        def set_password(*_a):
            raise RuntimeError('no backend')

        @staticmethod
        def delete_password(*_a):
            raise RuntimeError('no backend')

    monkeypatch.setattr(config, 'keyring', BadKeyring)
    assert config.get_saved_username() is None
    assert config.get_saved_password('u') is None
    assert config.save_credentials('u', 'p') is False
    assert config.delete_saved_credentials() is False


def test_invalid_legacy_booleans_and_percent_path_do_not_prevent_startup(tmp_path):
    path=tmp_path/'config.ini'
    original='[Settings]\nexport_word = invalid\nexport_pdf = True\nexport_path = D:\\100%\\notes\n'
    path.write_text(original,encoding='utf-8')
    settings=config.Settings(str(path))
    assert settings.export_word is True and settings.export_pdf is True
    assert settings.export_path == r'D:\100%\notes'
    assert path.read_text(encoding='utf-8')==original
