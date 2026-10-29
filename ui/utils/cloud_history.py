"""Private conversation persistence through user-scoped RLS, never service_role."""

from __future__ import annotations

import copy
import threading
import time

from app.accounts import AccountError
from ui.utils.session import SessionManager


class SupabaseSessionManager(SessionManager):
    def __init__(self, accounts, owner_id):
        self._lock = threading.RLock()
        self.accounts = accounts
        self.owner_id = owner_id
        self._snapshot = None
        self._history_version = None
        self._last_sync_at = 0.0

    def synchronize_privacy(self):
        """Refresh the erasure generation once per app rerun, across devices."""
        with self._lock:
            now = time.monotonic()
            if (
                getattr(self.accounts, "_real_transport", False)
                and self._history_version is not None
                and self._snapshot is not None
                and (now - self._last_sync_at) < 5.0
            ):
                return
            current = int(self.accounts.rpc("my_history_version"))
            self._last_sync_at = now
            if current != self._history_version:
                self._snapshot = None
                self._history_version = current

    def load_conversations(self):
        with self._lock:
            if self._history_version is None:
                self.synchronize_privacy()
            if self._snapshot is None:
                rows = self.accounts.rows(
                    "conversations",
                    select="id,payload",
                    filters={"owner_id": "eq." + self.owner_id},
                    order="updated_at.desc",
                )
                self._snapshot = [row["payload"] for row in rows]
            return copy.deepcopy(self._snapshot)

    def save_conversations(self, conversations):
        with self._lock:
            previous = {str(c["id"]): c for c in self.load_conversations()}
            current = {str(c["id"]): c for c in conversations}
            # RPC applies all changed rows/deletions in one DB transaction.
            changed = [c for key, c in current.items() if previous.get(key) != c]
            deleted = list(previous.keys() - current.keys())
            if changed or deleted:
                try:
                    self.accounts.rpc("save_my_conversations", {"changed": changed, "deleted": deleted,
                        "expected_history_version": self._history_version})
                except AccountError:
                    self._snapshot = None
                    self._history_version = None
                    self._last_sync_at = 0.0
                    raise
            self._snapshot = copy.deepcopy(conversations)
