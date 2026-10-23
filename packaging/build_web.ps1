param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
Push-Location frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }
& $Python -m PyInstaller --noconfirm --clean --onefile --console --name LGXT-Assistant-Web --icon assets/icon.ico --version-file packaging/version_web_info.txt --add-data "LICENSE;." --add-data "NOTICE.md;." --add-data "docs/third-party-editor-notices.txt;docs" --collect-all ttkbootstrap --add-data "frontend/dist;frontend/dist" web_app.py
if ($LASTEXITCODE -ne 0) { throw 'Windows web build failed' }
