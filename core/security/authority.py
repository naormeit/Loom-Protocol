import time
from dataclasses import dataclass
from typing import Dict, Tuple

from core.models import ATPPacket
from core.security.signing import verify_signature


@dataclass(frozen=True)
class AuthorityDecision:
    allowed: bool
    reason: str = "allowed"


class AuthorityVerifier:
    def __init__(
        self,
        shared_secret: str = "",
        require_signature: bool = False,
        freshness_seconds: int = 300,
    ):
        self.shared_secret = shared_secret
        self.require_signature = require_signature
        self.freshness_seconds = freshness_seconds
        self._seen_nonces: Dict[Tuple[str, str], int] = {}

    def verify(self, packet: ATPPacket) -> AuthorityDecision:
        if not self.require_signature and not packet.signature:
            return AuthorityDecision(True)

        if not self.shared_secret:
            return AuthorityDecision(False, "signature verification is not configured")
        if not packet.signature:
            return AuthorityDecision(False, "missing packet signature")
        if not packet.nonce:
            return AuthorityDecision(False, "missing packet nonce")
        if packet.timestamp is None:
            return AuthorityDecision(False, "missing packet timestamp")

        now = int(time.time())
        if abs(now - packet.timestamp) > self.freshness_seconds:
            return AuthorityDecision(False, "packet timestamp is outside freshness window")

        nonce_key = (packet.agent_id, packet.nonce)
        if nonce_key in self._seen_nonces:
            return AuthorityDecision(False, "replayed packet nonce")

        if not verify_signature(packet.to_signable_mapping(), self.shared_secret):
            return AuthorityDecision(False, "invalid packet signature")

        self._seen_nonces[nonce_key] = packet.timestamp
        self._evict_old_nonces(now)
        return AuthorityDecision(True)

    def _evict_old_nonces(self, now: int) -> None:
        expired = [
            key
            for key, timestamp in self._seen_nonces.items()
            if abs(now - timestamp) > self.freshness_seconds
        ]
        for key in expired:
            del self._seen_nonces[key]
