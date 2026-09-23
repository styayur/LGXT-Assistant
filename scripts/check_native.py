"""Hidden native WebView2 smoke test with temporary application state."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop.diagnostics import smoke_test

smoke_test(ROOT)
