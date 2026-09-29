"""In-process refusal of a second concurrent run on the same workspace.

Owned by the composition root and shared by the runs it starts; never global.
Not a lock across processes or hosts: operators must not point two processes
at one workspace. Different workspaces never contend.
"""

from threading import Lock


class WorkspaceGuard:
    __slots__ = ("_active", "_lock")

    def __init__(self) -> None:
        self._lock = Lock()
        self._active: set[str] = set()

    def acquire(self, workspace: str) -> bool:
        """Claim the workspace without waiting; False when a run holds it."""
        if type(workspace) is not str or not workspace:
            raise TypeError("workspace guard requires a nonblank key")
        with self._lock:
            if workspace in self._active:
                return False
            self._active.add(workspace)
            return True

    def release(self, workspace: str) -> None:
        with self._lock:
            if workspace not in self._active:
                raise RuntimeError("workspace was not held")
            self._active.remove(workspace)
