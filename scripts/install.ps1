$ErrorActionPreference = "Stop"

$Repository = "JoshDeanPro/JunctionNow-Discord-Bot"
$Origin = "https://github.com/$Repository.git"
$AppRoot = if ($env:JNBOT_INSTALL_ROOT) { $env:JNBOT_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA "JunctionNow" }
$InstallDir = if ($env:JNBOT_COMMAND_DIR) { $env:JNBOT_COMMAND_DIR } else { Join-Path $HOME ".junctionnow\bin" }
$Launcher = Join-Path $InstallDir "jnbot.cmd"
$Python = $null
$PythonArgs = @()
$PrivatePython = $false
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

$RuntimeRoot = Join-Path $AppRoot ".runtime"
New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null

if (-not $Python) {
    Write-Host "Installing a private Python 3.12 runtime..."
    $env:UV_INSTALL_DIR = Join-Path $RuntimeRoot "bin"
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $RuntimeRoot "python"
    $env:UV_CACHE_DIR = Join-Path $RuntimeRoot "uv-cache"
    $env:UV_NO_MODIFY_PATH = "1"
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $Python = Join-Path $env:UV_INSTALL_DIR "uv.exe"
    & $Python python install 3.12 | Out-Null
    Assert-Native "Unable to install the private Python runtime."
    $PrivatePython = $true
}

$NodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
$UseSystemNode = $false

if ($NodeCommand -and $NpmCommand) {
    $NodeMajor = [int](& $NodeCommand.Source -p "process.versions.node.split('.')[0]")
    $UseSystemNode = $NodeMajor -ge 22
}

if ($UseSystemNode) {
    $NodeExe = $NodeCommand.Source
    $NpmExe = $NpmCommand.Source
} else {
    Write-Host "Installing a private Node 22 runtime..."
    $Architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    $NodePlatform = switch ($Architecture) {
        "X64" { "win-x64" }
        "Arm64" { "win-arm64" }
        default { throw "This computer cannot use the automatic Node runtime." }
    }
    $Checksums = (Invoke-WebRequest https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt).Content
    $VersionMatch = [regex]::Match($Checksums, "node-(v[0-9.]+)-$NodePlatform\.zip")

    if (-not $VersionMatch.Success) {
        throw "Unable to find the current Node 22 runtime."
    }

    $NodeVersion = $VersionMatch.Groups[1].Value
    $ArchiveName = "node-$NodeVersion-$NodePlatform.zip"
    $ExpectedMatch = [regex]::Match($Checksums, "(?m)^([a-f0-9]{64})\s+$([regex]::Escape($ArchiveName))$")

    if (-not $ExpectedMatch.Success) {
        throw "Unable to verify the current Node 22 runtime."
    }

    $NodeArchive = Join-Path $RuntimeRoot $ArchiveName
    $NodeExtract = Join-Path $RuntimeRoot "node-new"
    Invoke-WebRequest "https://nodejs.org/dist/$NodeVersion/$ArchiveName" -OutFile $NodeArchive

    if ((Get-FileHash $NodeArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedMatch.Groups[1].Value) {
        throw "The private Node runtime failed verification."
    }

    if (Test-Path $NodeExtract) {
        Remove-Item -LiteralPath $NodeExtract -Recurse -Force
    }
    Expand-Archive $NodeArchive -DestinationPath $NodeExtract
    $NodeRoot = Join-Path $RuntimeRoot "node"
    if (Test-Path $NodeRoot) {
        Remove-Item -LiteralPath $NodeRoot -Recurse -Force
    }
    Move-Item (Join-Path $NodeExtract "node-$NodeVersion-$NodePlatform") $NodeRoot
    Remove-Item -LiteralPath $NodeExtract -Recurse -Force
    Remove-Item -LiteralPath $NodeArchive -Force
    $NodeExe = Join-Path $NodeRoot "node.exe"
    $NpmExe = Join-Path $NodeRoot "npm.cmd"
}

$VenvPython = Join-Path $AppRoot ".venv\Scripts\python.exe"
if ($PrivatePython) {
    & $Python venv --clear --python 3.12 (Join-Path $AppRoot ".venv") | Out-Null
    Assert-Native "Unable to create the private Python environment."
    & $Python pip install --quiet --python $VenvPython -e $AppRoot
    Assert-Native "Unable to install JunctionNow."
} else {
    & $Python @PythonArgs -m venv --clear (Join-Path $AppRoot ".venv")
    Assert-Native "Unable to create the Python environment."
    & $VenvPython -m pip install --quiet --upgrade pip
    Assert-Native "Unable to prepare Python."
    & $VenvPython -m pip install --quiet -e $AppRoot
    Assert-Native "Unable to install JunctionNow."
}
& $NpmExe --prefix (Join-Path $AppRoot "ui") ci --omit=dev --silent
Assert-Native "Unable to install the manager interface."

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$ExpectedLauncher = "@echo off`r`n`"$NodeExe`" `"$AppRoot\ui\src\index.mjs`" %*"

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
