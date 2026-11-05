import asyncio
import importlib.util
import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from core.api.server import create_handler
from core.kernel.handshake import LoomKernel

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "sdk" / "python", ROOT / "integrations" / "mcp_server"):
    if str(extra) not in sys.path:
        sys.path.append(str(extra))

import loom_tools  # noqa: E402
from loom_protocol import LoomClientError  # noqa: E402

MCP_AVAILABLE = (
    sys.version_info >= (3, 10) and importlib.util.find_spec("mcp") is not None
)


def _load(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def reserve(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class SummarizeTests(unittest.TestCase):
    def test_every_status_maps_to_an_outcome_with_guidance(self):
        cases = {
            201: "LOCKED",
            409: "CONFLICT",
            403: "UNSAFE",
            401: "UNAUTHORIZED",
            400: "INVALID",
            429: "RATE_LIMITED",
            500: "ERROR",
        }
        for status, outcome in cases.items():
            result = loom_tools.summarize_response({"status": status, "message": "m"})
            self.assertEqual(result["outcome"], outcome, status)
            self.assertEqual(result["locked"], status == 201)
            self.assertTrue(result["next_action"])

    def test_conflict_carries_machine_readable_retry_data(self):
        result = loom_tools.summarize_response(
            {
                "status": 409,
                "message": "locked",
                "conflict_with": "AGENT-A",
                "negotiation_payload": {
                    "action": "RENEGOTIATE",
                    "suggested_alternative_resource": "R_ALT",
                    "retry_backoff_ms": 222,
                },
            }
        )
        self.assertEqual(result["held_by"], "AGENT-A")
        self.assertEqual(result["retry_backoff_ms"], 222)
        self.assertEqual(result["suggested_alternative_resource"], "R_ALT")

    def test_rate_limit_carries_retry_after(self):
        result = loom_tools.summarize_response(
            {"status": 429, "negotiation_payload": {"retry_after_ms": 4500}}
        )
        self.assertEqual(result["retry_after_ms"], 4500)


class ReserveTests(unittest.TestCase):
    def test_passes_trimmed_values_to_the_client(self):
        client = FakeClient({"status": 201, "message": "ok", "correlation_id": "c"})
        result = loom_tools.reserve(client, " A ", " R ", " buy ", "7000")
        self.assertEqual(result["outcome"], "LOCKED")
        self.assertEqual(
            client.calls,
            [{"agent_id": "A", "resource_id": "R", "intent": "buy", "expiry_ms": 7000}],
        )

    def test_invalid_input_never_reaches_loom(self):
        for kwargs in (
            {"agent_id": "", "resource_id": "R", "intent": "x", "expiry_ms": 5000},
            {"agent_id": "A", "resource_id": "  ", "intent": "x", "expiry_ms": 5000},
            {"agent_id": "A", "resource_id": "R", "intent": None, "expiry_ms": 5000},
            {"agent_id": "A", "resource_id": "R", "intent": "x", "expiry_ms": 0},
            {"agent_id": "A", "resource_id": "R", "intent": "x", "expiry_ms": "soon"},
            {"agent_id": "A", "resource_id": "R", "intent": "x", "expiry_ms": 10**9},
        ):
            client = FakeClient({"status": 201})
            result = loom_tools.reserve(client, **kwargs)
            self.assertEqual(result["outcome"], "INVALID", kwargs)
            self.assertFalse(result["locked"])
            self.assertEqual(client.calls, [], kwargs)

    def test_unreachable_loom_is_an_error_never_a_lock(self):
        client = FakeClient(error=LoomClientError("connection refused"))
        result = loom_tools.reserve(
            client, "A", "R", "buy", 5000, error_type=LoomClientError
        )
        self.assertEqual(result["outcome"], "ERROR")
        self.assertFalse(result["locked"])
        self.assertEqual(result["status"], 0)
        self.assertIn("NOT hold a lock", result["next_action"])

    def test_health_reports_reachable_and_unreachable(self):
        ok = loom_tools.health(
            "http://x/", fetch=lambda url: json.dumps({"service": "loom-atp"}).encode()
        )
        self.assertTrue(ok["reachable"])
        self.assertEqual(ok["url"], "http://x/health")

        def broken(url):
            raise OSError("down")

        self.assertFalse(loom_tools.health("http://x", fetch=broken)["reachable"])
        wrong = loom_tools.health("http://x", fetch=lambda u: b'{"service": "other"}')
        self.assertFalse(wrong["reachable"])


class GatewayCase(unittest.TestCase):
    def setUp(self):
        self.kernel = LoomKernel()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(self.kernel))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()


class TwoAgentDemoTests(GatewayCase):
    def test_each_agent_ends_up_holding_one_distinct_resource(self):
        demo = _load("two_agent_demo", "examples/scenarios/two_agent_demo.py")
        for run_number in range(5):  # either agent may win; the shape must hold every time
            outcome = demo.run_demo(
                self.base_url, resource_id=f"DEMO-{run_number}", sleep=lambda seconds: None
            )
            holds = {name: data["holds"] for name, data in outcome["agents"].items()}
            self.assertEqual(len(set(holds.values())), 2, holds)
            self.assertIn(f"DEMO-{run_number}", holds.values())
            self.assertIn(f"DEMO-{run_number}_ALT", holds.values())

            loser = next(
                data for data in outcome["agents"].values() if data["holds"].endswith("_ALT")
            )
            self.assertEqual(
                [attempt["outcome"] for attempt in loser["attempts"]], ["CONFLICT", "LOCKED"]
            )
            self.assertEqual(loser["attempts"][1]["resource"], f"DEMO-{run_number}_ALT")


@unittest.skipUnless(MCP_AVAILABLE, "MCP SDK not installed (needs Python 3.10+ and 'mcp')")
class McpServerTests(GatewayCase):
    def test_stdio_round_trip_with_the_official_client(self):
        client_demo = _load("mcp_client_demo", "examples/mcp/mcp_client_demo.py")
        outcomes = asyncio.run(
            asyncio.wait_for(
                client_demo.run(self.base_url, "MCP-TEST-1", ["agent-one", "agent-two"]),
                timeout=90,
            )
        )

        self.assertEqual(sorted(outcomes["tools"]), ["loom_status", "reserve_resource"])
        self.assertTrue(outcomes["status"]["reachable"])

        first = outcomes["agent-one"]
        self.assertEqual((first["outcome"], first["locked"], first["status"]), ("LOCKED", True, 201))

        second = outcomes["agent-two"]
        self.assertEqual((second["outcome"], second["locked"], second["status"]), ("CONFLICT", False, 409))
        self.assertEqual(second["held_by"], "agent-one")
        self.assertEqual(second["suggested_alternative_resource"], "MCP-TEST-1_ALT")
        self.assertIn("retry_backoff_ms", second["next_action"])

    def test_pinned_agent_identity_overrides_what_the_model_supplies(self):
        server_module = _load("loom_mcp_server", "integrations/mcp_server/loom_mcp_server.py")
        client = FakeClient({"status": 201, "message": "ok", "correlation_id": "c"})

        def call(pinned, **arguments):
            server = server_module.build_server(client, "http://x", pinned_agent_id=pinned)
            result = asyncio.run(server.call_tool("reserve_resource", arguments))
            if isinstance(result, tuple):
                result = result[1]
            if isinstance(result, dict):
                return result.get("result", result)
            return json.loads(result[0].text)

        pinned = call("trusted-agent", resource_id="R-1", intent="buy", agent_id="victim-agent")
        self.assertEqual(client.calls[-1]["agent_id"], "trusted-agent")
        self.assertEqual(pinned["agent_id"], "trusted-agent")

        unpinned = call("", resource_id="R-2", intent="buy", agent_id="agent-7")
        self.assertEqual(client.calls[-1]["agent_id"], "agent-7")
        self.assertEqual(unpinned["agent_id"], "agent-7")

        missing = call("", resource_id="R-3", intent="buy")
        self.assertEqual(missing["outcome"], "INVALID")

    def test_unreachable_gateway_is_reported_as_error_not_lock(self):
        client_demo = _load("mcp_client_demo", "examples/mcp/mcp_client_demo.py")
        outcomes = asyncio.run(
            asyncio.wait_for(
                client_demo.run("http://127.0.0.1:9", "MCP-TEST-2", ["agent-x"]), timeout=90
            )
        )
        self.assertFalse(outcomes["status"]["reachable"])
        self.assertEqual(outcomes["agent-x"]["outcome"], "ERROR")
        self.assertFalse(outcomes["agent-x"]["locked"])


if __name__ == "__main__":
    unittest.main()
