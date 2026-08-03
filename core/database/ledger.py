import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class LockRecord:
    agent_id: str
    locked_at: int
    expires_at: int
    packet_fingerprint: Optional[str] = None


class LocalAtomicLedger:
    def __init__(self):
        self.records: Dict[str, LockRecord] = {}
        self._mutex = threading.Lock()

    def acquire_atomic_lock(
        self,
        intent_hash: str,
        agent_id: str,
        expiry_ms: int,
        packet_fingerprint: Optional[str] = None,
    ) -> Tuple[bool, str]:
        with self._mutex:
            current_time = int(time.time() * 1000)
            lock_data = self.records.get(intent_hash)
            if lock_data and current_time < lock_data.expires_at:
                return False, lock_data.agent_id

            self.records[intent_hash] = LockRecord(
                agent_id=agent_id,
                locked_at=current_time,
                expires_at=current_time + expiry_ms,
                packet_fingerprint=packet_fingerprint,
            )
            return True, agent_id
