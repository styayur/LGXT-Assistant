"""Bounded atomic mobile notes, in Flet's durable app-private data directory."""
import json
import copy
import logging
import os
import shutil
import threading
import uuid
from pathlib import Path

class LocalStore:
    def __init__(self, directory=None):
        root=Path(directory or os.environ.get('FLET_APP_STORAGE_DATA') or Path.home()/'.lgxt-assistant-mobile')
        root.mkdir(parents=True,exist_ok=True)
        self.path=root/'study-notes.json'
        self.lock=threading.RLock()
        self.values={}
        self.writable=True
        if self.path.exists():
            try:
                if self.path.stat().st_size>32*1024*1024:
                    raise ValueError('Local notes exceed limits')
                data=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data,dict) or data.get('schemaVersion')!=1 or not isinstance(data.get('values'),dict):
                    self.writable=False
                    raise ValueError('Unsupported mobile notes version')
                self.values=data['values']
            except (ValueError,UnicodeError):
                shutil.copy2(self.path,self.path.with_suffix('.recovery-'+uuid.uuid4().hex[:8]+'.bak'))
                self.writable=False
                logging.warning('Mobile notes preserved; recover the backup before writing')
    def get(self,key):
        with self.lock:return copy.deepcopy(self.values.get(key))
    def set(self,key,value):
        if key=='lgxt.pass':raise ValueError('Password persistence is disabled')
        with self.lock:
            if not self.writable:raise ValueError('本地笔记版本未知或损坏，已保留；请先恢复备份')
            values=self.values|{key:value}
            text=json.dumps({'schemaVersion':1,'values':values},ensure_ascii=False)
            if len(text.encode('utf-8'))>32*1024*1024:raise ValueError('本地笔记超过 32 MB，请先备份整理')
            temporary=self.path.with_suffix('.tmp')
            temporary.write_text(text,encoding='utf-8')
            os.replace(temporary,self.path)
            self.values=values
    def remove(self,key):
        with self.lock:
            if key not in self.values:return
            values=dict(self.values);values.pop(key,None)
            if not self.writable:raise ValueError('本地笔记不可写')
            text=json.dumps({'schemaVersion':1,'values':values},ensure_ascii=False)
            temporary=self.path.with_suffix('.tmp');temporary.write_text(text,encoding='utf-8')
            os.replace(temporary,self.path);self.values=values
