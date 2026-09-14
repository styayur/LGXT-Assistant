# LGXT Assistant code signing helper (PowerShell / Authenticode)
# Usage examples:
#   powershell -File packaging\sign.ps1 -Path dist\LGXT-Assistant.exe -Thumbprint <CERT_THUMBPRINT>
#   powershell -File packaging\sign.ps1 -Path dist\*.msi -PfxPath cert.pfx -PfxPassword (Read-Host -AsSecureString)
param(
  [Parameter(Mandatory=$true)][string[]]$Path,
  [string]$Thumbprint,
  [string]$PfxPath,
  [System.Security.SecureString]$PfxPassword,
  [string]$TimestampServer = 'http://timestamp.digicert.com'
)
$ErrorActionPreference = 'Stop'

if ($PfxPath) {
  $cert = Get-PfxCertificate -FilePath $PfxPath
  if ($PfxPassword) {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($PfxPath, $PfxPassword)
  }
} elseif ($Thumbprint) {
  $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Thumbprint -eq $Thumbprint }
  if (-not $cert) { $cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Thumbprint -eq $Thumbprint } }
} else {
  throw 'Provide -Thumbprint or -PfxPath.'
}
if (-not $cert) { throw 'Signing certificate not found.' }

foreach ($item in $Path) {
  $files = Get-Item $item -ErrorAction SilentlyContinue
  if (-not $files) { Write-Warning "skip missing: $item"; continue }
  foreach ($file in $files) {
    try {
      $sig = Set-AuthenticodeSignature -FilePath $file.FullName -Certificate $cert `
        -HashAlgorithm SHA256 -TimestampServer $TimestampServer
      Write-Host ("signed: {0}  status={1}" -f $file.Name, $sig.Status)
    } catch {
      Write-Warning ("timestamp failed, signing without timestamp: {0}" -f $file.Name)
      $sig = Set-AuthenticodeSignature -FilePath $file.FullName -Certificate $cert -HashAlgorithm SHA256
      Write-Host ("signed (no timestamp): {0}  status={1}" -f $file.Name, $sig.Status)
    }
  }
}

Get-ChildItem $Path -ErrorAction SilentlyContinue | ForEach-Object {
  Get-AuthenticodeSignature $_.FullName |
    Select-Object @{n='File';e={$_.Path}}, Status, @{n='Signer';e={$_.SignerCertificate.Subject}}
}
