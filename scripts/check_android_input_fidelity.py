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
        return self.adb('shell', *args).decode('utf-8', errors='replace')

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

    def edits(self):
        fields = [n for n in self.tree().iter('node') if n.get('class') == 'android.widget.EditText']
        if len(fields) != 2:
            raise AssertionError('Expected precisely two fixture login fields')
        return fields

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
        first, last = response.find('{'), response.rfind('}')
        if first < 0 or last < first:
            raise AssertionError('No controlled IME acknowledgement')
        result = json.loads(response[first:last+1])
        if result.get('ok') is not True or result.get('package') != PACKAGE:
            raise AssertionError('Controlled IME route unavailable; input was not qualified')
        return result

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
                self.tap(self.edits()[number])
                started = time.monotonic()
                field_record = {'field':'username' if number==0 else 'password',
                                'requestedLength':len(value), 'route':route}
                field_records.append(field_record)
                if route == 'adb-burst':
                    # Exact existing native route, not CUA app.typeText/IME paste.
                    self.shell('input', 'text', value)
                elif route == 'adb-per-key':
                    for char in value:
                        self.shell('input', 'text', char)
                else:
                    self.wait('LGXT TEST IME')
                    field_record['editor'] = self.ime('probe')
                    if number == 1:
                        editor = field_record['editor']
                        if not editor['inputType'] & 0x80 or not editor['inputType'] & 0x80000:
                            raise AssertionError('Native password variation/suggestion protection absent')
                        if not editor['imeOptions'] & 0x1000000:
                            raise AssertionError('Native no-personalized-learning flag absent')
                    if route == 'ime-per-key':
                        for index in range(len(value)):
                            self.ime('single', value, index)
                    elif route == 'editor-menu-paste':
                        field_record['pasteIme'] = self.original_ime
                        self.ime('clipboard', value)  # Remote emulator clipboard only.
                        self.shell('ime', 'set', self.original_ime)
                        field = self.edits()[number]
                        x, y = self.center(field)
                        self.shell('input', 'swipe', str(x), str(y), str(x), str(y), '850')
                        self.paste_from_editor_menu()
                        self.shell('ime', 'set', IME)
                    else:
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
                self.shell('input', 'keyevent', '4')
                time.sleep(.3)
            record['fields'] = field_records
            (folder/'before-submit.png').write_bytes(self.adb('exec-out', 'screencap', '-p'))
            record['stage'] = 'submit'
            self.tap_text('登录理工学堂')
            self.tap_text('允许并登录')  # Fake client only; no platform network request.
            target = '刷新作业状态' if expected else 'Synthetic input did not match exactly'
            self.wait(target)
            observations = self.observations()
            if len(observations) != 1:
                raise AssertionError('Expected exactly one strict synthetic login observation')
            observed = observations[0]
            record['observation'] = observed
            if observed['usernameLength'] != len(username) or observed['passwordLength'] != len(password):
                raise AssertionError('Input length changed before strict login handoff')
            if (observed['usernameExact'] and observed['passwordExact']) is not expected:
                raise AssertionError('Exact synthetic credential comparison differs')
            record.update(passed=True, stage='complete')
            (folder/'after-submit.png').write_bytes(self.adb('exec-out', 'screencap', '-p'))
        except Exception as error:
            # No arbitrary logcat, input payload or device data is serialized.
            record['errorType'] = type(error).__name__
            record['error'] = str(error) if isinstance(error, AssertionError) else 'Fixture route failed'
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
