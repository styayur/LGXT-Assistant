"""TEST APK ENTRY ONLY. Copied by CI; never the distributable app entry."""
import base64
import io
import json
import logging
import requests

import flet as ft
from PIL import Image

try:
    from app_under_test import main
except ModuleNotFoundError as error:
    if error.name != 'app_under_test':
        raise
    from mobile.src.main import main
try:
    from android_image_checks import run, credential_free_transport_probe
except ModuleNotFoundError as error:
    if error.name != 'android_image_checks':
        raise
    from scripts.android_image_checks import run, credential_free_transport_probe
try:
    from synthetic_credentials import credential_observation, exact_synthetic_login
except ModuleNotFoundError as error:
    if error.name != 'synthetic_credentials':
        raise
    from scripts.synthetic_credentials import credential_observation, exact_synthetic_login


class FixtureClient:
    fixture=True
    # Exercise the real consent UI with this isolated client only. login and
    # userInfo below remain synthetic; fixture credentials never reach a server.
    insecure=True
    allow_insecure=False
    base_url='http://fixture.invalid/api'
    def __init__(self):self.headers={};self.session=requests.Session()
    def login(self,username,password):
        self.headers.clear()
        observed=credential_observation(username,password)
        logging.getLogger('lgxt.input-fidelity').warning('LGXT_SYNTHETIC_LOGIN=%s',json.dumps(observed))
        if not exact_synthetic_login(username,password):
            return False,'Synthetic input did not match exactly'
        self.headers['Authorization']='synthetic'
        return True,'fixture'
    def logout(self):self.headers.clear()
    def get_user_info(self):
        return (True, {'name':'Synthetic user'}) if self.headers.get('Authorization')=='synthetic' else (False,'Invalid synthetic session')
    def get_my_courses(self):return True,[{'courseId':1,'courseName':'Fixture physics'}]
    def get_course_works(self,*args):return True,[{'workId':2,'workName':'Fixture assignment','tryTimes':3,'times':1,'grade':None}]
    def get_questions(self,*args):return True,[{'id':3,'name':'Fixture formula','imgurl':'fixture','answer':'synthetic'}]
    def fetch_image(self,*args):
        with Image.new('RGB',(240,100),'white') as image:
            result=io.BytesIO();image.save(result,'PNG');return result.getvalue()
    def submit_answer(self,*args):return True,'Fixture accepted; no server request'


def target(page):
    result=run()
    logging.getLogger('lgxt.acceptance').warning('LGXT_NATIVE_CHECKS=%s',json.dumps(result))
    logging.getLogger('lgxt.acceptance').warning('LGXT_NETWORK_PROBE=%s',json.dumps(credential_free_transport_probe()))
    main(page,FixtureClient)


if __name__ == '__main__':
    ft.run(target)
