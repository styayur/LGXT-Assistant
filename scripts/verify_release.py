"""Verify GitHub release bytes, including drafts resolved through gh release view."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def gh(*args):
    return json.loads(subprocess.check_output(['gh', *args], text=True, encoding='utf-8', timeout=60))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def release_record(tag):
    # REST releases/tags returns 404 for drafts; gh resolves draft IDs correctly.
    raw = gh('release', 'view', tag, '--json',
             'tagName,assets,isDraft,isPrerelease,url,targetCommitish')
    return {'tag_name': raw['tagName'], 'assets': raw['assets'], 'draft': raw['isDraft'],
            'prerelease': raw['isPrerelease'], 'html_url': raw['url'], 'target': raw['targetCommitish']}


def verify_assets(release, directory, tag, allow_draft=False, expected_commit=None, expected_certificate=None):
    directory = Path(directory)
    require(release['tag_name'] == tag, 'Wrong release tag')
    require(allow_draft or not release['draft'], 'Release is still a draft')
    require(release['prerelease'], 'This beta must not be labeled stable')
    if expected_commit:
        require(release['target'] == expected_commit, 'Release source commit differs')
    entries = {}
    for line in (directory / 'SHA256SUMS.txt').read_text(encoding='utf-8-sig').splitlines():
        digest, name = line.split('  ', 1)
        require(Path(name).name == name and len(digest) == 64, 'Invalid checksum entry')
        require(name not in entries, 'Duplicate checksum entry')
        entries[name] = digest.lower()
    files = {p.name: p for p in directory.iterdir() if p.is_file()}
    require(set(entries) == set(files) - {'SHA256SUMS.txt'}, 'Checksums omit assets')
    assets = {asset['name']: asset for asset in release['assets']}
    require(set(files) == set(assets), 'Remote asset set differs')
    for name, path in files.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(assets[name].get('digest') == 'sha256:' + digest, 'Remote bytes differ: ' + name)
        require(assets[name]['size'] == path.stat().st_size, 'Remote size differs: ' + name)
        if name in entries:
            require(entries[name] == digest, 'Checksum mismatch: ' + name)
    if tag.endswith('-android'):
        version = tag.removeprefix('v').removesuffix('-android')
        apk_name = 'LGXT-Assistant-Android-v' + version + '.apk'
        require(set(assets) == {apk_name, 'SHA256SUMS.txt', 'ANDROID-GUIDE.md',
                'THIRD-PARTY.txt', 'LICENSE', 'NOTICE.md', 'APK-IDENTITY.json'}, 'Wrong Android asset set')
        require(bool(expected_commit) and bool(expected_certificate), 'Android publication requires source and certificate pins')
        identity = json.loads((directory / 'APK-IDENTITY.json').read_text(encoding='utf-8'))
        require(identity.get('debugTestOnly') is False and identity.get('signatureVerified') is True, 'Test or unverified APK cannot be published')
        require(identity.get('fixture') is False, 'Synthetic APK cannot be published')
        require(identity.get('abis') == ['arm64-v8a', 'x86_64'] and identity.get('sdk') == ["sdkVersion:'24'", "targetSdkVersion:'36'"], 'Wrong Android SDK/ABI metadata')
        require(identity.get('sourceCommit') == expected_commit, 'APK source differs from release source')
        require(identity.get('certificateSha256') == expected_certificate.lower().replace(':', ''), 'Wrong Android signing identity')
        require(identity.get('version') == version and identity.get('versionCode') == 4
                and identity.get('package') == 'io.github.styayur.lgxt_assistant_mobile', 'Wrong Android package/version')
        require(identity.get('sha256') == entries[apk_name], 'APK identity digest differs')
    elif tag.endswith('-web'):
        require(not any(name.endswith('.apk') or 'Desktop' in name for name in assets), 'Mixed channel assets')
    else:
        require(not any(name.endswith('.apk') or 'Windows-Web' in name for name in assets), 'Mixed channel assets')
    return {'verified': True, 'tag': tag, 'url': release['html_url'],
            'source': release['target'], 'assets': sorted(assets), 'draft': release['draft']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--allow-draft', action='store_true')
    parser.add_argument('--expected-commit')
    parser.add_argument('--expected-certificate')
    args = parser.parse_args()
    result = verify_assets(release_record(args.tag), args.directory, args.tag,
                           args.allow_draft, args.expected_commit, args.expected_certificate)
    sys.stdout.write(json.dumps(result) + '\n')


if __name__ == '__main__':
    main()
