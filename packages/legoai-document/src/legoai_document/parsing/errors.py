"""Pack-local error hierarchy for the document.parsing capability.

Deliberately shallow -- three leaf categories under one base, matching what
live verification (see DOCUMENT-PARSING-CAPABILITY-DESIGN.md SS13, SS18a)
showed is actually distinguishable and actionable. No raw `pypdf` exception
is ever part of this capability's public API. A future governed Execution
boundary may map these to Lego AI's canonical error categories (SPEC SS10);
that mapping is not implemented here.
"""

from __future__ import annotations


class DocumentParsingError(Exception):
    """Base for all document.parsing failures."""


class UnsupportedDocumentFormatError(DocumentParsingError):
    """Raised when the declared DocumentFormat has no v1 realization."""


class MalformedDocumentError(DocumentParsingError):
    """Raised when declared-format content cannot be parsed as that format."""


class EncryptedDocumentError(DocumentParsingError):
    """Raised when a PDF is encrypted/password-protected and unreadable
    without a password. No password-input support exists in v1."""
