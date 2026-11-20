# SPDX-License-Identifier: AGPL-3.0-only
"""INPUT-FIDELITY TEST APK ONLY: production controls, strict synthetic client.

No credential-free real-platform probe is run by this dedicated fixture.
"""
import flet as ft

from app_under_test import main
from android_fixture_entry import FixtureClient


def target(page):
    main(page, FixtureClient)


if __name__ == '__main__':
    ft.run(target)
