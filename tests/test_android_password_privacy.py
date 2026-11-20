"""AOSP-format privacy readback rejects the observed unpatched bit loss."""
import pytest
from scripts.check_android_device import editor_protection_snapshot

PACKAGE = 'io.github.styayur.lgxt_assistant_mobile'
DUMP = """Input method service state for synthetic.test.Keyboard:
  mInputStarted=true mInputViewStarted=true mCandidatesViewStarted=false
  mInputEditorInfo:
    inputType=0x80081 imeOptions=0x3000006 privateImeOptions=null
    actionLabel=null actionId=0
    initialSelStart=0 initialSelEnd=0
    hintText=null label=null
    packageName=io.github.styayur.lgxt_assistant_mobile autofillId=null fieldId=0 fieldName=null
  mShowInputRequested=true mLastShowInputRequested=true mShowInputFlags=0x0
  mIsInputViewShown=true mStatusIcon=0
"""


def test_current_native_privacy_snapshot_has_no_input_or_raw_dump():
    record = editor_protection_snapshot(DUMP, PACKAGE)
    assert record['imeOptions'] == 50331654 and record['inputType'] == 524417
    assert record['verified'] and record['nativeInputViewReady']
    assert record['beforeProtectedFieldInjection'] is True
    assert not any(key in record for key in ('hintText','text','raw','dump','fieldName'))


@pytest.mark.parametrize('bad', [
    DUMP.replace('0x3000006','0x2000006'),
    DUMP.replace(PACKAGE,'unrelated.synthetic.package'),
    DUMP.replace('0x80081','0x81'),
    DUMP.replace('mInputViewStarted=true','mInputViewStarted=false'),
    DUMP+DUMP,
])
def test_unpatched_or_unrelated_editor_cannot_qualify(bad):
    with pytest.raises(ValueError):editor_protection_snapshot(bad, PACKAGE)


def test_attestation_uses_fixed_typed_metadata_not_the_probe_dictionary():
    from scripts.check_android_device import editor_protection_attestation
    snapshot = editor_protection_snapshot(DUMP, PACKAGE)
    snapshot.update(rawDump='synthetic data must not be serialized', hintText='fixture-only')
    record = editor_protection_attestation(snapshot, 'a'*64, True, True)
    assert set(record) == {'package','inputType','imeOptions','verified','nativeInputViewReady',
                           'masked','beforeProtectedFieldInjection','emptyFieldsAtProbe','apkSha256'}
    assert 'rawDump' not in record and 'hintText' not in record
    for bad in (dict(snapshot, imeOptions='50331654'), dict(snapshot, inputType=True)):
        with pytest.raises(ValueError):editor_protection_attestation(bad, 'a'*64, True, True)


def test_editor_measurement_requires_empty_fields_and_masking():
    from scripts.check_android_device import editor_protection_attestation
    snapshot = editor_protection_snapshot(DUMP, PACKAGE)
    for masked, empty in [(False, True), (True, False)]:
        with pytest.raises(ValueError):
            editor_protection_attestation(snapshot, 'a'*64, masked, empty)
