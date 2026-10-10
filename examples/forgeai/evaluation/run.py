"""ForgeAI-LQ1 evaluation command: replay self-demo or explicit live baseline.

Live execution is always an explicit maintainer action; the validator never
runs it. The operator names the model and its expected digest; a read-only
preflight verifies both against the serving Ollama and observes the server
version before any fixture runs. A failed preflight exits 3, runs nothing and
writes no report. Model replies are observed content-free (LQ1.2): live calls
pass through a local `ChatObserver`, replay models are wrapped in
`ObservingModel`; neither changes what ForgeAI receives.

    uv run python evaluation/run.py replay --output lq1-replay
    uv run python evaluation/run.py live --model <name> --model-digest <digest> \\
        --hardware "<class>" --repetitions 3 --output lq1-baseline
"""

import argparse
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from legoai.runtime.api import ModelBindingConfig

from forgeai.cli import ReplayModel, ollama_binding, replay_binding, terminal_approver
from forgeai_eval.fixtures import EVALUATION, Fixture, FixtureSet, load_fixture_set
from forgeai_eval.observer import ChatObserver, ObservationLog, ObservingModel
from forgeai_eval.preflight import PreflightError, verify_ollama
from forgeai_eval.report import build_report, write_report
from forgeai_eval.runner import BindingFactory, RunMetadata, RunSettings, evaluate

REVIEW_ACCEPT = EVALUATION / "replay" / "review_accept.json"
PREFLIGHT_FAILED = 3
# The observer waits slightly longer than the adapter, so the adapter's own
# timeout is what ForgeAI records; the run then waits for the observer.
OBSERVER_MARGIN_SECONDS = 5.0


def forgeai_commit(git: Path) -> str:
    """HEAD of the evaluated checkout, marked when the worktree is dirty."""
    root = EVALUATION.parents[2]
    head = subprocess.run(
        [str(git), "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        shell=False,
    ).stdout.strip()
    dirty = subprocess.run(
        [
            str(git),
            "status",
            "--porcelain",
            "--",
            "examples/forgeai/src",
            "src",
            "packages",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        shell=False,
    ).stdout.strip()
    return head + ("+dirty-runtime" if dirty else "")


def replay_bindings(
    fixture: Fixture, log: ObservationLog | None = None
) -> tuple[tuple[ModelBindingConfig, ...], str]:
    """Fresh replay model per run: the fixture's reference proposal, then accept."""
    model = ReplayModel(
        fixture.reference_proposal.read_text(encoding="utf-8"),
        REVIEW_ACCEPT.read_text(encoding="utf-8"),
    )
    if log is not None:
        return (replay_binding(ObservingModel(model, log)),), "replay"
    return (replay_binding(model),), "replay"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="forgeai-lq1")
    parser.add_argument("mode", choices=("replay", "live"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--model")
    parser.add_argument("--model-digest")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-timeout", type=float, default=600.0)
    parser.add_argument("--hardware")
    parser.add_argument("--git", type=Path, default=shutil.which("git"))
    parser.add_argument("--docker", type=Path, default=shutil.which("docker"))
    args = parser.parse_args(argv)
    if args.git is None or args.docker is None:
        parser.error("Git and Docker executables are required")
    fixtures: FixtureSet = load_fixture_set()
    log = ObservationLog()
    observer: ChatObserver | None = None
    if args.mode == "live":
        missing = [
            flag
            for flag, value in (
                ("--model", args.model),
                ("--model-digest", args.model_digest),
                ("--hardware", args.hardware),
                ("--repetitions", args.repetitions),
            )
            if not value
        ]
        if missing:
            parser.error("live mode requires " + ", ".join(missing))
        if args.repetitions < 3:
            parser.error("live baselines require --repetitions >= 3")
        try:
            identity = verify_ollama(args.ollama_url, args.model, args.model_digest)
        except ValueError as error:
            parser.error(str(error))
        except PreflightError as error:
            print(f"live preflight failed: {error}", file=sys.stderr)
            print("no fixture was run and no report was written", file=sys.stderr)
            return PREFLIGHT_FAILED
        # The real adapter reaches Ollama through the local observer, which
        # is started only for the evaluation itself.
        observer = ChatObserver(
            args.ollama_url, args.ollama_timeout + OBSERVER_MARGIN_SECONDS, log
        )
        live = observer
        model_name, timeout = identity.model_name, args.ollama_timeout

        def live_bindings(
            fixture: Fixture,
        ) -> tuple[tuple[ModelBindingConfig, ...], str]:
            return (ollama_binding(live.url, model_name, timeout),), "ollama"

        factory: BindingFactory = live_bindings
        # Observed and verified values only; operator text never overrides them.
        metadata_model = (
            identity.model_name,
            identity.model_digest,
            identity.ollama_version,
        )
        provider, binding_name = "ollama", "ollama"
    else:

        def observed_replay(
            fixture: Fixture,
        ) -> tuple[tuple[ModelBindingConfig, ...], str]:
            return replay_bindings(fixture, log)

        factory = observed_replay
        metadata_model = ("replay", "replay:reference-proposals", "not-applicable")
        provider, binding_name = "replay", "replay"
    repetitions = args.repetitions or 1
    metadata = RunMetadata(
        mode=args.mode,
        provider=provider,
        binding=binding_name,
        model_name=metadata_model[0],
        model_digest=metadata_model[1],
        ollama_version=metadata_model[2],
        forgeai_commit=forgeai_commit(args.git.resolve()),
        fixture_set=fixtures.name,
        fixture_revision=fixtures.revision,
        fixture_digest=fixtures.fixture_digest,
        hidden_revision=fixtures.hidden_revision,
        hidden_digest=fixtures.hidden_digest,
        hardware_class=args.hardware or "replay-self-test",
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        started_at=datetime.now(UTC).isoformat(timespec="seconds"),
        repetitions=repetitions,
    )
    if metadata.missing():
        parser.error("missing metadata: " + ", ".join(metadata.missing()))
    with TemporaryDirectory(prefix="forgeai-lq1-") as temporary:
        if observer is not None:
            observer.start()
        settings = RunSettings(
            bindings=factory,
            approve=terminal_approver(input if sys.stdin.isatty() else None, print),
            git=args.git.resolve(),
            docker=args.docker.resolve(),
            workdir=Path(temporary),
            observations=log,
            observation_wait_seconds=OBSERVER_MARGIN_SECONDS * 2,
        )
        try:
            runs, seconds = evaluate(fixtures, repetitions, settings)
        finally:
            if observer is not None:
                observer.close()
    json_path, markdown_path = write_report(
        build_report(metadata, fixtures, runs, seconds), args.output
    )
    print(f"report: {json_path}")
    print(f"report: {markdown_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
