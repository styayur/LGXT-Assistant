"""Small on-device decoder acceptance suite. Synthetic inputs; no network."""
import io
import json
import sys
import struct
import tempfile
import zlib


def run():
    import PIL
    from PIL import Image, features
    try:
        import lgxt_transport as transport
        from local_store import LocalStore
    except ImportError:
        from mobile.src import lgxt_transport as transport
        from mobile.src.local_store import LocalStore
    results = []
    def check(name, condition):
        if not condition: raise AssertionError(name)
        results.append(name)
    def rejects(name, data):
        try: transport.validate_image(data)
        except ValueError: results.append(name)
        else: raise AssertionError(name)
    samples = {}
    for fmt, mime in [('PNG','image/png'),('JPEG','image/jpeg'),('WEBP','image/webp')]:
        with Image.new('RGB',(32,24),'white') as image:
            output=io.BytesIO();image.save(output,fmt);samples[fmt]=output.getvalue()
        check(fmt+' decode',transport.validate_image(samples[fmt])==mime)
    rejects('SVG rejected', b'<svg xmlns="http://www.w3.org/2000/svg"/>')
    rejects('empty rejected', b'')
    rejects('invalid rejected', b'not an image')
    rejects('oversize bytes rejected', b'x'*(transport.MAX_IMAGE_BYTES+1))
    rejects('truncated JPEG rejected', samples['JPEG'][:-30])
    rejects('corrupt PNG rejected', samples['PNG'][:35])
    # Tiny malicious PNG header claims ten billion pixels; no huge allocation.
    bomb=bytearray(samples['PNG']);bomb[16:24]=struct.pack('>II',100000,100000)
    bomb[29:33]=struct.pack('>I',zlib.crc32(bomb[12:29]))
    rejects('decompression bomb rejected',bomb)
    large=bytearray(samples['PNG']);large[16:24]=struct.pack('>II',6000,4000)
    large[29:33]=struct.pack('>I',zlib.crc32(large[12:29]))
    rejects('20 MP limit rejected',large)
    for fmt in ('PNG','WEBP'):
        with Image.new('RGB',(16,16),'red') as first, Image.new('RGB',(16,16),'blue') as second:
            out=io.BytesIO();first.save(out,fmt,save_all=True,append_images=[second],duration=50,loop=0)
        rejects(fmt+' animation rejected',out.getvalue())
    for _ in range(30):
        for data in samples.values(): transport.validate_image(data)
    check('30 repeated decode cycles complete',True)
    client=transport.APIClient()
    client.session.post=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network must not run'))
    check('HTTP authentication blocked',not client.login('fixture','fixture')[0])
    with tempfile.TemporaryDirectory() as directory:
        store=LocalStore(directory);store.set('note','synthetic')
        check('notes survive restart',LocalStore(directory).get('note')=='synthetic')
        try:store.set('lgxt.pass','fixture')
        except ValueError:results.append('password persistence rejected')
        else:raise AssertionError('password persisted')
        store.path.write_text('{broken',encoding='utf-8')
        check('corrupt notes fail closed',not LocalStore(directory).writable)
    return {'pillow':PIL.__version__,'jpeg':features.version('jpg'),
            'webp':features.version('webp'),'passed':results,'count':len(results)}


if __name__=='__main__':
    sys.stdout.write(json.dumps(run(),ensure_ascii=False)+'\n')
