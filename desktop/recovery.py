"""Native recovery is available even when the HTML or WebView cannot start."""
import os
import subprocess
import sys
import traceback
import webbrowser
from pathlib import Path

RUNTIME_URL = 'https://developer.microsoft.com/microsoft-edge/webview2/'
RELEASE_URL = 'https://github.com/styayur/LGXT-Assistant/releases/latest'


def show_recovery(error):
    folder = Path(os.environ.get('APPDATA') or Path.home()) / 'LGXT-Assistant' / 'logs'
    try:
        folder.mkdir(parents=True, exist_ok=True)
        log = folder / 'startup-error.log'
        log.write_text(''.join(traceback.format_exception(error)), encoding='utf-8')
        details = f'错误记录：{log}'
    except OSError:
        details = '请将下方提示提供给项目维护者。'
    message = ('新版界面暂时无法打开。你仍可进入兼容界面使用课程功能。\n\n'
               '如果提示缺少 WebView2，请安装微软 WebView2 Evergreen 运行时后重试。\n'
               '便携版请完整解压，保留 _internal 文件夹；不要在压缩包里直接运行。\n\n'
               f'{type(error).__name__}: {error}\n\n{details}')
    try:
        import tkinter as tk
        from tkinter import ttk
        root = tk.Tk()
        root.title('LGXT Assistant · 启动帮助')
        root.geometry('670x380')
        root.minsize(570, 360)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='暂时无法进入新版界面', font=('Microsoft YaHei UI', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text=message, wraplength=600, justify='left', font=('Microsoft YaHei UI', 10)).pack(fill='x', pady=20)

        def legacy():
            args = [sys.executable, '--legacy'] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).resolve().parents[1] / 'default.pyw'), '--legacy']
            subprocess.Popen(args, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            root.destroy()
        actions = ttk.Frame(frame)
        actions.pack(fill='x', side='bottom')
        for label, action in [('进入兼容界面', legacy), ('安装 WebView2', lambda: webbrowser.open(RUNTIME_URL)),
                              ('重新下载完整版', lambda: webbrowser.open(RELEASE_URL)), ('关闭', root.destroy)]:
            ttk.Button(actions, text=label, command=action).pack(side='left', padx=(0, 8))
        root.mainloop()
    except Exception:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'LGXT Assistant · 启动帮助', 0x10)
        else:
            print(message, file=sys.stderr)
