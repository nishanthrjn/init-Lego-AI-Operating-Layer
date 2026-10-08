"""Presentation and configuration: bounded summary, exit codes, binding switch."""

import argparse
import asyncio
from pathlib import Path

import pytest
from forgeai_support import (
    FakeSandbox,
    approve,
    config,
    proposal,
    replay,
    repository,
    task,
)
from legoai_engineering.repository.mutation import FileChangeKind

from demo import OBJECTIVE, TARGETS
from forgeai.cli import _target, main, ollama_binding, summarize
from forgeai.composition import prepare_run
from forgeai.guard import WorkspaceGuard


def test_target_parsing_is_closed() -> None:
    assert _target("src/a.py").operation is FileChangeKind.UPDATE
    assert _target("src/b.py:create").operation is FileChangeKind.CREATE
    with pytest.raises(argparse.ArgumentTypeError):
        _target("src/a.py:delete")


def test_dirty_repository_exits_rejected_without_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = repository(tmp_path)
    (root / "untracked.txt").write_text("x\n", encoding="utf-8")
    replay = tmp_path / "proposal.json"
    replay.write_text(proposal(), encoding="utf-8")
    arguments = [str(root), "--objective", OBJECTIVE, "--replay", str(replay)]
    for target in TARGETS:
        arguments += ["--target", target]
    assert main(arguments, ready=lambda config: None) == 2
    output = capsys.readouterr().out
    assert "disposition: rejected" in output
    assert "repository has pre-existing changes" in output


def test_replay_binding_requires_recorded_output(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main([str(tmp_path), "--objective", "x", "--target", "a.py"])


def test_summary_is_bounded_and_omits_contents(tmp_path: Path) -> None:
    root = repository(tmp_path)
    prepared = prepare_run(
        config(root, replay()), WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    text = summarize(result)
    assert text.splitlines()[0] == "disposition: succeeded"
    assert "raise ValueError" not in text and len(text) < 4096
    assert "check pytest: passed" in text


def test_ollama_binding_is_configuration_only(tmp_path: Path) -> None:
    # Composition validates and binds Ollama without contacting it; the worker
    # code is identical to the replay binding.
    root = repository(tmp_path)
    cfg = config(
        root,
        replay(),
        extra=(ollama_binding("http://127.0.0.1:11434", "qwen2.5-coder:7b", 30.0),),
        binding="ollama",
    )
    prepared = prepare_run(
        cfg, WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )
    assert type(prepared.worker).__name__ == "RepositoryTaskWorker"
