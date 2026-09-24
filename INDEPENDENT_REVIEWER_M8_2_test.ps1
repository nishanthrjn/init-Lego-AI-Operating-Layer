# Local qualification only. Run from a symlink-capable Windows PowerShell session.
$ErrorActionPreference = 'Stop'

function Invoke-ReviewerCheck([scriptblock] $Action) {
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw 'M8.2 check failed; classify the failure before continuing'
    }
}

Push-Location $PSScriptRoot
try {
    Invoke-ReviewerCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider -q tests/unit/execution/test_agent.py tests/architecture/test_agent.py tests/integration/composition/test_agent.py tests/unit/reference/test_model_routing.py tests/architecture/test_model_routing.py tests/unit/reference/test_model.py tests/unit/intelligence/test_model_values.py tests/integration/composition/test_model_governed.py }
    Push-Location packages/legoai-engineering
    try {
        Invoke-ReviewerCheck { uv sync --locked --extra analyst }
        Invoke-ReviewerCheck { uv run --locked --no-sync ruff check --fix src tests examples }
        Invoke-ReviewerCheck { uv run --locked --no-sync ruff format src tests examples }
        Invoke-ReviewerCheck { uv run --locked --no-sync ruff check src tests examples }
        Invoke-ReviewerCheck { uv run --locked --no-sync ruff format --check src tests examples }
        Invoke-ReviewerCheck { uv run --locked --no-sync mypy src tests examples }
        $reviewerTemp = Join-Path ([IO.Path]::GetTempPath()) ('legoai-m82-' + [guid]::NewGuid().ToString('N'))
        Invoke-ReviewerCheck { uv run --locked --no-sync python -m pytest -p no:cacheprovider --basetemp $reviewerTemp -q tests --ignore=tests/test_sandbox_docker.py }
        Invoke-ReviewerCheck { uv run --locked --no-sync python examples/repository_analyst.py }
        Invoke-ReviewerCheck { uv run --locked --no-sync python examples/independent_reviewer.py }
    } finally {
        Pop-Location
    }
    Invoke-ReviewerCheck { git diff --check }
} finally {
    Pop-Location
}
