# M6.5 belongs to Core: run from this script's repository root.
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
# Avoid the shared pytest-of-user directory, which may contain links from
# previous elevated sessions. Each invocation receives a fresh, disposable path.
$coreTestTempPrefix = Join-Path ([System.IO.Path]::GetTempPath()) ('legoai-core-' + [guid]::NewGuid().ToString('N'))

uv sync --locked --group dev --no-install-project
if ($LASTEXITCODE -ne 0) { throw 'Core dependency sync failed' }
uv sync --locked --group dev --no-build-isolation
if ($LASTEXITCODE -ne 0) { throw 'Core project sync failed' }

# Routing contracts and architecture
uv run --locked --no-sync python -m pytest --basetemp "$coreTestTempPrefix-routing" -q tests/unit/reference/test_model_routing.py tests/architecture/test_model_routing.py
if ($LASTEXITCODE -ne 0) { throw 'Routing tests failed' }

# Existing Model behavior and governed routing
uv run --locked --no-sync python -m pytest --basetemp "$coreTestTempPrefix-model" -q tests/unit/intelligence/test_model_values.py tests/unit/reference/test_model.py tests/integration/composition/test_model_governed.py
if ($LASTEXITCODE -ne 0) { throw 'Model regression tests failed' }

# Full Core suite, including wheel/sdist and fresh-install tests
uv run --locked --no-sync python -m pytest --basetemp "$coreTestTempPrefix-full"
if ($LASTEXITCODE -ne 0) { throw 'Core suite failed' }

uv run --locked --no-sync python -m mypy src tests examples/model_routing.py
if ($LASTEXITCODE -ne 0) { throw 'mypy failed' }
uv run --locked --no-sync ruff check .
if ($LASTEXITCODE -ne 0) { throw 'Ruff lint failed' }
uv run --locked --no-sync ruff format --check .
if ($LASTEXITCODE -ne 0) { throw 'Ruff format check failed' }
uv build --no-build-isolation
if ($LASTEXITCODE -ne 0) { throw 'Core build failed' }
uv run --locked --no-sync python examples/model_routing.py
if ($LASTEXITCODE -ne 0) { throw 'Routing example failed' }
git diff --check
if ($LASTEXITCODE -ne 0) { throw 'Git whitespace check failed' }

Write-Host 'All Core M6.5 checks passed.'
} finally {
    Pop-Location
}
