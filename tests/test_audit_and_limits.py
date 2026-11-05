import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from urllib import request
from urllib.error import HTTPError

from core.api.server import create_handler
from core.audit import AuditLog, GENESIS_HASH, verify_file, verify_records
from core.kernel.handshake import LoomKernel
from core.ratelimit import RateLimiter
from core.security import AuthorityVerifier, attach_signature


def _packet(agent_id="AGENT-A", intent_hash="RESOURCE-1", intent="Purchase item"):
    return {
        "agent_id": agent_id,
        "intent": intent,
        "intent_hash": intent_hash,
        "expiry": 5000,
    }


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class AuditLogTests(unittest.TestCase):
    def test_every_outcome_is_recorded_without_raw_intent_or_signature(self):
        secret = "test-secret"
        log = AuditLog()
        kernel = LoomKernel(
            audit_log=log,
            authority_verifier=AuthorityVerifier(shared_secret=secret),
        )

        secret_intent = "Purchase one limited item for ACCOUNT-12345"
        kernel.process_handshake(
            attach_signature(_packet("AGENT-A", intent=secret_intent), secret)
        )  # 201
        kernel.process_handshake(_packet("AGENT-B", intent=secret_intent))  # 409
        kernel.process_handshake(_packet("AGENT-C", intent="bypass the checkout"))  # 403
        kernel.process_handshake({"agent_id": "AGENT-D"})  # 400

        records = log.recent()
        self.assertEqual([r["status"] for r in records], [201, 409, 403, 400])
        self.assertEqual(records[0]["agent_id"], "AGENT-A")
        self.assertTrue(records[0]["signed"])
        self.assertEqual(len(records[0]["signature_fingerprint"]), 16)
        self.assertEqual(records[1]["conflict_with"], "AGENT-A")
        self.assertEqual(len(records[0]["intent_sha256"]), 64)

        dumped = json.dumps(records)
        self.assertNotIn("ACCOUNT-12345", dumped)
        self.assertNotIn("signature\":", dumped.replace("signature_fingerprint", ""))

    def test_chain_verifies_and_detects_edits_and_deletions(self):
        log = AuditLog()
        kernel = LoomKernel(audit_log=log)
        for index in range(5):
            kernel.process_handshake(_packet(f"AGENT-{index}", f"RESOURCE-{index}"))

        records = log.recent()
        self.assertEqual(verify_records(records), (True, None))
        self.assertEqual(records[0]["prev_hash"], GENESIS_HASH)

        edited = [dict(r) for r in records]
        edited[2]["status"] = 201 if edited[2]["status"] != 201 else 409
        self.assertEqual(verify_records(edited), (False, 2))

        deleted = records[:2] + records[3:]
        self.assertEqual(verify_records(deleted), (False, 2))

        reordered = [records[1], records[0]] + records[2:]
        self.assertFalse(verify_records(reordered)[0])

    def test_file_log_persists_and_chain_continues_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "nested", "audit.jsonl")

            first = LoomKernel(audit_log=AuditLog(path))
            first.process_handshake(_packet("AGENT-A", "RESOURCE-1"))
            first.process_handshake(_packet("AGENT-B", "RESOURCE-1"))

            second = LoomKernel(audit_log=AuditLog(path))  # simulated restart
            second.process_handshake(_packet("AGENT-C", "RESOURCE-2"))

            ok, count, bad_line = verify_file(path)
            self.assertEqual((ok, count, bad_line), (True, 3, None))

            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            tampered = json.loads(lines[1])
            tampered["agent_id"] = "SOMEONE-ELSE"
            lines[1] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")

            ok, count, bad_line = verify_file(path)
            self.assertFalse(ok)
            self.assertEqual(bad_line, 2)

    def test_concurrent_writes_keep_the_chain_intact(self):
        log = AuditLog()
        kernel = LoomKernel(audit_log=log)

        def work(index):
            kernel.process_handshake(_packet(f"AGENT-{index}", "SHARED"))

        threads = [threading.Thread(target=work, args=(i,)) for i in range(60)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        records = log.recent(100)
        self.assertEqual(len(records), 60)
        self.assertEqual(verify_records(records), (True, None))
        self.assertEqual(sum(1 for r in records if r["status"] == 201), 1)


class RateLimiterTests(unittest.TestCase):
    def test_allows_up_to_the_limit_then_blocks_with_retry_hint(self):
        clock = FakeClock()
        limiter = RateLimiter(3, 10, clock=clock)

        self.assertEqual([limiter.check("a")[0] for _ in range(3)], [True, True, True])
        allowed, retry_after_ms = limiter.check("a")
        self.assertFalse(allowed)
        self.assertEqual(retry_after_ms, 10000)

        clock.advance(4)
        allowed, retry_after_ms = limiter.check("a")
        self.assertFalse(allowed)
        self.assertEqual(retry_after_ms, 6000)

    def test_recovers_after_the_window_and_keys_are_independent(self):
        clock = FakeClock()
        limiter = RateLimiter(2, 10, clock=clock)
        limiter.check("a")
        limiter.check("a")
        self.assertFalse(limiter.check("a")[0])
        self.assertTrue(limiter.check("b")[0])

        clock.advance(10.1)
        self.assertTrue(limiter.check("a")[0])

    def test_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            RateLimiter(0, 10)
        with self.assertRaises(ValueError):
            RateLimiter(5, 0)

    def test_memory_is_bounded_by_evicting_idle_keys(self):
        clock = FakeClock()
        limiter = RateLimiter(5, 1, clock=clock, max_keys=100)
        for index in range(100):
            limiter.check(f"key-{index}")
        clock.advance(5)
        for index in range(100, 130):
            limiter.check(f"key-{index}")
        self.assertLess(len(limiter._events), 100)


class KernelRateLimitTests(unittest.TestCase):
    def test_agent_over_limit_gets_429_and_back_off_and_it_is_audited(self):
        clock = FakeClock()
        log = AuditLog()
        kernel = LoomKernel(
            audit_log=log,
            rate_limiter=RateLimiter(2, 10, clock=clock),
        )

        statuses = [
            kernel.process_handshake(_packet("SPAMMER", f"RESOURCE-{i}"))["status"]
            for i in range(3)
        ]
        self.assertEqual(statuses, [201, 201, 429])

        limited = kernel.process_handshake(_packet("SPAMMER", "RESOURCE-9"))
        self.assertEqual(limited["status"], 429)
        self.assertEqual(limited["negotiation_payload"]["action"], "BACK_OFF")
        self.assertGreater(limited["negotiation_payload"]["retry_after_ms"], 0)
        self.assertNotIn("RESOURCE-9", kernel.db.mock_db)

        other = kernel.process_handshake(_packet("POLITE", "RESOURCE-10"))
        self.assertEqual(other["status"], 201)

        self.assertIn(429, [r["status"] for r in log.recent()])

    def test_invalid_packets_do_not_consume_an_agents_allowance(self):
        kernel = LoomKernel(rate_limiter=RateLimiter(1, 10, clock=FakeClock()))
        for _ in range(5):
            self.assertEqual(kernel.process_handshake({"agent_id": "A"})["status"], 400)
        self.assertEqual(kernel.process_handshake(_packet("A"))["status"], 201)


class ReplayRaceTests(unittest.TestCase):
    def test_concurrent_identical_signed_packets_have_exactly_one_acceptance(self):
        # Slow the signature check so concurrent packets overlap inside the verifier.
        # Without a lock around the nonce check-and-store, several would be accepted.
        import core.security.authority as authority_module

        real_verify = authority_module.verify_signature

        def slow_verify(payload, secret):
            result = real_verify(payload, secret)
            time.sleep(0.02)
            return result

        authority_module.verify_signature = slow_verify
        self.addCleanup(setattr, authority_module, "verify_signature", real_verify)

        secret = "race-secret"
        verifier = AuthorityVerifier(shared_secret=secret, require_signature=True)
        kernel = LoomKernel(authority_verifier=verifier)
        packet = attach_signature(_packet("RACER", "RACE-1"), secret)

        statuses = []
        lock = threading.Lock()
        barrier = threading.Barrier(24)

        def send():
            barrier.wait()
            status = kernel.process_handshake(dict(packet))["status"]
            with lock:
                statuses.append(status)

        threads = [threading.Thread(target=send) for _ in range(24)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # One request passes authority (then it may lock); every other one is a replay (401).
        self.assertEqual(statuses.count(401), 23)
        self.assertEqual(len(statuses) - statuses.count(401), 1)


class IpLimiterHttpTests(unittest.TestCase):
    def test_client_address_limit_returns_429_with_retry_after(self):
        log = AuditLog()
        kernel = LoomKernel(audit_log=log)
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            create_handler(kernel, ip_limiter=RateLimiter(2, 60)),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address

        def post(agent):
            body = json.dumps(_packet(agent, f"RES-{agent}")).encode("utf-8")
            req = request.Request(
                f"http://{host}:{port}/v1/handshake",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=5) as response:
                    return response.status, dict(response.headers), json.loads(response.read())
            except HTTPError as error:
                return error.code, dict(error.headers), json.loads(error.read())

        try:
            self.assertEqual(post("A")[0], 201)
            self.assertEqual(post("B")[0], 201)
            status, headers, payload = post("C")
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(status, 429)
        self.assertGreaterEqual(int(headers["Retry-After"]), 1)
        self.assertEqual(payload["negotiation_payload"]["action"], "BACK_OFF")
        limited = [r for r in log.recent() if r.get("scope") == "client_address"]
        self.assertEqual(len(limited), 1)
        self.assertNotIn("127.0.0.1", json.dumps(limited))


if __name__ == "__main__":
    unittest.main()
