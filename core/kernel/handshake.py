import hashlib
import random
from core.ai import LocalContentSafety, LocalIntentParser
from core.database.cosmos_client import LoomCosmosClient
from core.models import ATPPacket, HandshakeResult, PacketValidationError
from core.security import AuthorityVerifier

class LoomKernel:
    def __init__(
        self,
        db=None,
        intent_parser=None,
        safety_checker=None,
        authority_verifier=None,
    ):
        self.version = "1.0.0-alpha"
        # Imagine Cup Compliance: Tracking our 3 core Microsoft Cloud services
        self.services = ["Azure AI Foundry", "Azure Content Safety", "Azure Cosmos DB"]
        # Initialize the global transactional database layer (Option A)
        self.db = db or LoomCosmosClient()
        self.intent_parser = intent_parser or LocalIntentParser()
        self.safety_checker = safety_checker or LocalContentSafety()
        self.authority_verifier = authority_verifier or AuthorityVerifier()

    def process_handshake(self, agent_packet):
        """
        The ATP Handshake Pipeline:
        1. Ingress (Receive Packet)
        2. Intent Parsing (Azure AI Foundry)
        3. Safety Scrub (Azure Content Safety)
        4. Distributed Atomic Resolution (Azure Cosmos DB - Option A)
        5. Adaptive Conflict Negotiation (Option C)
        """
        try:
            packet = ATPPacket.from_mapping(agent_packet)
        except PacketValidationError as exc:
            return HandshakeResult(
                status=400,
                message=f"Invalid ATP packet: {exc}",
                correlation_id="invalid-packet",
            ).to_dict()

        correlation_id = self._correlation_id(packet)
        print(f"\n[Loom ATP] Handshake initiated by {packet.agent_id}")

        authority = self.authority_verifier.verify(packet)
        if not authority.allowed:
            return HandshakeResult(
                status=401,
                message=f"Rejected: {authority.reason}.",
                correlation_id=correlation_id,
            ).to_dict()
        
        # --- INTENT PARSING ---
        parsed_intent = self._parse_intent_with_ai_foundry(packet.intent)
        
        # --- CONTENT SAFETY SCRUB ---
        safety_decision = self._check_content_safety(parsed_intent)
        if not safety_decision.safe:
            return HandshakeResult(
                status=403,
                message=f"Rejected: {safety_decision.reason}.",
                correlation_id=correlation_id,
            ).to_dict()

        # --- DISTRIBUTED ATOMIC RESOLUTION VIA COSMOS DB (Option A Preservation) ---
        lock_success, holding_agent = self.db.acquire_atomic_lock(
            intent_hash=packet.intent_hash,
            agent_id=packet.agent_id,
            expiry_ms=packet.expiry
        )

        # --- OPTION C: ADAPTIVE CONFLICT RESOLUTION ENGINE ---
        if not lock_success:
            # Generate adaptive negotiation data for autonomous machine logic
            suggested_alt = f"{packet.intent_hash}_ALT"
            suggested_backoff = random.randint(150, 300)  # Jittered millisecond delay

            print(f" > [Conflict Engine] Generating Protocol Negotiation Payload for {packet.agent_id}...")
            return HandshakeResult(
                status=409,
                message=f"Conflict Rejected: Resource currently locked by {holding_agent}.",
                correlation_id=correlation_id,
                conflict_with=holding_agent,
                negotiation_payload={
                    "action": "RENEGOTIATE",
                    "suggested_alternative_resource": suggested_alt,
                    "retry_backoff_ms": suggested_backoff
                }
            ).to_dict()

        # Smooth path if Option A succeeds
        return HandshakeResult(
            status=201,
            message="Atomic Lock Secured.",
            correlation_id=correlation_id,
            parsed_as=parsed_intent,
        ).to_dict()

    def _parse_intent_with_ai_foundry(self, raw_text):
        print(f" > Intent Parser: Parsing intent '{raw_text}'...")
        return self.intent_parser.parse(raw_text).normalized_text

    def _check_content_safety(self, text):
        print(f" > Content Safety: Scrubbing intent for risk...")
        return self.safety_checker.evaluate(text)

    def _correlation_id(self, packet):
        seed = f"{packet.agent_id}:{packet.intent_hash}:{packet.intent}:{packet.expiry}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

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
