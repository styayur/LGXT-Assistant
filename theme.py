# -*- coding: utf-8 -*-
"""UI 设计令牌与 ttkbootstrap 主题应用（Developer Tool / Dark / Technical）。"""

BG = '#0B0D10'          # 窗口/内容底
BG_RAISED = '#0D1117'   # header / status / 进度窗
SURFACE = '#11161D'     # 面板/行
HOVER = '#18212B'
BORDER = '#232C37'
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

BUTTON_SCHEMES = {
    'primary':   ('#143D31', '#A7F3D0', '#1B5A47', '#0C241C'),
    'secondary': ('#232C37', '#C9D4DE', '#303C49', '#1A212A'),
    'info':      ('#103A4C', '#A5F3FC', '#15566E', '#0A2834'),
    'warning':   ('#3A2A0B', '#FDE68A', '#54400F', '#2A1E07'),
    'danger':    ('#421515', '#FCA5A5', '#5E1F1F', '#330F0F'),
}


def apply_theme(style):
    """把默认主题覆盖为统一的深色 Developer-Tool 风格。"""
    style.configure('TFrame', background=BG)
    style.configure('TLabel', background=BG, foreground=FG)
    style.configure('TButton', font=FONT_UI)
    style.configure('TLabelframe', background=BG, bordercolor=BORDER, relief='solid', borderwidth=1)
    style.configure('TLabelframe.Label', background=BG, foreground=MUTED, font=FONT_UI)
    style.configure('TEntry', fieldbackground=SURFACE, foreground=FG,
                    insertcolor=PRIMARY, bordercolor=BORDER)
    style.configure('TCheckbutton', background=BG, foreground=FG, font=FONT_UI)
    style.configure('TProgressbar', background=PRIMARY, troughcolor=SURFACE, bordercolor=BORDER)
    style.configure('Horizontal.TProgressbar', background=PRIMARY, troughcolor=SURFACE, bordercolor=BORDER)
    for name, (bg, fg, active, pressed) in BUTTON_SCHEMES.items():
        style.configure(f'{name}.TButton', background=bg, foreground=fg)
        style.map(f'{name}.TButton',
                  background=[('pressed', '!disabled', pressed), ('active', active)],
                  foreground=[('pressed', fg), ('disabled', '#5C6672')])
