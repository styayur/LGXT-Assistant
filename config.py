# -*- coding: utf-8 -*-
"""本地配置与凭据存储。

- 配置默认写入 %APPDATA%\\LGXT-Assistant\\config.ini（旧版脚本目录 config.ini 自动迁移读取）；
- keyring 读写全部带异常保护，失败只返回状态，不打断登录流程。
"""
import configparser
import logging
import os

import keyring

log = logging.getLogger(__name__)
SERVICE_NAME = '理工学堂'
APP_DIR_NAME = 'LGXT-Assistant'


def default_config_path():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, APP_DIR_NAME, 'config.ini')


def legacy_config_path(script_dir):
    return os.path.join(script_dir, 'config.ini')


class Settings:
    """导出设置；格式与旧版 config.ini 完全一致。"""

    def __init__(self, path=None, legacy_path=None):
        self.path = path or default_config_path()
        self.legacy_path = legacy_path
        self.export_path = os.getcwd()
        self.export_word = True
        self.export_word_include_answers = True
        self.export_pdf = False
        self.export_pdf_include_answers = True
        self.load()

    def _read(self, path):
        parser = configparser.ConfigParser()
        try:
            parser.read(path, encoding='utf-8')
        except (OSError, configparser.Error) as exc:
            log.warning('读取配置失败 %s: %s', path, exc)
            return None
        return parser

    def load(self):
        path = self.path
        if not os.path.exists(path) and self.legacy_path and os.path.exists(self.legacy_path):
            path = self.legacy_path  # 兼容旧版：迁移读取
            migrated = True
        else:
            migrated = False
        if not os.path.exists(path):
            self.save()
            return
        parser = self._read(path)
        if parser is None or 'Settings' not in parser:
            if migrated:
                self.save()
            return
        s = parser['Settings']
        self.export_path = s.get('export_path', self.export_path)
        self.export_word = s.getboolean('export_word', True)
        self.export_word_include_answers = s.getboolean('export_word_include_answers', True)
        self.export_pdf = s.getboolean('export_pdf', False)
        self.export_pdf_include_answers = s.getboolean('export_pdf_include_answers', True)
        if migrated:
            self.save()

    def save(self):
        parser = configparser.ConfigParser()
        parser['Settings'] = {
            'export_path': self.export_path,
            'export_word': str(self.export_word),
            'export_word_include_answers': str(self.export_word_include_answers),
            'export_pdf': str(self.export_pdf),
            'export_pdf_include_answers': str(self.export_pdf_include_answers),
        }
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                parser.write(f)
            return True
        except OSError as exc:
            log.warning('写入配置失败 %s: %s', self.path, exc)
            return False


# ---- 凭据（keyring；全部容错，不抛异常给 UI）----

def save_credentials(username, password):
    try:
        keyring.set_password(SERVICE_NAME, 'username', username)
        keyring.set_password(SERVICE_NAME, username, password)
        return True
    except Exception as exc:  # keyring 后端缺失/被拒绝等
        log.warning('保存凭据失败: %s', exc)
        return False


def get_saved_username():
    try:
        return keyring.get_password(SERVICE_NAME, 'username')
    except Exception as exc:
        log.warning('读取用户名失败: %s', exc)
        return None


def get_saved_password(username):
    try:
        return keyring.get_password(SERVICE_NAME, username)
    except Exception as exc:
        log.warning('读取密码失败: %s', exc)
        return None


def delete_saved_credentials():
    """只删除确实存在的条目；任何后端异常都不抛出。"""
    try:
        saved_username = keyring.get_password(SERVICE_NAME, 'username')
        if saved_username:
            try:
                keyring.delete_password(SERVICE_NAME, saved_username)
            except Exception as exc:
                log.info('删除密码条目失败（可能不存在）: %s', exc)
        try:
            if keyring.get_password(SERVICE_NAME, 'username') is not None:
                keyring.delete_password(SERVICE_NAME, 'username')
        except Exception as exc:
            log.info('删除用户条目失败（可能不存在）: %s', exc)
        return True
    except Exception as exc:
        log.warning('清理凭据失败: %s', exc)
        return False
