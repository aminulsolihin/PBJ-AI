# Local Evaluator - undo what install.ps1 set up. Files under C:\LocalEvaluator are left in place
# unless -RemoveFiles is given (that also deletes cached document text and run history).
param([switch]$RemoveFiles)
$ErrorActionPreference = 'Continue'
$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$AddinId = '7c1f0f5e-3b7a-4d0e-9c55-2a6b8e41d9a3'

Get-NetTCPConnection -LocalPort 47821 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Office\16.0\WEF\Developer' -Name $AddinId -ErrorAction SilentlyContinue
foreach ($folder in [Environment]::GetFolderPath('Startup'), [Environment]::GetFolderPath('Programs')) {
    Remove-Item (Join-Path $folder 'Local Evaluator engine.lnk') -ErrorAction SilentlyContinue
}
$thumbFile = Join-Path $Base 'certs\ca.thumbprint'
if (Test-Path $thumbFile) {
    $thumb = (Get-Content $thumbFile -Raw).Trim()
    if (Test-Path "Cert:\CurrentUser\Root\$thumb") {
        Write-Host 'Windows may ask to confirm removing the "Local Evaluator" certificate. Choose Yes.'
        Remove-Item "Cert:\CurrentUser\Root\$thumb"
    }
}
if ($RemoveFiles) {
    foreach ($d in 'venv', 'certs', 'data', 'app\web\office') { Remove-Item (Join-Path $Base $d) -Recurse -Force -ErrorAction SilentlyContinue }
}
Write-Host 'Local Evaluator was removed from Excel and from startup. Restart Excel.'
