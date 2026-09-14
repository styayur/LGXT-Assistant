# LGXT Assistant 打包脚本（PyInstaller 6.x）
# 用法: powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m PyInstaller --noconfirm --clean --onefile --noconsole `
  --name LGXT-Assistant `
  --icon assets/icon.ico `
  --version-file packaging/version_info.txt `
  --collect-all ttkbootstrap `
  default.pyw

python -m PyInstaller --noconfirm --clean --onedir --noconsole `
  --name LGXT-Assistant-portable `
  --icon assets/icon.ico `
  --version-file packaging/version_info.txt `
  --collect-all ttkbootstrap `
  default.pyw

if (Test-Path dist/LGXT-Assistant-portable.zip) { Remove-Item dist/LGXT-Assistant-portable.zip -Force }
Compress-Archive -Path dist/LGXT-Assistant-portable/* -DestinationPath dist/LGXT-Assistant-portable.zip -CompressionLevel Optimal

Get-ChildItem dist | Select-Object Name, Length
