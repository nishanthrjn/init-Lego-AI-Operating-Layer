# 1. Automatically request Administrator rights if we don't have them
if (-Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..."
    Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# 2. Ensure the script runs in the directory where the file is located
Set-Location $PSScriptRoot

Push-Location packages/legoai-engineering
uv sync --locked

docker --context desktop-linux version
docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'
docker --context desktop-linux image inspect 'python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56' --format '{{.Os}}/{{.Architecture}}'

uv run pytest -q
uv run mypy src tests examples
uv run ruff check src tests examples
uv run ruff format --check src tests examples
uv run python examples/sandbox_intake.py

Pop-Location
git diff --check