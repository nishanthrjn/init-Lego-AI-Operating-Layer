"""Operator completion policy: one coherent, bounded, hardware-neutral setting."""

import asyncio
import dataclasses
import math
import time as real_time
from datetime import UTC, datetime

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import FakeHTTP, FakeTime, workflow

from legoai_generative_media.comfyui import (
    HARD_MAX_WAIT_SECONDS,
    ComfyUIConfig,
    CompletionPolicy,
    LocalComfyUIAdapter,
)
from legoai_generative_media.composition import invoke
from legoai_generative_media.http import Endpoint, LocalHTTP
from legoai_generative_media.local_host import prepare_local
from legoai_generative_media.values import (
    Cessation,
    Outcome,
    TextToImageRequest,
)


def test_default_policy_preserves_prior_behaviour() -> None:
    policy = CompletionPolicy()
    assert (policy.max_wait_seconds, policy.poll_interval_seconds) == (300, 1)
    assert policy.request_timeout_seconds == 10
    assert ComfyUIConfig(workflow()).completion == policy


@pytest.mark.parametrize("wait", [900, 900.0, HARD_MAX_WAIT_SECONDS])
def test_long_waits_accepted(wait: float) -> None:
    policy = CompletionPolicy(wait)
    assert (
        ComfyUIConfig(workflow(), completion=policy).completion.max_wait_seconds == wait
    )


@pytest.mark.parametrize(
    "wait",
    [0, -1, -900, HARD_MAX_WAIT_SECONDS + 0.01, math.inf, math.nan, None, True, "900"],
)
def test_invalid_total_wait_rejected(wait: object) -> None:
    with pytest.raises(ValueError):
        CompletionPolicy(wait)  # type: ignore[arg-type]


@pytest.mark.parametrize("interval", [0, -1, 91, 31, math.inf, math.nan, None, True])
def test_invalid_poll_interval_rejected(interval: object) -> None:
    # 900 s wait: interval must be positive, <=30 s and <= a tenth of the wait.
    with pytest.raises(ValueError):
        CompletionPolicy(900, interval)  # type: ignore[arg-type]


def test_poll_interval_materially_smaller_than_wait() -> None:
    with pytest.raises(ValueError):
        CompletionPolicy(5, 1)
    assert CompletionPolicy(10, 1).poll_interval_seconds == 1


@pytest.mark.parametrize("timeout", [0, -1, 61, math.inf, math.nan, None, True])
def test_invalid_request_timeout_rejected(timeout: object) -> None:
    with pytest.raises(ValueError):
        CompletionPolicy(900, 1, timeout)  # type: ignore[arg-type]


def test_request_timeout_cannot_exceed_total_wait() -> None:
    with pytest.raises(ValueError):
        CompletionPolicy(20, 1, 30)


def test_request_timeout_is_separate_from_total_wait() -> None:
    policy = CompletionPolicy(900, 1, 10)
    assert policy.request_timeout_seconds == 10 != policy.max_wait_seconds
    real = LocalComfyUIAdapter(ComfyUIConfig(workflow(), completion=policy))
    http = real._http()
    assert isinstance(http, LocalHTTP) and http.timeout == 10


@pytest.mark.parametrize(
    "wait,interval,per_request",
    [(900, 1, 10), (300, 1, 10), (1800, 1, 10), (5, 0.5, 5), (0.5, 0.05, 0.5)],
)
def test_single_operator_setting_derives_the_rest(
    wait: float, interval: float, per_request: float
) -> None:
    policy = CompletionPolicy.for_wait(wait)
    assert policy == CompletionPolicy(wait, interval, per_request)


@pytest.mark.parametrize("wait", [0, -1, HARD_MAX_WAIT_SECONDS + 1, math.inf, None])
def test_single_operator_setting_bounded(wait: object) -> None:
    with pytest.raises(ValueError):
        CompletionPolicy.for_wait(wait)  # type: ignore[arg-type]


def test_poll_count_is_derived() -> None:
    assert CompletionPolicy(900, 1).max_polls == 901
    assert CompletionPolicy(900, 2).max_polls == 451
    assert CompletionPolicy(300, 1).max_polls == 301


def test_no_stale_independent_timing_controls() -> None:
    names = {f.name for f in dataclasses.fields(ComfyUIConfig)}
    assert names == {"workflow", "endpoint", "binding", "completion"}
    for stale in ("timeout_seconds", "poll_interval", "max_polls"):
        with pytest.raises(TypeError):
            ComfyUIConfig(workflow(), **{stale: 1})  # type: ignore[arg-type]


def test_request_contract_is_hardware_neutral() -> None:
    assert [f.name for f in dataclasses.fields(TextToImageRequest)] == [
        "prompt",
        "seed",
    ]


@pytest.mark.parametrize("timeout", [0, -1, 61, math.nan, True])
def test_http_timeout_bounded(timeout: object) -> None:
    with pytest.raises(ValueError):
        LocalHTTP(Endpoint(), timeout)  # type: ignore[arg-type]


def adapter(http: FakeHTTP, time: FakeTime, wait: float) -> LocalComfyUIAdapter:
    return LocalComfyUIAdapter(
        ComfyUIConfig(workflow(), completion=CompletionPolicy(wait, 1, 10)),
        http,
        clock=time.clock,
        sleep=time.sleep,
    )


def test_long_job_completes_within_900_second_policy() -> None:
    http, time = FakeHTTP(), FakeTime()
    http.time, http.ready_at = time, 640  # Observed ~10m40s CPU run.
    started = real_time.monotonic()
    result = asyncio.run(
        adapter(http, time, 900).generate(TextToImageRequest("red mug", 42))
    )
    assert result.outcome is Outcome.SUCCESS and result.effect is EffectExtent.COMPLETED
    assert 640 <= time.now < 900
    assert http.posts() == 1
    assert real_time.monotonic() - started < 30  # Simulated, not slept.


def test_long_job_exceeds_configured_deadline() -> None:
    http, time = FakeHTTP(), FakeTime()
    http.time, http.ready_at = time, 640
    result = asyncio.run(
        adapter(http, time, 300).generate(TextToImageRequest("red mug", 42))
    )
    assert result.outcome is Outcome.DEADLINE
    assert result.error is ErrorCategory.DEADLINE_EXCEEDED
    assert result.effect is EffectExtent.UNKNOWN
    assert result.cessation is Cessation.UNKNOWN
    assert result.job is not None and result.job.job_id == "job-1"
    assert http.posts() == 1
    assert time.now == 300
    assert all("interrupt" not in c[1] for c in http.calls)


def test_one_hung_request_does_not_consume_total_wait() -> None:
    http, time = FakeHTTP(), FakeTime()
    http.wait_at = "/history"
    policy = CompletionPolicy(900, 1, 0.05)
    started = real_time.monotonic()
    result = asyncio.run(
        LocalComfyUIAdapter(
            ComfyUIConfig(workflow(), completion=policy),
            http,
            clock=time.clock,
            sleep=time.sleep,
        ).generate(TextToImageRequest("x"))
    )
    # A hung exchange is a dependency failure, not an exceeded total deadline.
    assert result.outcome is Outcome.FAILED
    assert result.error is ErrorCategory.DEPENDENCY_FAILURE
    assert result.effect is EffectExtent.UNKNOWN and result.job is not None
    assert http.posts() == 1
    assert real_time.monotonic() - started < 30


def test_governed_900_second_execution_has_no_hidden_ceiling() -> None:
    async def run() -> None:
        http, time = FakeHTTP(), FakeTime()
        http.time, http.ready_at = time, 640
        session = await prepare_local(
            adapter(http, time, 900), "r1", approved=workflow().reference, timeout=900
        )
        assert session.context.deadline is not None
        remaining = (session.context.deadline - datetime.now(UTC)).total_seconds()
        assert 890 < remaining <= 900
        _, output = await invoke(
            session.coordinator,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            TextToImageRequest("red mug", 42),
        )
        assert output.outcome is Outcome.SUCCESS and http.posts() == 1

    asyncio.run(run())


@pytest.mark.parametrize("timeout", [0, -5, HARD_MAX_WAIT_SECONDS + 1, math.inf, None])
def test_execution_timeout_bounded(timeout: object) -> None:
    with pytest.raises(ValueError):
        asyncio.run(
            prepare_local(
                LocalComfyUIAdapter(ComfyUIConfig(workflow()), FakeHTTP()),
                "r1",
                approved=workflow().reference,
                timeout=timeout,  # type: ignore[arg-type]
            )
        )
