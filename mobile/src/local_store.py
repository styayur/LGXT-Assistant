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
        self.warning=''
        if self.path.exists():
            try:
                if self.path.stat().st_size>32*1024*1024:
                    raise ValueError('Local notes exceed limits')
                data=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data,dict) or data.get('schemaVersion')!=1 or not isinstance(data.get('values'),dict):
                    self.writable=False
                    raise ValueError('Unsupported mobile notes version')
                self.values=data['values']
                # Never revive credentials left by an older schema-1 writer.
                if 'lgxt.pass' in self.values:
                    self.values.pop('lgxt.pass', None)
                    self._commit(copy.deepcopy(self.values))
            except (ValueError,UnicodeError):
                shutil.copy2(self.path,self.path.with_suffix('.recovery-'+uuid.uuid4().hex[:8]+'.bak'))
                self.writable=False
                self.warning='本地资料损坏或版本未知，原文件与恢复副本已保留；请导入有效备份。'
                logging.warning('Mobile notes preserved; recover the backup before writing')
    def get(self,key):
        with self.lock:return copy.deepcopy(self.values.get(key))
    def set(self,key,value):
        if key=='lgxt.pass':raise ValueError('Password persistence is disabled')
        with self.lock:
            if not self.writable:raise ValueError('本地笔记版本未知或损坏，已保留；请先恢复备份')
            self._commit(self.values|{key:copy.deepcopy(value)})

    def _commit(self, values):
        text=json.dumps({'schemaVersion':1,'values':values},ensure_ascii=False)
        if len(text.encode('utf-8'))>32*1024*1024:raise ValueError('本地笔记超过 32 MB，请先备份整理')
        temporary=self.path.with_suffix('.tmp-'+uuid.uuid4().hex)
        backup_temp=self.path.with_suffix('.tmp-'+uuid.uuid4().hex)
        try:
            with temporary.open('w',encoding='utf-8') as target:
                target.write(text);target.flush();os.fsync(target.fileno())
            if self.path.exists() and self.writable:
                with backup_temp.open('w',encoding='utf-8') as target:
                    json.dump({'schemaVersion':1,'values':self.values},target,ensure_ascii=False)
                    target.flush();os.fsync(target.fileno())
                os.replace(backup_temp,self.path.with_suffix('.last-good.json'))
            os.replace(temporary,self.path)
            self.values=values
        finally:
            temporary.unlink(missing_ok=True)
            backup_temp.unlink(missing_ok=True)

    def save_document(self,key,value):
        with self.lock:
            if not self.writable:raise ValueError(self.warning)
            values=copy.deepcopy(self.values)
            if key in values:values[key+'.previous']=values[key]
            values[key]=copy.deepcopy(value)
            self._commit(values)

    def documents(self):
        with self.lock:
            return copy.deepcopy({k:v for k,v in self.values.items()
                                  if k.startswith('question.') and not k.endswith('.previous')})

    def export_backup(self):
        with self.lock:
            if not self.writable:raise ValueError(self.warning)
            return json.dumps({'schemaVersion':1,'documents':self.documents()},ensure_ascii=False).encode('utf-8')

    def import_backup(self,raw):
        try:
            from .question_documents import validate_document,document_key
        except ImportError:
            from question_documents import validate_document,document_key
        if len(raw)>32*1024*1024:raise ValueError('备份超过 32 MB')
        payload=json.loads(raw)
        if not isinstance(payload,dict) or payload.get('schemaVersion')!=1 or not isinstance(payload.get('documents'),dict):
            raise ValueError('备份版本或结构无效')
        documents={}
        for key,value in payload['documents'].items():
            value=validate_document(value)
            expected='question.'+document_key(value['courseId'],value['workId'],value['questionId'])
            if key!=expected:raise ValueError('备份题目编号不匹配')
            documents[key]=value
        with self.lock:
            # A corrupt original was already preserved at startup. Import is an
            # explicit recovery action; no credential fields are accepted.
            values=copy.deepcopy(self.values)
            for key,value in documents.items():
                if key in values:values[key+'.previous']=values[key]
                values[key]=value
            self._commit(values)
            self.writable=True;self.warning=''
        return len(documents)
    def remove(self,key):
        with self.lock:
            if key not in self.values:return
            values=dict(self.values);values.pop(key,None)
            if not self.writable:raise ValueError('本地笔记不可写')
            self._commit(values)
