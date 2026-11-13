"""Bounded optional offline Mathtext previews; original LaTeX remains authoritative."""
import importlib.util
import io
import multiprocessing
import os
from pathlib import Path
import re
import sys
import tempfile

RENDERER_VERSION = '3.11.2'
MAX_SOURCE = 1024
MAX_WIDTH = 1000
MAX_HEIGHT = 500
_FORBIDDEN = re.compile(r'\\(?:begin|end|input|include|write|read|openout|usepackage|newcommand|def|href|url|html|catcode)\b')
def _worker(latex, pipe, directory, module_root):
    """A trusted Python child process, without shell or TeX execution."""
    try:
        # Mathtext uses the pinned bundled DejaVu fonts. Avoid scanning every
        # installed Windows font while rebuilding this private, disposable cache.
        os.environ.update(MPLCONFIGDIR=directory, MPLBACKEND='Agg',
                          MPL_IGNORE_SYSTEM_FONTS='1')
        os.chdir(directory)
        sys.path.insert(0, module_root)
        import matplotlib
        if matplotlib.__version__ != RENDERER_VERSION:
            pipe.send_bytes(b'unsupported-renderer-version')
            return
        matplotlib.use('Agg')
        from matplotlib import rc_context
        from matplotlib.font_manager import FontProperties
        from matplotlib.mathtext import MathTextParser, math_to_image
        with rc_context({'text.usetex': False, 'mathtext.fontset': 'dejavusans'}):
            box = MathTextParser('path').parse('$'+latex+'$', dpi=144, prop=FontProperties(size=14))
            if box.width > MAX_WIDTH or box.height > MAX_HEIGHT:
                pipe.send_bytes(b'image-limit')
                return
            image = io.BytesIO()
            math_to_image('$'+latex+'$', image, prop=FontProperties(size=14), dpi=144, format='png', color='black')
            pipe.send_bytes(image.getvalue())
    except Exception:
        pipe.send_bytes(b'unsupported-expression')
    finally:
        pipe.close()


def render_preview(latex):
    """Return a PNG or a stable fallback reason; never run TeX or user commands."""
    fallback = lambda reason: {'status': 'source-fallback', 'reason': reason, 'editable': False}
    if not isinstance(latex, str) or not latex.strip():
        return fallback('empty-source')
    if len(latex) > MAX_SOURCE or '$' in latex or '\x00' in latex:
        return fallback('source-limit')
    if _FORBIDDEN.search(latex):
        return fallback('unsupported-command')
    depth = 0
    for char in latex:
        if char == '{': depth += 1
        if char == '}': depth -= 1
        if depth < 0 or depth > 16:
            return fallback('nesting-limit')
    if depth:
        return fallback('unbalanced-source')
    spec = importlib.util.find_spec('matplotlib')
    if spec is None or not spec.origin:
        return fallback('renderer-unavailable')
    if getattr(sys, 'frozen', False):
        return fallback('renderer-unavailable')
    module_root = str(Path(spec.origin).resolve().parent.parent)
    with tempfile.TemporaryDirectory(prefix='lgxt-equation-') as directory:
        context = multiprocessing.get_context('spawn')
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_worker, args=(latex, sender, directory, module_root))
        try:
            process.start()
            sender.close()
            if not receiver.poll(10):
                return fallback('renderer-timeout')
            data = receiver.recv_bytes(maxlength=2 * 1024 * 1024)
        except (OSError, EOFError, RuntimeError):
            return fallback('renderer-unavailable')
        finally:
            if process.pid is not None:
                process.join(timeout=1)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            receiver.close()
            sender.close()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return fallback('unsupported-expression')
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        width, height = image.size
        if width > MAX_WIDTH or height > MAX_HEIGHT:
            return fallback('image-limit')
        image.verify()
    return {'status': 'rendered', 'renderer': 'Matplotlib Mathtext ' + RENDERER_VERSION,
            'editable': False, 'png': data, 'width': width, 'height': height}
