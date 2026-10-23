"""Capture actual Flet renderer with explicit synthetic platform data.

Start: python scripts/preview_mobile.py --fixture --port 8554
Run: python scripts/check_mobile_browser.py
These are browser renderer checks, not Android APK/device acceptance.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':390,'height':844})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8554')
    page.locator('flt-semantics-placeholder').dispatch_event('click')
    expect(page.get_by_role('textbox')).to_have_count(2)
    page.screenshot(path=str(ROOT/'docs/screenshots/android-flet-login-fixture.png'))
    # Flutter editing expects keyboard events; DOM fill alone does not commit text.
    page.get_by_role('textbox').nth(0).click();page.keyboard.type('fixture-user',delay=25)
    page.get_by_role('textbox').nth(1).click();page.keyboard.type('fixture-password',delay=25)
    page.get_by_role('button',name='登录理工学堂',exact=True).click()
    expect(page.get_by_role('button',name='刷新作业状态',exact=True)).to_be_visible()
    page.screenshot(path=str(ROOT/'docs/screenshots/android-flet-dashboard-fixture.png'))
    # Navigation position is inspected in the genuine 390x844 renderer screenshot.
    page.mouse.click(195,798)
    expect(page.get_by_text('Synthetic physics course',exact=True)).to_be_visible()
    page.screenshot(path=str(ROOT/'docs/screenshots/android-flet-courses-fixture.png'))
    page.get_by_role('button').first.click()
    page.get_by_role('button',name='查看题目',exact=True).click()
    page.get_by_role('button',name='查看原图 / 识别公式 / AI 分析',exact=True).click()
    expect(page.get_by_text('题目与解答',exact=True)).to_be_visible()
    page.screenshot(path=str(ROOT/'docs/screenshots/android-flet-question-fixture.png'))
    page.set_viewport_size({'width':390,'height':480})
    page.screenshot(path=str(ROOT/'docs/screenshots/android-flet-keyboard-height-fixture.png'))
    assert not errors,errors
    browser.close()
