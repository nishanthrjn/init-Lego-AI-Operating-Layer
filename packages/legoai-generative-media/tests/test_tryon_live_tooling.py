"""VTO-3 operator tooling, proven offline: read-only preflight, explicit --live,
counted writes, same-job digest check, template preparation."""

import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from media_support import (
    TRYON_MODELS,
    FakeHTTP,
    Transports,
    make_png,
    tryon_request,
    write_tryon_workflow,
)

from legoai_generative_media.config import TryOnConfig, load_try_on_config
from legoai_generative_media.service import (
    PreflightReport,
    WriteCounter,
    open_virtual_try_on,
    preflight_virtual_try_on,
)
from legoai_generative_media.tryon import tryon_template
from legoai_generative_media.values import Outcome

REPO = Path(__file__).resolve().parents[3]
LOCAL = "http://127.0.0.1:8188"


def load(name: str) -> ModuleType:
    path = REPO / "examples" / "virtual-try-on" / name
    spec = importlib.util.spec_from_file_location("vto3_" + path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config_file(
    tmp_path: Path, *, sha: str | None = None, remote: bool = False
) -> Path:
    path, digest = write_tryon_workflow(tmp_path)
    provider = (
        'endpoint = "https://comfy.example.org"\ndeployment = "remote"\n'
        'allowed_origins = ["https://comfy.example.org"]\n'
        '[provider.auth]\ntype = "bearer"\nsecret_ref = "env:COMFY_API_KEY"\n'
        if remote
        else f'endpoint = "{LOCAL}"\n'
    )
    text = (
        '[provider]\ntype = "comfyui"\napi_family = "legacy"\n'
        + provider
        + "[try_on]\n"
        + f'path = "{path.as_posix()}"\nsha256 = "{sha or digest}"\n'
        + f'diffusion_model = "{TRYON_MODELS.diffusion_model}"\n'
        + f'text_encoder = "{TRYON_MODELS.text_encoder}"\n'
        + f'vae = "{TRYON_MODELS.vae}"\n'
    )
    target = tmp_path / "tryon.toml"
    target.write_text(text, encoding="utf-8")
    return target


def config(
    tmp_path: Path, *, sha: str | None = None, remote: bool = False
) -> TryOnConfig:
    return load_try_on_config(config_file(tmp_path, sha=sha, remote=remote))


def preflight(
    tmp_path: Path, http: FakeHTTP, *, sha: str | None = None
) -> PreflightReport:
    return asyncio.run(
        preflight_virtual_try_on(
            config(tmp_path, sha=sha),
            environ={"COMFY_API_KEY": "sk-test"},
            transports=Transports({LOCAL: http}),
        )
    )


def test_preflight_pass_performs_no_writes(tmp_path: Path) -> None:
    http = FakeHTTP()
    report = preflight(tmp_path, http)
    assert report.ok
    lines = dict(report.lines)
    assert lines["local-only policy"] == "PASS"
    assert lines["provider reachable"] == "YES"
    assert lines["api family"] == "legacy 0.37.0"
    assert lines["upload capability"] == "PASS"
    assert lines["node preflight"] == "PASS"
    assert lines["approved template"] == "PASS try-on 768x1024"
    assert TRYON_MODELS.vae in lines["vae"]
    assert all(c[0] == "GET" for c in http.calls)
    assert http.uploads() == 0 and http.prompts() == []


@pytest.mark.parametrize(
    "field,label",
    [
        ("unet_name", "UNETLoader.unet_name"),
        ("clip_name", "CLIPLoader.clip_name"),
        ("vae_name", "VAELoader.vae_name"),
    ],
)
def test_preflight_names_missing_model(tmp_path: Path, field: str, label: str) -> None:
    http = FakeHTTP()
    http.models[field] = ("other.safetensors",)
    report = preflight(tmp_path, http)
    assert not report.ok and label in dict(report.lines)["node preflight"]
    assert all(c[0] == "GET" for c in http.calls)


def test_preflight_names_missing_node(tmp_path: Path) -> None:
    http = FakeHTTP()
    http.missing_nodes = {"TextEncodeQwenImageEditPlus"}
    report = preflight(tmp_path, http)
    assert "TextEncodeQwenImageEditPlus" in dict(report.lines)["node preflight"]


def test_preflight_remote_refused_before_any_io(tmp_path: Path) -> None:
    http = FakeHTTP()
    report = asyncio.run(
        preflight_virtual_try_on(
            config(tmp_path, remote=True),
            environ={"COMFY_API_KEY": "sk-test"},
            transports=Transports({"https://comfy.example.org": http}),
        )
    )
    assert not report.ok and report.lines[0][1].startswith("FAIL")
    assert http.calls == []


def test_preflight_rejects_unapproved_template_before_provider(tmp_path: Path) -> None:
    http = FakeHTTP()
    report = preflight(tmp_path, http, sha="0" * 64)
    assert not report.ok
    assert dict(report.lines)["approved template"].startswith("FAIL")
    assert http.calls == []


def test_preflight_unreachable_provider(tmp_path: Path) -> None:
    http = FakeHTTP()
    http.fail_at = "/system_stats"
    report = preflight(tmp_path, http)
    assert dict(report.lines)["provider reachable"] == "FAIL (provider_unavailable)"


def test_write_counter_counts_attempts_by_kind(tmp_path: Path) -> None:
    http = FakeHTTP()
    http.image = make_png(768, 1024)
    counter = WriteCounter(Transports({LOCAL: http}))
    service = asyncio.run(open_virtual_try_on(config(tmp_path), transports=counter))
    result = asyncio.run(service.try_on(tryon_request()))
    assert result.outcome is Outcome.SUCCESS
    assert (counter.uploads, counter.submissions) == (2, 1)
    asyncio.run(service.reconcile(service.job("job-1")))
    assert (counter.uploads, counter.submissions) == (2, 1)  # Reconcile adds none.


def cli_args(tmp_path: Path, **values: object) -> argparse.Namespace:
    person, garment = tmp_path / "person.png", tmp_path / "garment.png"
    person.write_bytes(make_png(96, 128))
    garment.write_bytes(make_png(80, 80, color=6))
    base: dict[str, object] = {
        "person": person,
        "garment": garment,
        "seed": 42,
        "output": tmp_path / "result.png",
    }
    base.update(values)
    return argparse.Namespace(**base)


def test_cli_generation_reports_counted_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = load("try_on_cli.py")
    http = FakeHTTP()
    http.image = make_png(768, 1024)
    counter = WriteCounter(Transports({LOCAL: http}))
    code = asyncio.run(cli.generate(cli_args(tmp_path), config(tmp_path), counter))
    out = capsys.readouterr().out
    assert code == 0
    for line in (
        "preflight: PASS",
        "uploads performed: 2",
        "submissions attempted: 1",
        "input_disclosure: completed",
        "outcome: success",
        "effect: completed",
        "width: 768 height: 1024",
        "elapsed seconds:",
        "SHA-256:",
    ):
        assert line in out, line
    assert (tmp_path / "result.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert "tEXt" not in out and "prompt" not in out.lower()


def test_cli_generation_stops_when_preflight_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = load("try_on_cli.py")
    http = FakeHTTP()
    http.models["unet_name"] = ()
    counter = WriteCounter(Transports({LOCAL: http}))
    code = asyncio.run(cli.generate(cli_args(tmp_path), config(tmp_path), counter))
    out = capsys.readouterr().out
    assert code == 1 and "preflight: FAIL" in out and "uploads performed: 0" in out
    assert http.uploads() == 0 and http.prompts() == []


def test_cli_reconcile_digest_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = load("try_on_cli.py")
    http = FakeHTTP()
    http.use_tryon_job()
    counter = WriteCounter(Transports({LOCAL: http}))
    service = asyncio.run(open_virtual_try_on(config(tmp_path), transports=counter))
    digest = hashlib.sha256(http.image).hexdigest()
    assert asyncio.run(cli.reconcile(service, "job-1", None, counter, digest)) == 0
    assert "digest matches generation: YES" in capsys.readouterr().out
    assert asyncio.run(cli.reconcile(service, "job-1", None, counter, "0" * 64)) == 1
    assert "digest matches generation: NO" in capsys.readouterr().out
    assert counter.uploads == 0 and counter.submissions == 0


@pytest.mark.parametrize(
    "argv",
    [
        [],  # A mode is required.
        ["--person", "p.png", "--garment", "g.png", "--output", "o.png"],  # No --live.
        ["--live"],  # --live needs inputs.
        ["--preflight", "--person", "p.png"],
        ["--live", "--preflight"],
        ["--preflight", "--expect-sha256", "ab"],
    ],
)
def test_cli_requires_explicit_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    cli = load("try_on_cli.py")
    monkeypatch.setattr("sys.argv", ["try_on_cli.py", "--config", "x.toml", *argv])
    with pytest.raises(SystemExit) as caught:
        cli.main()
    assert caught.value.code == 2  # Refused by the parser: no provider contact.


def test_prepare_template_from_config_never_overwrites(tmp_path: Path) -> None:
    tool = load("prepare_template.py")
    cfg = config_file(tmp_path)
    output = tmp_path / "prepared.json"
    assert tool.main(["--config", str(cfg), "--output", str(output)]) == 0
    expected = json.dumps(tryon_template(TRYON_MODELS), indent=2).encode() + b"\n"
    assert output.read_bytes() == expected
    with pytest.raises(SystemExit):
        tool.main(["--config", str(cfg), "--output", str(output)])
    with pytest.raises(SystemExit):
        tool.main(["--config", str(cfg), "--vae", "x.safetensors"])
