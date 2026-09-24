function Invoke-AnalystCheck([scriptblock] $Action) {
    & $Action
    if ($LASTEXITCODE -ne 0) { throw 'Local M8.1 validation failed; classify before continuing' }
}

# Direct Core dependencies: M7, M6.5 and governed Model integration.
Invoke-AnalystCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider -q tests/unit/execution/test_agent.py tests/architecture/test_agent.py tests/integration/composition/test_agent.py tests/unit/reference/test_model_routing.py tests/architecture/test_model_routing.py tests/unit/reference/test_model.py tests/unit/intelligence/test_model_values.py tests/integration/composition/test_model_governed.py }

Push-Location packages/legoai-engineering
try {
    Invoke-AnalystCheck { uv lock }
    Invoke-AnalystCheck { uv sync --locked --extra analyst }
    Invoke-AnalystCheck { uv run --locked --no-sync ruff check --fix src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync ruff format src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync ruff check src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync ruff format --check src tests examples }
    Invoke-AnalystCheck { uv run --locked --no-sync mypy src tests examples }

    $analystTemp = Join-Path ([IO.Path]::GetTempPath()) ('legoai-m81-' + [guid]::NewGuid().ToString('N'))

    Invoke-AnalystCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider --basetemp $analystTemp -q tests --ignore=tests/test_sandbox_docker.py }
    Invoke-AnalystCheck { uv run --locked --no-sync python examples/repository_analyst.py }
} finally {
    Pop-Location
}

Invoke-AnalystCheck { git diff --check }