[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$expectedPython = (Get-Content (Join-Path $repositoryRoot '.python-version') -Raw).Trim()
$expectedUv = '0.12.5'

function Fail([string]$Message) {
    throw "[toolchain] $Message"
}

if ($IsWindows -or $env:OS -eq 'Windows_NT') {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        Fail 'Python Launcher não encontrado. Instale Python 3.11.'
    }
    $actualPython = (& py -3.11 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")').Trim()
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $uvLauncher = 'uv'
        $uvPrefix = @()
    } else {
        $uvLauncher = 'py'
        $uvPrefix = @('-3.11', '-m', 'uv')
    }
} else {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Fail 'Python não encontrado.'
    }
    $actualPython = (& python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")').Trim()
    $uvLauncher = 'uv'
    $uvPrefix = @()
}

if ($actualPython -ne $expectedPython) {
    Fail "Python $expectedPython é obrigatório; encontrado: $actualPython."
}
try {
    $uvOutput = (& $uvLauncher @uvPrefix --version 2>&1 | Out-String).Trim()
} catch {
    Fail "uv $expectedUv não encontrado. Consulte o README."
}
if ($uvOutput -notmatch "^uv $([regex]::Escape($expectedUv))(?:\s|$)") {
    Fail "uv $expectedUv é obrigatório; encontrado: $uvOutput."
}
if (-not (Test-Path (Join-Path $repositoryRoot 'uv.lock'))) {
    Fail 'uv.lock não encontrado.'
}

Push-Location $repositoryRoot
try {
    & $uvLauncher @uvPrefix lock --check
    if ($LASTEXITCODE -ne 0) {
        Fail 'uv.lock não corresponde ao pyproject.toml.'
    }
} finally {
    Pop-Location
}

Write-Host "[toolchain] OK - Python $actualPython e uv $expectedUv."
