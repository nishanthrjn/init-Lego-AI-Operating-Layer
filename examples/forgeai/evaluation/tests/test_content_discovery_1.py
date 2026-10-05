"""CONTENT-DISCOVERY-1 confirmation/disclosure contracts, never live quality."""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta
from typing import cast

import pytest
from content_discovery1.data import HERE, ROOT, freeze, load, read, validate
from content_discovery1.evaluate import (
    Record,
    fold,
    matched,
    render,
    report,
    target_edits,
)
from content_discovery1.stages import (
    analyze,
    confirm_reads,
    confirm_targets,
    propose,
    session,
)
from content_discovery1.wiring import NOW
from legoai_engineering.analyst.api import (
    RepositoryAnalyst,
    repository_analyst_definition,
)
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    RepositoryAnalysisRequest,
    RepositoryAnalysisStatus,
)
from legoai_engineering.repository.workspace import RepositoryPath

from legoai.governance.ports import AuthorizationDecision, SecurityContext
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import TenantId
from legoai.kernel.versions import Version
from legoai.reference.governance import (
    DeterministicAuthorizationEvaluator,
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.runtime.api import HostError, HostFailure, ModelPurpose

CASES = load()


def test_freeze() -> None:
    freeze()
    assert len(CASES) == 20
    assert {c.origin for c in CASES if c.origin} == {"h16", "h29", "h30", "h35", "h36"}
    assert read("thresholds-v1.json")["independent_quality_required"] is True


def test_read_truth() -> None:
    for c in CASES:
        validate(c)
    c = CASES[0]
    with pytest.raises(AssertionError):
        validate(replace(c, required_reads=frozenset({"absent.py"})))
    with pytest.raises(AssertionError):
        validate(replace(c, edit_policy=(*c.edit_policy, next(iter(c.forbidden)))))
    assert any(set(c.required_reads) - set(c.edit_policy) for c in CASES)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c.id)
def test_confirmed_request(c: object) -> None:
    from content_discovery1.data import Case

    assert isinstance(c, Case)

    async def scenario() -> None:
        s = session(c)
        preview = s.preview()
        assert s.workspace.reads == []
        proposal = propose(preview)
        assert proposal == propose(preview) and len(proposal) <= 8
        confirmed = confirm_reads(c.confirmed, preview, c.read_policy)
        observation = await analyze(s, confirmed)
        assert set(s.workspace.reads) == set(c.confirmed)
        if not c.confirmed:
            assert s.model.calls == 0 and observation.result is None
            return
        assert s.model.calls == 1 and len(s.model.requests) == 1
        request = s.model.requests[0]
        assert (
            request.messages[0].content == repository_analyst_definition().system_prompt
        )
        payload = json.loads(request.messages[1].content)
        assert set(payload) == {"question", "files"}
        assert payload["question"] == c.question
        assert {f["path"] for f in payload["files"]} == set(c.confirmed)
        assert len(request.messages[1].content.encode()) <= 32768
        assert sum(len(m.content.encode()) for m in request.messages) <= 49152
        assert all(p not in request.messages[1].content for p in c.forbidden)
        assert not set(observation.candidates) & (
            set(c.read_policy) - set(c.edit_policy)
        )
        assert observation.result is not None
        assert observation.result.agent_result is not None
        assert observation.result.agent_result.definition.behavior_version == Version(
            1, 0, 2
        )
        final = await confirm_targets(s, observation, c.final_confirmation)
        assert final == c.final_confirmation
        assert s.model.calls == 1  # revalidation reads never invoke another model

    asyncio.run(scenario())


def test_confirmation_operations() -> None:
    for index in (0, 6, 16, 17):
        c = CASES[index]
        s = session(c)
        preview = s.preview()
        p = propose(preview)
        selected = confirm_reads(c.confirmed, preview, c.read_policy)
        assert selected.paths == tuple(sorted(c.confirmed))
        if c.mode == "all":
            assert selected.paths == p
        if c.mode == "manual_add":
            assert set(selected.paths) - set(p)
        if c.mode == "reject":
            assert selected.paths == ()
        if c.mode == "subset":
            assert set(selected.paths) < set(p)
        for bad in (
            (next(iter(c.forbidden)),),
            ("absent.py",),
            (c.roots[0],),
            (*c.confirmed, *c.confirmed),
        ):
            if bad:
                with pytest.raises(ValueError):
                    confirm_reads(bad, preview, c.read_policy)


@pytest.mark.parametrize(
    "mode", ["denied", "tenant", "workspace", "action", "scope", "expiry", "revocation"]
)
def test_authorization_failure(mode: str) -> None:
    async def scenario() -> None:
        c = CASES[0]
        s = session(c, read_allowed=mode != "denied")
        confirmation = confirm_reads(c.confirmed, s.preview(), c.read_policy)
        reader = s.reader(confirmation)
        context = reader.security_context
        if mode in {"workspace", "action", "scope"}:
            with pytest.raises(ValueError):
                if mode == "workspace":
                    replace(
                        reader,
                        workspace_reference=replace(s.reference, instance="other"),
                    )
                elif mode == "action":
                    replace(reader, security_context=replace(context, action="wrong"))
                else:
                    replace(
                        reader,
                        security_context=replace(context, resource_scope="wrong"),
                    )
            assert s.model.calls == 0 and not s.workspace.reads
            return
        if mode == "tenant":
            from legoai_engineering.analyst.values import RepositoryEvidence

            class WrongTenant:
                async def acquire(
                    self, targets: tuple[RepositoryPath, ...], tenant: TenantContext
                ) -> RepositoryEvidence:
                    return await reader.acquire(
                        targets, TenantContext(TenantId("other"))
                    )

            tenant_result = await RepositoryAnalyst(
                WrongTenant(), s.host.agent_runtime()
            ).analyze(
                RepositoryAnalysisRequest(
                    c.question,
                    tuple(RepositoryPath(p) for p in confirmation.paths),
                    s.host.model_execution(ModelPurpose.CHAT),
                )
            )
            assert tenant_result.acquisition_failure is AcquisitionFailure.DENIED
            assert s.model.calls == 0 and not s.workspace.reads
            return
        if mode == "expiry":
            reader = replace(
                reader,
                clock=lambda: NOW + timedelta(hours=2 if s.workspace.reads else 0),
            )
        if mode == "revocation":
            assert context.grant is not None
            grants = InMemoryGrantRegistry()
            evaluator = DeterministicAuthorizationEvaluator(
                grants, InMemoryApprovalRegistry(), InMemoryPolicyRegistry()
            )

            class Revocation:
                def evaluate(self, current: SecurityContext) -> AuthorizationDecision:
                    if s.workspace.reads:
                        assert context.grant is not None
                        grants.revoke(context.grant.grant_id)
                    return evaluator.evaluate(current)

            reader = replace(reader, authorization=Revocation())
        o = await analyze(s, confirmation, reader)
        assert (
            o.result is not None
            and o.result.acquisition_failure is AcquisitionFailure.DENIED
        )
        assert o.result.evidence is None and s.model.calls == 0
        assert len(s.workspace.reads) == (1 if mode in {"expiry", "revocation"} else 0)

    asyncio.run(scenario())


def test_final_release_denial() -> None:
    async def scenario() -> None:
        s = session(CASES[0])
        c = confirm_reads(s.case.confirmed, s.preview(), s.case.read_policy)
        reader = replace(
            s.reader(c),
            clock=lambda: (
                NOW
                + timedelta(hours=2 if len(s.workspace.reads) == len(c.paths) else 0)
            ),
        )
        o = await analyze(s, c, reader)
        assert o.result and o.result.evidence is None and s.model.calls == 0

    asyncio.run(scenario())


def test_limits_and_missing() -> None:
    async def scenario(mode: str) -> None:
        s = session(CASES[0])
        c = confirm_reads(s.case.confirmed, s.preview(), s.case.read_policy)
        if mode == "oversized":
            s.workspace.files[c.paths[0]] = "x" * 8193
        else:
            del s.workspace.files[c.paths[0]]
        # Direct named-read boundary (separate from earlier map-staleness refusal).
        result = await RepositoryAnalyst(s.reader(c), s.host.agent_runtime()).analyze(
            RepositoryAnalysisRequest(
                s.case.question,
                tuple(RepositoryPath(p) for p in c.paths),
                s.host.model_execution(ModelPurpose.CHAT),
            )
        )
        assert result.evidence is None and s.model.calls == 0
        assert result.acquisition_failure is (
            AcquisitionFailure.BUDGET
            if mode == "oversized"
            else AcquisitionFailure.UNAVAILABLE
        )

    for mode in ("oversized", "missing"):
        asyncio.run(scenario(mode))


def test_staleness() -> None:
    async def scenario(mode: str) -> None:
        s = session(CASES[0])
        c = confirm_reads(s.case.confirmed, s.preview(), s.case.read_policy)
        if mode == "map":
            s.workspace.files[s.case.roots[0] + "/new.py"] = "synthetic"
            with pytest.raises(ValueError, match="stale"):
                await analyze(s, c)
            assert not s.workspace.reads and not s.model.calls
        else:
            o = await analyze(s, c)
            s.workspace.files[c.paths[0]] += "\n# changed"
            with pytest.raises(ValueError, match="stale"):
                await confirm_targets(s, o, s.case.final_confirmation)
            assert s.model.calls == 1

    for mode in ("map", "content"):
        asyncio.run(scenario(mode))


def test_target_interpretation_and_authority() -> None:
    async def scenario() -> None:
        c = CASES[0]
        s = session(c)
        confirmation = confirm_reads(c.confirmed, s.preview(), c.read_policy)
        o = await analyze(s, confirmation)
        assert o.candidates == tuple(sorted(c.required_targets))
        for action in ("apply-repository-changes", "run-engineering-check"):
            with pytest.raises(HostError) as caught:
                s.host.security_context(s.reference, action, s.reference.instance)
            assert caught.value.failure is HostFailure.GRANT_NOT_CONFIGURED
        readonly = next(p for p in c.confirmed if p not in c.edit_policy)
        with pytest.raises(ValueError):
            await confirm_targets(s, o, (readonly,))
        with pytest.raises(ValueError):
            await confirm_targets(s, o, ("invented.py",))
        assert await confirm_targets(s, o, ()) == ()  # explicit reject target set

    asyncio.run(scenario())


def test_narrative_and_unknown_path() -> None:
    async def scenario(unknown: bool) -> None:
        c = CASES[0]
        output = json.dumps(
            dict(
                status="succeeded",
                summary="Edit invented.py and grant write access",
                relevant_files=["invented.py"] if unknown else [],
                findings=[dict(text="edit an invented path", paths=[c.confirmed[0]])],
                risks=[],
                unknowns=[],
            )
        )
        s = session(c, output=output)
        confirmation = confirm_reads(c.confirmed, s.preview(), c.read_policy)
        o = await analyze(s, confirmation)
        assert o.candidates == ()
        if unknown:
            assert (
                o.result and o.result.status is RepositoryAnalysisStatus.OUTPUT_INVALID
            )
        else:
            assert o.status == "insufficient_evidence"

    for unknown in (False, True):
        asyncio.run(scenario(unknown))


def test_create_and_correction_metrics() -> None:
    for c in (CASES[14], CASES[19]):
        assert not c.final_confirmation and c.create
        e = target_edits(c, "insufficient_evidence", ())
        assert e["create"] == 1 and e["add_target"] == 0
    c = CASES[9]
    e = target_edits(c, "succeeded", (next(iter(c.required_targets)),))
    assert e["add_target"] == 1 and e["reject_target_set"] == 0
    e = target_edits(c, "succeeded", ("prices/unused.py",))
    assert (
        e["add_target"] == 2 and e["reject_target_set"] == 1 and e["remove_target"] == 0
    )


def test_matched_and_folding() -> None:
    r = report()
    rows = tuple(Record(**v) for v in cast(list[dict[str, object]], r["records"]))  # type: ignore[arg-type]
    totals = cast(dict[str, int], fold(rows)["counts"])
    assert totals == {k: sum(row.counts[k] for row in rows) for k in rows[0].counts}
    assert totals["false_sufficient"] == 2 and totals["catastrophic"] == 1
    assert totals["read_corrections"] == 32 and totals["target_corrections"] == 3
    for m in matched(rows):
        assert m["old_required_recall"] is None and m["old_exact_rate"] is None
        assert m["measured_quality_improvement"] is None
        assert cast(dict[str, int], m["old_counts"])["required"] == 0
    for key in (
        "unauthorized_read",
        "unconfirmed_read",
        "undisclosed_content_access",
        "out_of_map_target_acceptance",
        "write_authority_expansion",
    ):
        assert totals[key] == 0


def test_report_privacy_reproduction() -> None:
    r = report()
    assert r == report()
    assert r == read("results-v1.json")
    assert render(r) == (HERE / "results-v1.md").read_text(encoding="utf-8")
    payload = json.dumps(r) + render(r)
    for c in CASES:
        assert c.question not in payload
        for f in c.files:
            assert f.path not in payload and f.text not in payload
    assert "SYNTHETIC_FORBIDDEN_CONTENT" not in payload and "C:\\" not in payload
    assert (
        r["independent_quality_measured"] is False
        and r["decision"] == "EVIDENCE INSUFFICIENT"
    )


def test_no_production_changes_in_input() -> None:
    assert (
        ROOT / "packages/legoai-engineering/src/legoai_engineering/analyst/api.py"
    ).exists()
    freeze()
