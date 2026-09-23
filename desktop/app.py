"""WebView2 desktop entry point with a retained Tk compatibility option."""
import sys
from pathlib import Path


class StartupError(RuntimeError):
    """An actionable error that can be shown without loading the web frontend."""


def frontend_url(base):
    index = Path(base) / 'frontend' / 'dist' / 'desktop.html'
    if not index.exists():
        raise StartupError('界面文件不完整。请重新下载完整的单文件版，或完整解压便携版后再打开。源码运行需先构建 frontend。')
    # Separate generated entry contains a static desktop marker before JS executes.
    return str(index)


def main():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    if '--smoke-test' in sys.argv:
        from .diagnostics import smoke_test
        smoke_test(base)
        return
    index = frontend_url(base)
    try:
        import webview
        from .bridge import Bridge
    except ImportError as exc:
        raise StartupError('桌面组件未安装完整。普通用户请下载 Release 中的 Windows EXE；源码用户请安装 requirements.txt。') from exc
    bridge = Bridge()
    window = webview.create_window('LGXT Assistant · 理工学堂助手', index, js_api=bridge,
                                  width=1440, height=900, min_size=(860, 600),
                                  background_color='#191a1d', text_select=True)
    bridge._window = window
    webview.start(debug=bool(bridge._store.settings()['debug']),
                  storage_path=str(bridge._store.directory / 'webview'))
