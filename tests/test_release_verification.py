"""Release metadata guards must fail closed without touching GitHub."""
import hashlib
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('verify_release',Path(__file__).resolve().parents[1]/'scripts/verify_release.py')
verification=importlib.util.module_from_spec(spec);spec.loader.exec_module(verification)


def fixture(tmp_path):
    asset=tmp_path/'LGXT-Assistant-Windows-Web-v4.2.0.exe';asset.write_bytes(b'synthetic executable fixture, never launched')
    digest=hashlib.sha256(asset.read_bytes()).hexdigest()
    (tmp_path/'SHA256SUMS.txt').write_text(digest+'  '+asset.name+'\n')
    assets=[{'name':p.name,'size':p.stat().st_size,'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()} for p in tmp_path.iterdir()]
    return {'tag_name':'v4.2.0-web','draft':True,'prerelease':True,'target':'verified-source','html_url':'https://example.invalid/release','assets':assets}


def test_draft_lookup_uses_supported_cli(monkeypatch,tmp_path):
    r=fixture(tmp_path);calls=[]
    def fake(*args):
        calls.append(args)
        return {'tagName':r['tag_name'],'assets':r['assets'],'isDraft':True,'isPrerelease':True,'url':r['html_url'],'targetCommitish':r['target']}
    monkeypatch.setattr(verification,'gh',fake)
    value=verification.release_record('v4.2.0-web')
    assert calls[0][:2]==('release','view')
    assert verification.verify_assets(value,tmp_path,'v4.2.0-web',True,'verified-source')['verified']
    with pytest.raises(ValueError):verification.verify_assets(value,tmp_path,'v4.2.0-web',False)


@pytest.mark.parametrize('change',['bytes','missing','source','channel'])
def test_uploaded_release_guards(tmp_path,change):
    r=fixture(tmp_path)
    if change=='bytes':(tmp_path/'LGXT-Assistant-Windows-Web-v4.2.0.exe').write_bytes(b'tampered')
    if change=='missing':r['assets'].pop()
    if change=='source':r['target']='unexpected'
    if change=='channel':r['assets'].append({'name':'Android.apk','size':1,'digest':'sha256:x'})
    with pytest.raises(ValueError):verification.verify_assets(r,tmp_path,'v4.2.0-web',True,'verified-source')


@pytest.mark.parametrize('change',['valid','debug','certificate','source','mixed'])
def test_android_publication_identity_and_channel(tmp_path,change):
    import json
    apk='LGXT-Assistant-Android-v3.3.0.apk'
    (tmp_path/apk).write_bytes(b'fixture only: cryptographic verification is a separate apksigner gate')
    for name in ('ANDROID-GUIDE.md','THIRD-PARTY.txt','LICENSE','NOTICE.md'):(tmp_path/name).write_text('fixture')
    identity={'debugTestOnly':change=='debug','signatureVerified':True,'sourceCommit':'a'*40,
              'certificateSha256':'b'*64,'version':'3.3.0','versionCode':4,
              'package':'io.github.styayur.lgxt_assistant_mobile','sha256':hashlib.sha256((tmp_path/apk).read_bytes()).hexdigest()}
    if change=='source':identity['sourceCommit']='c'*40
    if change=='certificate':identity['certificateSha256']='c'*64
    (tmp_path/'APK-IDENTITY.json').write_text(json.dumps(identity))
    if change=='mixed':(tmp_path/'Windows.exe').write_bytes(b'fixture')
    (tmp_path/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in tmp_path.iterdir()))
    assets=[{'name':p.name,'size':p.stat().st_size,'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()} for p in tmp_path.iterdir()]
    release={'tag_name':'v3.3.0-android','draft':True,'prerelease':True,'target':'a'*40,'html_url':'fixture','assets':assets}
    if change=='valid':
        assert verification.verify_assets(release,tmp_path,'v3.3.0-android',True,'a'*40,'b'*64)['verified']
    else:
        with pytest.raises(ValueError):verification.verify_assets(release,tmp_path,'v3.3.0-android',True,'a'*40,'b'*64)
