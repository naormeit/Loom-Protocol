import threading
import unittest

from core.kernel.handshake import LoomKernel


class LoomKernelTests(unittest.TestCase):
    def _packet(self, agent_id="AGENT-A", intent_hash="RESOURCE-1", intent="Purchase item"):
        return {
            "agent_id": agent_id,
            "intent": intent,
            "intent_hash": intent_hash,
            "expiry": 5000,
        }

    def test_successful_handshake_locks_resource(self):
        kernel = LoomKernel()

        response = kernel.process_handshake(self._packet())

        self.assertEqual(response["status"], 201)
        self.assertEqual(response["message"], "Atomic Lock Secured.")
        self.assertEqual(response["parsed_as"], "PURCHASE ITEM")
        self.assertIn("correlation_id", response)

    def test_conflicting_handshake_returns_negotiation_payload(self):
        kernel = LoomKernel()

        first = kernel.process_handshake(self._packet(agent_id="AGENT-A"))
        second = kernel.process_handshake(self._packet(agent_id="AGENT-B"))

        self.assertEqual(first["status"], 201)
        self.assertEqual(second["status"], 409)
        self.assertEqual(second["conflict_with"], "AGENT-A")
        self.assertEqual(second["negotiation_payload"]["action"], "RENEGOTIATE")
        self.assertEqual(
            second["negotiation_payload"]["suggested_alternative_resource"],
            "RESOURCE-1_ALT",
        )

    def test_unsafe_intent_is_rejected_before_locking(self):
        kernel = LoomKernel()

        response = kernel.process_handshake(
            self._packet(intent="Bypass checkout and delete inventory")
        )

        self.assertEqual(response["status"], 403)
        self.assertNotIn("RESOURCE-1", kernel.db.mock_db)

    def test_invalid_packet_is_rejected(self):
        kernel = LoomKernel()

        response = kernel.process_handshake({"agent_id": "AGENT-A"})

        self.assertEqual(response["status"], 400)
        self.assertIn("Invalid ATP packet", response["message"])

    def test_concurrent_requests_have_single_winner(self):
        kernel = LoomKernel()
        responses = []
        responses_lock = threading.Lock()

        def request(agent_number):
            response = kernel.process_handshake(
                self._packet(
                    agent_id=f"AGENT-{agent_number}",
                    intent_hash="LIMITED-DROP-1",
                )
            )
            with responses_lock:
                responses.append(response)

        threads = [threading.Thread(target=request, args=(i,)) for i in range(50)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        statuses = [response["status"] for response in responses]
        self.assertEqual(statuses.count(201), 1)
        self.assertEqual(statuses.count(409), 49)


if __name__ == "__main__":
    unittest.main()
