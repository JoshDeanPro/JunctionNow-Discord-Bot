$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = $null
$PythonArgs = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 12))" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $Python = "py"
        $PythonArgs = @("-3.12")
    }
}

if (-not $Python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 12))" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $Python = "python"
    }
}

if (-not $Python) {
    throw "Python 3.12 is required. Install it with: winget install Python.Python.3.12"
}

if (-not (Get-Command node -ErrorAction SilentlyContinue) -or
    -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node 22 or newer is required. Install it with: winget install OpenJS.NodeJS.LTS"
}

$NodeMajor = [int](& node -p "process.versions.node.split('.')[0]")
if ($NodeMajor -lt 22) {
    throw "Node 22 or newer is required. Install it with: winget install OpenJS.NodeJS.LTS"
}

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $Python @PythonArgs -m venv (Join-Path $Root ".venv")
}

& $VenvPython -m pip install --quiet --upgrade pip
& $VenvPython -m pip install --quiet -e "$Root[dev]"
& npm --prefix (Join-Path $Root "ui") ci --silent

$InstallDir = Join-Path $HOME ".junctionnow\bin"
$Launcher = Join-Path $InstallDir "jnbot.cmd"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Content -Path $Launcher -Encoding ASCII -Value "@echo off`r`nnode `"$Root\ui\src\index.mjs`" %*"

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathParts = @($UserPath -split ";" | Where-Object { $_ })
if ($InstallDir -notin $PathParts) {
    [Environment]::SetEnvironmentVariable("Path", (($PathParts + $InstallDir) -join ";"), "User")
}
$env:Path = "$InstallDir;$env:Path"

& $Launcher
