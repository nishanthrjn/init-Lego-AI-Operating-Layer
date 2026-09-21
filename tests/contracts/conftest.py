"""Replace/parameterize this factory to run the same vectors on a later adapter."""

from collections.abc import Callable

import pytest

from legoai.application.ports import ConfigurationOwnerStore
from tests.support.configuration_store import ConfigurationStoreFake


@pytest.fixture
def store_factory() -> Callable[[str], ConfigurationOwnerStore]:
    return ConfigurationStoreFake
