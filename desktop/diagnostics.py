"""An isolated native startup check, usable from the packaged executable."""
import json
import sys
import tempfile
import time
from pathlib import Path


def smoke_test(base):
    import webview
    import config
    from .bridge import Bridge
    result = {'ok': False}
    index = sys.argv.index('--smoke-test') if '--smoke-test' in sys.argv else -1
    report = Path(sys.argv[index + 1]) if index >= 0 and len(sys.argv) > index + 1 else Path('build/native-smoke.json')
    with tempfile.TemporaryDirectory(prefix='lgxt-native-') as temp:
        config.get_saved_username = lambda: None
        bridge = Bridge(Path(temp) / 'state', legacy_settings=config.Settings(str(Path(temp) / 'config.ini')))
        bridge._key = lambda _: ''
        window = webview.create_window('LGXT startup test', str(Path(base) / 'frontend/dist/desktop.html'),
                                       js_api=bridge, hidden=True, width=1280, height=720)
        bridge._window = window

        def check():
            ready = False
            try:
                deadline = time.monotonic() + 35
                while time.monotonic() < deadline:
                    ready = window.evaluate_js("Boolean(document.querySelector('.app-shell'))")
                    if ready:
                        break
                    time.sleep(.2)
                result['ok'] = bool(ready)
                result['title'] = window.evaluate_js('document.title')
                result['preview'] = window.evaluate_js("Boolean(document.querySelector('.preview-badge'))")
                result['theme'] = window.evaluate_js('document.documentElement.dataset.theme')
                window.evaluate_js('window.pywebview.api.bootstrap()', callback=lambda value: result.update(bootstrap=True))
                time.sleep(.5)
            except Exception as exc:
                result['error'] = str(exc)
            finally:
                window.destroy()
        webview.start(check, storage_path=str(Path(temp) / 'webview'))
    result['ok'] = bool(result['ok'] and not result.get('preview', True) and result.get('bootstrap'))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if sys.stdout:
        print(json.dumps(result, ensure_ascii=False))
    if not result['ok']:
        raise SystemExit(1)
