"""TEST APK ENTRY ONLY. Copied by CI; never the distributable app entry."""
import base64
import io
import json

import flet as ft
from PIL import Image

from app_under_test import main
from android_image_checks import run


class FixtureClient:
    fixture=True
    insecure=False
    allow_insecure=False
    def __init__(self):self.headers={}
    def login(self,*args):self.headers['Authorization']='synthetic';return True,'fixture'
    def logout(self):self.headers.clear()
    def get_my_courses(self):return True,[{'courseId':1,'courseName':'Fixture physics'}]
    def get_course_works(self,*args):return True,[{'workId':2,'workName':'Fixture assignment','tryTimes':3,'times':1,'grade':None}]
    def get_questions(self,*args):return True,[{'id':3,'name':'Fixture formula','imgurl':'fixture','answer':'synthetic'}]
    def fetch_image(self,*args):
        with Image.new('RGB',(240,100),'white') as image:
            result=io.BytesIO();image.save(result,'PNG');return result.getvalue()
    def submit_answer(self,*args):return True,'Fixture accepted; no server request'


def target(page):
    result=run()
    print('LGXT_NATIVE_CHECKS='+json.dumps(result),flush=True)
    main(page,FixtureClient)


ft.run(target)
