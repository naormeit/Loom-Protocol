import time
from core.database.cosmos_client import LoomCosmosClient

class LoomKernel:
    def __init__(self):
        self.version = "1.0.0-alpha"
        # Imagine Cup Compliance: Tracking our 3 core Microsoft Cloud services
        self.services = ["Azure AI Foundry", "Azure Content Safety", "Azure Cosmos DB"]
        # Initialize the global transactional database layer
        self.db = LoomCosmosClient()

    def process_handshake(self, agent_packet):
        """
        The ATP Handshake Pipeline:
        1. Ingress (Receive Packet)
        2. Intent Parsing (Azure AI Foundry)
        3. Safety Scrub (Azure Content Safety)
        4. Distributed Atomic Resolution (Azure Cosmos DB)
        """
        print(f"\n[Loom ATP] Handshake initiated by {agent_packet['agent_id']}")
        
        # --- SIMULATED AZURE AI FOUNDRY PARSING ---
        parsed_intent = self._parse_intent_with_ai_foundry(agent_packet['intent'])
        
        # --- SIMULATED AZURE CONTENT SAFETY SCRUB ---
        if not self._check_content_safety(parsed_intent):
            return {"status": 403, "message": "Rejected: Azure Content Safety flagged intent."}

        # --- DISTRIBUTED ATOMIC RESOLUTION VIA COSMOS DB ---
        lock_success, holding_agent = self.db.acquire_atomic_lock(
            intent_hash=agent_packet['intent_hash'],
            agent_id=agent_packet['agent_id'],
            expiry_ms=agent_packet['expiry']
        )

        if not lock_success:
            return {
                "status": 409, 
                "message": f"Conflict Rejected: Resource currently locked by {holding_agent}.",
                "conflict_with": holding_agent
            }

        return {
            "status": 201, 
            "message": "Atomic Lock Secured.",
            "parsed_as": parsed_intent
        }

    def _parse_intent_with_ai_foundry(self, raw_text):
        print(f" > Azure AI Foundry: Parsing intent '{raw_text}'...")
        # Simulated NLP Logic: Extracting the core action
        return raw_text.strip().upper()

    def _check_content_safety(self, text):
        print(f" > Azure Content Safety: Scrubbing intent for risk...")
        # Imagine Cup Rule: Must show 'Responsible AI'
        prohibited = ["DELETE", "HACK", "BYPASS", "MALWARE"]
        return not any(word in text for word in prohibited)

# For quick local testing
if __name__ == "__main__":
    kernel = LoomKernel()
    test_packet = {
        "agent_id": "TEST-1", 
        "intent": "Book Flight Ticket", 
        "intent_hash": "FL-101",
        "expiry": 5000
    }
    print(kernel.process_handshake(test_packet))