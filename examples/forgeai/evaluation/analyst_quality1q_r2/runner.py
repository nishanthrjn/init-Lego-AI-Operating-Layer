"""One r2 call: the unchanged 1Q request path, scored by 1Q and diagnosed by DIAG-1.

Exactly one governed Analyst call per (case, repetition). The 1Q reconciliation
and scoring and the DIAG-1 first-failure diagnosis are applied to the same
in-memory result; the reply text is then dropped. Nothing is retried or repaired.
"""

import asyncio
import time

from analyst_contract_diag1 import runner as diag
from analyst_contract_diag1.diagnose import COARSE
from analyst_quality1q.data import Case
from analyst_quality1q.harness import CallResult, _analyze, reconcile
from analyst_quality1q.metrics import score

from legoai.runtime.api import ModelBindingConfig


def run_call(
    case: Case, repetition: int, binding: ModelBindingConfig
) -> dict[str, object]:
    """One content-free r2 record."""
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
    return {
        **score(case, repetition, call),
        **diagnosis.as_record(),
        # The fine stage must refine the 1Q category of the very same reply.
        "coarse_consistent": COARSE[diagnosis.stage] == call.category.value,
    }
