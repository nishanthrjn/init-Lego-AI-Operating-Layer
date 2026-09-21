"""Pack-local error type for the document.chunking capability.

This is intentionally not a new error hierarchy and does not extend or
modify ``legoai.kernel.errors``. A future governed Execution boundary may
map ``ChunkingValidationError`` to Lego AI's canonical ``ValidationError``
category (SPEC SS10); that mapping is not implemented here.
"""

from __future__ import annotations


class ChunkingValidationError(ValueError):
    """Raised when a document.chunking request has invalid parameters."""
