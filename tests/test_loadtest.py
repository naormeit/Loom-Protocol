import http.client
import json
import os
import random
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from core.api.server import LoomHTTPServer, create_handler
from core.kernel.handshake import LoomKernel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "loadtest") not in sys.path:
    sys.path.append(str(ROOT / "loadtest"))

import run_load_test as lt  # noqa: E402


class GatewayCase(unittest.TestCase):
    def setUp(self):
        self.server = LoomHTTPServer(("127.0.0.1", 0), create_handler(LoomKernel()))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def base_url(self):
        return f"http://{self.host}:{self.port}"

    def run_level(self, **overrides):
        args = dict(
            target=(self.host, self.port, False),
            agents=60,
            concurrency=20,
            resources=1,
            unsafe_percent=0.0,
            timeout=10.0,
            seed=1,
            run_id=f"t{random.randint(0, 10**9)}",
            keepalive=True,
        )
        args.update(overrides)
        return lt.run_level(**args)


class StatisticsTests(unittest.TestCase):
    def test_percentile_interpolates(self):
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(lt.percentile(values, 0), 1.0)
        self.assertEqual(lt.percentile(values, 50), 2.5)
        self.assertEqual(lt.percentile(values, 100), 4.0)
        self.assertEqual(lt.percentile([7.0], 99), 7.0)
        self.assertIsNone(lt.percentile([], 50))

    def test_latency_summary_shape_and_order(self):
        summary = lt.latency_summary([5.0, 1.0, 3.0, 2.0, 4.0])
        self.assertEqual(summary["count"], 5)
        self.assertEqual((summary["min"], summary["max"]), (1.0, 5.0))
        self.assertLessEqual(summary["p50"], summary["p90"])
        self.assertLessEqual(summary["p90"], summary["p95"])
        self.assertLessEqual(summary["p95"], summary["p99"])
        self.assertEqual(lt.latency_summary([])["p50"], None)

    def test_command_is_quoted_and_hides_local_paths(self):
        command = lt.sanitize_command(
            ["--agents", "100", "--label", "local gateway", "--output-dir", "C:\\Users\\me\\tmp", "--report=x.md", "--check"]
        )
        self.assertIn("'local gateway'", command)
        self.assertNotIn("Users", command)
        self.assertNotIn("--output-dir", command)
        self.assertNotIn("--report", command)
        self.assertIn("--check", command)


class PacketTests(unittest.TestCase):
    def test_resources_are_shared_out_evenly(self):
        packets = lt.build_packets(10, 3, 0.0, "r", random.Random(1))
        counts = {}
        for packet in packets:
            counts[packet["intent_hash"]] = counts.get(packet["intent_hash"], 0) + 1
        self.assertEqual(sorted(counts.values()), [3, 3, 4])
        self.assertEqual(len({packet["agent_id"] for packet in packets}), 10)

    def test_unsafe_share_is_exact_and_marked(self):
        packets = lt.build_packets(40, 1, 25.0, "r", random.Random(1))
        unsafe = [packet for packet in packets if packet["_unsafe"]]
        self.assertEqual(len(unsafe), 10)
        self.assertTrue(all(packet["intent"] == lt.UNSAFE_INTENT for packet in unsafe))

    def test_same_seed_gives_same_order(self):
        first = [p["agent_id"] for p in lt.build_packets(30, 2, 10.0, "r", random.Random(5))]
        second = [p["agent_id"] for p in lt.build_packets(30, 2, 10.0, "r", random.Random(5))]
        self.assertEqual(first, second)


class RunTests(GatewayCase):
    def test_one_winner_with_connection_reuse(self):
        result = self.run_level(keepalive=True)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["status_counts"], {"201": 1, "409": 59})
        self.assertTrue(result["exactly_one_winner_each"])
        self.assertEqual(result["latency_ms"]["count"], 60)

    def test_one_winner_with_a_new_connection_per_request(self):
        result = self.run_level(keepalive=False)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["status_counts"], {"201": 1, "409": 59})
        self.assertTrue(result["exactly_one_winner_each"])

    def test_agents_spread_across_resources_get_one_winner_each(self):
        result = self.run_level(agents=60, resources=6)
        self.assertEqual(result["locks_granted"], 6)
        self.assertEqual(result["status_counts"].get("409"), 54)
        self.assertTrue(result["exactly_one_winner_each"])
        self.assertEqual(result["resources_with_multiple_winners"], [])

    def test_unsafe_requests_are_rejected_and_counted(self):
        result = self.run_level(agents=40, unsafe_percent=25.0)
        self.assertEqual(result["unsafe_sent"], 10)
        self.assertEqual(result["unsafe_rejected_403"], 10)
        self.assertEqual(result["status_counts"].get("403"), 10)
        self.assertEqual(result["status_counts"].get("201"), 1)

    def test_failures_are_counted_not_hidden(self):
        result = lt.run_level(
            target=("127.0.0.1", 9, False),
            agents=8,
            concurrency=4,
            resources=1,
            unsafe_percent=0.0,
            timeout=2.0,
            seed=1,
            run_id="down",
            keepalive=True,
        )
        self.assertEqual(result["errors"], 8)
        self.assertEqual(result["responded"], 0)
        self.assertEqual(result["error_rate_percent"], 100.0)
        self.assertFalse(result["exactly_one_winner_each"])
        self.assertTrue(result["one_winner_rule_held"])  # nothing was granted, so nothing broke


class CommandLineTests(GatewayCase):
    def test_check_run_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = os.path.join(directory, "report.md")
            code = lt.main(
                [
                    "--base-url", self.base_url(),
                    "--agents", "30,60",
                    "--concurrency", "10",
                    "--rounds", "2",
                    "--warmup", "2",
                    "--pause", "0",
                    "--output-dir", directory,
                    "--report", report_path,
                    "--label", "unit test",
                    "--check",
                ]
            )
            self.assertEqual(code, 0)
            files = sorted(os.listdir(directory))
            self.assertEqual(sum(name.endswith(".json") for name in files), 1)
            self.assertIn("report.md", files)
            json_path = next(os.path.join(directory, n) for n in files if n.endswith(".json"))
            with open(json_path, encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertEqual(len(data["runs"]), 4)
            self.assertNotIn(directory, data["meta"]["command"])
            with open(report_path, encoding="utf-8") as handle:
                markdown = handle.read()
            self.assertIn("One-winner rule", markdown)
            self.assertIn("Read this before quoting the numbers", markdown)

    def test_unreachable_gateway_is_a_clear_failure(self):
        code = lt.main(["--base-url", "http://127.0.0.1:9", "--agents", "5", "--warmup", "0", "--timeout", "2"])
        self.assertEqual(code, 2)

    def test_bad_arguments_are_rejected(self):
        self.assertEqual(lt.main(["--agents", "ten"]), 2)
        self.assertEqual(lt.main(["--agents", "5", "--resources", "9"]), 2)


class ServerSettingsTests(GatewayCase):
    """Settings found by the load test: burst-sized backlog and reusable connections."""

    def test_backlog_is_sized_for_bursts(self):
        self.assertGreaterEqual(LoomHTTPServer.request_queue_size, 128)
        self.assertTrue(LoomHTTPServer.daemon_threads)

    def test_one_connection_serves_many_requests(self):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            for _ in range(3):
                connection.request("GET", "/health")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertFalse(response.will_close)
                response.read()
        finally:
            connection.close()

    def test_connection_close_is_honoured(self):
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            connection.request("GET", "/health", headers={"Connection": "close"})
            response = connection.getresponse()
            response.read()
            # The server closes its side after answering: the next read sees end-of-stream.
            connection.sock.settimeout(3)
            self.assertEqual(connection.sock.recv(1), b"")
        finally:
            connection.close()

    def test_idle_connections_time_out(self):
        handler = create_handler(LoomKernel())
        self.assertEqual(handler.protocol_version, "HTTP/1.1")
        self.assertGreater(handler.timeout, 0)


if __name__ == "__main__":
    unittest.main()
