# Loom Protocol

**ATP: an atomic reservation layer for AI agents competing for finite resources.**

Loom helps marketplaces, commerce platforms, booking systems, and agent builders avoid the same failure mode: many autonomous agents trying to buy, book, or reserve one scarce item at the same time.

The current MVP focuses on **limited-inventory agent commerce**. A shopping agent sends intent to Loom before hitting the final vendor checkout. Loom validates the packet, checks authority, screens unsafe intent, attempts an atomic lock, and returns either a confirmed lock or a negotiation payload.

> **Honest status:** Loom is a working **local MVP**. The hosted Azure deployment so far runs in `LOOM_MODE=local`. The Azure OpenAI, Content Safety, and Cosmos DB adapters exist but have **not** been validated against live Azure services. No customer validation exists yet. See [Status](#status) and [Known Limitations](#known-limitations).

## Contents

- [Status](#status)
- [How It Works](#how-it-works)
- [Product Wedge](#product-wedge)
- [Quick Start](#quick-start)
- [The Website](#the-website)
- [Configuration Reference](#configuration-reference)
- [Signed Packets](#signed-packets)
- [API Contract](#api-contract)
- [Azure Mode](#azure-mode)
- [Microsoft Imagine Cup 2027](#microsoft-imagine-cup-2027)
- [Known Limitations](#known-limitations)
- [Repository Map](#repository-map)
- [Continuous Integration](#continuous-integration)
- [Roadmap](#roadmap)

## Status

| Area | State | Notes |
| --- | --- | --- |
| ATP handshake kernel (validation, correlation IDs, stable response contract) | Implemented | Local and tested. |
| Atomic local ledger (one winner under concurrency) | Implemented | Thread-safe, in memory; proven by tests and the collision scenario. |
| Local HTTP API gateway (`/health`, `POST /v1/handshake`) | Implemented | Standard-library server; intended for local and demo use. |
| Python SDK (`reserve`, optional signing) | Implemented | `sdk/python/`. |
| HMAC-SHA256 signing, nonce, timestamp, replay protection | Implemented | Shared-secret scheme; see [limitations](#known-limitations). |
| Local intent parser and content-safety checker | Implemented | Deterministic; the safety check is a keyword list, not real screening. |
| Static website with live per-agent response grid | Implemented | See [The Website](#the-website). |
| Landing-page particle intro | Implemented | Decorative only. |
| Azure-mode adapters (OpenAI-style parser, Content Safety, Cosmos DB) | Implemented, not live-validated | Unit-tested with mocks only. |
| Hosted deployment on Azure Container Apps | Partial | Deployed and health-checked in `LOOM_MODE=local` only. |
| CI (Python 3.10/3.11, website checks, Docker build, Bicep validation) | Implemented | See [CI](#continuous-integration). |
| Full `LOOM_MODE=azure` with live Microsoft AI services | In progress | Blocked on a subscription/region that allows Azure OpenAI and Content Safety. |
| Public-key signatures (true non-repudiation), audit trail, rate limiting | Planned | |
| Microsoft Entra ID authority verification | Planned | Not implemented. |
| TypeScript SDK | Planned | |
| Customer validation and pricing | Planned | None collected yet. |

## How It Works

Every request goes through the same handshake on `POST /v1/handshake`:

1. An agent or the SDK sends an ATP packet.
2. Loom validates the packet shape (`400` on failure).
3. Loom verifies authority when signature mode is enabled (`401` on failure).
4. Loom parses and normalizes the intent.
5. Loom screens the intent for unsafe behavior (`403` if rejected).
6. Loom attempts an atomic lock on the target resource.
7. Loom returns `201` with a lock, or `409` with a `negotiation_payload` for the losing agents.

Loom is not a marketplace or a checkout replacement. It is a pre-transaction decision layer for a specific class of high-contention, agent-driven transactions.

## Product Wedge

Loom starts with limited-inventory drops:

1. Hundreds or thousands of agents attempt to reserve the same resource.
2. Loom pre-clears the intent before checkout.
3. One agent receives an atomic lock.
4. Other agents receive a structured conflict response with retry guidance.
5. The vendor avoids duplicate reservations, retry storms, and ambiguous partial state.

This wedge is intentionally concrete, but it is still a hypothesis: vendors usually already prevent double-selling inside their own inventory systems, so the real customer pain has to be confirmed through discovery interviews before the project commits to it (see [Roadmap](#roadmap)).

## Quick Start

All commands are PowerShell. Python 3.10 or newer is required; the local mode has no third-party dependencies.

### Run the tests

```powershell
python -m unittest discover -s tests -p "test*.py"
```

Expected: 16 tests, all passing.

### Run the two-agent collision demo

```powershell
python tests\stress\collision_test.py
```

### Start the local API gateway

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

Send the same packet again with a different `agent_id` to see the `409` conflict response with retry guidance.

### Run the limited-inventory scenario

Start the API gateway in one terminal, then run:

```powershell
python examples\scenarios\limited_inventory_drop.py --agents 100
```

Expected result: one secured lock and 99 agents receiving conflict negotiation responses.

## The Website

The static website in `website/` is the judge-facing demo surface. It needs no build step.

### Run it locally

Terminal 1, the API:

```powershell
python -m core.api.server
```

Terminal 2, the website (serve it over HTTP so the logo can be sampled for the intro):

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory website
```

Open `http://127.0.0.1:5500/`. The API allows browser calls from `http://127.0.0.1:5500` and `http://localhost:5500` by default.

### Live response grid (the simulator)

Press **Run** and the simulator sends one real `POST /v1/handshake` request per agent (20 to 300, set by the slider):

- Each agent is one cell in the grid. The cell is coloured by the status code of that agent's own response as it arrives: gold for `201` lock, red for `409` conflict, grey for an error, dim while waiting.
- The real winning agent is outlined and named in the header, with the time the lock was granted.
- A chart shows responses arriving over time, and the lock/conflict counters tick up live.
- Nothing is decided ahead of time; the winner and timings are whatever the server returned.

If the API is not reachable, the view is labelled **SIMULATED**, its outcomes are generated locally, and the timing label reads "simulated, not measured". It never presents generated results as measured.

### Pointing the website at another backend

Open the page with `?api=https://<host>` (http/https origins only). The endpoint shown in the page updates to match. For a browser on another origin to call the API, add that origin to the server:

```powershell
$env:LOOM_ALLOWED_ORIGINS="https://my-site.example.com,https://other.example.com"
python -m core.api.server
```

### Landing-page intro

`website/hero-intro.js` plays a short decorative intro: particles gather into a rotating sphere, morph into the Loom logo (sampled from `website/assets/loom-logo.png`), and the page content then fades in. It does not represent any request or protocol data.

- Plays once per browser session; `?intro=1` forces it and `?intro=0` disables it.
- Skipped when the visitor prefers reduced motion.
- Skippable with a click or any key.
- Plain canvas and the Web Animations API; no dependency or CDN.
- Opened directly from `file://`, the logo cannot be sampled and the particles settle into a ring instead.

More website notes are in `website/README.md` and `docs/website/main_website_memory.md`.

## Configuration Reference

| Variable | Default | Purpose |
| --- | --- | --- |
| `LOOM_MODE` | `local` | `local` for deterministic adapters, `azure` for the Azure adapters. |
| `LOOM_HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` inside a container. |
| `LOOM_PORT` | `8080` | Port. |
| `LOOM_REQUIRE_SIGNATURE` | `false` | Require signed packets. |
| `LOOM_SHARED_SECRET` | empty | Shared secret for HMAC signing. |
| `LOOM_ALLOWED_ORIGINS` | empty | Comma-separated extra browser origins allowed to call the API (added to the localhost:5500 defaults). |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT` | | Azure OpenAI intent parsing (azure mode). |
| `CONTENT_SAFETY_ENDPOINT`, `CONTENT_SAFETY_KEY`, `CONTENT_SAFETY_BLOCK_THRESHOLD` | empty, empty, `4` | Azure AI Content Safety (azure mode). |
| `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER` | empty, empty, `loom`, `locks` | Cosmos DB lock ledger (azure mode). |

`.env.example` lists them all. Never commit real keys.

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

Signed packets carry a `nonce` and `timestamp`; repeated nonces and stale timestamps are rejected (replay protection).

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

Every response includes a `correlation_id`. `GET /health` returns `{"status": "ok", "service": "loom-atp"}`.

## Azure Mode

The MVP supports two runtime modes:

- `LOOM_MODE=local`: deterministic local adapters for development, tests, and offline demos.
- `LOOM_MODE=azure`: adapters for Azure OpenAI / Azure AI Foundry-style chat deployments, Azure AI Content Safety, and Azure Cosmos DB.

The intended production path:

- Azure AI Foundry or Azure OpenAI for structured intent parsing.
- Azure AI Content Safety for intent risk screening.
- Azure Cosmos DB for globally distributed conditional locks.
- Azure Functions or Azure Container Apps for the ATP gateway.
- Microsoft Entra ID for agent authority and enterprise identity (not yet implemented).

**Current status:** the adapters exist and are unit-tested with mocks. A container image was deployed to Azure Container Apps and health-checked, with Cosmos DB and a container registry created, but it ran in `LOOM_MODE=local`. Live Azure OpenAI, Content Safety, and Cosmos lock evidence has not been collected. See `docs/operations/live_azure_validation_2026-08-06.md` for exactly what was and was not validated.

### Azure mode configuration

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

Operational docs: `docs/operations/azure_mode.md` and `docs/operations/deployment_runbook.md`. The Bicep template in `infra/main.bicep` currently defines the Container Apps environment and app; other Azure resources are created separately.

## Microsoft Imagine Cup 2027

Loom is being prepared as an entry to Imagine Cup 2027. The format is a startup competition run through Microsoft for Startups, not a student-project contest:

- Applications close **2027-02-28, 23:59 CST** via Award Force.
- The entrant must be a registered legal entity founded on or after 2024-11-02, with at most four team members.
- By the deadline the startup must use at least ten Azure services on one subscription, with at least USD 1.00 of usage on each.
- Planned category: **Student Startup** (all founders enrolled students; the Student Prize is the ceiling for that category).
- Stages: application scoring, expert review (March 2027), recorded interviews, final judging (April 2027).

The full plan, rubric mapping, ten-service Azure set, evidence checklist, and timeline are in [`docs/competition/score_to_10_plan.md`](docs/competition/score_to_10_plan.md). Open items that matter most: incorporation, a startup Azure subscription, live Azure-mode evidence, and customer validation.

## Known Limitations

- **Safety screening is a keyword list locally.** It blocks a few terms (delete, hack, bypass, malware, steal, exploit) and will pass many unsafe intents. Real screening depends on the Azure Content Safety path, which is not live-validated.
- **Signing is shared-secret HMAC.** It authenticates and prevents replay, but either side could have produced a signature, so it does not provide non-repudiation. Public-key signatures are planned.
- **No Entra ID verification, audit trail, or rate limiting yet.**
- **Negotiation is synthetic.** The suggested alternative resource and retry backoff are demo logic, not a negotiation policy.
- **The local ledger is in memory and single-process.** Cross-process and cross-region locking relies on the Cosmos DB adapter, which has not been tested against real contention.
- **The API uses the standard-library HTTP server,** suitable for local and demo use only.
- **No customer validation or pricing yet.**

## Repository Map

- `core/kernel/handshake.py`: ATP handshake orchestration.
- `core/models.py`: packet and response models.
- `core/config.py`: environment-driven configuration.
- `core/ai/`: local and Azure intent and safety services.
- `core/security/`: signing, signature verification, and replay protection.
- `core/database/`: local atomic ledger and Cosmos DB adapter.
- `core/api/`: local HTTP API gateway.
- `sdk/python/`: Python client SDK.
- `examples/`: agent and scenario demos.
- `tests/`: unit and integration tests.
- `website/`: static demo site (`index.html`, `app.js` simulator, `hero-intro.js` intro, `styles.css`, `assets/`).
- `infra/main.bicep`: Azure Container Apps template.
- `Dockerfile`: API container image.
- `docs/competition/`: Imagine Cup 2027 plan.
- `docs/operations/`: Azure mode, deployment runbook, validation evidence.
- `docs/spec/`: ATP specification and architecture notes.
- `docs/website/`: website notes.
- `.github/workflows/ci.yml`: CI.

## Continuous Integration

GitHub Actions runs on every push and pull request:

- **Python 3.10 and 3.11:** import smoke test, compile check, unit tests, local example smoke, API scenario smoke.
- **Website static checks:** required files and key strings in `index.html`, `app.js`, and `styles.css`.
- **Docker build:** builds the API image and smoke-tests it.
- **Bicep validation:** builds `infra/main.bicep`.

## Roadmap

1. **Customer discovery:** about 15 interviews with agent builders, marketplace and e-commerce platform engineers, and operations teams; decide whether to keep or change the wedge.
2. **Company and Azure subscription:** incorporate, enroll in Microsoft for Startups, create the startup subscription.
3. **Live Azure mode:** real Foundry intent parsing, Content Safety, and Cosmos locks with captured evidence (public `/health`, one `201` and one `409` for the same resource, service metrics).
4. **Security:** public-key signatures, persistent audit trail, rate limiting, Entra ID or an explicit scope-out.
5. **Load evidence:** 100 and 1,000 agent runs (then larger) with saved latency and conflict metrics.
6. **Infrastructure as code** for all required Azure services.
7. **TypeScript SDK** and a minimal agent integration sample.
8. **Submission package:** written responses, pitch deck, demo video, architecture diagram, judge FAQ.
