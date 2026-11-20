"""Actual Flet browser renderer, with an explicit optional synthetic fixture."""
import argparse
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import flet as ft
from mobile.src.main import main
parser=argparse.ArgumentParser()
parser.add_argument('--fixture',action='store_true')
parser.add_argument('--fixture-prefill',action='store_true',help='Seed only a fixed public synthetic username; requires --fixture')
parser.add_argument('--port',type=int,default=8553)
parser.add_argument('--headless',action='store_true')
args=parser.parse_args()
if args.fixture_prefill and not args.fixture:
    parser.error('--fixture-prefill requires --fixture')
if args.headless:
    os.environ['FLET_FORCE_WEB_SERVER']='true'
def target(page):
    if args.fixture:
        sys.path.insert(0,str(ROOT/'tests'))
        from test_mobile import FixtureClient, Storage
        storage=Storage()
        if args.fixture_prefill:
            storage.set('lgxt.user','fixture-prefilled-user')
        main(page,FixtureClient,storage)
    else:
        main(page)
ft.run(target, view=None if args.headless else ft.AppView.WEB_BROWSER, port=args.port, host='127.0.0.1')
