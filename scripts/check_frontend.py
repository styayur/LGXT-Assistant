"""Production UI regression and screenshots. Fixtures never enter the shipped app.

Run: python scripts/check_frontend.py (requires playwright + chromium and frontend build).
No credentials, real API requests, or user application data are used.
"""
import functools
import http.server
import json
import threading
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs/screenshots'
OUTPUT.mkdir(parents=True, exist_ok=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'frontend/dist')))
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{server.server_port}'
errors = []


def screenshot(page, name):
    page.screenshot(path=str(OUTPUT / f'modern-{name}.png'))


def no_overflow(page):
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'Horizontal page overflow'
    assert page.locator('main').bounding_box()['width'] >= min(350, page.viewport_size['width']), 'Main workspace collapsed'
    box = page.get_by_role('button', name='发送消息', exact=True).bounding_box()
    if box:
        assert box['x'] >= 0 and box['y'] + box['height'] <= page.viewport_size['height'], 'Composer is clipped'


FIXTURE = r"""
window.__test = {calls:[], stopped:false, count:0, saved:[], settings:null};
const test = window.__test;
const defaults = {theme:'dark',language:'zh',startup:'new',reduceMotion:true,provider:'Local',endpoint:'http://localhost:11434/v1',model:'test-model',temperature:.7,contextMessages:40,maxTokens:4096,storeConversations:true,memoryEnabled:false,memory:'',debug:false,profiles:{}};
window.pywebview={api:{
 bootstrap:async()=>({settings:defaults,hasKey:false,conversations:[],prompts:[],username:'测试账号',savedUsername:'',export:{export_path:'test-output',export_word:true,export_pdf:false,export_word_include_answers:true,export_pdf_include_answers:true}}),
 save_conversation:async c=>{test.saved.push(c);return true;},
 save_workspace:async()=>true,
 save_settings:async s=>{test.settings=s;return {settings:s,hasKey:false};},
 start_chat:async m=>{test.calls.push({action:'chat',messages:m});test.count=0;test.stopped=false;return 'fixture-job';},
 poll_job:async(id,offset)=>{test.count++;let text='这是一段用于验证流式渲染的测试回复。'.repeat(Math.min(test.count,12));return {id,kind:'chat',done:test.stopped||test.count>=12,error:'',delta:text.slice(offset),offset:text.length,status:test.stopped?'已停止':'正在生成',progress:0,maximum:100};},
 stop_chat:async()=>{test.stopped=true;return true;},
 courses:async()=>Array.from({length:25},(_,i)=>({courseId:i+1,courseName:i===0?'大学物理 · 测试课程':`测试课程 ${i+1}`})),
 works:async id=>[{workId:101,workName:'动量与冲量 · 测试作业',chapterName:'第一章',grade:null,times:0,tryTimes:3,expireTime:'2026-12-31'}],
 questions:async id=>[{id:201,name:'动量守恒 · 测试题目',answer:'测试参考答案',imgurl:''}],
 submit_grade:async(id,grade)=>{test.calls.push({action:'submit',id,grade});return 'ok';},
 dashboard:async()=>({pending:2,completed:3,average:90,total:5,fetch_fail:0}),
 delete_conversation:async()=>true,
 export_chat:async()=>true,
}};
"""

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_load_state('networkidle')
        expect(page.locator('.welcome')).to_be_visible()
        no_overflow(page)
        screenshot(page, 'dark-1440')
        # Commands and Escape should close the dialog, never the application.
        page.keyboard.press('Control+k')
        expect(page.get_by_role('dialog')).to_be_visible()
        page.get_by_role('textbox', name='搜索命令').fill('打开设置')
        page.keyboard.press('Enter')
        expect(page.get_by_role('heading', name='设置', exact=True)).to_be_visible()
        page.get_by_role('button', name='浅色', exact=True).click()
        expect(page.locator('html')).to_have_attribute('data-theme', 'light')
        page.get_by_role('button', name='保存更改', exact=True).click()
        expect(page.get_by_text('设置已保存', exact=True)).to_be_visible()
        screenshot(page, 'settings-light')
        page.reload()
        expect(page.locator('html')).to_have_attribute('data-theme', 'light')
        screenshot(page, 'light-1440')
        page.keyboard.press('Control+Shift+p')
        page.keyboard.press('Escape')
        expect(page.get_by_role('dialog')).to_have_count(0)
        expect(page.locator('.app-shell')).to_be_visible()
        # User-created prompts survive reload.
        page.locator('.sidebar nav').get_by_role('button', name='提示词库', exact=True).click()
        page.get_by_role('button', name='新建提示词', exact=True).click()
        dialog = page.get_by_role('dialog')
        dialog.get_by_label('名称', exact=True).fill('自动化测试模板')
        dialog.get_by_label('提示词内容', exact=True).fill('请一步步分析动量守恒。')
        dialog.get_by_role('button', name='保存提示词', exact=True).click()
        expect(page.get_by_role('heading', name='自动化测试模板')).to_be_visible()
        page.locator('.prompt-card').filter(has_text='自动化测试模板').get_by_role('button', name='使用模板').click()
        expect(page.get_by_role('textbox', name='消息输入')).to_have_value('请一步步分析动量守恒。')
        page.keyboard.press('Control+n')
        expect(page.get_by_role('textbox', name='消息输入')).to_have_value('')
        # Browse, attach a real file, then reference it in the composer.
        page.locator('.sidebar nav').get_by_role('button', name='工作区', exact=True).click()
        page.locator('input[type=file]').set_input_files({'name':'study-notes.md','mimeType':'text/markdown','buffer':b'# Study notes\nMomentum is conserved in an isolated system.'})
        expect(page.get_by_text('study-notes.md', exact=True)).to_be_visible()
        page.get_by_role('button', name='引用到对话', exact=True).click()
        expect(page.locator('.composer-files')).to_contain_text('study-notes.md')
        # Persist an explicit rendering fixture, not a generated AI answer.
        cid = str(uuid.uuid4())
        messages = [{'id':'u','role':'user','content':'请用公式、表格与代码解释动量守恒。'} , {'id':'a','role':'assistant','content':r'''## 从系统出发理解动量守恒

当系统所受的**合外力为零**时，系统的总动量保持不变。

$$m_1 v_1 + m_2 v_2 = m_1 v'_1 + m_2 v'_2$$

| 情况 | 动量 | 动能 |
| --- | --- | --- |
| 弹性碰撞 | 守恒 | 守恒 |
| 完全非弹性碰撞 | 守恒 | 不守恒 |

```python
def momentum(mass, velocity):
    return mass * velocity
```

> 先确定研究对象，再检查外力条件。这比直接套公式更重要。
'''}]
        c = {'id':cid,'title':'动量守恒的理解 · 渲染测试','updated':1,'messages':messages}
        page.evaluate('(c)=>{localStorage.setItem("lgxt.preview."+c.id,JSON.stringify(c));localStorage.setItem("lgxt.preview.index",JSON.stringify([{id:c.id,title:c.title,updated:c.updated}]));const s=JSON.parse(localStorage.getItem("lgxt.preview.settings"));s.theme="dark";s.startup="last";localStorage.setItem("lgxt.preview.settings",JSON.stringify(s));}', c)
        page.reload()
        expect(page.locator('.katex')).to_have_count(1)
        expect(page.locator('.markdown table')).to_have_count(1)
        expect(page.locator('code .hljs-keyword').first).to_be_visible()
        page.locator('.chat-scroll').evaluate('(el)=>el.scrollTop=0')
        screenshot(page, 'chat-fixture')
        page.get_by_role('button', name='编辑消息', exact=True).click()
        page.get_by_role('dialog').get_by_role('button', name='继续', exact=True).click()
        expect(page.get_by_role('textbox', name='消息输入')).to_have_value(messages[0]['content'])
        expect(page.locator('.message')).to_have_count(0)
        # Responsive screenshots use the real empty state.
        page.keyboard.press('Control+n')
        for width,height in [(1280,720),(1920,1080),(3840,2160),(860,600),(390,844)]:
            page.set_viewport_size({'width':width,'height':height})
            page.wait_for_timeout(250)
            no_overflow(page)
            screenshot(page, f'dark-{width}')
        context.close()

        # Separate deterministic bridge fixture for native data and streaming interaction.
        context = browser.new_context(viewport={'width':1440,'height':900})
        context.add_init_script(FIXTURE)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_load_state('networkidle')
        page.get_by_role('textbox',name='消息输入').fill('流式输出测试')
        page.keyboard.press('Control+Enter')
        expect(page.get_by_role('button',name='停止生成',exact=True)).to_be_visible()
        page.wait_for_function('window.__test.count>=2')
        page.keyboard.press('Escape')
        expect(page.get_by_role('button',name='发送消息',exact=True)).to_be_visible()
        assert page.evaluate('window.__test.stopped')
        assert page.evaluate('window.__test.saved.at(-1).messages.at(-1).content.length') > 0
        page.get_by_role('button',name='重新生成',exact=True).click()
        page.get_by_role('dialog').get_by_role('button',name='继续',exact=True).click()
        page.wait_for_function('window.__test.calls.filter(x=>x.action==="chat").length===2')
        expect(page.get_by_role('button',name='发送消息',exact=True)).to_be_visible(timeout=15000)
        page.locator('.sidebar nav').get_by_role('button',name='我的课程',exact=True).click()
        expect(page.locator('.course-card')).to_have_count(20)
        page.get_by_role('button',name='下一页',exact=True).click()
        expect(page.locator('.course-card')).to_have_count(5)
        page.get_by_role('button',name='上一页',exact=True).click()
        page.get_by_role('button',name='加载学习概览',exact=True).click()
        expect(page.locator('.course-summary')).to_contain_text('平均成绩')
        screenshot(page, 'courses-fixture')
        page.locator('.course-card').first.click()
        page.locator('.assignment-row').first.click()
        expect(page.get_by_role('heading',name='动量守恒 · 测试题目',exact=True)).to_be_visible()
        page.get_by_role('button',name='查看答案',exact=True).click()
        expect(page.locator('.answer')).to_contain_text('测试参考答案')
        page.get_by_role('spinbutton',name='提交成绩').fill('87')
        page.get_by_role('button',name='提交成绩',exact=True).click()
        assert not page.evaluate('window.__test.calls.some(x=>x.action==="submit")')
        page.get_by_role('button',name='确认提交',exact=True).click()
        page.wait_for_function('window.__test.calls.some(x=>x.action==="submit"&&x.grade==="87")')
        page.get_by_role('button',name='向 AI 请教这道题',exact=True).click()
        expect(page.locator('.composer-files')).to_contain_text('题目 201')
        assert not errors, errors
        context.close()
        # A desktop entry must wait for its bridge, not load browser preview data.
        context = browser.new_context(viewport={'width':1280,'height':720})
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL+'/desktop.html')
        page.wait_for_load_state('networkidle')
        expect(page.locator('.startup')).to_be_visible()
        expect(page.locator('.preview-badge')).to_have_count(0)
        page.evaluate(FIXTURE)
        page.evaluate("window.dispatchEvent(new Event('pywebviewready'))")
        expect(page.locator('.app-shell')).to_be_visible()
        expect(page.locator('.fatal')).to_have_count(0)
        context.close()

        # One unreadable recent conversation must not lock the entire application.
        context = browser.new_context(viewport={'width':1440,'height':900})
        context.add_init_script(FIXTURE + """
          const original=window.pywebview.api.bootstrap;
          window.pywebview.api.bootstrap=async()=>{const b=await original();b.settings.startup='last';b.conversations=[{id:'broken',title:'无法恢复的会话',updated:1}];b.username='';return b;};
          window.pywebview.api.conversation=async()=>{throw Error('测试：会话损坏');};
          window.pywebview.api.credential_status=async()=>new Promise(()=>{});
          window.pywebview.api.login=async()=>new Promise(()=>{});
          window.pywebview.api.cancel_login=async()=>true;
          const originalTimeout=window.setTimeout;
          window.setTimeout=(fn,ms,...args)=>originalTimeout(fn,ms===20000?300:ms,...args);
        """)
        page=context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL+'/desktop.html')
        expect(page.locator('.welcome')).to_be_visible()
        expect(page.locator('.fatal')).to_have_count(0)
        page.locator('.sidebar nav').get_by_role('button',name='我的课程',exact=True).click()
        page.get_by_role('button',name='登录理工学堂',exact=True).click()
        screenshot(page,'login')
        dialog=page.get_by_role('dialog')
        dialog.get_by_label('账号',exact=True).fill('test-user')
        dialog.get_by_label('密码',exact=True).fill('test-password')
        dialog.get_by_role('button',name='登录',exact=True).click()
        expect(dialog.get_by_role('alert')).to_contain_text('登录超时')
        expect(dialog.get_by_role('button',name='登录',exact=True)).to_be_enabled()
        dialog.get_by_role('button',name='取消',exact=True).click()
        expect(page.get_by_role('dialog')).to_have_count(0)
        context.close()
        assert not errors, errors
        browser.close()
    print(json.dumps({'ok':True,'console_errors':errors,'screenshots':str(OUTPUT),'checks':['theme persistence','command palette and Escape','prompt CRUD','file references','Markdown/code/math/table','message editing','5 viewport sizes','stream/stop/regenerate','course pagination','grade confirmation']},ensure_ascii=False))
finally:
    server.shutdown()
