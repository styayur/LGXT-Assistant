"""Publication rejects native reports for other bytes or incomplete sessions."""
import json

import pytest

from scripts.publish_android_beta import verify_native_reports


@pytest.fixture
def evidence(tmp_path):
    identity = {'sha256': 'a'*64, 'sourceCommit': 'b'*40, 'version':'3.3.2'}
    record = {'buildRun': '123', 'sourceCommit': identity['sourceCommit'],
              'validatedHead': 'c'*40, 'signedApkSha256': identity['sha256'],
              'fixtureApkSha256': 'd'*64}
    shared = ['native file-picker backup export/import', 'note survives process termination']
    ordinary = {'apkSha256': identity['sha256'], 'fixture': False,
                'previousBetaInPlaceUpgrade': True, 'historicalUpgradeIncompatible': True,
                'passed': shared}
    fixture = {'apkSha256': record['fixtureApkSha256'], 'fixture': True,
               'passed': shared + ['device encrypted synthetic token session restores after process termination and validates',
                                   'logout clears device session across process termination']}
    for report in (ordinary, fixture):
        report['editorProtection']={'verified':True,'masked':True,'nativeInputViewReady':True,
            'apkSha256':report['apkSha256'],'package':'io.github.styayur.lgxt_assistant_mobile',
            'imeOptions':50331654,'inputType':524417}
    for name, value in [('APK-IDENTITY.json', identity), ('ACCEPTANCE-IDENTITY.json', identity),
                        ('NATIVE-ACCEPTANCE.json', record), ('device/acceptance.json', ordinary),
                        ('device-fixture/acceptance.json', fixture)]:
        path = tmp_path/name
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value))
    return tmp_path, identity


def test_same_byte_native_evidence(evidence):
    directory, identity = evidence
    verify_native_reports(directory, identity, '123', 'c'*40)


@pytest.mark.parametrize('path,key,value', [
    ('NATIVE-ACCEPTANCE.json', 'buildRun', '999'),
    ('NATIVE-ACCEPTANCE.json', 'validatedHead', 'e'*40),
    ('device/acceptance.json', 'apkSha256', 'e'*64),
    ('device/acceptance.json', 'previousBetaInPlaceUpgrade', False),
    ('device-fixture/acceptance.json', 'apkSha256', 'e'*64),
    ('device-fixture/acceptance.json', 'passed', []),
])
def test_foreign_or_incomplete_native_evidence_rejected(evidence, path, key, value):
    directory, identity = evidence
    target = directory/path
    report = json.loads(target.read_text())
    report[key] = value
    target.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        verify_native_reports(directory, identity, '123', 'c'*40)


@pytest.mark.parametrize('change', ['missing','foreign-bytes','missing-learning-bit'])
def test_new_beta_requires_exact_byte_native_privacy(evidence, change):
    directory, identity = evidence
    path = directory/'device/acceptance.json'
    report = json.loads(path.read_text())
    if change == 'missing':report.pop('editorProtection')
    elif change == 'foreign-bytes':report['editorProtection']['apkSha256']='f'*64
    else:report['editorProtection']['imeOptions']=33554438
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='native password privacy'):
        verify_native_reports(directory, identity, '123', 'c'*40)
