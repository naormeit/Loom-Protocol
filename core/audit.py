"""Append-only, hash-chained audit log for ATP handshake decisions.

Every handshake outcome (accepted, conflicted, rejected, rate limited, invalid)
is recorded as one JSON line. Each record stores the hash of the previous
record, so deleting, reordering, or editing a line breaks the chain and is
detected by ``verify_file``.

What this is: tamper-evident local logging. What it is not: tamper-proof.
Someone who can rewrite the whole file can also rewrite the whole chain, so
for stronger guarantees the head hash should be anchored somewhere the writer
cannot change (for example a separate store). Raw intent text is never written;
only its SHA-256 digest.

Verify a file from the command line:

    python -m core.audit verify path/to/loom-audit.jsonl
"""

import hashlib
import json
import os
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

GENESIS_HASH = "0" * 64


def _canonical(body: Dict[str, Any]) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _chain_hash(previous_hash: str, body: Dict[str, Any]) -> str:
    return hashlib.sha256((previous_hash + _canonical(body)).encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class NullAuditLog:
    """Audit log that records nothing. Used when auditing is not configured."""

    def record(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None


class AuditLog:
    """Thread-safe hash-chained audit log, in memory or backed by a JSONL file."""

    def __init__(self, path: Optional[str] = None, memory_limit: int = 10000):
        self.path = path
        self._lock = threading.Lock()
        self._last_hash = GENESIS_HASH
        self._memory: Deque[Dict[str, Any]] = deque(maxlen=memory_limit)

        if path:
            directory = os.path.dirname(os.path.abspath(path))
            os.makedirs(directory, exist_ok=True)
            self._last_hash = self._read_last_hash(path)

    @staticmethod
    def _read_last_hash(path: str) -> str:
        if not os.path.exists(path):
            return GENESIS_HASH
        last_line = ""
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last_line = line
        if not last_line:
            return GENESIS_HASH
        try:
            return json.loads(last_line)["record_hash"]
        except (ValueError, KeyError) as exc:
            raise ValueError(
                f"audit log {path} is corrupt: last line has no valid record_hash"
            ) from exc

    def record(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        body = dict(entry)
        body["ts"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock:
            body["prev_hash"] = self._last_hash
            record = dict(body)
            record["record_hash"] = _chain_hash(self._last_hash, body)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(_canonical(record) + "\n")
                    handle.flush()
            self._memory.append(record)
            self._last_hash = record["record_hash"]
        return record

    @property
    def head_hash(self) -> str:
        with self._lock:
            return self._last_hash

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._memory)[-limit:]


def verify_records(records: List[Dict[str, Any]]) -> Tuple[bool, Optional[int]]:
    """Return (ok, index_of_first_bad_record) for an ordered list of records."""
    previous = GENESIS_HASH
    for index, record in enumerate(records):
        stored_hash = record.get("record_hash")
        body = {key: value for key, value in record.items() if key != "record_hash"}
        if body.get("prev_hash") != previous:
            return False, index
        if stored_hash != _chain_hash(previous, body):
            return False, index
        previous = stored_hash
    return True, None


def verify_file(path: str) -> Tuple[bool, int, Optional[int]]:
    """Verify a JSONL audit file. Returns (ok, record_count, first_bad_line_number)."""
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                return False, len(records), line_number
    ok, bad_index = verify_records(records)
    return ok, len(records), (None if ok else bad_index + 1)


def _main(argv: List[str]) -> int:
    if len(argv) != 3 or argv[1] != "verify":
        print("usage: python -m core.audit verify <path-to-audit.jsonl>")
        return 2
    path = argv[2]
    if not os.path.exists(path):
        print(f"audit file not found: {path}")
        return 2
    ok, count, bad_line = verify_file(path)
    if ok:
        print(f"OK: {count} record(s), hash chain intact")
        return 0
    print(f"FAILED: chain broken at line {bad_line} (after {count} readable record(s))")
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
