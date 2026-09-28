"""Collate one air-temperature reading reported by three invented feeds.

Every feed describes the same station, time, metric and unit, so all
readings share one ComparisonContext. feed-a outranks feed-b; feed-c is not
in the policy, so it is kept but excluded.

    uv run python examples/station_reading.py
"""

from decimal import Decimal

from legoai_collation import (
    Collation,
    ComparisonContext,
    DecimalRule,
    PrecedencePolicy,
    RawInput,
    Reading,
    SourceId,
    SourceRef,
    canonical_decimal_text,
    collate_field,
)

CONTEXT = ComparisonContext(
    "demo-station-01",
    "air_temperature",
    (("observed_at", "2026-03-01T06:00:00Z"), ("unit", "degC")),
)
POLICY = PrecedencePolicy(
    "demo-feeds/1", ((SourceId("feed-a"), 0), (SourceId("feed-b"), 1))
)
RULE = DecimalRule(allow_negative_sign=True, max_fraction_digits=2)


def reading(source: str, raw: RawInput) -> Reading:
    return Reading(SourceRef(SourceId(source)), CONTEXT, raw, RULE)


def _text(value: str | Decimal | None) -> str:
    if isinstance(value, Decimal):
        return canonical_decimal_text(value)
    return "none" if value is None else value


def summary(collation: Collation) -> str:
    values = ",".join(_text(value) for value in collation.distinct_values)
    disagreement = "yes" if collation.has_disagreement else "no"
    return (
        f"{collation.status.value} selected={_text(collation.selected)} "
        f"disagreement={disagreement} values={values}"
    )


def main() -> None:
    agreed = collate_field(
        CONTEXT,
        (
            reading("feed-a", RawInput.of("4.20")),
            reading("feed-b", RawInput.of(Decimal("4.2"))),
        ),
        POLICY,
    )
    selected = collate_field(
        CONTEXT,
        (
            reading("feed-c", RawInput.of("4.4")),
            reading("feed-b", RawInput.of("4.6")),
            reading("feed-a", RawInput.of("4.20")),
        ),
        POLICY,
    )
    print(summary(agreed))
    print(summary(selected))
    for candidate in selected.candidates:
        rank = "none" if candidate.rank is None else str(candidate.rank)
        print(
            f"{candidate.reading.ref.source.value} rank={rank} "
            f"raw={candidate.reading.raw.value!s} {candidate.admission.value}"
        )


if __name__ == "__main__":
    main()
