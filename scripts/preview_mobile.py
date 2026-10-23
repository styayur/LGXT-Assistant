"""Render the actual Flet Android UI in Flet's web runtime, no remote API."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import flet as ft
from mobile.src.main import main
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8551, host='127.0.0.1', web_renderer=ft.WebRenderer.CANVAS_KIT)
