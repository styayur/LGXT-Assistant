# -*- coding: utf-8 -*-
"""本地配置（config.ini）与凭据存储（keyring）。不改变已有配置文件格式。"""
import configparser
import os

import keyring

SERVICE_NAME = '理工学堂'


class Settings:
    """导出设置。格式与旧版 config.ini 完全一致。"""

    def __init__(self, path):
        self.path = path
        self.export_path = os.getcwd()
        self.export_word = True
        self.export_word_include_answers = True
        self.export_pdf = False
        self.export_pdf_include_answers = True
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self.save()
            return
        parser = configparser.ConfigParser()
        parser.read(self.path, encoding='utf-8')
        if 'Settings' in parser:
            s = parser['Settings']
            self.export_path = s.get('export_path', self.export_path)
            self.export_word = s.getboolean('export_word', True)
            self.export_word_include_answers = s.getboolean('export_word_include_answers', True)
            self.export_pdf = s.getboolean('export_pdf', False)
            self.export_pdf_include_answers = s.getboolean('export_pdf_include_answers', True)

    def save(self):
        parser = configparser.ConfigParser()
        parser['Settings'] = {
            'export_path': self.export_path,
            'export_word': str(self.export_word),
            'export_word_include_answers': str(self.export_word_include_answers),
            'export_pdf': str(self.export_pdf),
            'export_pdf_include_answers': str(self.export_pdf_include_answers),
        }
        with open(self.path, 'w', encoding='utf-8') as f:
            parser.write(f)


# ---- 凭据（keyring）----

def save_credentials(username, password):
    keyring.set_password(SERVICE_NAME, 'username', username)
    keyring.set_password(SERVICE_NAME, username, password)


def get_saved_username():
    return keyring.get_password(SERVICE_NAME, 'username')


def get_saved_password(username):
    return keyring.get_password(SERVICE_NAME, username)


def delete_saved_credentials():
    saved_username = get_saved_username()
    if saved_username:
        keyring.delete_password(SERVICE_NAME, saved_username)
    keyring.delete_password(SERVICE_NAME, 'username')
