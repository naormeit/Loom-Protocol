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


class CosmosAtomicLedger:
    def __init__(
        self,
        endpoint: str,
        key: str,
        database_name: str,
        container_name: str,
        container=None,
    ):
        if container is None:
            if not endpoint or not key or not database_name or not container_name:
                raise ValueError(
                    "Cosmos endpoint, key, database, and container are required"
                )
            try:
                from azure.cosmos import CosmosClient
            except ImportError as exc:
                raise RuntimeError(
                    "Install the azure optional dependencies to use Cosmos DB"
                ) from exc

            client = CosmosClient(endpoint, credential=key)
            database = client.get_database_client(database_name)
            container = database.get_container_client(container_name)

        self.container = container

    def acquire_atomic_lock(
        self,
        intent_hash: str,
        agent_id: str,
        expiry_ms: int,
        packet_fingerprint: Optional[str] = None,
    ) -> Tuple[bool, str]:
        current_time = int(time.time() * 1000)
        lock_item = {
            "id": intent_hash,
            "resource_id": intent_hash,
            "agent_id": agent_id,
            "locked_at": current_time,
            "expires_at": current_time + expiry_ms,
            "packet_fingerprint": packet_fingerprint,
        }

        try:
            self.container.create_item(lock_item)
            return True, agent_id
        except Exception as exc:
            if exc.__class__.__name__ != "CosmosResourceExistsError":
                raise

        existing = self.container.read_item(
            item=intent_hash,
            partition_key=intent_hash,
        )
        if current_time < int(existing["expires_at"]):
            return False, existing["agent_id"]

        try:
            self.container.replace_item(
                item=existing["id"],
                body=lock_item,
                partition_key=intent_hash,
                if_match_etag=existing.get("_etag"),
            )
            return True, agent_id
        except Exception as exc:
            if exc.__class__.__name__ in {
                "CosmosAccessConditionFailedError",
                "CosmosHttpResponseError",
            }:
                refreshed = self.container.read_item(
                    item=intent_hash,
                    partition_key=intent_hash,
                )
                return False, refreshed["agent_id"]
            raise
