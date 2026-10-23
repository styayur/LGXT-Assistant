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
