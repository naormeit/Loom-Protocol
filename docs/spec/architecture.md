# Loom Protocol Architecture

Loom is an atomic reservation middleware layer for AI agents. The first MVP use case is limited-inventory agent commerce.

## Local MVP Architecture

1. Agent or SDK submits an ATP packet to `POST /v1/handshake`.
2. API gateway validates JSON and forwards the packet to the Loom kernel.
3. Kernel validates packet shape.
4. Authority verifier checks packet signature when signature mode is enabled.
5. Intent parser normalizes the raw agent intent.
6. Content-safety checker rejects unsafe intent before state mutation.
7. Atomic ledger attempts to lock the resource.
8. Kernel returns lock success, conflict negotiation, unsafe rejection, invalid packet, or authority rejection.

## Components

| Layer | Local implementation | Production target |
| --- | --- | --- |
| Gateway | `core/api/server.py` | Azure Functions or Azure Container Apps |
| Kernel | `core/kernel/handshake.py` | Same orchestration logic |
| Intent parser | `core/ai/intent_parser.py` | Azure AI Foundry or Azure OpenAI |
| Safety checker | `core/ai/content_safety.py` | Azure AI Content Safety |
| Authority | `core/security/authority.py` | Microsoft Entra ID plus packet signatures |
| Ledger | `core/database/ledger.py` | Azure Cosmos DB conditional writes |
| SDK | `sdk/python/loom_protocol/client.py` | Python and TypeScript SDKs |

## Data Flow

```text
Agent -> SDK -> ATP Gateway -> Authority Check -> Intent Parser
      -> Content Safety -> Atomic Ledger -> Lock / Conflict Response
```

## Reliability Properties

- One-winner lock behavior for a single resource under concurrent local requests.
- Expiring locks through millisecond TTL values.
- Replay rejection for signed packets.
- Structured conflict response for autonomous retry or alternative selection.

## Production Requirements

- Cosmos DB unique key or ETag-based conditional writes.
- Multi-region latency and consistency measurements.
- Azure AI service telemetry and failure handling.
- Rate limiting and abuse controls.
- Persistent audit log.
- Deployment and rollback runbook.
