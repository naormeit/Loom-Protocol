import json
from typing import Any, Dict, Optional
from urllib import error, request

from core.security.signing import attach_signature


class LoomClientError(RuntimeError):
    pass


class LoomClient:
    def __init__(self, base_url: str, shared_secret: Optional[str] = None, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.shared_secret = shared_secret
        self.timeout = timeout

    def reserve(
        self,
        agent_id: str,
        resource_id: str,
        intent: str,
        expiry_ms: int = 5000,
    ) -> Dict[str, Any]:
        packet = {
            "agent_id": agent_id,
            "intent": intent,
            "intent_hash": resource_id,
            "expiry": expiry_ms,
        }
        if self.shared_secret:
            packet = attach_signature(packet, self.shared_secret)
        return self.handshake(packet)

    def handshake(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(packet).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}/v1/handshake",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            payload = exc.read().decode("utf-8")
            try:
                return json.loads(payload)
            except json.JSONDecodeError as parse_exc:
                raise LoomClientError(payload) from parse_exc
        except error.URLError as exc:
            raise LoomClientError(f"failed to reach Loom gateway: {exc}") from exc
