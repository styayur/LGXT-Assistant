"""Verify uploaded GitHub release bytes against an exact local staging directory."""
import argparse
import hashlib
import json
import sys
import subprocess
from pathlib import Path


def gh(*args):
    return json.loads(subprocess.check_output(['gh',*args],text=True,encoding='utf-8'))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tag',required=True)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--allow-draft',action='store_true')
    args=parser.parse_args()
    repo=gh('repo','view','--json','nameWithOwner')['nameWithOwner']
    release=gh('api',f'repos/{repo}/releases/tags/{args.tag}')
    assert release['tag_name']==args.tag
    assert args.allow_draft or not release['draft'],'Release is still a draft'
    assert release['prerelease'],'This candidate must not be labeled stable'
    sums=args.directory/'SHA256SUMS.txt'
    entries={}
    for line in sums.read_text(encoding='utf-8-sig').splitlines():
        digest,name=line.split('  ',1)
        assert Path(name).name==name and len(digest)==64
        entries[name]=digest.lower()
    files={p.name:p for p in args.directory.iterdir() if p.is_file()}
    assert set(entries)==set(files)-{'SHA256SUMS.txt'},'Checksums omit assets'
    assets={asset['name']:asset for asset in release['assets']}
    assert set(files)==set(assets),'Remote asset set differs'
    for name,path in files.items():
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert assets[name].get('digest')=='sha256:'+digest, f'Remote bytes differ: {name}'
        assert assets[name]['size']==path.stat().st_size
        if name in entries:assert entries[name]==digest
    if args.tag.endswith('-web'):
        assert not any(name.endswith('.apk') or 'Desktop' in name for name in assets)
    sys.stdout.write(json.dumps({'verified':True,'tag':args.tag,'url':release['html_url'],'assets':sorted(assets),'draft':release['draft']}))

if __name__=='__main__':main()
