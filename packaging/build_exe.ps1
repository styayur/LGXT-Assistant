# LGXT Assistant 打包脚本（PyInstaller 6.x）
# 用法: powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Push-Location frontend
try {
  npm ci
  if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }

& $Python -m PyInstaller --noconfirm --clean --onefile --noconsole `
  --name LGXT-Assistant `
  --icon assets/icon.ico `
  --version-file packaging/version_info.txt `
  --collect-all ttkbootstrap `
  --collect-all webview `
  --add-data "frontend/dist;frontend/dist" `
  default.pyw
if ($LASTEXITCODE -ne 0) { throw 'Single-file build failed' }

& $Python -m PyInstaller --noconfirm --clean --onedir --noconsole `
  --name LGXT-Assistant-portable `
  --icon assets/icon.ico `
  --version-file packaging/version_info.txt `
  --collect-all ttkbootstrap `
  --collect-all webview `
  --add-data "frontend/dist;frontend/dist" `
  default.pyw
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed' }

Copy-Item output/pdf/LGXT-Assistant-4.0.1-User-Guide.pdf dist/LGXT-Assistant-portable/
if (Test-Path dist/LGXT-Assistant-portable.zip) { Remove-Item dist/LGXT-Assistant-portable.zip -Force }
Compress-Archive -Path dist/LGXT-Assistant-portable/* -DestinationPath dist/LGXT-Assistant-portable.zip -CompressionLevel Optimal

Get-ChildItem dist | Select-Object Name, Length
