"""Verify the single-file EXE and a fresh extraction of the actual portable ZIP."""
import json
import sys
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
with tempfile.TemporaryDirectory(prefix='lgxt-portable-smoke-') as temporary:
    extracted = Path(temporary)
    with zipfile.ZipFile(DIST / 'LGXT-Assistant-portable.zip') as archive:
        assert archive.testzip() is None, 'Portable archive CRC failure'
        archive.extractall(extracted)
    assert (extracted / '_internal/frontend/dist/desktop.html').is_file()
    assert (extracted / 'USER-GUIDE.md').is_file()
    assert (extracted / 'THIRD-PARTY.txt').is_file()
    for name, exe in (
        ('single-file', DIST / 'LGXT-Assistant.exe'),
        ('portable', extracted / 'LGXT-Assistant-portable.exe'),
    ):
        report = ROOT / 'build' / f'{name}-smoke.json'
        report.unlink(missing_ok=True)
        subprocess.run([str(exe), '--smoke-test', str(report)], cwd=ROOT,
                       check=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
        result = json.loads(report.read_text(encoding='utf-8'))
        assert result['ok'], result
        sys.stdout.write(name + ' ' + json.dumps(result, ensure_ascii=False) + '\n')
