"""Actual Flet browser renderer, with an explicit optional synthetic fixture."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import flet as ft
from mobile.src.main import main
parser=argparse.ArgumentParser()
parser.add_argument('--fixture',action='store_true')
parser.add_argument('--port',type=int,default=8553)
args=parser.parse_args()
def target(page):
    if args.fixture:
        sys.path.insert(0,str(ROOT/'tests'))
        from test_mobile import FixtureClient, Storage
        main(page,FixtureClient,Storage())
    else:
        main(page)
ft.run(target, view=ft.AppView.WEB_BROWSER, port=args.port, host='127.0.0.1')
