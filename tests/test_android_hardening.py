import copy
import json
import threading
from types import SimpleNamespace

import flet as ft
import pytest

from mobile.src import model_transport as models, question_documents as documents
from mobile.src.local_store import LocalStore
from mobile.src.main import main, ICONS
from scripts.android_image_checks import run
from test_mobile import Page, FixtureClient, Storage, find, wait_for


def test_decoder_acceptance():
    result=run()
    assert result['pillow']=='13.0.0' and result['count']>=18


def doc():
    return {'schemaVersion':1,'courseId':'1','workId':'2','questionId':'3',
            'solutionMarkdown':'original','sources':[]}


def test_store_copy_atomic_revision_and_recovery(tmp_path,monkeypatch):
    store=LocalStore(tmp_path);key='question.'+documents.document_key('1','2','3')
    value=doc();store.save_document(key,value);value['solutionMarkdown']='caller mutation'
    assert store.get(key)['solutionMarkdown']=='original'
    store.save_document(key,doc()|{'solutionMarkdown':'second'})
    assert store.get(key+'.previous')['solutionMarkdown']=='original'
    before=store.path.read_bytes()
    import mobile.src.local_store as storage_module
    with monkeypatch.context() as patch:
        patch.setattr(storage_module.os,'replace',lambda *a: (_ for _ in ()).throw(OSError('fixture full disk')))
        with pytest.raises(OSError):store.save_document(key,doc()|{'solutionMarkdown':'lost'})
    assert store.path.read_bytes()==before and store.get(key)['solutionMarkdown']=='second'
    assert not list(tmp_path.glob('*.tmp-*'))
    backup=store.export_backup();assert b'lgxt.user' not in backup and b'lgxt.pass' not in backup
    store.path.write_text('{broken')
    recovery=LocalStore(tmp_path);assert not recovery.writable
    assert recovery.import_backup(backup)==1
    assert LocalStore(tmp_path).get(key)['solutionMarkdown']=='second'
    assert list(tmp_path.glob('*.recovery-*.bak'))
    with pytest.raises(ValueError):recovery.import_backup(json.dumps({'schemaVersion':99,'documents':{}}).encode())
    with pytest.raises(ValueError):recovery.import_backup(json.dumps({'schemaVersion':1,'documents':{'wrong':doc()}}).encode())


def test_cancelled_login_cannot_navigate_back_or_persist_password():
    started=threading.Event();finish=threading.Event();instances=[]
    class Delayed(FixtureClient):
        def __init__(self):super().__init__();instances.append(self)
        def login(self,*a):started.set();finish.wait(3);return super().login(*a)
    page=Page();store=Storage();main(page,Delayed,store)
    find(page,ft.TextField,label='账号').value='fixture'
    password=find(page,ft.TextField,label='密码');password.value='fixture-secret'
    find(page,ft.Button,text='登录理工学堂').on_click(None)
    assert started.wait(1) and password.value==''
    find(page,ft.Button,text='取消').on_click(None)
    assert page.views[-1].route=='/login'
    finish.set();wait_for(lambda:len(instances)==2 and not instances[-1].headers)
    assert page.views[-1].route=='/login' and 'lgxt.pass' not in store.data


def test_offline_library_survives_restart_without_login(tmp_path):
    store=LocalStore(tmp_path);key='question.'+documents.document_key('1','2','3')
    store.save_document(key,doc())
    page=Page();main(page,FixtureClient,LocalStore(tmp_path))
    find(page,ft.TextButton,text='离线打开本地资料').on_click(None)
    find(page,ft.TextButton,text='打开本地笔记').on_click(None)
    assert find(page,ft.TextField,label='解答笔记（Markdown）').value=='original'
    for lifecycle in ft.AppLifecycleState:
        page.on_app_lifecycle_state_change(SimpleNamespace(state=lifecycle))


def test_provider_cancel_redirect_and_unconfirmed_vision(monkeypatch):
    from desktop.storage import DEFAULTS
    settings=DEFAULTS|{'model':'fixture'}
    calls=[]
    monkeypatch.setattr(models.requests,'post',lambda *a,**k:calls.append(k))
    cancel=threading.Event();cancel.set()
    assert list(models.stream(settings,'fixture',[],cancel))==[] and not calls
    with pytest.raises(ValueError,match='视觉'):
        models.request_config(settings,'fixture',[{'role':'user','content':[{'type':'image_url','image_url':{'url':'https://untrusted/image.png'}}]}])
    with pytest.raises(ValueError,match='图片'):
        models.request_config(settings|{'visionEnabled':True},'fixture',[{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,aGVsbG8='}}]}])
    from test_desktop import Response
    response=Response([]);response.status_code=302
    monkeypatch.setattr(models.requests,'post',lambda *a,**k:response)
    with pytest.raises(ValueError,match='302'):list(models.stream(settings,'fixture',[],threading.Event()))
    assert response.closed
