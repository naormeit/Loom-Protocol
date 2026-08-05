# Loom Protocol

**ATP: an atomic reservation layer for AI agents competing for finite resources.**

Loom helps marketplaces, commerce platforms, booking systems, and agent builders avoid the same failure mode: many autonomous agents trying to buy, book, or reserve one scarce item at the same time.

The current MVP focuses on **limited-inventory agent commerce**. A shopping agent sends intent to Loom before hitting the final vendor checkout. Loom validates the packet, checks authority, screens unsafe intent, attempts an atomic lock, and returns either a confirmed lock or a negotiation payload.

## What Works Today

- Local ATP kernel with packet validation and stable response contracts.
- Thread-safe local atomic ledger that proves one-winner lock behavior.
- Local intent parser and content-safety checker.
- Optional HMAC-SHA256 packet signing with nonce and timestamp replay protection.
- Local HTTP API gateway: `POST /v1/handshake`.
- Python SDK client for agent integrations.
- Stress and scenario demos for limited-inventory collisions.
- Unit tests for success, conflict, safety, validation, API, SDK, signing, and replay protection.

## Product Wedge

Loom starts with limited-inventory drops:

1. Hundreds or thousands of agents attempt to reserve the same resource.
2. Loom pre-clears the intent before checkout.
3. One agent receives an atomic lock.
4. Other agents receive a structured conflict response with retry guidance.
5. The vendor avoids duplicate reservations, retry storms, and ambiguous partial state.

This wedge is intentionally concrete. The long-term protocol vision is broader, but the MVP must first solve one painful workflow well.

## Quick Start

### Run Tests

```powershell
python -m unittest discover -s tests -p "test*.py"
```

### Run The Two-Agent Collision Demo

```powershell
python tests\stress\collision_test.py
```

### Start The Local API Gateway

```powershell
python -m core.api.server
```

The gateway starts at `http://127.0.0.1:8080` by default.

Health check:

```powershell
curl http://127.0.0.1:8080/health
```

Handshake:

```powershell
curl -X POST http://127.0.0.1:8080/v1/handshake `
  -H "Content-Type: application/json" `
  -d "{\"agent_id\":\"SHOPPING-AGENT-1\",\"intent\":\"Purchase one limited item\",\"intent_hash\":\"DROP-001\",\"expiry\":5000}"
```

### Run The Limited Inventory Scenario

Start the API gateway in one terminal, then run:

```powershell
python examples\scenarios\limited_inventory_drop.py --agents 100
```

Expected result: one secured lock and the remaining agents receiving conflict negotiation responses.

## Signed Packets

Set a shared secret and require signatures:

```powershell
$env:LOOM_REQUIRE_SIGNATURE="true"
$env:LOOM_SHARED_SECRET="dev-secret"
python -m core.api.server
```

Use the SDK to sign packets:

```python
from loom_protocol import LoomClient

client = LoomClient("http://127.0.0.1:8080", shared_secret="dev-secret")
response = client.reserve(
    agent_id="SHOPPING-AGENT-42",
    resource_id="DROP-SURFACE-001",
    intent="Purchase one Surface Pro from the limited drop",
)
print(response)
```

## API Contract

`POST /v1/handshake`

Required fields:

- `agent_id`: unique agent identifier.
- `intent`: natural language transaction intent.
- `intent_hash`: resource identifier or resource-intent hash.
- `expiry`: lock expiry in milliseconds.

Optional signed-packet fields:

- `nonce`
- `timestamp`
- `signature`

Status codes:

- `201`: atomic lock secured.
- `409`: active lock conflict; response includes `negotiation_payload`.
- `403`: unsafe intent rejected.
- `401`: authority/signature failure.
- `400`: invalid packet.

## Microsoft Imagine Cup Direction

The MVP now supports two runtime modes:

- `LOOM_MODE=local`: deterministic local adapters for development, tests, and offline demos.
- `LOOM_MODE=azure`: production adapters for Azure OpenAI / Azure AI Foundry-style chat deployments, Azure AI Content Safety, and Azure Cosmos DB.

The production path uses Microsoft Cloud services cleanly:

- Azure AI Foundry or Azure OpenAI for structured intent parsing.
- Azure AI Content Safety for intent risk screening.
- Azure Cosmos DB for globally distributed conditional locks.
- Azure Functions or Azure Container Apps for the ATP gateway.
- Microsoft Entra ID for agent authority and enterprise identity.

Current status: the repo contains local mode and Azure-mode adapters. Azure credentials, deployed resources, and live integration testing are still required before claiming a production deployment.

### Azure Mode Configuration

```powershell
$env:LOOM_MODE="azure"
$env:AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com"
$env:AZURE_OPENAI_API_KEY="<key>"
$env:AZURE_OPENAI_DEPLOYMENT="<deployment>"
$env:CONTENT_SAFETY_ENDPOINT="https://<resource>.cognitiveservices.azure.com"
$env:CONTENT_SAFETY_KEY="<key>"
$env:COSMOS_ENDPOINT="https://<account>.documents.azure.com:443/"
$env:COSMOS_KEY="<key>"
$env:COSMOS_DATABASE="loom"
$env:COSMOS_CONTAINER="locks"
python -m core.api.server
```

Cosmos DB container expectation: use `/resource_id` as the partition key. The Azure adapter creates lock documents with `id` and `resource_id` equal to the ATP `intent_hash`.

## Repository Map

- `core/kernel/handshake.py`: ATP handshake orchestration.
- `core/models.py`: packet and response models.
- `core/ai/`: local intent and safety services.
- `core/security/`: signing, signature verification, and replay protection.
- `core/database/`: local atomic ledger and Cosmos DB adapter.
- `core/api/`: local HTTP API gateway.
- `sdk/python/`: Python client SDK.
- `examples/`: agent and scenario demos.
- `tests/`: unit and integration tests.
- `docs/competition/score_to_10_plan.md`: roadmap to a judge-ready 10/10 submission.

## Next Production Milestones

- Add TypeScript SDK.
- Expand CI with Docker build, example smoke tests, Bicep validation, and website checks.
- Complete Azure deployment infrastructure with a real Loom container image, service configuration, and live validation evidence.
- Collect founder-led validation from marketplaces, agent builders, and platform teams.
