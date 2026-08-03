from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


class PacketValidationError(ValueError):
    """Raised when an ATP packet cannot be processed safely."""


@dataclass(frozen=True)
class ATPPacket:
    agent_id: str
    intent: str
    intent_hash: str
    expiry: int
    nonce: Optional[str] = None
    timestamp: Optional[int] = None
    signature: Optional[str] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ATPPacket":
        missing = [
            field
            for field in ("agent_id", "intent", "intent_hash", "expiry")
            if field not in payload
        ]
        if missing:
            raise PacketValidationError(
                "Missing required ATP packet field(s): " + ", ".join(missing)
            )

        agent_id = cls._required_text(payload["agent_id"], "agent_id")
        intent = cls._required_text(payload["intent"], "intent")
        intent_hash = cls._required_text(payload["intent_hash"], "intent_hash")

        try:
            expiry = int(payload["expiry"])
        except (TypeError, ValueError) as exc:
            raise PacketValidationError("expiry must be a positive integer") from exc

        if expiry <= 0:
            raise PacketValidationError("expiry must be a positive integer")

        timestamp = payload.get("timestamp")
        if timestamp is not None:
            try:
                timestamp = int(timestamp)
            except (TypeError, ValueError) as exc:
                raise PacketValidationError("timestamp must be an integer") from exc

        return cls(
            agent_id=agent_id,
            intent=intent,
            intent_hash=intent_hash,
            expiry=expiry,
            nonce=cls._optional_text(payload.get("nonce"), "nonce"),
            timestamp=timestamp,
            signature=cls._optional_text(payload.get("signature"), "signature"),
        )

    @staticmethod
    def _required_text(value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PacketValidationError(f"{field_name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _optional_text(value: Any, field_name: str) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise PacketValidationError(f"{field_name} must be a non-empty string")
        return value.strip()

    def to_signable_mapping(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "agent_id": self.agent_id,
            "intent": self.intent,
            "intent_hash": self.intent_hash,
            "expiry": self.expiry,
        }
        if self.nonce is not None:
            payload["nonce"] = self.nonce
        if self.timestamp is not None:
            payload["timestamp"] = self.timestamp
        if self.signature is not None:
            payload["signature"] = self.signature
        return payload


@dataclass(frozen=True)
class HandshakeResult:
    status: int
    message: str
    correlation_id: str
    parsed_as: Optional[str] = None
    conflict_with: Optional[str] = None
    negotiation_payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        response = {
            "status": self.status,
            "message": self.message,
            "correlation_id": self.correlation_id,
        }

        if self.parsed_as is not None:
            response["parsed_as"] = self.parsed_as
        if self.conflict_with is not None:
            response["conflict_with"] = self.conflict_with
        if self.negotiation_payload is not None:
            response["negotiation_payload"] = self.negotiation_payload

        return response
