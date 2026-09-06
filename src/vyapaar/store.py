"""Small transactional JSON store for the hackathon deployment."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def seed_state() -> dict[str, Any]:
    return {
        "sequences": {"customer": 3, "voiceJob": 1, "order": 1042, "invoice": 1042},
        "merchants": [{"id": "mer_demo", "name": "Sharma Distributors",
                       "timezone": "Asia/Kolkata", "language": "hi-IN"}],
        "customers": [
            {"id": "cus_ramesh", "merchantId": "mer_demo", "name": "Ramesh Stores",
             "aliases": ["Ramesh"], "phone": "REDACTED", "address": "Demo Market",
             "creditLimitPaise": 5_000_000},
            {"id": "cus_neha", "merchantId": "mer_demo", "name": "Neha Kirana",
             "aliases": ["Neha"], "phone": "REDACTED", "address": "Main Road",
             "creditLimitPaise": 3_000_000},
        ],
        "uploads": [], "voiceJobs": [], "drafts": [], "clarifications": [],
        "orders": [], "invoices": [],
        "ledgerEntries": [{"id": "led_opening_ramesh", "merchantId": "mer_demo",
                           "customerId": "cus_ramesh", "type": "OPENING_BALANCE",
                           "debitPaise": 1_250_000, "creditPaise": 0,
                           "occurredAt": "2026-09-01T00:00:00+00:00", "reference": "Opening balance"}],
        "outboxEvents": [], "artifacts": [],
        "idempotency": {}, "audit": [],
    }


class JsonStore:
    """Serializes transactions and replaces the JSON file only after success."""

    def __init__(self, path: str | Path | None = None, initial: dict[str, Any] | None = None):
        self.path = Path(path) if path else None
        self._lock = threading.RLock()
        if self.path and self.path.exists():
            self._state = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self._state = copy.deepcopy(initial if initial is not None else seed_state())
            if self.path:
                self._persist(self._state)

    def read(self, reader: Callable[[dict[str, Any]], T]) -> T:
        with self._lock:
            return reader(self._state)

    def snapshot(self) -> dict[str, Any]:
        return self.read(copy.deepcopy)

    def transaction(self, operation: Callable[[dict[str, Any]], T]) -> T:
        with self._lock:
            candidate = copy.deepcopy(self._state)
            result = operation(candidate)  # exceptions discard candidate: all-or-nothing
            if self.path:
                self._persist(candidate)
            self._state = candidate
            return result

    def reset(self) -> None:
        self.transaction(lambda state: (state.clear(), state.update(seed_state())))

    def _persist(self, state: dict[str, Any]) -> None:
        assert self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise


def reset_main() -> None:
    """Console entry point used by ``vyapaar-reset``."""
    path = os.environ.get("DATA_FILE", "data/vyapaar.json")
    if path == ":memory:":
        raise SystemExit("DATA_FILE=:memory: has nothing persistent to reset")
    JsonStore(path).reset()
    print(f"Reset demo data at {path}")
