# LGXT Assistant MSI build script (WiX Toolset v3: heat / candle / light)
# Usage: powershell -ExecutionPolicy Bypass -File packaging\build_msi.ps1 -WixBin <wix3 dir>
param(
  [string]$WixBin = $env:WIX_BIN
)
$ErrorActionPreference = "Stop"
if (-not $WixBin -or -not (Test-Path (Join-Path $WixBin 'candle.exe'))) {
  throw "WiX v3 not found. Download wix314-binaries.zip, extract it, then pass -WixBin <dir> or set WIX_BIN."
}
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$heat = Join-Path $WixBin 'heat.exe'
$candle = Join-Path $WixBin 'candle.exe'
$light = Join-Path $WixBin 'light.exe'

New-Item -ItemType Directory -Path 'packaging\installer\obj' -Force | Out-Null
$harvest = 'packaging\installer\harvest.wxs'
$source = (Resolve-Path 'dist\LGXT-Assistant-portable').Path
$icon = (Resolve-Path 'assets\icon.ico').Path
$msi = 'dist\LGXT-Assistant-3.1.0-setup.msi'

& $heat dir $source -cg AppFiles -gg -g1 -sfrag -srd -sreg -scom -dr INSTALLFOLDER -var var.SourceDir -out $harvest
& $candle -nologo ("-dSourceDir=" + $source) ("-dIconPath=" + $icon) -out 'packaging\installer\obj\' 'packaging\installer\Package.wxs' $harvest
& $light -nologo -out $msi 'packaging\installer\obj\Package.wixobj' 'packaging\installer\obj\harvest.wixobj'

Get-Item $msi | Select-Object Name, Length
