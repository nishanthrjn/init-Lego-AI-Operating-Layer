"""Collation input errors.

Messages name the failing position or limit, never a raw value. Wrong Python
types raise the built-in ``TypeError`` and malformed rule or identity values
raise ``ValueError``, matching the rest of LegoAI.
"""


class CollationError(ValueError):
    """Base class for inputs this package refuses to collate."""


class LimitExceededError(CollationError):
    """An input exceeds a local protection bound before any work is done."""


class MixedContextError(CollationError):
    """A reading describes a different subject, field or qualifier set."""


class IncompatibleRulesError(CollationError):
    """Readings normalize to different value kinds or choice vocabularies."""


class DuplicateReadingError(CollationError):
    """Two readings share an identity, or a source's readings lack locators.

    Duplicates are never merged or discarded silently.
    """
