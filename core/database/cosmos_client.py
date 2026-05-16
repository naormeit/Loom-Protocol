# core/database/cosmos_client.py
import time

class LoomCosmosClient:
    def __init__(self):
        # In a production environment, this would initialize:
        # from azure.cosmos import CosmosClient
        # self.client = CosmosClient(ENDPOINT, KEY)
        self.mock_db = {}  # Simulates globally distributed ledger storage
        print("[Azure Cosmos DB] Initialized client with Multi-Region Writes enabled.")

    def acquire_atomic_lock(self, intent_hash, agent_id, expiry_ms):
        """
        Simulates an Optimistic Concurrency Control (OCC) transactional write.
        In Azure Cosmos DB, this uses item ETag checks or conditional upserts.
        """
        current_time = int(time.time() * 1000)
        
        # Check if a lock already exists for this specific resource hash
        if intent_hash in self.mock_db:
            lock_data = self.mock_db[intent_hash]
            # Check if the existing lock has expired
            if current_time < lock_data["expires_at"]:
                print(f" > [Azure Cosmos DB] Conflict! Resource {intent_hash} is locked by {lock_data['agent_id']}.")
                return False, lock_data["agent_id"]
        
        # If no active lock exists, secure it atomically
        self.mock_db[intent_hash] = {
            "agent_id": agent_id,
            "locked_at": current_time,
            "expires_at": current_time + expiry_ms,
            "_etag": f"W/\"datetime'{current_time}'\"" # Simulating Cosmos DB ETag
        }
        print(f" > [Azure Cosmos DB] Transaction Success: Atomic lock secured for resource {intent_hash} by {agent_id}.")
        return True, agent_id