# ATP (Agent Transfer Protocol) v1.0 Spec

## 1. The Handshake Packet
Every agent request must include the following metadata:
* `Agent-ID`: Unique identifier from Microsoft Entra ID.
* `Intent-Hash`: A SHA-256 hash of the specific goal (e.g., "Seat-4A-Flight-102").
* `Atomic-Expiry`: Milliseconds until the intent is considered "stale."

## 2. The Resolution Logic
If `Intent-Hash` exists in the global ledger (Cosmos DB):
* **Status 409 (Conflict)**: Trigger the Loom Negotiation Agent.
* **Status 201 (Locked)**: Proceed to execution.