# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic input routes on an explicitly addressed disposable REMOTE emulator.

This never controls a host desktop/clipboard. It cannot target the release package.
adb key events, controlled IME calls and editor-menu paste are distinct evidence.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

try:
    from synthetic_credentials import FIXTURE_USERNAME, FIXTURE_PASSWORD
except ModuleNotFoundError as error:
    if error.name != 'synthetic_credentials':
        raise
    from scripts.synthetic_credentials import FIXTURE_USERNAME, FIXTURE_PASSWORD

PACKAGE = 'io.github.styayur.lgxt_input_fidelity'
IME = 'io.github.styayur.lgxt_input_ime/.FidelityIme'
BRIDGE = 'io.github.styayur.lgxt_input_ime/.FidelityIme$Bridge'
BANNER = 'Fixture · 合成数据验收，未连接真实平台'
ROUTES = ('adb-burst', 'adb-per-key', 'ime-commit-bulk', 'ime-commit-fast',
          'ime-per-key', 'ime-compose', 'ime-context-paste', 'editor-menu-paste')


def parse_ime_response(response):
    # `am broadcast` first echoes "Intent { ... }". Only the completion's
    # result data belongs to our receiver; the first brace is not JSON.
    completed = re.findall(r'^Broadcast completed: result=-?\d+, data="(\{[^\r\n]*\})"\s*$',
                           response, re.MULTILINE)
    if len(completed) != 1:
        raise AssertionError('Missing unique controlled IME completion data')
    try:
        result = json.loads(completed[0])
    except json.JSONDecodeError as error:
        raise AssertionError('Invalid controlled IME completion JSON') from error
    if not isinstance(result, dict):
        raise AssertionError('Controlled IME completion is not an object')
    result['broadcastCompletionParsed'] = True
    result['intentWrapperIgnored'] = 'Broadcasting: Intent {' in response
    return result


def require_exact_boundary(observed, username, password, expected):
    if (observed.get('usernameType') != 'str' or observed.get('passwordType') != 'str'
            or observed['usernameLength'] != len(username)
            or observed['passwordLength'] != len(password)):
        raise AssertionError('Input type/length changed before strict login handoff')
    # Password negatives must still prove the correct username reached login.
    if observed['usernameExact'] is not True or observed['passwordExact'] is not expected:
        raise AssertionError('Exact synthetic credential comparison differs')


def require_disposable_runner(serial, environment=None):
    environment = os.environ if environment is None else environment
    if environment.get('GITHUB_ACTIONS') != 'true' or not re.fullmatch(r'emulator-\d+', serial):
        raise ValueError('Refusing anything except an explicit remote CI emulator')


def verify_fixture_apk(apk, identity):
    if identity.get('fixtureOnly') is not True or identity.get('package') != PACKAGE:
        raise ValueError('Refusing a non-input-fixture identity')
    if hashlib.sha256(apk.read_bytes()).hexdigest() != identity.get('apkSha256'):
        raise ValueError('Input fixture APK hash mismatch')
    with zipfile.ZipFile(apk) as outer:
        archives = [n for n in outer.namelist() if n.endswith('/app.zip')]
        if len(archives) != 1:
            raise ValueError('Missing unique compiled fixture payload')
        with zipfile.ZipFile(io.BytesIO(outer.read(archives[0]))) as inner:
            names = [Path(n).name for n in inner.namelist()]
            for marker in ('app_under_test.', 'android_fixture_entry.', 'synthetic_credentials.'):
                if not any(name.startswith(marker) for name in names):
                    raise ValueError('Refusing payload without strict test-only fixture markers')


class RemoteEmulator:
    def __init__(self, serial, output):
        require_disposable_runner(serial)
        self.serial, self.output = serial, Path(output)
        if self.shell('getprop', 'ro.kernel.qemu').strip() != '1':
            raise ValueError('Refusing a non-emulator device')
        if self.shell('getprop', 'ro.product.cpu.abi').strip() != 'x86_64':
            raise ValueError('Input diagnostic is qualified only for disposable x86_64')
        if self.shell('getprop', 'ro.build.version.sdk').strip() != '35':
            raise ValueError('Input diagnostic is qualified only for disposable API35')
        self.output.mkdir(parents=True, exist_ok=True)
        self.original_ime = self.shell('settings', 'get', 'secure', 'default_input_method').strip()
        if not self.original_ime or self.original_ime == 'null':
            raise ValueError('No baseline software keyboard identity')

    def adb(self, *args):
        return subprocess.check_output(['adb', '-s', self.serial, *map(str, args)], timeout=90)

    def shell(self, *args):
        # adb joins arguments for a second, remote shell. Preserve literal $
        # in the nested receiver class name instead of expanding $Bridge.
        return self.adb('shell', shlex.join(map(str, args))).decode('utf-8', errors='replace')

    def tree(self):
        self.shell('uiautomator', 'dump', '/sdcard/lgxt-input-fixture.xml')
        return ET.fromstring(self.shell('cat', '/sdcard/lgxt-input-fixture.xml'))

    @staticmethod
    def matching(root, text):
        return [n for n in root.iter('node') if text.casefold() in
                (n.get('text', '') + ' ' + n.get('content-desc', '')).casefold()]

    def wait(self, text, timeout=40):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            root = self.tree()
            if self.matching(root, text):
                return root
            time.sleep(.3)
        raise AssertionError('Synthetic fixture UI readiness failed')

    @staticmethod
    def center(node):
        x1, y1, x2, y2 = map(int, re.findall(r'\d+', node.get('bounds', '')))
        return (x1+x2)//2, (y1+y2)//2

    def tap(self, node):
        # Preserve the existing native driver's UIAutomator teardown settling.
        time.sleep(.5)
        self.shell('input', 'tap', *map(str, self.center(node)))

    def tap_text(self, text):
        nodes = self.matching(self.wait(text), text)
        self.tap(nodes[-1])

    def paste_from_editor_menu(self):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            nodes = [n for n in self.matching(self.tree(), 'Paste') if n.get('package') == PACKAGE]
            if nodes:
                self.tap(nodes[-1])
                return
            time.sleep(.3)
        raise AssertionError('Fixture editor-menu Paste unavailable; no keyboard suggestion substituted')

    def edits(self, timeout=40):
        # Switching between the stock keyboard and the test IME changes the
        # viewport asynchronously. Require both target-app fields before input.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            fields = [n for n in self.tree().iter('node')
                      if n.get('class') == 'android.widget.EditText' and n.get('package') == PACKAGE]
            self.last_fixture_field_count = len(fields)
            if len(fields) == 2:
                return fields
            time.sleep(.3)
        raise AssertionError('Expected precisely two fixture login fields')

    def observations(self):
        result = []
        for line in self.shell('logcat', '-d').splitlines():
            if 'LGXT_SYNTHETIC_LOGIN=' in line:
                result.append(json.loads(line.split('LGXT_SYNTHETIC_LOGIN=', 1)[1]))
        return result

    def ime(self, mode, text='', index=None):
        args = ['am', 'broadcast', '-n', BRIDGE, '--es', 'mode', mode]
        if text:
            args += ['--es', 'text64', base64.b64encode(text.encode()).decode()]
        if index is not None:
            args += ['--ei', 'index', str(index)]
        response = self.shell(*args)
        self.last_ime_transport = {
            'componentEchoExact': BRIDGE in response,
            'completionLinePresent': 'Broadcast completed:' in response,
            'completionDataPresent': bool(re.search(r'Broadcast completed:.*?, data=', response)),
        }
        result = parse_ime_response(response)
        self.last_ime_probe = result
        if result.get('ok') is not True or result.get('package') != PACKAGE:
            raise AssertionError('Controlled IME route unavailable; input was not qualified')
        return result

    def wait_ime(self, timeout=40):
        # An app's UIAutomator tree is not an InputConnection readiness oracle.
        # Poll only read-only native state; never retry or pace an input write.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                result = self.ime('probe')
                if all(result.get(key) is True for key in
                       ('inputViewRequested', 'inputViewAttached', 'inputViewVisible')):
                    return result
            except AssertionError as error:
                self.last_ime_error = str(error)
            time.sleep(.3)
        raise AssertionError('Controlled IME editor/view readiness failed before input')

    def dismiss_controlled_keyboard(self):
        # Android Back exits the app when no IME view is visible. In particular,
        # switching back from the stock editor menu need not reopen that view.
        probe = self.ime('probe')
        visible = all(probe.get(k) is True for k in
                      ('inputViewRequested', 'inputViewAttached', 'inputViewVisible'))
        if visible:
            self.shell('input', 'keyevent', '4')
        return {'probe': probe, 'backSentToVisibleIme': visible}

    def scroll_to_rejection(self, timeout=40):
        # show_login places the rejection after the form. UIAutomator omits
        # offscreen text, so navigate the actual app scroll view to expose it.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            root = self.tree()
            if self.matching(root, 'Synthetic input did not match exactly'):
                return root
            scrolls = [n for n in root.iter('node')
                       if n.get('package') == PACKAGE and n.get('scrollable') == 'true']
            if scrolls:
                n = scrolls[0]
                x1, y1, x2, y2 = map(int, re.findall(r'\d+', n.get('bounds', '')))
                x = (x1+x2)//2
                self.shell('input', 'swipe', str(x), str(y1+(y2-y1)*3//4),
                           str(x), str(y1+(y2-y1)//3), '400')
            time.sleep(.3)
        raise AssertionError('Strict synthetic rejection was not visible in login UI')

    def case(self, name, route, username, password, expected):
        folder = self.output/name
        folder.mkdir(exist_ok=True)
        record = {'case':name, 'route':route, 'expectedAccepted':expected,
                  'passed':False, 'stage':'prepare', 'hostClipboardUsed':False}
        try:
            self.shell('am', 'force-stop', PACKAGE)
            if 'Success' not in self.shell('pm', 'clear', PACKAGE):
                raise AssertionError('Disposable fixture state could not be cleared')
            selected = self.original_ime if route.startswith('adb-') else IME
            self.shell('ime', 'set', selected)
            self.shell('logcat', '-c')
            self.shell('am', 'start', '-W', '-n', PACKAGE+'/.MainActivity')
            self.wait(BANNER)
            record['baselineIme'] = self.original_ime
            record['selectedIme'] = selected
            record['stage'] = 'input'
            field_records = record['fields'] = []
            for number, value in enumerate((username, password)):
                self.last_ime_probe = None
                self.last_ime_transport = None
                self.last_ime_error = None
                record['stage'] = 'focus'
                self.tap(self.edits()[number])
                started = time.monotonic()
                field_record = {'field':'username' if number==0 else 'password',
                                'requestedLength':len(value), 'route':route}
                field_records.append(field_record)
                if route == 'adb-burst':
                    record['stage'] = 'input'
                    # Exact existing native route, not CUA app.typeText/IME paste.
                    self.shell('input', 'text', value)
                elif route == 'adb-per-key':
                    record['stage'] = 'input'
                    for char in value:
                        self.shell('input', 'text', char)
                else:
                    record['stage'] = 'ime-ready'
                    field_record['editor'] = self.wait_ime()
                    if number == 1:
                        editor = field_record['editor']
                        if not editor['inputType'] & 0x80 or not editor['inputType'] & 0x80000:
                            raise AssertionError('Native password variation/suggestion protection absent')
                        if not editor['imeOptions'] & 0x1000000:
                            raise AssertionError('Native no-personalized-learning flag absent')
                    if route == 'ime-per-key':
                        record['stage'] = 'input'
                        for index in range(len(value)):
                            self.ime('single', value, index)
                    elif route == 'editor-menu-paste':
                        record['stage'] = 'input'
                        field_record['pasteIme'] = self.original_ime
                        self.ime('clipboard', value)  # Remote emulator clipboard only.
                        self.shell('ime', 'set', self.original_ime)
                        field = self.edits()[number]
                        x, y = self.center(field)
                        self.shell('input', 'swipe', str(x), str(y), str(x), str(y), '850')
                        self.paste_from_editor_menu()
                        self.shell('ime', 'set', IME)
                    else:
                        record['stage'] = 'input'
                        mode = {'ime-commit-bulk':'commit', 'ime-commit-fast':'fast',
                                'ime-compose':'compose', 'ime-context-paste':'paste'}[route]
                        field_record['acknowledgement'] = self.ime(mode, value)
                field_record['elapsedMs'] = round((time.monotonic()-started)*1000)
                # Retain original per-field waits; never pace a burst into a pass.
                time.sleep(.5)
                current = self.edits()[number]
                field_record['masked'] = current.get('password') == 'true'
                field_record['accessibilityTextLength'] = len(current.get('text', ''))
                if number == 1 and not field_record['masked']:
                    raise AssertionError('Password masking unexpectedly disabled')
                record['stage'] = 'dismiss-keyboard'
                if route.startswith('adb-'):
                    self.shell('input', 'keyevent', '4')
                else:
                    field_record['keyboardDismissal'] = self.dismiss_controlled_keyboard()
                time.sleep(.3)
            record['fields'] = field_records
            (folder/'before-submit.png').write_bytes(self.adb('exec-out', 'screencap', '-p'))
            record['stage'] = 'submit'
            self.tap_text('登录理工学堂')
            self.tap_text('允许并登录')  # Fake client only; no platform network request.
            if expected:
                self.wait('刷新作业状态')
            else:
                self.scroll_to_rejection()
            observations = self.observations()
            if len(observations) != 1:
                raise AssertionError('Expected exactly one strict synthetic login observation')
            observed = observations[0]
            record['observation'] = observed
            require_exact_boundary(observed, username, password, expected)
            record.update(passed=True, stage='complete')
            (folder/'after-submit.png').write_bytes(self.adb('exec-out', 'screencap', '-p'))
        except Exception as error:
            # No arbitrary logcat, input payload or device data is serialized.
            record['errorType'] = type(error).__name__
            record['error'] = str(error) if isinstance(error, AssertionError) else 'Fixture route failed'
            record['lastFixtureFieldCount'] = getattr(self, 'last_fixture_field_count', None)
            if not route.startswith('adb-'):
                record['lastImeProbe'] = getattr(self, 'last_ime_probe', None)
                record['lastImeTransport'] = getattr(self, 'last_ime_transport', None)
                record['lastImeError'] = getattr(self, 'last_ime_error', None)
            try:
                (folder/'failure.png').write_bytes(self.adb('exec-out', 'screencap', '-p'))
                ET.ElementTree(self.tree()).write(folder/'failure.xml', encoding='utf-8')
                record['failureUiCaptured'] = True
            except Exception:
                record['failureUiCaptured'] = False
            if record['stage'] != 'prepare':
                try:
                    record['observationsOnFailure'] = self.observations()
                except Exception:
                    record['observationUnavailable'] = True
        (folder/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', required=True)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--identity', type=Path, required=True)
    parser.add_argument('--ime-apk', type=Path, required=True)
    parser.add_argument('--output', default='build/android/input-results')
    args = parser.parse_args()
    require_disposable_runner(args.serial)  # Before any adb or device read.
    identity = json.loads(args.identity.read_text())
    if identity.get('sourceCommit') != os.environ.get('GITHUB_SHA'):
        raise ValueError('Fixture source identity does not match the current remote run')
    verify_fixture_apk(args.apk, identity)
    runner = RemoteEmulator(args.serial, args.output)
    runner.adb('install', '-t', '-r', args.ime_apk)
    runner.adb('install', '-t', '-r', args.apk)
    runner.shell('ime', 'enable', IME)
    results = [runner.case(route,route,FIXTURE_USERNAME,FIXTURE_PASSWORD,True) for route in ROUTES]
    for name, wrong in (('same-length-wrong','fixture-passw0rd'),
                        ('duplicate',FIXTURE_PASSWORD*2), ('truncated',FIXTURE_PASSWORD[:-1])):
        results.append(runner.case('negative-'+name,'ime-commit-bulk',FIXTURE_USERNAME,wrong,False))
    report = {'fixtureOnly':True,'sourceCommit':identity.get('sourceCommit'),
              'apkSha256':identity['apkSha256'],'package':PACKAGE,'cases':results,
              'passed':all(r['passed'] for r in results),
              'notCovered':['CUA host app.typeText implementation','real credentials/platform',
                            'physical ARM64/vendor IMEs','production APK/account acceptance']}
    (runner.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    sys.stdout.write(json.dumps({'passed':report['passed'],'cases':len(results),
                      'failed':[r['case'] for r in results if not r['passed']]})+'\n')
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
