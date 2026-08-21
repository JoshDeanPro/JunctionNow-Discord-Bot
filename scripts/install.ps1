$ErrorActionPreference = "Stop"

$Repository = "JoshDeanPro/JunctionNow-Discord-Bot"
$Origin = "https://github.com/$Repository.git"
$AppRoot = if ($env:JNBOT_INSTALL_ROOT) { $env:JNBOT_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA "JunctionNow" }
$InstallDir = if ($env:JNBOT_COMMAND_DIR) { $env:JNBOT_COMMAND_DIR } else { Join-Path $HOME ".junctionnow\bin" }
$Launcher = Join-Path $InstallDir "jnbot.cmd"
$Python = $null
$PythonArgs = @()
$Created = $false

if (-not $AppRoot -or $AppRoot -eq $HOME -or $AppRoot -eq $env:LOCALAPPDATA) {
    throw "The install location is unsafe."
}

trap {
    if ($Created -and (Test-Path $AppRoot)) {
        Remove-Item -LiteralPath $AppRoot -Recurse -Force
    }
    Write-Error $_
    exit 1
}

function Assert-Native($Message) {
    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

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

if (Test-Path $AppRoot) {
    $ExistingOrigin = & git -C $AppRoot remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0 -or $ExistingOrigin -ne $Origin) {
        throw "The install location is occupied by another application: $AppRoot"
    }

    $Changes = & git -C $AppRoot status --porcelain --untracked-files=no
    if ($Changes) {
        throw "The installed application has tracked local changes."
    }

    & git -C $AppRoot fetch --quiet origin main
    Assert-Native "Unable to check GitHub main."
    & git -C $AppRoot merge --quiet --ff-only origin/main
    Assert-Native "The installed application cannot be updated safely."
} else {
    $Created = $true
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        & gh repo clone $Repository $AppRoot -- --quiet --branch main --single-branch
    } else {
        & git clone --quiet --branch main --single-branch $Origin $AppRoot
    }
    Assert-Native "Unable to download JunctionNow from GitHub."
}

$VenvPython = Join-Path $AppRoot ".venv\Scripts\python.exe"
& $Python @PythonArgs -m venv --clear (Join-Path $AppRoot ".venv")
Assert-Native "Unable to create the Python environment."
& $VenvPython -m pip install --quiet --upgrade pip
Assert-Native "Unable to prepare Python."
& $VenvPython -m pip install --quiet -e $AppRoot
Assert-Native "Unable to install JunctionNow."
& npm --prefix (Join-Path $AppRoot "ui") ci --omit=dev --silent
Assert-Native "Unable to install the manager interface."

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$ExpectedLauncher = "@echo off`r`nnode `"$AppRoot\ui\src\index.mjs`" %*"

if ((Test-Path $Launcher) -and (Get-Content -Raw $Launcher).Trim() -ne $ExpectedLauncher.Trim()) {
    throw "The jnbot command is managed by another application: $Launcher"
}

Set-Content -Path $Launcher -Encoding ASCII -Value $ExpectedLauncher

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathParts = @($UserPath -split ";" | Where-Object { $_ })
if ($InstallDir -notin $PathParts) {
    [Environment]::SetEnvironmentVariable("Path", (($PathParts + $InstallDir) -join ";"), "User")
}
$env:Path = "$InstallDir;$env:Path"

Write-Host "Installed. Run: jnbot"

if ($env:JNBOT_NO_LAUNCH -ne "1") {
    & $Launcher
}
