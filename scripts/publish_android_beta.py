"""Publish the exact accepted signed bytes; no signing credentials are available here."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from verify_release import verify_assets, release_record


def command(*args):
    return subprocess.check_output(list(args), text=True, encoding='utf-8', timeout=180)


def gh_json(*args):
    return json.loads(command('gh', *args))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-run', required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'[0-9]+', args.build_run), 'Invalid build run')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Publication requires main')
    repo, source = os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_SHA']
    require(re.fullmatch(r'[a-f0-9]{40}', source), 'Invalid source commit')
    run = gh_json('api', f'repos/{repo}/actions/runs/{args.build_run}')
    require(run['head_repository']['full_name'] == repo and run['head_branch'] == 'main'
            and run['head_sha'] == source and run['path'] == '.github/workflows/android-apk.yml'
            and run['status'] == 'completed' and run['conclusion'] == 'success',
            'A complete successful signed main build at this exact source is required')
    jobs = gh_json('api', f'repos/{repo}/actions/runs/{args.build_run}/jobs?per_page=100')['jobs']
    require(all(any(j['name'] == name and j['conclusion'] == 'success' for j in jobs)
                for name in ('validate-request', 'build-apk', 'sign-apk', 'emulator')),
            'Build/sign/native acceptance did not all pass')
    checks = gh_json('api', f'repos/{repo}/commits/{source}/check-runs?per_page=100')['check_runs']
    for name in ('python', 'frontend', 'dependencies', 'android-dependencies',
                 'Offline equation export roundtrip', 'Android Flet renderer (synthetic browser)'):
        matching = [c for c in checks if c['name'] == name]
        require(matching and max(matching, key=lambda c: c['id'])['conclusion'] == 'success',
                'Latest source check must pass: ' + name)
    prs = gh_json('api', f'repos/{repo}/commits/{source}/pulls')
    require(any(pr['merged_at'] and pr['base']['ref'] == 'main' and pr['merge_commit_sha'] == source for pr in prs),
            'Source must be a normally merged main pull request')
    project = tomllib.loads(Path('mobile/pyproject.toml').read_text(encoding='utf-8'))
    version = project['project']['version']
    tag = f'v{version}-android'
    apk = f'LGXT-Assistant-Android-v{version}.apk'
    pin = json.loads(Path('packaging/android/signing-identity.json').read_text())['certificateSha256']
    assets = args.directory
    expected = {apk, 'APK-IDENTITY.json', 'SHA256SUMS.txt', 'LICENSE', 'NOTICE.md', 'THIRD-PARTY.txt', 'ANDROID-GUIDE.md'}
    require({p.name for p in assets.iterdir()} == expected, 'Unexpected signed artifact asset set')
    identity = json.loads((assets/'APK-IDENTITY.json').read_text())
    require(identity['sourceCommit'] == source and identity['certificateSha256'] == pin, 'Artifact provenance differs')

    def verify_identity(directory, output):
        command(sys.executable, 'scripts/check_android_metadata.py', '--apk', str(directory/apk),
                '--expected-certificate', pin, '--source-commit', source, '--output', str(output))
        require(json.loads(output.read_text()) == identity, 'Independent SDK verification differs')

    work = Path('publication-evidence')
    work.mkdir(exist_ok=True)
    verify_identity(assets, work/'artifact-identity.json')
    existing = subprocess.run(['gh', 'release', 'view', tag, '--json', 'isDraft,targetCommitish'],
                              capture_output=True, text=True, timeout=60)
    if existing.returncode == 0:
        record = json.loads(existing.stdout)
        require(record['targetCommitish'] == source, 'Existing release points to another source')
    else:
        require('release not found' in existing.stderr.lower() or '404' in existing.stderr, 'Release lookup failed')
        command('gh', 'release', 'create', tag, '--target', source, '--draft', '--prerelease',
                '--title', f'Android {version} Beta', '--notes-file', f'docs/releases/v{version}-android.md')
    record = release_record(tag)
    remote = {a['name']: a for a in record['assets']}
    require(set(remote) <= expected, 'Existing release contains unexpected assets')
    for path in sorted(assets.iterdir()):
        if path.name in remote:
            digest = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
            require(remote[path.name].get('digest') == digest, 'Existing asset differs; never overwrite')
        else:
            require(record['draft'], 'Cannot add assets to a published release')
            command('gh', 'release', 'upload', tag, str(path))
    downloaded = work/'downloaded-before-publication'
    downloaded.mkdir(exist_ok=True)
    command('gh', 'release', 'download', tag, '--dir', str(downloaded), '--clobber')
    verify_assets(release_record(tag), downloaded, tag, True, source, pin)
    verify_identity(downloaded, work/'downloaded-identity.json')
    if record['draft']:
        command('gh', 'release', 'edit', tag, '--draft=false', '--prerelease', '--latest=false')
    public = work/'downloaded-published'
    public.mkdir(exist_ok=True)
    command('gh', 'release', 'download', tag, '--dir', str(public), '--clobber')
    result = verify_assets(release_record(tag), public, tag, False, source, pin)
    verify_identity(public, work/'published-identity.json')
    remote_tag = gh_json('api', f'repos/{repo}/git/ref/tags/{tag}')['object']
    if remote_tag['type'] == 'tag':
        remote_tag = gh_json('api', f'repos/{repo}/git/tags/{remote_tag["sha"]}')['object']
    require(remote_tag['type'] == 'commit' and remote_tag['sha'] == source, 'Tag source differs')
    result.update(buildRun=args.build_run, certificateSha256=pin,
                  hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(public.iterdir())})
    (work/'PUBLICATION.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
