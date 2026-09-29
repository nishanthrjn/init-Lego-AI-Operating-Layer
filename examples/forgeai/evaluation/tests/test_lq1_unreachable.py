"""Live-mode negative path: an unreachable provider is a recorded outcome.

Uses the real Ollama binding against a closed local port. No Ollama is
needed; nothing is retried and replay is never used as a fallback.
"""

from pathlib import Path

from eval_support import fixture, metadata
from forgeai_support import FakeSandbox, git_executable
from legoai.runtime.api import ModelBindingConfig

from forgeai.cli import ollama_binding
from forgeai_eval.fixtures import Fixture, FixtureSet
from forgeai_eval.hidden import HiddenOutcome
from forgeai_eval.report import build_report, write_report
from forgeai_eval.runner import RunSettings, evaluate


def test_unreachable_provider_is_recorded_model_failure(tmp_path: Path) -> None:
    binding = ollama_binding("http://127.0.0.1:9", "unreachable-model", 5.0)

    def bindings(item: Fixture) -> tuple[tuple[ModelBindingConfig, ...], str]:
        return (binding,), "ollama"

    forge = FakeSandbox()
    hidden = FakeSandbox()
    settings = RunSettings(
        bindings=bindings,
        git=git_executable(),
        docker=git_executable(),
        workdir=tmp_path / "work",
        forgeai_sandbox=forge,
        hidden_sandbox=lambda: hidden,
    )
    item = fixture("text-slug")
    single = FixtureSet("forgeai-lq1", "1", "1", (item,))
    runs, _ = evaluate(single, 1, settings)
    (run,) = runs
    assert run.task_result.disposition.value == "failed"
    assert run.task_result.failure is not None
    assert run.task_result.failure.name == "MODEL_FAILED"
    assert run.hidden.outcome is HiddenOutcome.NOT_RUN
    assert forge.calls == 0 and hidden.calls == 0
    report = build_report(
        metadata(single, 1, mode="live", provider="ollama", binding="ollama"),
        single,
        runs,
        1.0,
    )
    write_report(report, tmp_path / "out")
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["execution"]["task_failures"] == {"MODEL_FAILED": 1}
    assert metrics["hidden"]["outcomes"] == {"not_run": 1}
