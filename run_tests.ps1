# 1. Automatically request Administrator rights if we don't have them
if (-Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..."
    Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# 2. Ensure the script runs in the directory where the file is located
Set-Location $PSScriptRoot

# 3. Your test commands
Push-Location packages/legoai-engineering

Write-Host "Running uv sync..." -ForegroundColor Cyan
uv sync --locked

Write-Host "Checking git version..." -ForegroundColor Cyan
git --version

Write-Host "Running pytest..." -ForegroundColor Cyan
uv run pytest -q

Write-Host "Running mypy..." -ForegroundColor Cyan
uv run mypy src tests examples

Write-Host "Running ruff check..." -ForegroundColor Cyan
uv run ruff check src tests examples

Write-Host "Running ruff format..." -ForegroundColor Cyan
uv run ruff format --check src tests examples

Write-Host "Running mutation_intake.py..." -ForegroundColor Cyan
uv run python examples/mutation_intake.py

Pop-Location

Write-Host "Checking git diff..." -ForegroundColor Cyan
git diff --check

Write-Host "All tests completed!" -ForegroundColor Green