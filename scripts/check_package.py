"""Verify the actual single-file and extracted portable release artifacts."""
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
EXTRACTED = ROOT / 'build' / 'release-verification'
EXTRACTED.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(DIST / 'LGXT-Assistant-portable.zip') as archive:
    archive.extractall(EXTRACTED)
assert (EXTRACTED / '_internal/frontend/dist/desktop.html').is_file()
assert (EXTRACTED / 'LGXT-Assistant-4.0.1-User-Guide.pdf').is_file()
for name, exe in (
    ('single-file', DIST / 'LGXT-Assistant.exe'),
    ('portable', EXTRACTED / 'LGXT-Assistant-portable.exe'),
):
    report = ROOT / 'build' / f'{name}-smoke.json'
    report.unlink(missing_ok=True)
    subprocess.run([str(exe), '--smoke-test', str(report)], cwd=ROOT,
                   check=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['ok'], result
    print(name, json.dumps(result, ensure_ascii=False))
