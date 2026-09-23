# -*- coding: utf-8 -*-
"""LGXT Assistant 4.0.1 桌面入口，--legacy 保留旧版 Tk 界面。"""
import sys


def main():
    if '--legacy' in sys.argv:
        import ttkbootstrap as ttk
        from ui import App
        root = ttk.Window()
        App(root)
        root.mainloop()
    else:
        try:
            from desktop.app import main as desktop_main
            desktop_main()
        except Exception as exc:
            if '--smoke-test' in sys.argv:
                raise
            from desktop.recovery import show_recovery
            show_recovery(exc)


if __name__ == '__main__':
    main()
