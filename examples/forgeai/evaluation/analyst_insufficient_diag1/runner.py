"""One diagnostic call on the unchanged 1Q/r2 request path.

The governed host, evidence reader, request and RepositoryAnalyst 1.0.1 are
exactly r2's. The 1Q category, the DIAG-1 first-failure stage and the clause
refinement are all derived from the same in-memory result; the reply is then
dropped. Nothing is retried, repaired or written.
"""

import asyncio
import time

from analyst_contract_diag1 import runner as diag
from analyst_contract_diag1.diagnose import COARSE
from analyst_quality1q.data import Case
from analyst_quality1q.harness import _analyze, reconcile

from analyst_insufficient_diag1.clauses import observe
from legoai.runtime.api import ModelBindingConfig


def run_call(
    case: Case, repetition: int, binding: ModelBindingConfig
) -> dict[str, object]:
    """One content-free diagnostic record."""
    started = time.perf_counter()
    result, _ = asyncio.run(_analyze(case, binding))
    seconds = round(time.perf_counter() - started, 3)
    category = reconcile(result, case).category.value
    diagnosis, _, _ = diag.reconcile(result, case)
    agent = result.agent_result
    reply = agent.output if agent is not None else None
    return {
        "case": case.id,
        "partition": case.partition,
        "class": case.klass,
        "repetition": repetition,
        "expected": case.oracle.expected,
        "runtime_status": result.status.value,
        "category": category,
        "stage": diagnosis.stage.value,
        "representation": diagnosis.representation,
        **observe(diagnosis, reply),
        "coarse_consistent": COARSE[diagnosis.stage] == category,
        "seconds": seconds,
    }
