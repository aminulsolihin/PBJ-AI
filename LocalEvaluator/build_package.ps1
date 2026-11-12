# Builds dist\LocalEvaluator-setup.zip: everything another computer needs, and nothing tied to this one.
# Left out on purpose: venv (rebuilt there), certs (each computer makes its own), data (cached bidder text,
# folder choices, logs), test (holds a copy of a real workbook), the launcher workbook (made by setup).
$ErrorActionPreference = 'Stop'
$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$dist = Join-Path $Base 'dist'
$stage = Join-Path $env:TEMP ("LocalEvaluator-stage-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$root = Join-Path $stage 'LocalEvaluator'
New-Item -ItemType Directory -Force $root, $dist | Out-Null
try {
    & robocopy.exe (Join-Path $Base 'app') (Join-Path $root 'app') /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Copying the app folder failed (robocopy $LASTEXITCODE)." }
    foreach ($file in 'Install.cmd', 'install.ps1', 'uninstall.ps1', 'Attach to workbook.cmd', 'READ ME FIRST.txt') {
        Copy-Item (Join-Path $Base $file) $root
    }
    foreach ($must in 'app\server.py', 'app\engine.py', 'app\excel_io.py', 'app\docs.py', 'app\criteria.py', 'app\launcher.py',
        'app\make_cert.py', 'app\ocr.ps1', 'app\manifest.xml', 'app\web\taskpane.html', 'app\web\taskpane.js', 'app\web\taskpane.css',
        'app\web\commands.html', 'app\web\help.html', 'app\web\assets\icon-32.png', 'app\web\office\office.js') {
        if (-not (Test-Path (Join-Path $root $must))) { throw "Missing from the package: $must" }
    }
    $zip = Join-Path $dist 'LocalEvaluator-setup.zip'
    if (Test-Path $zip) { Remove-Item $zip }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $false)
    $files = (Get-ChildItem $root -Recurse -File).Count
    "{0}  ({1:N1} MB, {2} files)" -f $zip, ((Get-Item $zip).Length / 1MB), $files
}
finally { Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue; $global:LASTEXITCODE = 0 }
