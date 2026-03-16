[CmdletBinding()]
param(
    [string]$LeeRepo = "E:\ai\LEE",
    [string]$MarathonRepo = "E:\projects\ai-marathon-coach",
    [string]$LeePythonExe = "D:\soft\miniconda\envs\lee-dev\python.exe",
    [string]$MarathonPythonExe = "D:\soft\miniconda\envs\marathon-runtime\python.exe",
    [switch]$KeepBuildArtifacts
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message"
}

function Assert-PathExists {
    param(
        [string]$PathValue,
        [string]$Description
    )

    if (-not (Test-Path $PathValue)) {
        throw "$Description not found: $PathValue"
    }
}

function Invoke-RobocopySnapshot {
    param(
        [string]$Source,
        [string]$Destination
    )

    $excludeDirs = @(
        ".git",
        ".github",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        ".tmp",
        "pytest-temp"
    )

    $excludeFiles = @(
        "*.pyc",
        "*.pyo",
        "*.pyd"
    )

    $args = @(
        $Source,
        $Destination,
        "/MIR",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP",
        "/XD"
    ) + $excludeDirs + @("/XF") + $excludeFiles

    & robocopy @args | Out-Host
    $code = $LASTEXITCODE
    if ($code -gt 7) {
        throw "robocopy failed with exit code $code"
    }
}

Assert-PathExists -PathValue $LeeRepo -Description "LEE repo"
Assert-PathExists -PathValue $MarathonRepo -Description "Marathon repo"
Assert-PathExists -PathValue $LeePythonExe -Description "LEE Python"
Assert-PathExists -PathValue $MarathonPythonExe -Description "Marathon Python"

$resolvedLeeRepo = (Resolve-Path $LeeRepo).Path
$resolvedMarathonRepo = (Resolve-Path $MarathonRepo).Path
$resolvedLeePython = (Resolve-Path $LeePythonExe).Path
$resolvedMarathonPython = (Resolve-Path $MarathonPythonExe).Path

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "lee-local-publish"
$snapshotDir = Join-Path $tempRoot "snapshot"
$buildOutputDir = Join-Path $tempRoot "dist"

if (Test-Path $tempRoot) {
    Remove-Item -Recurse -Force $tempRoot
}
New-Item -ItemType Directory -Path $snapshotDir | Out-Null
New-Item -ItemType Directory -Path $buildOutputDir | Out-Null

Write-Step "Creating local source snapshot"
Invoke-RobocopySnapshot -Source $resolvedLeeRepo -Destination $snapshotDir

$gitSha = (& git -C $resolvedLeeRepo rev-parse --short HEAD).Trim()
if (-not $gitSha) {
    throw "Failed to resolve git short SHA from $resolvedLeeRepo"
}
$stamp = Get-Date -Format "yyyyMMdd"

Write-Step "Computing candidate version"
$version = (& $resolvedLeePython `
    (Join-Path $resolvedLeeRepo "scripts\ci\compute_version.py") `
    --mode candidate `
    --pyproject (Join-Path $snapshotDir "pyproject.toml") `
    --stamp $stamp `
    --sha $gitSha `
    --write-pyproject).Trim()

if (-not $version) {
    throw "Failed to compute local candidate version"
}

Write-Step "Ensuring build dependency"
& $resolvedLeePython -m pip install build | Out-Host

Write-Step "Building wheel for version $version"
Push-Location $snapshotDir
try {
    & $resolvedLeePython -m build --wheel --outdir $buildOutputDir | Out-Host
}
finally {
    Pop-Location
}

$wheel = Get-ChildItem -Path $buildOutputDir -Filter *.whl | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $wheel) {
    throw "No wheel produced in $buildOutputDir"
}

Write-Step "Installing candidate package into Marathon runtime"
& powershell -ExecutionPolicy Bypass `
    -File (Join-Path $resolvedMarathonRepo "tools\scripts\install-lee.ps1") `
    -PackagePath $wheel.FullName `
    -PythonExe $resolvedMarathonPython | Out-Host

Write-Step "Verifying Marathon runtime version"
& $resolvedMarathonPython -c "import importlib.metadata as m, inspect, lee; print(m.version('lee-framework')); print(inspect.getfile(lee))" | Out-Host

if (-not $KeepBuildArtifacts) {
    Remove-Item -Recurse -Force $tempRoot
}
else {
    Write-Host ""
    Write-Host "Build artifacts kept at: $tempRoot"
}

Write-Host ""
Write-Host "Published local LEE snapshot to Marathon"
Write-Host "Version: $version"
