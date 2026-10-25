"""Flet control-tree interaction tests, using synthetic course data only."""
import io
import dataclasses
import time
from types import SimpleNamespace

import flet as ft
import pytest
from PIL import Image

from mobile.src.main import main, ICONS

class Storage:
    def __init__(self): self.data={'lgxt.pass':'legacy-plaintext'}
    def get(self,key):return self.data.get(key)
    def set(self,key,value):self.data[key]=value
    def remove(self,key):self.data.pop(key,None)

class Page:
    def __init__(self,width=390,height=844):
        self.width=width;self.height=height;self.views=[];self.client_storage=Storage();self.dialog=None
    def update(self,*controls):pass
    def show_dialog(self,dialog):self.dialog=dialog
    def pop_dialog(self):self.dialog=None

class FixtureClient:
    fixture=True
    insecure=False
    allow_insecure=False
    calls=[]
    def __init__(self):self.headers={}
    def login(self,*args):self.headers['Authorization']='fixture';return True,'fixture login'
    def logout(self):self.headers.clear()
    def get_my_courses(self):return True,[{'courseId':1,'courseName':'Synthetic physics course'}]
    def get_course_works(self,*args):return True,[{'workId':2,'workName':'Synthetic assignment','tryTimes':3,'times':1,'grade':None,'expireTime':'2026-12-31'}]
    def get_questions(self,*args):return True,[{'id':3,'name':'Synthetic integral','imgurl':'fixture://image','answer':'1/3'}]
    def fetch_image(self,*args):
        b=io.BytesIO();Image.new('RGB',(100,50),'white').save(b,'PNG');return b.getvalue()
    def submit_answer(self,*args):self.calls.append(args);return True,'fixture accepted'


def walk(control):
    yield control
    if dataclasses.is_dataclass(control):
        for field in dataclasses.fields(control):
            if field.name.startswith('_'):continue
            value=getattr(control,field.name)
            if isinstance(value,ft.BaseControl):yield from walk(value)
            elif isinstance(value,list):
                for child in value:
                    if isinstance(child,ft.BaseControl):yield from walk(child)

def controls(page):return list(walk(page.views[-1]))

def matches(control,key,value):
    actual=getattr(control,'content' if key=='text' and not hasattr(control,'text') else key,None)
    return actual==value

def find(page,typ,**attrs):
    return next(c for c in controls(page) if isinstance(c,typ) and all(matches(c,k,v) for k,v in attrs.items()))

def wait_for(fn):
    for _ in range(200):
        try:
            value=fn()
            if value:return value
        except (StopIteration,IndexError):pass
        time.sleep(.01)
    raise AssertionError('Flet state did not become ready')

@pytest.mark.parametrize('size',[(390,844),(360,740),(390,480)])
def test_mobile_login_assignment_document_confirmation(size):
    FixtureClient.calls=[]
    page=Page(*size);main(page,FixtureClient,page.client_storage)
    assert 'lgxt.pass' not in page.client_storage.data
    find(page,ft.TextField,label='账号').value='fixture'
    find(page,ft.TextField,label='密码').value='not-a-real-password'
    find(page,ft.Button,text='登录理工学堂').on_click(None)
    wait_for(lambda: page.views[-1].route=='/dashboard')
    nav=find(page,ft.NavigationBar);nav.selected_index=1;nav.on_change(SimpleNamespace(control=nav))
    wait_for(lambda: find(page,ft.IconButton,icon=ICONS.CHEVRON_RIGHT)).on_click(None)
    wait_for(lambda: find(page,ft.Button,text='查看题目')).on_click(None)
    wait_for(lambda: find(page,ft.Button,text='提交成绩')).on_click(None)
    assert not FixtureClient.calls and page.dialog
    page.dialog.actions[0].on_click(None)
    assert not FixtureClient.calls
    find(page,ft.Button,text='提交成绩').on_click(None)
    confirm = page.dialog.actions[1].on_click
    confirm(None)
    wait_for(lambda: len(FixtureClient.calls)==1)
    confirm(None)  # A replayed callback must not consume another attempt.
    assert len(FixtureClient.calls)==1
    find(page,ft.TextButton,text='查看原图 / 识别公式 / AI 分析').on_click(None)
    assert page.views[-1].route=='/question-document'
    find(page,ft.TextField,label='校正题面 / LaTeX 源码').value=r'Corrected $\int_0^1 x^2 dx$'
    find(page,ft.TextField,label='解答笔记（Markdown）').value='User derivation'
    find(page,ft.Button,text='保存学习材料').on_click(None)
    saved=[v for k,v in page.client_storage.data.items() if k.startswith('question.')]
    assert saved and saved[0]['schemaVersion']==1 and 'Corrected' in saved[0]['correctedMarkdown']
    assert find(page,ft.TextButton,text='图片转 LaTeX')
    assert find(page,ft.Button,text='使用 AI 分析此题')

def test_atomic_mobile_store_preserves_versions_and_never_passwords(tmp_path):
    import json
    from mobile.src.local_store import LocalStore
    store=LocalStore(tmp_path)
    store.set('question.1',{'schemaVersion':1,'corrected':'original'})
    value=store.get('question.1');value['corrected']='edited'
    assert store.get('question.1')['corrected']=='original'
    with pytest.raises(ValueError):store.set('lgxt.pass','not-a-real-password')
    assert LocalStore(tmp_path).get('question.1')['corrected']=='original'
    path=tmp_path/'study-notes.json'
    path.write_text(json.dumps({'schemaVersion':99,'values':{}}))
    future=LocalStore(tmp_path)
    with pytest.raises(ValueError):future.set('question.2',{})
    assert json.loads(path.read_text())['schemaVersion']==99
    assert list(tmp_path.glob('*.bak'))


@pytest.mark.parametrize('confirm',[True,False])
def test_import_waits_for_dismiss_and_preserves_previous_once(tmp_path,monkeypatch,confirm):
    import asyncio,json
    from mobile.src.local_store import LocalStore
    from mobile.src.question_documents import document_key
    store=LocalStore(tmp_path/'store')
    key='question.'+document_key('1','2','3')
    old={'schemaVersion':1,'courseId':'1','workId':'2','questionId':'3','solutionMarkdown':'edited current'}
    store.save_document(key,old)
    raw=json.dumps({'schemaVersion':1,'documents':{key:dict(old,solutionMarkdown='exported original')}}).encode()
    backup=tmp_path/'backup.json';backup.write_bytes(raw)
    calls=[]
    original=store.import_backup
    def imported(value):calls.append(value);return original(value)
    store.import_backup=imported
    async def pick_files(**kwargs):return [SimpleNamespace(size=len(raw),path=str(backup))]
    monkeypatch.setattr(ft,'FilePicker',lambda:SimpleNamespace(pick_files=pick_files))
    page=Page();main(page,FixtureClient,store)
    find(page,ft.TextButton,text='离线打开本地资料').on_click(None)
    asyncio.run(find(page,ft.TextButton,text='导入备份 / 恢复').on_click(None))
    dialog=page.dialog
    dialog.actions[1 if confirm else 0].on_click(None)
    assert dialog.open is False and not calls
    # Replayed clicks cannot change a cancelled choice or trigger another import.
    dialog.actions[1].on_click(None)
    dialog.on_dismiss(None);dialog.on_dismiss(None)
    assert len(calls)==int(confirm)
    assert store.get(key)['solutionMarkdown']==('exported original' if confirm else 'edited current')
    if confirm:assert store.get(key+'.previous')['solutionMarkdown']=='edited current'
