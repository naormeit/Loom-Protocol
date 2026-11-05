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
- [Agent Integrations](#agent-integrations)
- [Azure Mode](#azure-mode)
- [Microsoft Imagine Cup 2027](#microsoft-imagine-cup-2027)
- [Audit Log and Rate Limiting](#audit-log-and-rate-limiting)
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
| MCP server (`reserve_resource`, `loom_status`) and a two-agent demo | Implemented | Round trip tested with the official MCP Python client; see [Agent Integrations](#agent-integrations). Not tested with a real MCP host or an LLM. |
| HMAC-SHA256 signing, nonce, timestamp, replay protection | Implemented | Shared-secret scheme; see [limitations](#known-limitations). |
| Local intent parser and content-safety checker | Implemented | Deterministic; the safety check is a keyword list, not real screening. |
| Static website: landing page plus live demo page with per-agent response grid | Implemented | See [The Website](#the-website). |
| Landing-page particle intro | Implemented | Decorative only; plays on the landing page. |
| Azure-mode adapters (OpenAI-style parser, Content Safety, Cosmos DB) | Implemented, not live-validated | Unit-tested with mocks only. |
| Hosted deployment on Azure Container Apps | Partial | Deployed and health-checked in `LOOM_MODE=local` only. |
| CI (Python 3.10/3.11, website checks, Docker build, Bicep validation) | Implemented | See [CI](#continuous-integration). |
| Full `LOOM_MODE=azure` with live Microsoft AI services | In progress | Blocked on a subscription/region that allows Azure OpenAI and Content Safety. |
| Hash-chained audit log, per-agent and per-client-address rate limiting | Implemented (local) | Tamper-evident file log and in-memory limiters; see [Audit Log and Rate Limiting](#audit-log-and-rate-limiting). |
| Public-key signatures (true non-repudiation) | Planned | |
| Microsoft Entra ID authority verification | Planned | Not implemented. |
| TypeScript SDK | Planned | |
| Customer validation and pricing | Planned | None collected yet. |

## How It Works

Every request goes through the same handshake on `POST /v1/handshake`:

1. An agent or the SDK sends an ATP packet.
2. Loom validates the packet shape (`400` on failure) and applies the per-agent rate limit (`429` when exceeded).
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

The static website in `website/` has two pages and needs no build step:

- **Landing page** (`index.html`): the front door. A short story for a first-time visitor: what Loom is, the problem (framed as a hypothesis), how it works in three steps, who it might be for, an honest "where it stands" section, and two calls to action. It opens with the particle intro.
- **Live demo** (`demo.html`): the simulator with real responses, a "how to read the simulator" section, the protocol path, the implementation status, and the proof grid.

The landing page has an illustration of many agents, Loom, one lock and the retry answers; it is labelled as an illustration and is not live data. The "Tell us what breaks for you" button opens a pre-filled GitHub issue on this repository, which is a lightweight way to collect problem reports without running any backend. To use a form or another channel instead, change the `href` of those links in `website/index.html`.

#### Landing-page animation

All landing-page animation is decorative and plain CSS and JavaScript (no animation library):

- **Scroll reveal** (`website/landing.js`): sections, headings, step cards and status cards fade and rise into view as you scroll, with a 90 ms stagger between sibling cards. Content stays visible if the script does not run.
- **Looping illustration** (CSS keyframes in `website/styles.css`, 5-second loop): agents light up and send requests along flowing dashed lines, Loom pulses, the winning agent pops and gets its "201 lock" label, then the retry agents light up with "409 + retry guidance". It is labelled as an illustration, not live data.
- **Hover and focus**: buttons lift on hover, cards brighten, and links, buttons and form controls get a visible keyboard focus outline (also on the demo page).
- **Reduced motion**: with `prefers-reduced-motion`, scroll reveal, the illustration loop and hover motion are all switched off and everything is shown statically.

### Run it locally

Terminal 1, the API:

```powershell
python -m core.api.server
```

Terminal 2, the website (serve it over HTTP so the logo can be sampled for the intro):

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory website
```

Open `http://127.0.0.1:5500/` for the landing page and `http://127.0.0.1:5500/demo.html` for the simulator. The API allows browser calls from `http://127.0.0.1:5500` and `http://localhost:5500` by default.

### Live response grid (the simulator, on `demo.html`)

Press **Run** and the simulator sends one real `POST /v1/handshake` request per agent (20 to 300, set by the slider):

- Each agent is one cell in the grid. The cell is coloured by the status code of that agent's own response as it arrives: gold for `201` lock, red for `409` conflict, grey for an error, dim while waiting.
- The real winning agent is outlined and named in the header, with the time the lock was granted.
- A chart shows responses arriving over time, and the lock/conflict counters tick up live.
- Nothing is decided ahead of time; the winner and timings are whatever the server returned.
- Motion (3 seconds in total): on Run a black hole forms at the centre of the grid area, releases the cubes (one per agent) along spiral paths into their own blocks, then collapses; the winning agent sends out a pulse ring and the result line appears at 2.4 seconds. Each cell also pops when its response arrives. The motion is decorative: positions never encode results and colours always come from the real responses, so the counters and cell colours can already be final while the motion plays. It is disabled for visitors who prefer reduced motion (`prefers-reduced-motion`). The timings are the constants at the top of `website/app.js`.

If the API is not reachable, the view is labelled **SIMULATED**, its outcomes are generated locally, and the timing label reads "simulated, not measured". It never presents generated results as measured.

### Pointing the website at another backend

Open the page with `?api=https://<host>` (http/https origins only). The endpoint shown in the page updates to match. For a browser on another origin to call the API, add that origin to the server:

```powershell
$env:LOOM_ALLOWED_ORIGINS="https://my-site.example.com,https://other.example.com"
python -m core.api.server
```

### Landing-page intro (on `index.html`)

`website/hero-intro.js` plays a short decorative intro: particles (electric blue, soft lavender and acid green, defined in the `PALETTE` constant of `website/hero-intro.js`) gather into a rotating sphere, morph into the Loom logo (sampled from `website/assets/loom-logo.png`), and the page content then fades in. As the particles land on the logo's shape, a clean cut-out of the real logo (white background made transparent, aligned to the particle targets) is cross-faded in and the particles fade out, so the finished mark is solid with no gaps. The whole intro lasts about 3.8 seconds (3.4 seconds of animation plus a 0.4 second fade); the timings are in the `TIMING` constant at the top of `website/hero-intro.js`. It does not represent any request or protocol data.

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
| `LOOM_AUDIT_LOG` | empty (off) | Path of the hash-chained JSONL audit log. |
| `LOOM_RATE_LIMIT_AGENT_MAX`, `LOOM_RATE_LIMIT_AGENT_WINDOW` | `30`, `10` | Max requests per agent ID per window (seconds). `0` disables. |
| `LOOM_RATE_LIMIT_IP_MAX`, `LOOM_RATE_LIMIT_IP_WINDOW` | `0` (off), `10` | Max requests per client address per window (seconds). |
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
- `429`: rate limit exceeded; `negotiation_payload` carries `action: "BACK_OFF"` and `retry_after_ms` (the HTTP server also sets `Retry-After` for per-address limits).

Every response includes a `correlation_id`. `GET /health` returns `{"status": "ok", "service": "loom-atp"}`.

## Agent Integrations

### MCP server (`integrations/mcp_server/`)

Any MCP-capable agent can reserve a resource through Loom with an MCP server that wraps the gateway. It is a client of the HTTP API, so start the gateway first (`python -m core.api.server`).

Install the MCP SDK (Python 3.10+; the project pins `mcp>=1.2,<2` and has not been tried with SDK 2.x):

```powershell
pip install -e ".[mcp]"
```

Run it over stdio, the way an MCP client launches a server:

```powershell
python integrations\mcp_server\loom_mcp_server.py
```

Tools it offers:

- `reserve_resource(resource_id, intent, agent_id="", expiry_ms=5000)`: asks Loom for an exclusive, time-limited lock. The result always has the same shape: `outcome` (`LOCKED`, `CONFLICT`, `UNSAFE`, `UNAUTHORIZED`, `INVALID`, `RATE_LIMITED`, or `ERROR`), `locked` (true only when this agent holds the resource), the raw `status`, `message`, `correlation_id` (matches the audit log), and a plain-language `next_action`. Conflicts carry `held_by`, `retry_backoff_ms`, and `suggested_alternative_resource`; rate limits carry `retry_after_ms`. If Loom cannot be reached the result is `ERROR` with `locked: false`, never a lock.
- `loom_status()`: checks that the gateway is reachable.

Configuration (environment variables of the MCP server process):

| Variable | Default | Purpose |
| --- | --- | --- |
| `LOOM_API_URL` | `http://127.0.0.1:8080` | Gateway to call. |
| `LOOM_SHARED_SECRET` | empty | Sign packets with this secret (match the gateway's signing settings). |
| `LOOM_AGENT_ID` | empty | Pin the agent identity: every reservation is made as this agent and the model-supplied `agent_id` is ignored. **Set this in production**, otherwise a model, or a prompt injected into it, can claim any agent id. |

Example client configuration (the exact file depends on your MCP client):

```json
{
  "mcpServers": {
    "loom": {
      "command": "python",
      "args": ["integrations/mcp_server/loom_mcp_server.py"],
      "env": {
        "LOOM_API_URL": "http://127.0.0.1:8080",
        "LOOM_AGENT_ID": "shopping-agent-1"
      }
    }
  }
}
```

See it work without an LLM: with the gateway running,

```powershell
python examples\mcp\mcp_client_demo.py
```

starts the server over stdio with the official MCP Python client, lists its tools, and has two agents reserve the same resource: the first gets `LOCKED`, the second gets `CONFLICT` with its next steps. What has been tested: that round trip, locally on Windows (CI is configured to run it too). What has not: a real MCP host such as Claude Desktop, or an LLM choosing to call the tool.

The logic that turns Loom responses into these results lives in `integrations/mcp_server/loom_tools.py` and has no MCP dependency, so other agent frameworks can reuse it.

### Two-agent demo

```powershell
python examples\scenarios\two_agent_demo.py
```

Two scripted agents (plain Python, no LLM) ask for the same item at the same moment. One gets the lock. The other reads the machine-readable conflict, waits the suggested back-off, asks for the suggested alternative resource, and gets it. Add `--check` to fail unless each agent ends up holding exactly one distinct resource. The retry hint Loom returns today is simple (a jittered back-off and a `<resource>_ALT` suggestion), so this shows the loop working end to end, not a smart negotiation policy.

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

## Audit Log and Rate Limiting

### Audit log

Set `LOOM_AUDIT_LOG` to a file path and every handshake outcome is appended as one JSON line (accepted, conflict, unsafe, bad signature, rate limited, invalid):

```powershell
$env:LOOM_AUDIT_LOG="audit\loom-audit.jsonl"
python -m core.api.server
```

Each record holds the time, status, correlation ID, agent ID, resource, a SHA-256 digest of the intent, whether the packet was signed and a short fingerprint of its signature, plus the hash of the previous record. The raw intent text and the signature are never written. Verify a file any time:

```powershell
python -m core.audit verify audit\loom-audit.jsonl
```

This prints `OK` when the hash chain is intact, or the first broken line when a record was edited, deleted, or reordered. It is **tamper-evident, not tamper-proof**: someone who can rewrite the whole file can also rewrite the whole chain, so for a stronger guarantee the latest head hash should be stored somewhere the writer cannot change. On a container without a mounted volume the file disappears with the container, so mount storage or ship the log elsewhere. The log is off unless `LOOM_AUDIT_LOG` is set.

### Rate limiting

- **Per agent** (on by default): at most `LOOM_RATE_LIMIT_AGENT_MAX` (default 30) requests per `LOOM_RATE_LIMIT_AGENT_WINDOW` seconds (default 10) for each `agent_id`. Over the limit the response is `429` with `negotiation_payload.action = "BACK_OFF"` and a `retry_after_ms`. Invalid packets do not use up an agent's allowance. Set the max to `0` to disable it.
- **Per client address** (off by default): set `LOOM_RATE_LIMIT_IP_MAX` (and `LOOM_RATE_LIMIT_IP_WINDOW`) to limit one address. The response is `429` with a `Retry-After` header. It is off by default because the simulator sends hundreds of requests from one address on purpose. Only a short digest of the address is written to the audit log.
- The limiters keep their counters in memory per process, so with several server instances each one limits on its own. They slow down a flood from one agent or address; they are not a defence against a distributed attack.

## Known Limitations

- **Safety screening is a keyword list locally.** It blocks a few terms (delete, hack, bypass, malware, steal, exploit) and will pass many unsafe intents. Real screening depends on the Azure Content Safety path, which is not live-validated.
- **Signing is shared-secret HMAC.** It authenticates and prevents replay, but either side could have produced a signature, so it does not provide non-repudiation. Public-key signatures are planned.
- **No Entra ID verification yet.** The audit log is a local tamper-evident file (not tamper-proof, and ephemeral on a container without a volume), and rate limiting is in-memory per process.
- **Negotiation is synthetic.** The suggested alternative resource and retry backoff are demo logic, not a negotiation policy.
- **The local ledger is in memory and single-process.** Cross-process and cross-region locking relies on the Cosmos DB adapter, which has not been tested against real contention.
- **The API uses the standard-library HTTP server,** suitable for local and demo use only.
- **The MCP server and demo agents have only been exercised with the official MCP Python client and scripted agents.** No LLM-driven agent has been run through them yet.
- **No customer validation or pricing yet.**

## Repository Map

- `core/kernel/handshake.py`: ATP handshake orchestration.
- `core/models.py`: packet and response models.
- `core/config.py`: environment-driven configuration.
- `core/ai/`: local and Azure intent and safety services.
- `core/security/`: signing, signature verification, and replay protection (the nonce check is lock-protected).
- `core/audit.py`: hash-chained audit log and the `python -m core.audit verify` command.
- `core/ratelimit.py`: sliding-window rate limiter.
- `core/database/`: local atomic ledger and Cosmos DB adapter.
- `core/api/`: local HTTP API gateway.
- `sdk/python/`: Python client SDK.
- `integrations/mcp_server/`: MCP server (`loom_mcp_server.py`) and the MCP-free result logic (`loom_tools.py`).
- `examples/`: agent and scenario demos (`scenarios/two_agent_demo.py`, `mcp/mcp_client_demo.py`).
- `tests/`: unit and integration tests.
- `website/`: static site (`index.html` landing page, `demo.html` live demo, `app.js` simulator, `hero-intro.js` landing intro, `landing.js` scroll reveal, `styles.css`, `assets/`).
- `infra/main.bicep`: Azure Container Apps template.
- `Dockerfile`: API container image.
- `docs/competition/`: Imagine Cup 2027 plan.
- `docs/operations/`: Azure mode, deployment runbook, validation evidence.
- `docs/spec/`: ATP specification and architecture notes.
- `docs/website/`: website notes.
- `.github/workflows/ci.yml`: CI.

## Continuous Integration

GitHub Actions runs on every push and pull request:

- **Python 3.10 and 3.11:** installs the package with the `mcp` extra, import smoke test, compile check, unit tests (including the real MCP stdio round trip), local example smoke, and an API scenario smoke that also runs the two-agent demo and the MCP client demo against a live gateway.
- **Website static checks:** required files and key strings in the landing page (`index.html`), the demo page (`demo.html`), `app.js`, `hero-intro.js`, `landing.js`, and `styles.css`.
- **Docker build:** builds the API image and smoke-tests it.
- **Bicep validation:** builds `infra/main.bicep`.

## Roadmap

1. **Customer discovery:** about 15 interviews with agent builders, marketplace and e-commerce platform engineers, and operations teams; decide whether to keep or change the wedge.
2. **Company and Azure subscription:** incorporate, enroll in Microsoft for Startups, create the startup subscription.
3. **Live Azure mode:** real Foundry intent parsing, Content Safety, and Cosmos locks with captured evidence (public `/health`, one `201` and one `409` for the same resource, service metrics).
4. **Security:** public-key signatures, a stronger local safety check, Entra ID or an explicit scope-out (the audit log and rate limiting now exist locally; anchoring the audit head hash remotely is still open).
5. **Load evidence:** 100 and 1,000 agent runs (then larger) with saved latency and conflict metrics.
6. **Infrastructure as code** for all required Azure services.
7. **TypeScript SDK**, and a plugin for an agent framework (for example Semantic Kernel or LangChain). The MCP server and a two-agent demo already exist.
8. **Submission package:** written responses, pitch deck, demo video, architecture diagram, judge FAQ.
