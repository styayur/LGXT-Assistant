"""Sign an ordinary APK with the enduring identity; secrets only enter via env."""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def signing_configuration(environ, identity):
    if environ.get('GITHUB_ACTIONS') == 'true' and environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('Release signing is restricted to main')
    expected = environ.get('ANDROID_CERTIFICATE_SHA256', '')
    if not re.fullmatch('[a-f0-9]{64}', expected) or expected != identity['certificateSha256']:
        raise ValueError('Protected and source-pinned signing fingerprints must agree')
    if not environ.get('ANDROID_KEYSTORE_PASSWORD'):
        raise ValueError('Protected signing password is required')
    try:
        keystore = base64.b64decode(environ.get('ANDROID_KEYSTORE_BASE64', ''), validate=True)
    except ValueError:
        raise ValueError('Protected keystore is invalid') from None
    if not 1024 <= len(keystore) <= 64 * 1024:
        raise ValueError('Protected keystore is missing or invalid')
    return expected, keystore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    identity = json.loads((root/'packaging/android/signing-identity.json').read_text())
    expected, keystore = signing_configuration(os.environ, identity)
    out = Path(args.directory); out.mkdir(parents=True, exist_ok=True)
    apk = out/'LGXT-Assistant-Android-v3.3.0.apk'
    if apk.exists(): raise ValueError('Do not overwrite a signed artifact')
    tools = Path(os.environ['ANDROID_HOME'])/'build-tools'/'36.0.0'
    suffix = '.bat' if os.name == 'nt' else ''
    verifier = [sys.executable, str(root/'scripts/check_android_metadata.py')]
    with tempfile.TemporaryDirectory(prefix='lgxt-sign-', dir=os.environ.get('RUNNER_TEMP')) as private:
        private = Path(private)
        input_identity = private/'input.json'
        subprocess.run(verifier+['--apk', args.input, '--allow-debug-for-testing',
                       '--source-commit', args.source_commit, '--output', str(input_identity)], check=True)
        keyfile = private/'identity.p12'; keyfile.write_bytes(keystore); keyfile.chmod(0o600)
        subprocess.run([str(tools/('apksigner'+suffix)), 'sign', '--ks', str(keyfile),
                       '--ks-type', 'PKCS12', '--ks-key-alias', identity['alias'],
                       '--ks-pass', 'env:ANDROID_KEYSTORE_PASSWORD', '--key-pass', 'env:ANDROID_KEYSTORE_PASSWORD',
                       '--debuggable-apk-permitted', 'false', '--out', str(apk), args.input], check=True)
        output_identity = out/'APK-IDENTITY.json'
        subprocess.run(verifier+['--apk', str(apk), '--expected-certificate', expected,
                       '--source-commit', args.source_commit, '--output', str(output_identity)], check=True)
        before = json.loads(input_identity.read_text())
        after = json.loads(output_identity.read_text())
        if before['appPayloadSha256'] != after['appPayloadSha256']:
            raise ValueError('Signing changed the application payload')
    apk.with_suffix('.apk.idsig').unlink(missing_ok=True)


if __name__ == '__main__': main()
