import time
import unittest

from core.kernel.handshake import LoomKernel
from core.security import AuthorityVerifier, attach_signature


class SecurityTests(unittest.TestCase):
    def test_signed_packet_is_accepted_when_signature_required(self):
        secret = "test-secret"
        kernel = LoomKernel(
            authority_verifier=AuthorityVerifier(
                shared_secret=secret,
                require_signature=True,
            )
        )

        packet = attach_signature(
            {
                "agent_id": "AGENT-SIGNED",
                "intent": "Reserve one limited product",
                "intent_hash": "DROP-1",
                "expiry": 5000,
            },
            secret,
        )

        response = kernel.process_handshake(packet)

        self.assertEqual(response["status"], 201)

    def test_missing_signature_is_rejected_when_required(self):
        kernel = LoomKernel(
            authority_verifier=AuthorityVerifier(
                shared_secret="test-secret",
                require_signature=True,
            )
        )

        response = kernel.process_handshake(
            {
                "agent_id": "AGENT-UNSIGNED",
                "intent": "Reserve one limited product",
                "intent_hash": "DROP-1",
                "expiry": 5000,
            }
        )

        self.assertEqual(response["status"], 401)
        self.assertIn("missing packet signature", response["message"])

    def test_replayed_nonce_is_rejected(self):
        secret = "test-secret"
        kernel = LoomKernel(
            authority_verifier=AuthorityVerifier(
                shared_secret=secret,
                require_signature=True,
            )
        )
        packet = attach_signature(
            {
                "agent_id": "AGENT-REPLAY",
                "intent": "Reserve one limited product",
                "intent_hash": "DROP-1",
                "expiry": 5000,
                "nonce": "nonce-1",
                "timestamp": int(time.time()),
            },
            secret,
        )

        first = kernel.process_handshake(packet)
        second = kernel.process_handshake(packet)

        self.assertEqual(first["status"], 201)
        self.assertEqual(second["status"], 401)
        self.assertIn("replayed packet nonce", second["message"])


if __name__ == "__main__":
    unittest.main()
