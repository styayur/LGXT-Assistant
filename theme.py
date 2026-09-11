# -*- coding: utf-8 -*-
"""UI 设计令牌与 ttkbootstrap 主题应用（Developer Tool / Dark / Technical）。

LAYOUT 3：无硬线条 —— 层级完全靠背景深浅表达；字体按窗口尺寸自适应缩放。
"""

BG = '#0B0D10'          # 窗口/内容底
BG_RAISED = '#0D1117'   # header / status / command bar
SURFACE = '#11161D'     # 面板/行
SURFACE_2 = '#151B24'   # 次级面（淡出层次）
HOVER = '#18212B'
BORDER = '#161C24'      # 近乎不可见的“淡出”分隔（替代实线）
FG = '#D7E0EA'
MUTED = '#8B98A5'
DIM = '#5C6672'
PRIMARY = '#34D399'     # terminal green
SECONDARY = '#22D3EE'   # cyan
WARNING = '#FBBF24'     # amber
ERROR = '#F87171'

FONT_UI = ('Microsoft YaHei', 10)
FONT_UI_BOLD = ('Microsoft YaHei', 10, 'bold')
FONT_MONO = ('Consolas', 10)
FONT_MONO_BOLD = ('Consolas', 10, 'bold')

SCALE = 1.0             # 运行时由 App 根据窗口尺寸调整

BUTTON_SCHEMES = {
    'primary':   ('#143D31', '#A7F3D0', '#1B5A47', '#0C241C'),
    'secondary': ('#232C37', '#C9D4DE', '#303C49', '#1A212A'),
    'info':      ('#103A4C', '#A5F3FC', '#15566E', '#0A2834'),
    'warning':   ('#3A2A0B', '#FDE68A', '#54400F', '#2A1E07'),
    'danger':    ('#421515', '#FCA5A5', '#5E1F1F', '#330F0F'),
}


def set_scale(value):
    global SCALE
    SCALE = value


def ui(size, bold=False, family='Microsoft YaHei'):
    return (family, max(8, int(round(size * SCALE))), 'bold') if bold \
        else (family, max(8, int(round(size * SCALE))))


def mono(size, bold=False):
    return ('Consolas', max(8, int(round(size * SCALE))), 'bold') if bold \
        else ('Consolas', max(8, int(round(size * SCALE))))


def apply_theme(style):
    """统一深色主题：无实线边框，全部靠背景层次。"""
    style.configure('TFrame', background=BG, borderwidth=0, relief='flat')
    style.configure('TLabel', background=BG, foreground=FG, borderwidth=0)
    style.configure('TButton', font=ui(10), borderwidth=0, relief='flat')
    style.configure('TLabelframe', background=BG, bordercolor=BG, relief='flat', borderwidth=0)
    style.configure('TLabelframe.Label', background=BG, foreground=MUTED, font=ui(10))
    style.configure('TEntry', fieldbackground=SURFACE, foreground=FG, insertcolor=PRIMARY,
                    bordercolor=BG, lightcolor=BG, darkcolor=BG, borderwidth=0, relief='flat')
    style.configure('TCombobox', fieldbackground=SURFACE, background=SURFACE, foreground=FG,
                    arrowcolor=MUTED, bordercolor=BG, lightcolor=BG, darkcolor=BG,
                    borderwidth=0, relief='flat')
    style.map('TCombobox', fieldbackground=[('readonly', SURFACE)],
              foreground=[('readonly', FG)])
    style.configure('TCheckbutton', background=BG, foreground=FG, font=ui(10),
                    borderwidth=0, relief='flat')
    style.configure('TProgressbar', background=PRIMARY, troughcolor=SURFACE,
                    bordercolor=BG, borderwidth=0)
    style.configure('Horizontal.TProgressbar', background=PRIMARY, troughcolor=SURFACE,
                    bordercolor=BG, borderwidth=0)
    # 树状图（无边框、淡化行）
    style.configure('Treeview', background=SURFACE, fieldbackground=SURFACE, foreground=FG,
                    bordercolor=BG, lightcolor=BG, darkcolor=BG, borderwidth=0,
                    relief='flat', rowheight=int(26 * SCALE), font=ui(10))
    style.configure('Treeview.Heading', background=BG_RAISED, foreground=MUTED,
                    bordercolor=BG, lightcolor=BG, darkcolor=BG, borderwidth=0,
                    relief='flat', font=mono(9))
    style.map('Treeview', background=[('selected', HOVER)], foreground=[('selected', PRIMARY)])
    style.map('Treeview.Heading', background=[('active', BG_RAISED)])
    for name, (bg, fg, active, pressed) in BUTTON_SCHEMES.items():
        style.configure(f'{name}.TButton', background=bg, foreground=fg,
                        bordercolor=bg, borderwidth=0, relief='flat')
        style.map(f'{name}.TButton',
                  background=[('pressed', '!disabled', pressed), ('active', active)],
                  foreground=[('pressed', fg), ('disabled', '#5C6672')])
