# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed, one-field privacy backport on the exact reviewed Flutter SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

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


def verify_selected_sdk(sdk, meta):
    from importlib.metadata import version
    from flet_cli.commands.flutter_base import BaseFlutterCommand
    if version('flet-cli') != '1.1.2':
        raise ValueError('Refusing a different Flet SDK selector')
    from packaging.version import Version
    selector = SimpleNamespace(required_flutter_version=Version(meta['flutterVersion']))
    result = {}
    for executable in ('flutter', 'dart'):
        selected = BaseFlutterCommand.find_flutter_batch(selector, executable)
        # setup-flutter can expose the SDK's own cached Dart binary on PATH.
        # It belongs to this SDK, unlike an unrelated system Dart installation.
        allowed = {(sdk/'bin'/executable).resolve(),
                   (sdk/'bin'/(executable+'.bat')).resolve()}
        if executable == 'dart':
            allowed |= {(sdk/'bin/cache/dart-sdk/bin/dart').resolve(),
                        (sdk/'bin/cache/dart-sdk/bin/dart.exe').resolve()}
        if not selected or Path(selected).resolve() not in allowed:
            raise ValueError('Flet '+executable+' selector does not match the reviewed SDK: '+str(selected))
        result[executable+'WithinReviewedSdk'] = True
    return result



def built_project_evidence(project, apk, sdk):
    properties = (project/'android/local.properties').read_text().splitlines()
    roots = [line.split('=', 1)[1] for line in properties if line.startswith('flutter.sdk=')]
    if len(roots) != 1 or Path(roots[0]).resolve() != sdk:
        raise ValueError('Generated Android project uses a different Flutter SDK')
    lock = (project/'pubspec.lock').read_bytes()
    policy = ROOT/'packaging/android/kotlin-official-repository.init.gradle'
    return {'generatedProjectSdkMatchesRequested': True,
            'apkSha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
            'pubspecLockSha256': hashlib.sha256(lock).hexdigest(),
            'kotlinRepositoryPolicySha256': hashlib.sha256(policy.read_bytes()).hexdigest(),
            'buildWorkflowSha256': hashlib.sha256((ROOT/'.github/workflows/android-apk.yml').read_bytes()).hexdigest(),
            'sourceCommit': subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--flutter-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--built-project', type=Path)
    parser.add_argument('--apk', type=Path)
    args = parser.parse_args()
    if bool(args.built_project) != bool(args.apk) or (args.built_project and not args.verify_only):
        parser.error('--built-project and --apk require each other and --verify-only')
    meta = json.loads(META.read_text())
    sdk = args.flutter_root.resolve()
    selected_tools = verify_selected_sdk(sdk, meta)
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
    if args.verify_only and hashlib.sha256(source).hexdigest() != meta['patchedSha256']:
        raise ValueError('Flet build SDK does not contain the reviewed privacy backport')
    result, already = patched_bytes(source, meta)
    if not args.verify_only:
        target.write_bytes(result)
    record = dict(meta, alreadyApplied=already, applied=True,
                  actualSha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  pythonAppFlagsChanged=False, autofillGroupRetained=True,
                  fletSelectedSdkMatchesRequested=True, selectedTools=selected_tools, verifyOnly=args.verify_only)
    if args.built_project:
        record['buildEvidence'] = built_project_evidence(args.built_project, args.apk, sdk)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    sys.stdout.write(json.dumps({'applied':True,'alreadyApplied':already,
                                'actualSha256':record['actualSha256']})+'\n')


if __name__ == '__main__':
    main()
