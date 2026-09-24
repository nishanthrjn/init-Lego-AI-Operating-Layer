# 1. Automatically request Administrator rights if we don't have them
if (-Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..."
    Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# 2. Ensure the script runs in the directory where the file is located
Set-Location $PSScriptRoot
Push-Location examples/documind
try {
    uv sync --locked --group dev --no-install-project
    if ($LASTEXITCODE -ne 0) { throw 'Dependency sync failed' }
    uv sync --locked --group dev --no-build-isolation
    if ($LASTEXITCODE -ne 0) { throw 'Project sync failed' }
    uv run --locked --no-sync python -m pytest -q tests/integration/test_end_to_end.py
    if ($LASTEXITCODE -ne 0) { throw 'DocuMind regression failed' }
} finally {
    Pop-Location
}
git diff --check