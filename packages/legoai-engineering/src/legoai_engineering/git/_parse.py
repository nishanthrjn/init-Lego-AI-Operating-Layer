"""Private strict porcelain-v2 parser; no I/O or raw output in failures."""

from legoai_engineering.git.errors import GitError, GitFailure
from legoai_engineering.git.values import (
    GitChange,
    GitCommitId,
    GitHead,
    GitHeadKind,
    GitRepositoryState,
    GitStatusEntry,
)
from legoai_engineering.repository.workspace import RepositoryPath


def parse_status(data: bytes, max_entries: int) -> GitRepositoryState:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise GitError(GitFailure.DECODE) from error
    if not text.endswith("\0"):
        raise GitError(GitFailure.FORMAT)
    headers: dict[str, str] = {}
    entries: list[GitStatusEntry] = []
    try:
        for record in text[:-1].split("\0"):
            if record.startswith("# "):
                key, value = record[2:].split(" ", 1)
                if key not in {
                    "branch.oid",
                    "branch.head",
                    "branch.upstream",
                    "branch.ab",
                }:
                    raise GitError(GitFailure.FORMAT)
                if key in headers or entries:
                    raise GitError(GitFailure.FORMAT)
                headers[key] = value
                continue
            if len(entries) >= max_entries:
                raise GitError(GitFailure.ENTRY_LIMIT)
            if record.startswith("? "):
                entries.append(
                    GitStatusEntry(
                        RepositoryPath(record[2:]),
                        GitChange.UNCHANGED,
                        GitChange.UNCHANGED,
                        True,
                    )
                )
            elif record.startswith("1 "):
                fields = record.split(" ", 8)
                if len(fields) != 9 or len(fields[1]) != 2:
                    raise GitError(GitFailure.FORMAT)
                if fields[2] != "N..." or "160000" in fields[3:6]:
                    raise GitError(GitFailure.UNSUPPORTED)
                if any(
                    mode not in {"000000", "100644", "100755"} for mode in fields[3:6]
                ):
                    raise GitError(GitFailure.UNSUPPORTED)
                if any(
                    not 1 <= len(oid) <= 128
                    or any(char not in "0123456789abcdef" for char in oid)
                    for oid in fields[6:8]
                ):
                    raise GitError(GitFailure.FORMAT)
                entries.append(
                    GitStatusEntry(
                        RepositoryPath(fields[8]),
                        GitChange(fields[1][0]),
                        GitChange(fields[1][1]),
                        False,
                    )
                )
            elif record.startswith(("u ", "2 ")):
                raise GitError(GitFailure.UNSUPPORTED)
            else:
                raise GitError(GitFailure.FORMAT)
        oid = headers["branch.oid"]
        branch = headers["branch.head"]
        if oid == "(initial)":
            head = GitHead(GitHeadKind.UNBORN, branch, None)
            if branch == "(detached)":
                raise GitError(GitFailure.FORMAT)
        elif branch == "(detached)":
            head = GitHead(GitHeadKind.DETACHED, None, GitCommitId(oid))
        else:
            head = GitHead(GitHeadKind.ATTACHED, branch, GitCommitId(oid))
        return GitRepositoryState(
            head, tuple(sorted(entries, key=lambda entry: entry.path.value))
        )
    except (KeyError, ValueError) as error:
        raise GitError(GitFailure.FORMAT) from error


def check_index(data: bytes, max_entries: int) -> None:
    """Reject conflicts, gitlinks and indexed symlinks before status can read them."""
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise GitError(GitFailure.DECODE) from error
    if not text:
        return
    if not text.endswith("\0"):
        raise GitError(GitFailure.FORMAT)
    records = text[:-1].split("\0")
    if len(records) > max_entries:
        raise GitError(GitFailure.ENTRY_LIMIT)
    for record in records:
        attributes, separator, path = record.partition("\t")
        fields = attributes.split(" ")
        if not separator or len(fields) != 3:
            raise GitError(GitFailure.FORMAT)
        if fields[0] not in {"100644", "100755"} or fields[2] != "0":
            raise GitError(GitFailure.UNSUPPORTED)
        try:
            GitCommitId(fields[1])
        except ValueError as error:
            raise GitError(GitFailure.FORMAT) from error
        RepositoryPath(path)
