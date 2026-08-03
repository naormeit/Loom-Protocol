import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib import request

from core.api.server import create_handler
from core.kernel.handshake import LoomKernel

sys.path.append(str(Path(__file__).resolve().parents[1] / "sdk" / "python"))
from loom_protocol import LoomClient


class APITests(unittest.TestCase):
    def setUp(self):
        self.kernel = LoomKernel()
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            create_handler(self.kernel),
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_health_endpoint(self):
        with request.urlopen(f"{self.base_url}/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"loom-atp", response.read())

    def test_python_sdk_can_reserve_resource(self):
        client = LoomClient(self.base_url)

        response = client.reserve(
            agent_id="SDK-AGENT-1",
            resource_id="DROP-SDK-1",
            intent="Purchase one limited item",
        )

        self.assertEqual(response["status"], 201)
        self.assertEqual(response["message"], "Atomic Lock Secured.")


if __name__ == "__main__":
    unittest.main()
