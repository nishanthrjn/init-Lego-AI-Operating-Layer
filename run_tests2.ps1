# 1. Automatically request Administrator rights if we don't have them
if (-Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..."
    Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# 2. Ensure the script runs in the directory where the file is located
Set-Location $PSScriptRoot

Push-Location packages/legoai-engineering
uv run ruff check src tests examples
uv run ruff format --check src tests examples
Pop-Location
git diff --check