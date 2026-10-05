"""One R3 call: 1Q scoring, DIAG-1 diagnosis and clause observation, one reply.

Exactly one governed Analyst call per (case, repetition) on the unchanged 1Q
request path. Every view is derived from the same in-memory result; the reply
text is then dropped. Nothing is retried, repaired or written.
"""

import asyncio
import time

from analyst_contract_diag1 import runner as diag
from analyst_contract_diag1.diagnose import COARSE
from analyst_insufficient_diag1.clauses import observe
from analyst_quality1q.data import Case
from analyst_quality1q.harness import CallResult, _analyze, reconcile
from analyst_quality1q.metrics import score

from legoai.runtime.api import ModelBindingConfig


def run_call(
    case: Case, repetition: int, binding: ModelBindingConfig
) -> dict[str, object]:
    """One content-free R3 record."""
    started = time.perf_counter()
    result, workspace = asyncio.run(_analyze(case, binding))
    seconds = round(time.perf_counter() - started, 3)
    view = reconcile(result, case)
    call = CallResult(
        view.status,
        view.category,
        view.relevant,
        view.accepted_paths,
        tuple(workspace.reads),
        seconds,
    )
    diagnosis, _, _ = diag.reconcile(result, case)
    agent = result.agent_result
    reply = agent.output if agent is not None else None
    return {
        **score(case, repetition, call),
        **diagnosis.as_record(),
        **observe(diagnosis, reply),
        "coarse_consistent": COARSE[diagnosis.stage] == call.category.value,
    }
