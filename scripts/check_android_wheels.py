"""Check the built wheel tags, license/version metadata and actual ELF machines."""
import argparse
import email.parser
import hashlib
import json
import struct
import zipfile
from pathlib import Path


def verify(directory):
    results=[]
    for architecture,machine in [('arm64_v8a',183),('x86_64',62)]:
        candidates=list(Path(directory).glob('*cp314-cp314-android_24_'+architecture+'.whl'))
        if len(candidates)!=1:raise ValueError('Expected one wheel for '+architecture)
        wheel=candidates[0]
        with zipfile.ZipFile(wheel) as archive:
            paths=archive.namelist()
            metadata=email.parser.Parser().parsestr(archive.read(next(n for n in paths if n.endswith('/METADATA'))).decode())
            if metadata['Version']!='13.0.0' or metadata['License-Expression']!='MIT-CMU':raise ValueError('Unexpected Pillow source identity')
            natives=[n for n in paths if n.endswith('.so')]
            if not any('_imaging.' in n for n in natives) or not any('_webp.' in n for n in natives):raise ValueError('Missing required native decoders')
            for name in natives:
                with archive.open(name) as module:header=module.read(20)
                if header[:6]!=b'\x7fELF\x02\x01' or struct.unpack('<H',header[18:20])[0]!=machine:
                    raise ValueError('Incorrect native architecture: '+name)
            with wheel.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
            results.append({'wheel':wheel.name,'sha256':digest,'elfMachine':machine,'nativeModules':natives,
                            'runtimeRequirements':metadata.get_all('Requires-Dist',[])})
    Path(directory,'ABI.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    verify(parser.parse_args().directory)
