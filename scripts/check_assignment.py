"""Assignment workflow in the production React build using synthetic bridge data."""
import base64
import functools
import http.server
import io
import json
import threading
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright, expect
from ui_fixtures import FIXTURE

ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

buffer=io.BytesIO()
image=Image.new('RGB',(640,180),'white');draw=ImageDraw.Draw(image)
draw.text((20,30),'FIXTURE: Evaluate integral from 0 to 1 of x^2 dx.',fill='black')
draw.text((20,90),'Printed question image - synthetic test data',fill='black')
image.save(buffer,'PNG')
IMAGE='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()
EXTRA=r'''
const api=window.pywebview.api;
test.documents={};test.ai=[];test.writes=[];test.cancelled=[];
api.question_image=async()=>IMAGE;
api.question_document=async(c,w,q)=>test.documents[q]||null;
api.save_question_document=async d=>{test.documents[d.questionId]=structuredClone(d);return d;};
api.questions=async()=>[{id:201,name:'积分与能量 · 合成测试题',imgurl:'https://lgxt.wutp.com.cn/fixture.png',answer:'1/3'}];
api.start_question_ai=async(d,p,image,recognize)=>{test.ai.push({d,p,image,recognize});test.mode=recognize?'recognize':'solve';test.step=0;return 'question-job';};
api.parse_recognition=async text=>JSON.parse(text);
const originalPoll=api.poll_job;
api.poll_job=async(id,offset)=>{
 if(id==='question-job') {const text=test.mode==='recognize'?JSON.stringify({text:'计算积分（识别草稿）',latex:'\\int_0^1 x^2\\,dx'}):'## 逐步推导\n\n$$\\int_0^1 x^2\\,dx=\\frac13$$\n\n来源：当前题目图片；计算为模型解释。';return {id,kind:'chat',done:true,error:'',delta:text.slice(offset),offset:text.length,status:'已完成'};}
 if(id==='batch-job')return {id,kind:'task',done:test.cancelled.includes(id),error:'',delta:'',offset:0,status:'逐项提交',progress:1,maximum:2};
 return originalPoll(id,offset);
};
api.preview_batch=async(scope)=>{test.scope=scope;return {scope,count:2,grade:'100',fetchFailed:0,token:'preview-token',works:[{workId:101,workName:'测试作业 A',tryTimes:3,times:1},{workId:102,workName:'测试作业 B'}]};};
api.confirm_batch=async token=>{test.writes.push(token);return 'batch-job';};
api.cancel_task=async id=>{test.cancelled.push(id);return true;};
'''
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'frontend/dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  context=browser.new_context(viewport={'width':1920,'height':1080})
  context.add_init_script(FIXTURE+'\nconst IMAGE='+json.dumps(IMAGE)+';\n'+EXTRA)
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{server.server_port}');page.wait_for_load_state('networkidle')
  page.locator('.sidebar nav').get_by_role('button',name='我的课程',exact=True).click()
  # Each scope previews and cancellation performs no writes.
  for scope in ['all','course','assignment']:
   page.get_by_role('button',name='一键满分',exact=True).click()
   dialog=page.get_by_role('dialog');expect(dialog).to_contain_text('共 2 个作业')
   assert page.evaluate('window.__test.scope')==scope
   assert not page.evaluate('window.__test.writes.length')
   dialog.get_by_role('button',name='取消',exact=True).click()
   if scope=='all':page.locator('.course-card').first.click()
   if scope=='course':page.locator('.assignment-row').first.click()
  expect(page.get_by_alt_text('原始题目图片，点击放大')).to_be_visible()
  page.get_by_role('button',name='图片转 LaTeX',exact=True).click()
  expect(page.get_by_text('检查识别结果',exact=True)).to_be_visible()
  page.get_by_label('LaTeX 源码',exact=True).fill(r'\int_0^1 x^3\,dx')
  page.get_by_role('button',name='应用校正结果',exact=True).click()
  assert r'\int_0^1 x^3' in page.get_by_role('textbox',name='校正题面',exact=True).input_value()
  expect(page.locator('.question-document .katex').first).to_be_visible()
  page.get_by_role('button',name='使用 AI 分析此题',exact=True).click()
  expect(page.get_by_role('button',name='将回复加入解答',exact=True)).to_be_visible()
  payload=page.evaluate('window.__test.ai.at(-1)')
  assert payload['image']==IMAGE and 'x^3' in payload['d']['correctedMarkdown']
  page.get_by_role('button',name='将回复加入解答',exact=True).click()
  expect(page.locator('.solution-editor .katex').first).to_be_visible()
  editor=page.get_by_role('textbox',name='题目解答编辑器')
  # contenteditable has generic role on some engines; use the declared accessible name.
  page.locator('.solution-editor').click();page.keyboard.press('Control+End');page.keyboard.type(' Correction round trip.')
  page.get_by_role('button',name='保存题目文档',exact=True).click()
  page.wait_for_function('window.__test.documents[201].solutionMarkdown.includes("Correction round trip")')
  page.get_by_role('button',name='Markdown 源码',exact=True).click()
  source=page.get_by_role('textbox',name='解答 Markdown 源码')
  assert r'\int' in source.input_value(), source.input_value()
  source.fill(source.input_value()+'\n\n| a | b |\n|---|---|\n|1|2|\n\n<script>window.__pwned=true</script>')
  page.get_by_role('button',name='转换并应用',exact=True).click()
  assert not page.evaluate('Boolean(window.__pwned)')
  expect(page.locator('.solution-editor table')).to_have_count(1)
  page.get_by_role('button',name='Markdown 源码',exact=True).click()
  source=page.get_by_role('textbox',name='解答 Markdown 源码')
  source.fill('\n'.join(line for line in source.input_value().splitlines() if '__pwned' not in line))
  page.get_by_role('button',name='转换并应用',exact=True).click()
  page.locator('.page-scroll').evaluate('(el)=>el.scrollTop=0')
  page.screenshot(path=str(ROOT/'docs/screenshots/assignment-desktop-fixture.png'))
  for width,height in [(390,844),(390,480),(860,600)]:
   page.set_viewport_size({'width':width,'height':height})
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
   expect(page.get_by_role('textbox',name='校正题面',exact=True)).to_be_attached()
   page.screenshot(path=str(ROOT/f'docs/screenshots/assignment-{width}x{height}-fixture.png'))
  page.set_viewport_size({'width':1920,'height':1080})
  page.get_by_role('button',name='一键满分',exact=True).click()
  page.get_by_role('dialog').get_by_role('button',name='确认提交',exact=True).click()
  expect(page.get_by_role('button',name='停止后续请求',exact=True)).to_be_visible()
  page.get_by_role('button',name='停止后续请求',exact=True).click()
  page.wait_for_function('window.__test.cancelled.includes("batch-job")')
  assert page.evaluate('window.__test.writes.length')==1
  assert not errors,errors
  browser.close()
 print(json.dumps({'ok':True,'checks':['three batch scopes','confirmation','cancel','question image','OCR correction','safe math','rich text and table','document persistence','contextual AI','390x844 and keyboard-height layout'],'console_errors':errors}))
finally:server.shutdown()
