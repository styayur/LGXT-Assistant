# SPDX-License-Identifier: AGPL-3.0-only
"""Exact 25ms synthetic browser oracle, including empty/prefill setup controls."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from playwright.sync_api import expect, sync_playwright
from browser_input_checks import field_metadata, focus_editor, replace_with_keys
from synthetic_credentials import FIXTURE_USERNAME, FIXTURE_PASSWORD

PREFILL = 'fixture-prefilled-user'
STALE_PASSWORD = 'fixture-stale-password'
BANNER = 'Fixture · 合成数据验收，未连接真实平台'
MARKER = 'LGXT_SYNTHETIC_LOGIN='


def observations(path):
    if not path.exists():
        return []
    return [json.loads(line.split(MARKER, 1)[1]) for line in
            path.read_text(encoding='utf-8', errors='replace').splitlines() if MARKER in line]


def run_case(browser, name, prefill, replace, wrong, log):
    context = browser.new_context(viewport={'width':390, 'height':844},
                                  storage_state={'cookies':[], 'origins':[]})
    record = {'case':name, 'passed':False, 'stage':'setup', 'fixtureOnly':True,
              'typingDelayMs':25, 'prefill':prefill, 'replace':replace,
              'hostClipboardUsed':False, 'expectedAccepted':not wrong and (not prefill or replace)}
    before = len(observations(log))
    page = context.new_page()
    try:
        page.goto('http://127.0.0.1:'+('8555' if prefill else '8554'))
        page.wait_for_load_state('networkidle', timeout=45000)
        page.locator('flt-semantics-placeholder').dispatch_event('click')
        expect(page.get_by_role('textbox')).to_have_count(2)
        expect(page.get_by_text(BANNER, exact=True)).to_be_visible()
        page.wait_for_timeout(500)  # Same existing Flutter route-animation wait.
        fields = record['fields'] = []
        for index, text in enumerate((FIXTURE_USERNAME,
                                      'fixture-passw0rd' if wrong else FIXTURE_PASSWORD)):
            record['stage'] = 'editor-ready'
            field = focus_editor(page, index)
            initial = PREFILL if prefill and index == 0 else ''
            expect(field).to_have_value(initial)
            detail = {'field':'username' if index == 0 else 'password',
                      'initial':field_metadata(field, initial)}
            fields.append(detail)
            if index == 1 and not detail['initial']['masked']:
                raise AssertionError('Password masking must remain enabled')
            if replace and prefill and index == 1:
                # Prior user input, not password restoration or browser autofill.
                page.keyboard.type(STALE_PASSWORD, delay=25)
                expect(field).to_have_value(STALE_PASSWORD)
                detail['beforeReplace'] = field_metadata(field, STALE_PASSWORD)
            record['stage'] = 'input'
            if name == 'prefill-append25-rejected' and index == 0:
                page.keyboard.press('End')
            detail['beforeInput'] = field_metadata(field, initial)
            if replace:
                replace_with_keys(page, text)
            else:
                page.keyboard.type(text, delay=25)
            expected = text if replace else initial + text
            detail['afterInput'] = field_metadata(field, expected)
            if name == 'prefill-click-type25-rejected' and index == 0:
                # A click may place the cursor inside existing text. Preserve
                # this original setup control separately from explicit append.
                if detail['afterInput']['length'] != len(expected):
                    raise AssertionError('Prefilled input length changed')
            else:
                expect(field).to_have_value(expected)
        record['stage'] = 'login'
        page.get_by_role('button', name='登录理工学堂', exact=True).click()
        target = (page.get_by_role('button', name='刷新作业状态', exact=True)
                  if record['expectedAccepted'] else
                  page.get_by_text('Synthetic input did not match exactly', exact=True))
        expect(target).to_be_visible()
        record['stage'] = 'boundary'
        deadline = time.monotonic()+5
        received = observations(log)[before:]
        while not received and time.monotonic() < deadline:
            time.sleep(.05)
            received = observations(log)[before:]
        if len(received) != 1:
            raise AssertionError('Exactly one login boundary observation is required')
        observed = record['observation'] = received[0]
        expected_user_length = len(FIXTURE_USERNAME)+(len(PREFILL) if prefill and not replace else 0)
        if (observed['usernameLength'] != expected_user_length or
                observed['passwordLength'] != len(FIXTURE_PASSWORD) or
                observed.get('usernameType') != 'str' or observed.get('passwordType') != 'str' or
                observed['usernameExact'] is not (not prefill or replace) or
                observed['passwordExact'] is not (not wrong)):
            raise AssertionError('Strict login handoff differed from the synthetic input')
        record.update(passed=True, stage='complete')
    except Exception as error:
        record.update(errorType=type(error).__name__,
                      observationsOnFailure=observations(log)[before:])
    finally:
        context.close()
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--empty-log', type=Path, default=Path('mobile-render.log'))
    parser.add_argument('--prefill-log', type=Path, default=Path('mobile-prefill-render.log'))
    parser.add_argument('--output', type=Path, default=Path('work/input-fidelity-browser/report.json'))
    args = parser.parse_args()
    cases = [('empty-append25', False, False, False),
             ('empty-replace25', False, True, False),
             ('prefill-append25-rejected', True, False, False),
             ('prefill-click-type25-rejected', True, False, False),
             ('prefill-replace25', True, True, False),
             ('same-length-wrong25-rejected', False, False, True)]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            results = []
            args.output.parent.mkdir(parents=True, exist_ok=True)
            for name, prefill, replace, wrong in cases:
                result = run_case(browser, name, prefill, replace, wrong,
                                  args.prefill_log if prefill else args.empty_log)
                results.append(result)
                (args.output.parent/(name+'.json')).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
                sys.stdout.write(json.dumps({'case':name, 'passed':result['passed'],
                                            'stage':result['stage']})+'\n')
                sys.stdout.flush()
            report = {'fixtureOnly':True, 'sourceCommit':os.environ.get('GITHUB_SHA'),
                      'browser':browser.version, 'passed':all(r['passed'] for r in results),
                      'cases':results, 'productionFlagsChanged':False,
                      'notCovered':['Android APK/IME','real accounts','CUA host input transport']}
        finally:
            browser.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    sys.stdout.write(json.dumps({'passed':report['passed'],
                                'failed':[r['case'] for r in results if not r['passed']]})+'\n')
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
