"""Validate APK identity. Temporary debug certificates require an explicit test flag."""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import zipfile
import sys
from pathlib import Path


def validate_badging(info):
    lines = info.splitlines()
    for expected in ("name='io.github.styayur.lgxt_assistant_mobile'", "versionName='3.3.0'", "versionCode='4'"):
        if expected not in lines[0]: raise ValueError('Incorrect Android metadata: ' + expected)
    if "sdkVersion:'24'" not in lines or "targetSdkVersion:'36'" not in lines:
        raise ValueError('Android SDK levels must be min 24 / target 36')
    if 'application-debuggable' in lines:
        raise ValueError('Debuggable application cannot be released')


def app_payload(archive):
    raw = archive.read('assets/app.zip')
    with zipfile.ZipFile(io.BytesIO(raw)) as app:
        names = app.namelist()
        if 'main.pyc' not in names or len(names) != len(set(names)):
            raise ValueError('Missing or malformed application entry')
        if any(Path(n).stem in ('app_under_test', 'android_fixture_entry', 'android_image_checks') for n in names):
            raise ValueError('Synthetic fixture APK cannot be released')
    return hashlib.sha256(raw).hexdigest()


def certificate_fingerprint(signature):
    # Recent SDK tools include SDK-range labels before the signer number.
    values=re.findall(r'^(?:V[1-4] )?Signer[^\r\n]* certificate SHA-256 digest:\s*([a-f0-9:]+)\s*$',signature,re.IGNORECASE|re.MULTILINE)
    fingerprints={value.replace(':','').lower() for value in values}
    if len(fingerprints)!=1 or any(not re.fullmatch('[a-f0-9]{64}',value) for value in fingerprints):
        raise ValueError('One verifiable APK signing certificate is required: '+signature)
    return fingerprints.pop()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apk',required=True)
    parser.add_argument('--expected-certificate')
    parser.add_argument('--allow-debug-for-testing',action='store_true')
    parser.add_argument('--output',required=True)
    parser.add_argument('--source-commit')
    args=parser.parse_args()
    tools=Path(os.environ['ANDROID_HOME'])/'build-tools'/'36.0.0'
    suffix='.bat' if os.name=='nt' else ''
    signature=subprocess.check_output([str(tools/('apksigner'+suffix)),'verify','--verbose','--print-certs',args.apk],text=True)
    fingerprint=certificate_fingerprint(signature)
    if args.expected_certificate:
        if fingerprint!=args.expected_certificate.lower().replace(':',''):raise ValueError('Unexpected signing identity')
    elif not args.allow_debug_for_testing:raise ValueError('A pinned release signing fingerprint is required')
    if not args.allow_debug_for_testing and not args.source_commit:raise ValueError('Release source commit is required')
    if 'CN=Android Debug' in signature and not args.allow_debug_for_testing:raise ValueError('Debug signature cannot be published')
    aapt=tools/('aapt.exe' if os.name=='nt' else 'aapt')
    info=subprocess.check_output([str(aapt),'dump','badging',args.apk],text=True)
    validate_badging(info)
    with zipfile.ZipFile(args.apk) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or any('..' in Path(n).parts for n in names):raise ValueError('Malformed APK archive')
        abis=sorted({name.split('/')[1] for name in names if name.startswith('lib/')})
        if abis!=['arm64-v8a','x86_64']:raise ValueError('Unexpected APK architectures: '+str(abis))
        if archive.testzip():raise ValueError('APK ZIP integrity failure')
        payload_digest=app_payload(archive)
    with open(args.apk,'rb') as source:apk_digest=hashlib.file_digest(source,'sha256').hexdigest()
    result={'apk':Path(args.apk).name,'sha256':apk_digest,
            'certificateSha256':fingerprint,'debugTestOnly':args.allow_debug_for_testing,
            'package':'io.github.styayur.lgxt_assistant_mobile','version':'3.3.0','versionCode':4,'abis':abis,
            'signatureVerified':True,'fixture':False,'appPayloadSha256':payload_digest,
            'sdk':[line for line in info.splitlines() if line.startswith(('sdkVersion:','targetSdkVersion:'))]}
    if args.source_commit:
        if not re.fullmatch('[a-fA-F0-9]{40}',args.source_commit):raise ValueError('Invalid source commit')
        result['sourceCommit']=args.source_commit.lower()
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    sys.stdout.write(json.dumps(result)+'\n')


if __name__=='__main__':main()
