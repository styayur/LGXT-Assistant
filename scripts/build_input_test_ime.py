# SPDX-License-Identifier: AGPL-3.0-only
"""Compile an original, network-free, testOnly IME on a disposable CI runner."""
import argparse
import os
import pathlib
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='build/android/input-ime')
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise ValueError('This helper is built only on a disposable remote CI runner')
    root = pathlib.Path(__file__).resolve().parents[1]
    source = root / 'scripts/input_fidelity'
    output = pathlib.Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    sdk = pathlib.Path(os.environ['ANDROID_HOME'])
    tools = sdk / 'build-tools/36.0.0'
    android = sdk / 'platforms/android-35/android.jar'
    classes, dex = output / 'classes', output / 'dex'
    classes.mkdir(exist_ok=True)
    dex.mkdir(exist_ok=True)
    def run(*command):
        subprocess.run([str(part) for part in command], check=True, timeout=120)
    run(tools/'aapt2', 'compile', '--dir', source/'res', '-o', output/'resources.zip')
    run(tools/'aapt2', 'link', '-o', output/'unsigned.apk', '-I', android,
        '--manifest', source/'AndroidManifest.xml', output/'resources.zip',
        '--min-sdk-version', '24', '--target-sdk-version', '35')
    run('javac', '-source', '8', '-target', '8', '-classpath', android,
        '-d', classes, source/'FidelityIme.java')
    run(tools/'d8', '--lib', android, '--min-api', '24', '--output', dex,
        *sorted(classes.rglob('*.class')))
    run('jar', 'uf', output/'unsigned.apk', '-C', dex, 'classes.dex')
    run(tools/'zipalign', '-f', '4', output/'unsigned.apk', output/'aligned.apk')
    # An ephemeral, public-password test key is never a release identity and
    # neither the key nor its directory is included in workflow artifacts.
    run('keytool', '-genkeypair', '-noprompt', '-keystore', output/'test-only.keystore',
        '-storepass', 'android', '-keypass', 'android', '-alias', 'input-fidelity',
        '-dname', 'CN=LGXT Synthetic Input Test Only', '-keyalg', 'RSA',
        '-keysize', '2048', '-validity', '2')
    run(tools/'apksigner', 'sign', '--ks', output/'test-only.keystore',
        '--ks-pass', 'pass:android', '--key-pass', 'pass:android',
        '--out', output/'LGXT-test-ime.apk', output/'aligned.apk')
    run(tools/'apksigner', 'verify', output/'LGXT-test-ime.apk')


if __name__ == '__main__':
    main()
