"""Shared LQ1 self-test support: fixture lookup, replay settings, sandboxes."""

from dataclasses import replace
from pathlib import Path

from forgeai_support import FakeSandbox, LoggedReplay, git_executable
from legoai.runtime.api import ModelBindingConfig
from legoai_engineering.sandbox.errors import SandboxError
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult

from forgeai.cli import replay_binding
from forgeai_eval.fixtures import EVALUATION, Fixture, FixtureSet, load_fixture_set
from forgeai_eval.runner import RunMetadata, RunSettings

SENTINEL = "lq1-hidden-acceptance"
REVIEW_ACCEPT = (EVALUATION / "replay" / "review_accept.json").read_text(
    encoding="utf-8"
)


def fixture_set() -> FixtureSet:
    return load_fixture_set()


def fixture(fixture_id: str) -> Fixture:
    return next(f for f in fixture_set().fixtures if f.fixture_id == fixture_id)


def reference(item: Fixture) -> str:
    return item.reference_proposal.read_text(encoding="utf-8")


class RecordingSandbox(FakeSandbox):
    """Fake sandbox that records every request and the shared call order."""

    def __init__(
        self,
        log: list[str],
        name: str,
        exits: tuple[int, ...] = (0, 0, 0),
        error: SandboxError | None = None,
    ) -> None:
        super().__init__(exits, error)
        self.log = log
        self.name = name
        self.requests: list[SandboxRequest] = []

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.log.append(self.name)
        self.requests.append(request)
        return super().execute(request, cancellation)


def replay_settings(
    tmp_path: Path,
    outputs: tuple[str | Exception, ...],
    *,
    log: list[str] | None = None,
    forge_exits: tuple[int, ...] = (0, 0, 0),
    hidden_exits: tuple[int, ...] = (0,),
    hidden_error: SandboxError | None = None,
) -> tuple[RunSettings, LoggedReplay, RecordingSandbox, RecordingSandbox]:
    log = log if log is not None else []
    model = LoggedReplay(log, *outputs)
    forge = RecordingSandbox(log, "forgeai-check", forge_exits)
    hidden = RecordingSandbox(log, "hidden-check", hidden_exits, hidden_error)

    def bindings(item: Fixture) -> tuple[tuple[ModelBindingConfig, ...], str]:
        return (replay_binding(model),), "replay"

    settings = RunSettings(
        bindings=bindings,
        git=git_executable(),
        docker=git_executable(),
        workdir=tmp_path,
        forgeai_sandbox=forge,
        hidden_sandbox=lambda: hidden,
    )
    return settings, model, forge, hidden


def metadata(fixtures: FixtureSet, repetitions: int, **changes: object) -> RunMetadata:
    base = RunMetadata(
        mode="replay",
        provider="replay",
        binding="replay",
        model_name="replay",
        model_digest="replay:self-test",
        ollama_version="not-applicable",
        forgeai_commit="self-test",
        fixture_set=fixtures.name,
        fixture_revision=fixtures.revision,
        fixture_digest=fixtures.fixture_digest,
        hidden_revision=fixtures.hidden_revision,
        hidden_digest=fixtures.hidden_digest,
        hardware_class="self-test",
        platform="self-test",
        started_at="2026-09-29T00:00:00+00:00",
        repetitions=repetitions,
    )
    return replace(base, **changes)  # type: ignore[arg-type]
