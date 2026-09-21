"""Actual F4 values for codec tests; no synthetic historical release."""

from legoai.application.ports import DutyPage, PendingSourceDuty, PublicationResult
from tests.contracts.test_configuration_store import command, published, query, subject
from tests.support.configuration_store import ConfigurationStoreFake


def committed(*, update: bool = False, duty: bool = True) -> PublicationResult:
    store = ConfigurationStoreFake("codec-fixture")
    first = published(store, command(subject(), "first", duty=duty))
    if update:
        return published(
            store,
            command(
                subject(),
                "second",
                first.record.head.revision,
                duty,
                {"max_input_length": 123, "allowed_whitespace": []},
            ),
        )
    return first


def pending() -> PendingSourceDuty:
    store = ConfigurationStoreFake("codec-fixture")
    published(store, command(subject(), "first", duty=True))
    page = store.list_obligations(query(subject()))
    assert isinstance(page, DutyPage)
    return page.duties[0]
