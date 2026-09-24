"""Offline governed Reviewer: a textual opinion with no approval or mutation."""

import asyncio
import json

from governed_demo import create_governed_demo
from legoai.execution.agent.values import AgentId

from legoai_engineering.reviewer.api import IndependentReviewer
from legoai_engineering.reviewer.values import ReviewMaterial, ReviewRequest


async def main() -> None:
    output = json.dumps(
        {
            "decision": "changes_required",
            "summary": "The proposal needs a missing-input policy.",
            "findings": [
                {
                    "category": "correctness",
                    "severity": "blocking",
                    "message": "The proposed conversion does not handle missing input.",
                    "evidence_refs": ["proposal", "requirement"],
                    "required_action": "Specify the behavior for missing input.",
                }
            ],
            "risks": [],
            "unknowns": ["No implementation or deterministic test was supplied."],
        }
    )
    demo = create_governed_demo(output)
    request = ReviewRequest(
        AgentId("proposal-author"),
        "Review this proposal for input handling.",
        ("Check the explicit missing-input requirement.",),
        "Convert the supplied string to an integer and return it.",
        (ReviewMaterial("requirement", "Missing input must yield a clear failure."),),
        demo.context,
    )
    result = await IndependentReviewer(demo.runtime).review(request)
    assert result.review is not None and demo.model.calls == 1
    print(result.review.decision.value)
    print(result.review.findings[0].category.value)
    print(result.review.summary)


if __name__ == "__main__":
    asyncio.run(main())
