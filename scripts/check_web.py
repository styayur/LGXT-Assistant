"""Real browser + local RPC checks using isolated application data.

Optional --exe verifies the distributed executable with the same browser checks.
"""
import argparse
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe')
    args = parser.parse_args()
    command = [str(Path(args.exe).resolve())] if args.exe else [sys.executable, str(ROOT / 'web_app.py')]
    with tempfile.TemporaryDirectory(prefix='lgxt-web-check-') as directory:
        env = dict(os.environ, APPDATA=directory, PYTHONIOENCODING='utf-8')
        process = subprocess.Popen(command + ['--no-browser'], cwd=directory, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lines = queue.Queue()

        def output():
            for raw in process.stdout:
                lines.put(raw.decode('utf-8', errors='replace').strip())
        threading.Thread(target=output, daemon=True).start()
        try:
            url = ''
            for _ in range(20):
                line = lines.get(timeout=60)
                if line.startswith('http://127.0.0.1:'):
                    url = line
                    break
            assert url, 'Application did not print its launch URL'
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 900})
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                # Never read actual system credentials during automated verification.
                def credentials(route):
                    if route.request.post_data_json.get('method') == 'credential_status':
                        route.fulfill(json={'result': {'hasKey': False, 'savedUsername': ''}})
                    else:
                        route.continue_()
                page.route('**/api/call', credentials)
                page.goto(url)
                page.wait_for_load_state('networkidle')
                expect(page.locator('.welcome')).to_be_visible()
                expect(page.get_by_text('Windows 网页版', exact=True)).to_be_visible()
                assert '#token=' not in page.url
                page.locator('.sidebar').get_by_role('button', name='设置 4.0', exact=True).click()
                page.get_by_role('button', name='浅色', exact=True).click()
                page.get_by_role('button', name='保存更改', exact=True).click()
                expect(page.get_by_text('设置已保存', exact=True)).to_be_visible()
                page.reload()
                expect(page.locator('html')).to_have_attribute('data-theme', 'light')
                page.locator('.sidebar').get_by_role('button', name='设置 4.0', exact=True).click()
                page.get_by_role('button', name='导出', exact=True).click()
                expect(page.get_by_label('导出目录', exact=True)).to_be_visible()
                expect(page.get_by_role('button', name='选择导出目录')).to_have_count(0)
                saved = page.evaluate("""async () => {
                    const c = {id:crypto.randomUUID(), title:'网页导出验证', updated:Date.now(),
                        messages:[{id:crypto.randomUUID(), role:'user', content:'验证 Markdown 导出'}]};
                    const r = await fetch('/api/call', {method:'POST', headers:{
                        'Content-Type':'application/json', 'X-LGXT-Token':sessionStorage.getItem('lgxt.browser.token')},
                        body:JSON.stringify({method:'save_conversation', args:[c]})});
                    return r.ok;
                }""")
                assert saved
                page.reload()
                expect(page.get_by_text('验证 Markdown 导出', exact=True)).to_be_visible()
                with page.expect_download() as download:
                    page.locator('.topbar-actions').get_by_role('button', name='导出会话', exact=True).click()
                assert download.value.suggested_filename.endswith('.md')
                assert '验证 Markdown 导出' in Path(download.value.path()).read_text(encoding='utf-8')
                for width, height in [(1280, 720), (1920, 1080)]:
                    page.set_viewport_size({'width': width, 'height': height})
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
                page.set_viewport_size({'width': 1440, 'height': 900})
                screenshot = ROOT / 'docs/screenshots/windows-web.png'
                page.screenshot(path=str(screenshot))
                assert not errors, errors
                browser.close()
            print('PASS: browser connection, settings persistence, reload, export UI, download, layouts, JS errors')
        finally:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                else:
                    process.terminate()
                process.wait(timeout=15)


if __name__ == '__main__':
    main()

