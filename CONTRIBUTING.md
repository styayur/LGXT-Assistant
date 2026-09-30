# Contributing

LGXT Assistant has multiple supported clients. Change the smallest shared boundary needed and document the channel affected.

## Development environment

Recommended: Python 3.13, Node.js 22, and Microsoft Edge WebView2.

```powershell
py -3.13 -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
py -3.13 default.pyw
```

Legacy Tk compatibility is available with `py -3.13 default.pyw --legacy`. Android development lives in `mobile/` and uses the pinned Flet/Flutter toolchain documented in the release workflow.

## Validation

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt playwright pyinstaller
python -m playwright install chromium
python -m pytest -q
python scripts/check_frontend.py
powershell -ExecutionPolicy Bypass -File packaging/build_exe.ps1
python scripts/check_package.py
```

Android work should at minimum compile, with device or emulator verification noted when it was not possible.

## Architecture rules

- Shared domain behavior belongs in Python service modules, not duplicated in React or Flet clients.
- `desktop/` and `frontend/` form the current desktop UI boundary.
- `web_app.py` exposes the Windows web channel and must remain loopback-only by default.
- `mobile/` is a separate Flet client; keep platform-specific behavior out of desktop code.
- `ui/` and the `--legacy` path are compatibility surfaces, not the default target for new features.
- Never commit user credentials, AI keys, account exports, private course content, or generated release binaries.

## Pull requests

Add tests for shared logic. UI pull requests need screenshots and window-size coverage. Persistence or provider changes need migration/compatibility notes. Maintainers perform releases and channel publication.

Security issues must follow [SECURITY.md](SECURITY.md), not public issues.
