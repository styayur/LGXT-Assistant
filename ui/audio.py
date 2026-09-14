# -*- coding: utf-8 -*-
"""轻量音效（Windows winsound；其它平台/异常时静默降级）。"""
import logging

log = logging.getLogger(__name__)
_enabled = True

try:
    import winsound
except Exception:                      # 非 Windows
    winsound = None

_ALIASES = {
    'hover': 'SystemAsterisk',
    'click': 'SystemDefault',
    'ok': 'SystemAsterisk',
    'error': 'SystemHand',
}


def set_enabled(flag):
    global _enabled
    _enabled = bool(flag)


def enabled():
    return _enabled


def play(kind='click'):
    if not _enabled or winsound is None:
        return
    alias = _ALIASES.get(kind, 'SystemDefault')
    try:
        winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        log.debug('音效播放失败: %s', kind, exc_info=True)
