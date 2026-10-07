"""Private SQLite mechanics, not a persistence Port or domain transaction API.

Separate owner files/schemas; a sidecar EXCLUSIVE transaction admits one writer
incarnation. Crash releases that lock. No busy retries or recovery initialization.
"""

import sqlite3
from pathlib import Path


class _StorageGap(RuntimeError):
    pass


class _Conflict(ValueError):
    pass


class _ScopeDenied(PermissionError):
    pass


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    conn = None
    try:
        uri = path.resolve().as_uri() + ("?mode=ro" if readonly else "?mode=rw")
        conn = sqlite3.connect(uri, uri=True, timeout=0, autocommit=True)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=0")
        if not readonly:
            conn.execute("PRAGMA synchronous=EXTRA")
        if conn.execute("PRAGMA journal_mode").fetchone() != ("delete",):
            conn.close()
            raise _StorageGap("unsupported journal profile")
        return conn
    except sqlite3.Error:
        if conn is not None:
            conn.close()
        raise _StorageGap("custody storage unavailable") from None


def _check(conn: sqlite3.Connection, owner: str) -> None:
    try:
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise _StorageGap("custody integrity gap")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise _StorageGap("custody reference gap")
        if conn.execute("SELECT owner,version FROM metadata").fetchall() != [
            (owner, 1)
        ]:
            raise _StorageGap("custody schema mismatch")
    except sqlite3.Error:
        raise _StorageGap("custody schema gap") from None


def _provision(path: Path, owner: str, schema: str) -> None:
    """Explicit new-store operation only. Never called by reopen/recovery."""
    with path.open("xb"):
        pass
    conn = _connect(path)
    try:
        conn.executescript(
            "BEGIN IMMEDIATE; CREATE TABLE metadata(owner TEXT NOT NULL,version INTEGER NOT NULL,binding TEXT);"
            + schema
        )
        conn.execute("INSERT INTO metadata VALUES (?,1,NULL)", (owner,))
        conn.execute("COMMIT")
    finally:
        conn.close()
    lock = path.with_suffix(path.suffix + ".writer")
    with lock.open("xb"):
        pass
    admission = _connect(lock)
    try:
        admission.execute("CREATE TABLE admission(owner TEXT NOT NULL)")
        admission.execute("INSERT INTO admission VALUES (?)", (owner,))
    finally:
        admission.close()


def _admit(path: Path, owner: str) -> sqlite3.Connection:
    conn = _connect(path.with_suffix(path.suffix + ".writer"))
    try:
        conn.execute("BEGIN EXCLUSIVE")
        if conn.execute("SELECT owner FROM admission").fetchall() != [(owner,)]:
            raise _StorageGap("writer admission mismatch")
        return conn
    except sqlite3.Error, _StorageGap:
        conn.close()
        raise _StorageGap("writer admission unavailable") from None


def _commit(conn: sqlite3.Connection) -> None:
    """Single commit seam also used by deterministic process-death tests."""
    conn.execute("COMMIT")


def _bind(conn: sqlite3.Connection, binding: str, *, readonly: bool) -> None:
    """Pin this physical owner store to one admitted scope; never rebind it.

    Scope comparison is not authentication. Trusted composition establishes the
    admission before constructing a private adapter.
    """
    try:
        row = conn.execute("SELECT binding FROM metadata").fetchone()
        if row == (binding,):
            return
        if row != (None,) or readonly:
            raise _ScopeDenied("custody scope unavailable")
        conn.execute("BEGIN IMMEDIATE")
        updated = conn.execute(
            "UPDATE metadata SET binding=? WHERE binding IS NULL", (binding,)
        )
        if updated.rowcount != 1:
            raise _ScopeDenied("custody scope unavailable")
        _commit(conn)
    except sqlite3.Error:
        raise _StorageGap("custody scope history unavailable") from None
    finally:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
