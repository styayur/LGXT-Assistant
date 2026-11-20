# SPDX-License-Identifier: AGPL-3.0-only
"""Strict synthetic oracle and handoff tests; no IME/device acceptance claim."""
import json

import flet as ft
import pytest

from scripts.synthetic_credentials import (
    FIXTURE_PASSWORD, FIXTURE_USERNAME, credential_observation, exact_synthetic_login,
)
from scripts.android_fixture_entry import FixtureClient as NativeFixtureClient
from test_mobile import FixtureClient as BrowserFixtureClient, Page, Storage, controls, find, wait_for
from mobile.src.main import main


@pytest.mark.parametrize('username,password', [
    ('fixture-useR', FIXTURE_PASSWORD),
    (FIXTURE_USERNAME, 'fixture-passw0rd'),
    (FIXTURE_USERNAME, FIXTURE_PASSWORD * 2),
    (FIXTURE_USERNAME, FIXTURE_PASSWORD[:-1]),
    (FIXTURE_USERNAME, ' ' + FIXTURE_PASSWORD),
    (FIXTURE_USERNAME, FIXTURE_PASSWORD + ' '),
    (FIXTURE_USERNAME, FIXTURE_PASSWORD.upper()),
    (FIXTURE_USERNAME, 'fixture-passwörd'),
    (' ' + FIXTURE_USERNAME, FIXTURE_PASSWORD),
    ('', ''),
    (None, FIXTURE_PASSWORD),
    (FIXTURE_USERNAME, False),
])
def test_oracle_rejects_changed_text_even_when_nonempty(username, password):
    assert exact_synthetic_login(username, password) is False
    for client_type in (NativeFixtureClient, BrowserFixtureClient):
        client = client_type()
        assert client.login(FIXTURE_USERNAME, FIXTURE_PASSWORD)[0] is True
        assert client.headers
        assert client.login(username, password)[0] is False
        assert not client.headers, 'A failed input check must not retain a prior session'


def test_oracle_logs_only_equality_and_lengths(caplog):
    client = NativeFixtureClient()
    assert client.login(FIXTURE_USERNAME, FIXTURE_PASSWORD)[0]
    lines = [r.message for r in caplog.records if 'LGXT_SYNTHETIC_LOGIN=' in r.message]
    assert len(lines) == 1
    observed = json.loads(lines[0].split('LGXT_SYNTHETIC_LOGIN=', 1)[1])
    assert observed == credential_observation(FIXTURE_USERNAME, FIXTURE_PASSWORD)
    assert observed['usernameExact'] and observed['passwordExact']
    assert FIXTURE_USERNAME not in lines[0] and FIXTURE_PASSWORD not in lines[0]


@pytest.mark.parametrize('password,accepted', [
    (FIXTURE_PASSWORD, True),
    ('fixture-passw0rd', False),
    (FIXTURE_PASSWORD * 2, False),
    (FIXTURE_PASSWORD[:-1], False),
    (FIXTURE_PASSWORD + ' ', False),
])
def test_product_control_handoff_obeys_strict_fixture(password, accepted):
    observations = []
    course_queries = []
    class RecordingClient(BrowserFixtureClient):
        def login(self, username, received):
            observations.append(credential_observation(username, received))
            return super().login(username, received)
        def get_my_courses(self):
            course_queries.append(True)
            return super().get_my_courses()

    page = Page()
    main(page, RecordingClient, Storage())
    find(page, ft.TextField, label='账号').value = FIXTURE_USERNAME
    field = find(page, ft.TextField, label='密码')
    field.value = password
    find(page, ft.Button, text='登录理工学堂').on_click(None)
    wait_for(lambda: observations)
    if accepted:
        wait_for(lambda: page.views[-1].route == '/dashboard')
        wait_for(lambda: course_queries)
    else:
        wait_for(lambda: page.views[-1].route == '/login' and
                 any(getattr(c, 'value', '') == 'Synthetic input did not match exactly'
                     for c in controls(page)))
        assert not course_queries
    assert field.value == '', 'Existing password clearing after submission is retained'
    assert observations[0]['passwordExact'] is accepted
    assert observations[0]['passwordLength'] == len(password)


def test_product_password_protection_flags_are_retained():
    page = Page()
    main(page, BrowserFixtureClient, Storage())
    field = find(page, ft.TextField, label='密码')
    assert field.password is True and field.can_reveal_password is True
    assert field.enable_ime_personalized_learning is False
    assert field.autocorrect is False and field.enable_suggestions is False
    assert field.on_change is None, 'Test observation must not add a field change handler'
    assert find(page, ft.AutofillGroup) is not None, 'Keep autofill grouping while repairing privacy forwarding'


def test_native_driver_refuses_host_and_non_emulator_targets_before_adb():
    from scripts.check_android_input_fidelity import require_disposable_runner
    for serial, env in [('emulator-5554', {}), ('physical-device', {'GITHUB_ACTIONS':'true'}),
                        ('', {'GITHUB_ACTIONS':'true'})]:
        with pytest.raises(ValueError, match='remote CI emulator'):
            require_disposable_runner(serial, env)
    require_disposable_runner('emulator-5554', {'GITHUB_ACTIONS':'true'})


def test_native_ime_readiness_requires_attached_visible_view_before_writing(monkeypatch):
    from scripts import check_android_input_fidelity as driver
    runner = object.__new__(driver.RemoteEmulator)
    calls = []
    pending = {'ok':True, 'inputViewRequested':True, 'inputViewAttached':False,
               'inputViewVisible':False}
    ready = dict(pending, inputViewAttached=True, inputViewVisible=True)
    def probe(mode):
        calls.append(mode)
        return pending if len(calls) == 1 else ready
    runner.ime = probe
    monkeypatch.setattr(driver.time, 'sleep', lambda _: None)
    assert runner.wait_ime() == ready
    assert calls == ['probe', 'probe'], 'Readiness polling must never repeat text writes'


def test_native_ime_parser_uses_completion_data_not_intent_wrapper():
    from scripts.check_android_input_fidelity import PACKAGE, parse_ime_response
    data = {'ok':True, 'package':PACKAGE, 'inputType':1}
    response = ('Broadcasting: Intent { flg=0x400000 cmp=test/.Bridge (has extras) }\n'
                'Broadcast completed: result=-1, data="'+json.dumps(data)+'"\n')
    result = parse_ime_response(response)
    assert result['ok'] and result['package'] == PACKAGE
    assert result['broadcastCompletionParsed'] and result['intentWrapperIgnored']
    for invalid in ('Broadcasting: Intent { no completion }',
                    response+response, 'Broadcast completed: result=0, data="{bad}"'):
        with pytest.raises(AssertionError):
            parse_ime_response(invalid)


def test_adb_remote_shell_preserves_literal_nested_receiver_name():
    import shlex
    from scripts.check_android_input_fidelity import BRIDGE, RemoteEmulator
    runner = object.__new__(RemoteEmulator)
    commands = []
    runner.adb = lambda *args: commands.append(args) or b'synthetic acknowledgement'
    arguments = ('am', 'broadcast', '-n', BRIDGE, '--es', 'mode', 'probe')
    assert runner.shell(*arguments) == 'synthetic acknowledgement'
    assert len(commands[0]) == 2 and commands[0][0] == 'shell'
    assert shlex.split(commands[0][1]) == list(arguments)
    assert "'"+BRIDGE+"'" in commands[0][1], 'The remote shell must not expand $Bridge'


def test_native_field_readiness_requires_both_target_fields(monkeypatch):
    import xml.etree.ElementTree as ET
    from scripts import check_android_input_fidelity as driver
    runner = object.__new__(driver.RemoteEmulator)
    partial = ET.fromstring('<hierarchy><node class="android.widget.EditText" package="'+driver.PACKAGE+'"/><node class="android.widget.EditText" package="unrelated.keyboard"/></hierarchy>')
    complete = ET.fromstring('<hierarchy><node class="android.widget.EditText" package="'+driver.PACKAGE+'"/><node class="android.widget.EditText" package="'+driver.PACKAGE+'"/></hierarchy>')
    snapshots = iter((partial, complete))
    runner.tree = lambda: next(snapshots)
    monkeypatch.setattr(driver.time, 'sleep', lambda _: None)
    assert len(runner.edits()) == 2
    assert runner.last_fixture_field_count == 2


def test_flutter_backport_refuses_unreviewed_source():
    from scripts.apply_flutter_autofill_backport import META, patched_bytes
    meta = json.loads(META.read_text())
    with pytest.raises(ValueError, match='unreviewed Flutter'):
        patched_bytes(b'unreviewed SDK baseline', meta)


def test_native_driver_refuses_release_and_unbound_payload(tmp_path):
    import hashlib
    import io
    import zipfile
    from scripts.check_android_input_fidelity import PACKAGE, verify_fixture_apk
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as inner:
        inner.writestr('app_under_test.pyc', b'synthetic marker, not executable')
        inner.writestr('android_fixture_entry.pyc', b'synthetic marker, not executable')
        inner.writestr('synthetic_credentials.pyc', b'synthetic marker, not executable')
    apk = tmp_path/'test-only.apk'
    with zipfile.ZipFile(apk, 'w') as outer:
        outer.writestr('assets/flutter_assets/app/app.zip', archive.getvalue())
    identity = {'fixtureOnly':True, 'package':PACKAGE,
                'apkSha256':hashlib.sha256(apk.read_bytes()).hexdigest()}
    verify_fixture_apk(apk, identity)
    for delta in ({'fixtureOnly':False}, {'package':'io.github.styayur.lgxt_assistant_mobile'},
                  {'apkSha256':'0'*64}):
        with pytest.raises(ValueError):
            verify_fixture_apk(apk, identity|delta)


def test_built_project_sdk_binding_rejects_other_sdk_and_binds_bytes(tmp_path):
    import hashlib
    from scripts.apply_flutter_autofill_backport import built_project_evidence
    sdk = (tmp_path/'reviewed-sdk').resolve()
    project = tmp_path/'project'
    (project/'android').mkdir(parents=True)
    properties = project/'android/local.properties'
    properties.write_text('flutter.sdk='+str(sdk)+'\n')
    (project/'pubspec.lock').write_bytes(b'synthetic resolved lock')
    apk = tmp_path/'synthetic.apk'
    apk.write_bytes(b'synthetic candidate bytes')
    record = built_project_evidence(project, apk, sdk)
    assert record['generatedProjectSdkMatchesRequested'] is True
    assert record['apkSha256'] == hashlib.sha256(apk.read_bytes()).hexdigest()
    assert record['pubspecLockSha256'] == hashlib.sha256((project/'pubspec.lock').read_bytes()).hexdigest()
    properties.write_text('flutter.sdk='+str(tmp_path/'different-sdk')+'\n')
    with pytest.raises(ValueError, match='different Flutter SDK'):
        built_project_evidence(project, apk, sdk)


def test_password_negative_cannot_pass_through_a_corrupted_username():
    from scripts.check_android_input_fidelity import require_exact_boundary
    wrong = 'fixture-passw0rd'
    observed = credential_observation(FIXTURE_USERNAME, wrong)
    require_exact_boundary(observed, FIXTURE_USERNAME, wrong, False)
    # Both credentials have the expected lengths, and login rejects them.
    # That alone must not qualify a password-only negative challenge.
    corrupt = credential_observation('fixture-useR', wrong)
    with pytest.raises(AssertionError, match='Exact synthetic'):
        require_exact_boundary(corrupt, FIXTURE_USERNAME, wrong, False)
    with pytest.raises(AssertionError, match='type/length'):
        require_exact_boundary(dict(observed, passwordType='other'), FIXTURE_USERNAME, wrong, False)


@pytest.mark.parametrize('visible', [True, False])
def test_keyboard_dismissal_never_sends_back_to_an_already_hidden_ime(visible):
    from scripts.check_android_input_fidelity import RemoteEmulator
    runner = object.__new__(RemoteEmulator)
    probes, actions = [], []
    def probe(mode):
        probes.append(mode)
        return dict(inputViewRequested=visible, inputViewAttached=visible, inputViewVisible=visible)
    runner.ime = probe
    runner.shell = lambda *args: actions.append(args)
    result = runner.dismiss_controlled_keyboard()
    assert result['backSentToVisibleIme'] is visible
    assert probes == ['probe'], 'Only native read-only state; no repeated text writes'
    assert actions == ([('input', 'keyevent', '4')] if visible else [])
