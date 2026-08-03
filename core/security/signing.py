import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, Mapping


SIGNED_FIELDS = ("agent_id", "intent", "intent_hash", "expiry", "nonce", "timestamp")


def canonical_payload(payload: Mapping[str, Any]) -> str:
    signable = {field: payload[field] for field in SIGNED_FIELDS if field in payload}
    return json.dumps(signable, separators=(",", ":"), sort_keys=True)


def sign_payload(payload: Mapping[str, Any], secret: str) -> str:
    if not secret:
        raise ValueError("shared secret is required to sign ATP packets")
    message = canonical_payload(payload).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_signature(payload: Mapping[str, Any], secret: str) -> bool:
    signature = payload.get("signature")
    if not isinstance(signature, str) or not signature:
        return False
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(signature, expected)


def attach_signature(payload: Mapping[str, Any], secret: str) -> Dict[str, Any]:
    signed = dict(payload)
    signed.setdefault("nonce", uuid.uuid4().hex)
    signed.setdefault("timestamp", int(time.time()))
    signed["signature"] = sign_payload(signed, secret)
    return signed
