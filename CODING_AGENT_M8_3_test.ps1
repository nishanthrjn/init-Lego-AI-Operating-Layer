# Local M8.3 qualification. Symlink-capable Windows session required for new escapes.
$ErrorActionPreference = 'Stop'

function Invoke-CodingCheck([scriptblock] $Action) {
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw 'M8.3 check failed; classify the failure before continuing'
    }
}

Push-Location $PSScriptRoot
try {
    Invoke-CodingCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider -q tests/unit/execution/test_agent.py tests/architecture/test_agent.py tests/integration/composition/test_agent.py tests/unit/reference/test_model_routing.py tests/architecture/test_model_routing.py tests/unit/reference/test_model.py tests/unit/intelligence/test_model_values.py tests/integration/composition/test_model_governed.py }
    Push-Location packages/legoai-engineering
    try {
        Invoke-CodingCheck { uv sync --locked --extra analyst }
        Invoke-CodingCheck { uv run --locked --no-sync ruff check --fix src tests examples }
        Invoke-CodingCheck { uv run --locked --no-sync ruff format src tests examples }
        Invoke-CodingCheck { uv run --locked --no-sync ruff check src tests examples }
        Invoke-CodingCheck { uv run --locked --no-sync ruff format --check src tests examples }
        Invoke-CodingCheck { uv run --locked --no-sync mypy src tests examples }
        $codingTemp = Join-Path ([IO.Path]::GetTempPath()) ('legoai-m83-' + [guid]::NewGuid().ToString('N'))
        # Includes M8.3, M8.2/M8.1, M4 compatibility, architecture and packaging.
        Invoke-CodingCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider --basetemp $codingTemp -q tests --ignore=tests/test_sandbox_docker.py }
        Invoke-CodingCheck { uv run --locked --no-sync python examples/repository_analyst.py }
        Invoke-CodingCheck { uv run --locked --no-sync python examples/independent_reviewer.py }
        Invoke-CodingCheck { uv run --locked --no-sync python examples/bounded_coding.py }
    } finally {
        Pop-Location
    }
    Invoke-CodingCheck { git diff --check }
} finally {
    Pop-Location
}
