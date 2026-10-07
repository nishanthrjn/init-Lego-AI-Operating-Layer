"""Closed deterministic full-set matching; semantic errors confer no authority."""

import re
import unicodedata
from dataclasses import dataclass

from legoai_engineering.analyst.sufficiency import EvidenceRequest

from analyst_design_eval2.data import Criterion, Policy


def normalize(text: str) -> str:
    value = " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))
    for prefix in (
        "could you please provide ",
        "please provide ",
        "please clarify ",
        "provide ",
        "show ",
    ):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    return value


def matches(r: EvidenceRequest, c: Criterion) -> bool:
    if r.kind.value != c.kind:
        return False
    if c.kind == "named_evidence":
        return r.path is not None and r.path.value == c.path
    if r.path is not None:
        return False
    if normalize(r.description) not in {normalize(t) for t in c.alternatives}:
        return False
    if c.kind == "operator_clarification":
        if not r.choices:
            return True
        matched = [
            next(
                (
                    i
                    for i, group in enumerate(c.choice_groups)
                    if normalize(choice) in {normalize(x) for x in group}
                ),
                -1,
            )
            for choice in r.choices
        ]
        return len(matched) == len(set(matched)) and set(matched) == set(
            range(len(c.choice_groups))
        )
    return not r.choices


def canonical(r: EvidenceRequest) -> tuple[str, str, str, tuple[str, ...]]:
    return (
        r.kind.value,
        r.path.value if r.path else "",
        "" if r.path else normalize(r.description),
        tuple(sorted(normalize(x) for x in r.choices)),
    )


@dataclass(frozen=True)
class SetScore:
    required: int
    covered: int
    emitted: int
    allowed_extra: int
    matched: int
    under: int
    over: int
    forbidden: int
    invented: int
    duplicates: int
    exact: bool
    acceptable: bool


def score_requests(requests: tuple[EvidenceRequest, ...], p: Policy) -> SetScore:
    seen: set[object] = set()
    covered: set[str] = set()
    matched = over = forbidden = invented = duplicates = 0
    all_criteria = (*p.required, *p.allowed)
    for r in requests:
        candidates = [c for c in all_criteria if matches(r, c)]
        semantic: object = candidates[0].id if candidates else canonical(r)
        duplicate = semantic in seen
        seen.add(semantic)
        duplicates += int(duplicate)
        bad = r.path is not None and r.path.value in p.forbidden_paths
        forbidden += int(bad)
        invented += int(
            r.path is not None
            and not any(
                c.kind == "named_evidence" and c.path == r.path.value
                for c in all_criteria
            )
        )
        if candidates and not duplicate and not bad:
            matched += 1
            covered.update(c.id for c in candidates if c in p.required)
        else:
            over += 1
    under = len(p.required) - len(covered)
    acceptable = (
        under == 0
        and over == 0
        and forbidden == 0
        and invented == 0
        and duplicates == 0
    )
    return SetScore(
        len(p.required),
        len(covered),
        len(requests),
        matched - len(covered),
        matched,
        under,
        over,
        forbidden,
        invented,
        duplicates,
        acceptable and len(requests) == len(p.required),
        acceptable,
    )


def unresolved_mixed(
    requests: tuple[EvidenceRequest, ...], *, one_round_resolves: bool
) -> bool:
    kinds = {r.kind.value for r in requests}
    return (
        "operator_clarification" in kinds
        and bool(kinds - {"operator_clarification"})
        and not one_round_resolves
    )
