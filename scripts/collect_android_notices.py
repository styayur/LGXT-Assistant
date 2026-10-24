"""Extract notices from the actual APK, retaining Python and Flutter attribution."""
import argparse
import email.parser
import gzip
import io
import zipfile
from pathlib import Path


def collect(apk, output):
    sections=['LGXT Assistant Android third-party notices\nApplication: AGPL-3.0-only.\n'
              'Inventory extracted from this APK, not inferred from desktop dependencies.\n']
    with zipfile.ZipFile(apk) as package:
        with zipfile.ZipFile(io.BytesIO(package.read('assets/sitepackages.zip'))) as libraries:
            names=libraries.namelist()
            for metadata_path in sorted(n for n in names if n.endswith('.dist-info/METADATA')):
                metadata=email.parser.Parser().parsestr(libraries.read(metadata_path).decode('utf-8'))
                prefix=metadata_path.rsplit('/',1)[0]+'/'
                sections.append('\n\n'+metadata['Name']+' '+metadata['Version']+'\n'+
                                'License: '+(metadata.get('License-Expression') or metadata.get('License') or 'see accompanying license texts')+'\n')
                license_paths=[n for n in names if n.startswith(prefix) and
                               any(word in n.rsplit('/',1)[-1].lower() for word in ('license','copying','notice','patents'))]
                for name in sorted(license_paths):
                    sections.append('\n'+name+'\n'+libraries.read(name).decode('utf-8',errors='replace'))
                if not license_paths:
                    if metadata['Name'].lower()=='flet':
                        sections.append(Path('packaging/android/licenses/FLET-LICENSE').read_text(encoding='utf-8'))
                    else:raise ValueError('Missing bundled license text: '+metadata['Name'])
        sections.append('\n\nFlutter/Dart and bundled assets: upstream NOTICES\n'+
                        gzip.decompress(package.read('assets/flutter_assets/NOTICES.Z')).decode('utf-8'))
    Path(output).write_text('\n'.join(sections),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apk',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();collect(args.apk,args.output)
