# -*- coding: utf-8 -*-
"""LGXT Assistant 3.0 启动入口。"""
import ttkbootstrap as ttk

from ui import App


def main():
    root = ttk.Window()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
