# Local Evaluator - setup.  Double-click Install.cmd to do everything, or run single steps:
#   -Prerequisites  check for Python, Ollama and the local model; install what is missing (asks first)  [internet]
#   -Packages       private Python environment + packages, and Office.js if it is not in the folder     [internet]
#   -Certificate    create a localhost-only HTTPS certificate and trust it for this Windows user        [Windows asks you to confirm]
#   -Register       show the add-in in Excel and start the engine when you log in                       [current user only]
#   -Start          start the engine now
# Options: -Model <name> (local model to pull), -Yes (do not ask before installing), -Force (redo a step)
# Nothing here needs administrator rights. After setup the add-in works without internet.
param([switch]$Prerequisites, [switch]$Packages, [switch]$Certificate, [switch]$Register, [switch]$Start,
      [switch]$Force, [switch]$Yes, [string]$Model = 'qwen3-vl:8b')
$ErrorActionPreference = 'Stop'
$Base = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $Base 'app'
$Venv = Join-Path $Base 'venv'
$Certs = Join-Path $Base 'certs'
$Port = 47821
$AddinId = '7c1f0f5e-3b7a-4d0e-9c55-2a6b8e41d9a3'
$all = -not ($Prerequisites -or $Packages -or $Certificate -or $Register -or $Start)
function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)." } }

function Quiet([scriptblock]$Block) {
    # Run a program, hiding its output; returns its exit code (or 1 if it could not run).
    $old = $ErrorActionPreference; $ErrorActionPreference = 'SilentlyContinue'; $global:LASTEXITCODE = 1
    try { & $Block 2>$null | Out-Null } catch { $global:LASTEXITCODE = 1 }
    $ErrorActionPreference = $old
    return $LASTEXITCODE
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Find-Python {
    # A real Python 3.10+ with venv and tkinter (not the Microsoft Store placeholder).
    $found = @()
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $old = $ErrorActionPreference; $ErrorActionPreference = 'SilentlyContinue'
        try { $p = & py.exe -3 -c "import sys; print(sys.executable)" 2>$null; if ($p) { $found += "$p".Trim() } } catch {}
        $ErrorActionPreference = $old
    }
    $found += @(Get-Command python.exe -All -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike '*WindowsApps*' } | ForEach-Object { $_.Source })
    $found += @(Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:ProgramFiles\Python3*\python.exe",
            "$env:LOCALAPPDATA\Python\pythoncore-3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
    foreach ($exe in $found) {
        if ($exe -and (Test-Path $exe)) {
            if ((Quiet { & $exe -c "import sys, venv, tkinter; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" }) -eq 0) { return $exe }
        }
    }
    return $null
}
function Find-Ollama {
    $cmd = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $path = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (Test-Path $path) { return $path }
    return $null
}
function Has-Model($ollama, $name) {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'SilentlyContinue'
    try { $list = & $ollama list 2>$null } catch { $list = @() }
    $ErrorActionPreference = $old
    return [bool]($list | Where-Object { "$_" -match ('^' + [regex]::Escape($name) + '(\s|$)') })
}

# Files copied from another computer or downloaded can be marked "blocked" by Windows; clear that for this folder.
Get-ChildItem $Base -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "$Venv\*" } | Unblock-File -ErrorAction SilentlyContinue

if ($all -or $Prerequisites) {
    Step 'Checking what this computer needs'
    $excel = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe' -ErrorAction SilentlyContinue).'(default)'
    if ($excel) { Write-Host "  Excel            found" }
    else { Write-Host "  Excel            NOT FOUND - desktop Excel (2016 or later, or Microsoft 365) is required. Setup continues, but the pane needs it." -ForegroundColor Yellow }
    $python = Find-Python
    $ollama = Find-Ollama
    $hasModel = $ollama -and (Has-Model $ollama $Model)
    Write-Host "  Python           $(if ($python) { 'found' } else { 'missing' })"
    Write-Host "  Ollama           $(if ($ollama) { 'found' } else { 'missing' })"
    Write-Host "  Model $Model  $(if ($hasModel) { 'found' } else { 'missing (about 6 GB to download)' })"
    $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
    if ($ram -lt 15) { Write-Host "  Memory           $ram GB - the model needs about 16 GB; it may be very slow here." -ForegroundColor Yellow }
    $free = [math]::Round((Get-PSDrive -Name $Base.Substring(0, 1)).Free / 1GB)
    $need = 1 + $(if ($hasModel) { 0 } else { 7 })
    if ($free -lt $need) { throw "Not enough free disk space on drive $($Base.Substring(0, 1)): $free GB free, about $need GB needed." }

    $todo = @()
    if (-not $python) { $todo += 'Python 3.13 (from python.org, through the Windows package manager)' }
    if (-not $ollama) { $todo += 'Ollama (runs the local model, from ollama.com, through the Windows package manager)' }
    if (-not $hasModel) { $todo += "the local model $Model (about 6 GB, from Ollama's library)" }
    if ($todo) {
        Write-Host "`nSetup will download and install:" -ForegroundColor Yellow
        $todo | ForEach-Object { Write-Host "  - $_" }
        Write-Host "Installing through the Windows package manager accepts each program's licence terms on your behalf."
        if (-not $Yes) {
            $answer = Read-Host 'Go ahead? (Y/N)'
            if ($answer -notmatch '^(y|yes)$') { throw 'Setup stopped; nothing was installed.' }
        }
        if ((-not $python -or -not $ollama) -and -not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
            throw "The Windows package manager (winget) is not available on this computer. Install these by hand, then run Install.cmd again:`n  Python 3:  https://www.python.org/downloads/`n  Ollama:    https://ollama.com/download"
        }
        if (-not $python) {
            Step 'Installing Python'
            & winget.exe install -e --id Python.Python.3.13 --scope user --silent --accept-package-agreements --accept-source-agreements
            Refresh-Path
            $python = Find-Python
            if (-not $python) { throw 'Python was installed but could not be found. Restart the computer and run Install.cmd again.' }
        }
        if (-not $ollama) {
            Step 'Installing Ollama'
            & winget.exe install -e --id Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements
            Refresh-Path
            $ollama = Find-Ollama
            if (-not $ollama) { throw 'Ollama was installed but could not be found. Restart the computer and run Install.cmd again.' }
            Start-Sleep 5
        }
        if (-not (Has-Model $ollama $Model)) {
            Step "Downloading the local model $Model (this is the long part)"
            & $ollama pull $Model
            if ($LASTEXITCODE -ne 0 -or -not (Has-Model $ollama $Model)) {
                Write-Host "The model could not be downloaded. Setup continues; later run:  ollama pull $Model" -ForegroundColor Yellow
            }
        }
    }
    else { Write-Host '  Nothing to install.' }
}

if ($all -or $Packages) {
    Step 'Python environment and packages'
    if (-not (Test-Path "$Venv\Scripts\python.exe")) {
        $python = Find-Python
        if (-not $python) { throw 'Python 3 was not found. Run Install.cmd (or install.ps1 -Prerequisites) first.' }
        & $python -m venv $Venv
        Check 'Creating the Python environment'
    }
    & "$Venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet pywin32 pymupdf openpyxl cryptography
    Check 'Installing Python packages'
    & "$Venv\Scripts\python.exe" -c "import win32com.client, pymupdf, openpyxl, cryptography, tkinter; print('Python packages OK')"
    Check 'Checking Python packages'

    $office = Join-Path $App 'web\office'
    if ($Force -or -not (Test-Path "$office\office.js")) {
        Step 'Office.js library (local copy, so the pane works offline)'
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "The folder app\web\office is missing. Copy it from the original package, or install Node.js so it can be downloaded." }
        $tmp = Join-Path $Base 'tmp-npm'
        if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
        New-Item -ItemType Directory -Force $tmp | Out-Null
        # pinned: the 1.1.x line ships the classic dist\office.js files that a task pane loads with a script tag
        & npm install '@microsoft/office-js@1.1.110' --prefix $tmp --no-audit --no-fund --loglevel=error
        Check 'Fetching Office.js'
        New-Item -ItemType Directory -Force $office | Out-Null
        Copy-Item "$tmp\node_modules\@microsoft\office-js\dist\*" $office -Recurse -Force
        Remove-Item $tmp -Recurse -Force
    }
    if (-not (Test-Path "$office\office.js")) { throw 'office.js was not copied.' }
    Write-Host 'Office.js OK'
}

if ($all -or $Certificate) {
    Step 'HTTPS certificate for localhost'
    if (-not (Test-Path "$Venv\Scripts\python.exe")) { throw 'Run the Packages step first (install.ps1 -Packages).' }
    if ($Force -or -not ((Test-Path "$Certs\server.crt") -and (Test-Path "$Certs\server.key") -and (Test-Path "$Certs\ca.crt"))) {
        # Made on this computer for this computer. The signing key is never written to disk.
        & "$Venv\Scripts\python.exe" "$App\make_cert.py" $Certs
        Check 'Creating the certificate'
    }
    $ca = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("$Certs\ca.crt")
    function Trusted {   # a fresh look at the store each time; the Cert: drive can show a stale view
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store('Root', 'CurrentUser')
        $store.Open('ReadOnly')
        try { [bool]($store.Certificates | Where-Object { $_.Thumbprint -eq $ca.Thumbprint }) } finally { $store.Close() }
    }
    if (-not (Trusted)) {
        Write-Host 'Windows will now ask whether to trust "Local Evaluator (this computer only)". Choose Yes.' -ForegroundColor Yellow
        Write-Host '(The question may open behind this window: look for it on the taskbar.)' -ForegroundColor Yellow
        # certutil shows the Windows confirmation dialog even when this script has no console of its own
        & certutil.exe -user -addstore Root "$Certs\ca.crt" | Out-Null
        if (-not (Trusted)) {
            throw 'The certificate was not trusted (the Windows question was answered No or did not appear). Run Install.cmd again and choose Yes.'
        }
    }
    Set-Content -Path "$Certs\ca.thumbprint" -Value $ca.Thumbprint -Encoding ascii
    Write-Host "Certificate OK (trusted for this Windows user only, thumbprint $($ca.Thumbprint))"
}

if ($all -or $Register) {
    Step 'Excel add-in registration and engine shortcuts'
    $key = 'HKCU:\Software\Microsoft\Office\16.0\WEF\Developer'
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -Path $key -Name $AddinId -Value (Join-Path $App 'manifest.xml') -PropertyType String -Force | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    foreach ($folder in [Environment]::GetFolderPath('Startup'), [Environment]::GetFolderPath('Programs')) {
        $lnk = $shell.CreateShortcut((Join-Path $folder 'Local Evaluator engine.lnk'))
        $lnk.TargetPath = "$Venv\Scripts\pythonw.exe"
        $lnk.Arguments = "`"$App\server.py`""
        $lnk.WorkingDirectory = $App
        $lnk.Description = 'Local Evaluator engine (offline, this computer only)'
        $lnk.Save()
    }
    # Excel shows a locally registered add-in only in workbooks that refer to it, so make one that does.
    $launcher = Join-Path $Base 'Open Local Evaluator.xlsx'
    if (-not (Test-Path $launcher)) { & "$Venv\Scripts\python.exe" "$App\launcher.py" new $launcher | Out-Null }
    Write-Host 'Add-in registered for this Windows user.'
}

if ($all -or $Start) {
    Step 'Starting the engine'
    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listening -and $Force) { $listening | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }; Start-Sleep 1; $listening = $null }
    if (-not $listening) { Start-Process "$Venv\Scripts\pythonw.exe" -ArgumentList "`"$App\server.py`"" -WorkingDirectory $App }
    Start-Sleep 3
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { Write-Host "Engine running on https://localhost:$Port" }
    else { Write-Host "The engine did not start. See $Base\data\engine.log" -ForegroundColor Red }
}

if ($all) {
    Step 'Final check'
    $check = "import json, ssl, urllib.request; r = json.loads(urllib.request.urlopen('https://localhost:$Port/api/status', context=ssl.create_default_context(), timeout=90).read()); print('  engine: OK'); print('  link to Excel:', 'OK' if r['excelLink'] else 'MISSING'); print('  local model service:', 'OK' if r['ollama'] else 'NOT RUNNING'); print('  model ${Model}:', 'OK' if '${Model}' in r['models'] else 'NOT INSTALLED')"
    & "$Venv\Scripts\python.exe" -c $check
    if ($LASTEXITCODE -ne 0) { Write-Host "  The engine did not answer over HTTPS. See $Base\data\engine.log" -ForegroundColor Red }
    Write-Host "`nSetup finished. To use Local Evaluator:" -ForegroundColor Green
    Write-Host "  1. Close your evaluation workbook if it is open."
    Write-Host "  2. Double-click `"$Base\Attach to workbook.cmd`" and choose the workbook."
    Write-Host "  3. It opens with the Local Evaluator pane on the right, now and every time you open it."
    Write-Host "  (Or open `"$Base\Open Local Evaluator.xlsx`" to see the pane straight away.)"
}
else { Write-Host "`nDone." -ForegroundColor Green }
