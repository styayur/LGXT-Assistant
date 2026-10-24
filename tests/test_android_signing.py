"""Signing gates reject absent credentials, wrong identities and synthetic payloads."""
import base64
import io
import zipfile
import pytest
from scripts.sign_android_apk import signing_configuration
from scripts.check_android_metadata import validate_badging, app_payload


def test_signing_credentials_fail_closed():
    identity={'certificateSha256':'a'*64}
    env={'ANDROID_CERTIFICATE_SHA256':'a'*64,'ANDROID_KEYSTORE_PASSWORD':'synthetic fixture only',
         'ANDROID_KEYSTORE_BASE64':base64.b64encode(b'fixture'*300).decode()}
    assert signing_configuration(env,identity)[0]=='a'*64
    for key in env:
        incomplete=dict(env);incomplete.pop(key)
        with pytest.raises(ValueError):signing_configuration(incomplete,identity)
    with pytest.raises(ValueError):signing_configuration(dict(env,ANDROID_CERTIFICATE_SHA256='b'*64),identity)
    with pytest.raises(ValueError):signing_configuration(dict(env,ANDROID_KEYSTORE_BASE64='invalid!'),identity)
    with pytest.raises(ValueError):signing_configuration(dict(env,GITHUB_ACTIONS='true',GITHUB_REF='refs/heads/unreviewed'),identity)


def test_manifest_and_fixture_boundary():
    info="package: name='io.github.styayur.lgxt_assistant_mobile' versionCode='4' versionName='3.3.0'\nsdkVersion:'24'\ntargetSdkVersion:'36'"
    validate_badging(info)
    for bad in [info.replace("sdkVersion:'24'","sdkVersion:'23'"),info.replace("versionCode='4'","versionCode='3'"),info+'\napplication-debuggable']:
        with pytest.raises(ValueError):validate_badging(bad)
    for fixture in [False,True]:
        payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w') as app:
            app.writestr('main.pyc',b'synthetic compiled entry')
            if fixture:app.writestr('app_under_test.pyc',b'synthetic fixture')
        apk=io.BytesIO()
        with zipfile.ZipFile(apk,'w') as archive:archive.writestr('assets/app.zip',payload.getvalue())
        with zipfile.ZipFile(apk) as archive:
            if fixture:
                with pytest.raises(ValueError):app_payload(archive)
            else:assert len(app_payload(archive))==64
