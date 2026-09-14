# Create a SELF-SIGNED code signing certificate (development/testing only).
# A self-signed signature does NOT remove Windows SmartScreen warnings;
# for public distribution purchase a CA-issued code signing certificate.
$subject = 'CN=Styayur, O=LGXT Assistant, C=CN'
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
  -CertStoreLocation Cert:\CurrentUser\My -KeyUsage DigitalSignature `
  -KeyExportPolicy Exportable -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(3)

$outDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'packaging'
$cerPath = Join-Path $outDir 'LGXT-Assistant-SelfSigned.cer'
Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null

Write-Host ("Self-signed certificate created. Thumbprint: {0}" -f $cert.Thumbprint)
Write-Host ("Public certificate exported to: {0}" -f $cerPath)
Write-Host 'Sign with: powershell -File packaging\sign.ps1 -Path dist\LGXT-Assistant.exe -Thumbprint <thumbprint>'
