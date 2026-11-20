# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed, one-field privacy backport on the exact reviewed Flutter SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
META = ROOT/'packaging/flutter/autofill-backport.json'
ANCHOR = b'         autofillConfiguration: currentClientConfiguration.autofillConfiguration,\n'
FORWARD = b'         enableIMEPersonalizedLearning: currentClientConfiguration.enableIMEPersonalizedLearning,\n'


def patched_bytes(source, meta):
    before = hashlib.sha256(source).hexdigest()
    if before == meta['patchedSha256']:
        return source, True
    if before != meta['originalSha256'] or source.count(ANCHOR) != 1:
        raise ValueError('Refusing an unreviewed Flutter autofill source baseline')
    result = source.replace(ANCHOR, ANCHOR+FORWARD)
    if hashlib.sha256(result).hexdigest() != meta['patchedSha256']:
        raise ValueError('Flutter autofill backport output hash mismatch')
    return result, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--flutter-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    meta = json.loads(META.read_text())
    sdk = args.flutter_root.resolve()
    head = subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip()
    if head != meta['flutterCommit']:
        raise ValueError('Refusing a different Flutter SDK revision')
    changed = subprocess.check_output(['git','-C',str(sdk),'diff','--name-only','HEAD',
                                       '--','packages/flutter/lib'],text=True).splitlines()
    if set(changed)-{meta['path']}:
        raise ValueError('Refusing unrelated Flutter framework modifications')
    if (sdk/'LICENSE').read_bytes() != (ROOT/'packaging/flutter/LICENSE.flutter').read_bytes():
        raise ValueError('Flutter license differs from the reviewed SDK license')
    target = sdk/meta['path']
    source = target.read_bytes()
    result, already = patched_bytes(source, meta)
    target.write_bytes(result)
    record = dict(meta, alreadyApplied=already, applied=True,
                  actualSha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  pythonAppFlagsChanged=False, autofillGroupRetained=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    sys.stdout.write(json.dumps({'applied':True,'alreadyApplied':already,
                                'actualSha256':record['actualSha256']})+'\n')


if __name__ == '__main__':
    main()
