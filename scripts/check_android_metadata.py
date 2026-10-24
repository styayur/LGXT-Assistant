"""Validate APK identity. Temporary debug certificates require an explicit test flag."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import zipfile
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apk',required=True)
    parser.add_argument('--expected-certificate')
    parser.add_argument('--allow-debug-for-testing',action='store_true')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    sdk=Path(os.environ['ANDROID_HOME'])/'build-tools'
    tools=sorted(sdk.iterdir(),key=lambda p:tuple(map(int,re.findall(r'\d+',p.name))))[-1]
    suffix='.bat' if os.name=='nt' else ''
    signature=subprocess.check_output([str(tools/('apksigner'+suffix)),'verify','--verbose','--print-certs',args.apk],text=True)
    cert=re.search(r'Signer #1 certificate SHA-256 digest: ([a-f0-9]{64})',signature)
    if not cert:raise ValueError('APK signing certificate not found')
    if args.expected_certificate:
        if cert[1]!=args.expected_certificate.lower().replace(':',''):raise ValueError('Unexpected signing identity')
    elif not args.allow_debug_for_testing:raise ValueError('A pinned release signing fingerprint is required')
    if 'CN=Android Debug' in signature and not args.allow_debug_for_testing:raise ValueError('Debug signature cannot be published')
    aapt=tools/('aapt.exe' if os.name=='nt' else 'aapt')
    info=subprocess.check_output([str(aapt),'dump','badging',args.apk],text=True)
    for expected in ("name='io.github.styayur.lgxt_assistant_mobile'","versionName='3.3.0'","versionCode='4'"):
        if expected not in info.splitlines()[0]:raise ValueError('Incorrect Android metadata: '+expected)
    with zipfile.ZipFile(args.apk) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or any('..' in Path(n).parts for n in names):raise ValueError('Malformed APK archive')
        abis=sorted({name.split('/')[1] for name in names if name.startswith('lib/')})
        if abis!=['arm64-v8a','x86_64']:raise ValueError('Unexpected APK architectures: '+str(abis))
        if archive.testzip():raise ValueError('APK ZIP integrity failure')
    result={'apk':Path(args.apk).name,'sha256':hashlib.file_digest(open(args.apk,'rb'),'sha256').hexdigest(),
            'certificateSha256':cert[1],'debugTestOnly':args.allow_debug_for_testing,
            'package':'io.github.styayur.lgxt_assistant_mobile','version':'3.3.0','versionCode':4,'abis':abis,
            'signatureVerified':True,'sdk':[line for line in info.splitlines() if line.startswith(('sdkVersion:','targetSdkVersion:'))]}
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    sys.stdout.write(json.dumps(result)+'\n')


if __name__=='__main__':main()
