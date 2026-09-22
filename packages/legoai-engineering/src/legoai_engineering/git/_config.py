"""Fail-closed admission of a small local-config subset before invoking Git.

This is intentionally not a general Git config parser. Includes, escaping,
continuations, helper settings and unsupported extensions are not admitted.
"""

from legoai_engineering.git.errors import GitError, GitFailure


def check_config(text: str) -> None:
    section = ""
    seen: set[tuple[str, str]] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if "\\" in line or any(ord(char) < 32 and char != "\t" for char in line):
            raise GitError(GitFailure.UNSUPPORTED)
        if line.startswith("[") and line.endswith("]"):
            body = line[1:-1]
            section = body.lower()
            if section not in {"core", "user", "extensions"}:
                # Remote/branch labels and their inert values are data only.
                prefix, separator, label = body.partition(' "')
                if (
                    prefix.lower() not in {"remote", "branch"}
                    or not separator
                    or not label.endswith('"')
                    or not label[:-1]
                    or '"' in label[:-1]
                ):
                    raise GitError(GitFailure.UNSUPPORTED)
                section = prefix.lower()
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip().lower(), value.strip()
        allowed = {
            "core": {
                "repositoryformatversion",
                "filemode",
                "bare",
                "logallrefupdates",
                "ignorecase",
                "precomposeunicode",
                "symlinks",
                "autocrlf",
            },
            "user": {"name", "email"},
            "extensions": {"objectformat"},
            "remote": {"url", "fetch"},
            "branch": {"remote", "merge"},
        }
        if not separator or key not in allowed.get(section, set()):
            raise GitError(GitFailure.UNSUPPORTED)
        if section in {"core", "extensions"}:
            if (section, key) in seen:
                raise GitError(GitFailure.UNSUPPORTED)
            seen.add((section, key))
            supported = {"true", "false"}
            if key == "repositoryformatversion":
                supported = {"0", "1"}
            elif key == "bare":
                supported = {"false"}
            elif key == "objectformat":
                supported = {"sha1", "sha256"}
            elif key == "autocrlf":
                supported = {"true", "false", "input"}
            if value.lower() not in supported:
                raise GitError(GitFailure.UNSUPPORTED)
        elif not value or any(char in value for char in '"#;'):
            raise GitError(GitFailure.UNSUPPORTED)
