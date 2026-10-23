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


def verify_assets(release, directory, tag, allow_draft=False, expected_commit=None):
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
    if tag.endswith('-web'):
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
    args = parser.parse_args()
    result = verify_assets(release_record(args.tag), args.directory, args.tag,
                           args.allow_draft, args.expected_commit)
    sys.stdout.write(json.dumps(result) + '\n')


if __name__ == '__main__':
    main()
