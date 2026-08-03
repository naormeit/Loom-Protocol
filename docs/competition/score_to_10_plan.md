# Loom Protocol 10/10 Competition Readiness Plan

## Goal

Turn Loom Protocol from a strong concept prototype into a judge-ready Imagine Cup 2027 submission with a defensible MVP, real Microsoft AI usage, measurable technical proof, customer validation, and a polished demo package.

This plan targets a strict judge, not a friendly reader. A 10/10 score means the repository, demo, cloud deployment, and pitch evidence can survive technical review without relying on simulated claims.

## Current Baseline

- The repo demonstrates the ATP story through a local Python kernel, mock locking layer, CLI demo, and two-agent collision simulation.
- The current Azure AI Foundry, Azure Content Safety, Cosmos DB, Azure Functions, and Entra ID claims are mostly architectural intent rather than working integrations.
- The SDK directories exist but are empty.
- There is no hosted API, real cloud state, cryptographic proof, CI, unit test suite, or customer validation evidence in the repo.
- The competition narrative is promising but too broad; it needs one painful initial wedge use case.

## Target Scores

| Factor | Current | 10/10 Target |
| --- | ---: | --- |
| Idea / ambition | 8 | Keep the bold protocol story, but anchor it in one urgent real-world transaction bottleneck. |
| Problem clarity | 5 | Show a concrete before/after use case with measurable failure from current APIs. |
| Technical execution | 2 | Ship a deployed MVP with real Azure services, SDKs, tests, metrics, and repeatable setup. |
| Microsoft AI requirement | 2 | Make at least two Microsoft AI services required in the product path, not optional labels. |
| MVP demonstrability | 3 | Provide a hosted judge demo, local fallback demo, scripts, sample packets, and a 2-minute flow. |
| Security credibility | 2 | Implement signed ATP packets, identity checks, audit trails, rate limits, and threat model docs. |
| Business viability | 4 | Replace "Loom Tax" as the main claim with a credible wedge, buyer, pricing model, and GTM. |
| Founder-led validation | 1 | Add interview notes, pilot targets, waitlist/LOI evidence, and iteration history. |
| Documentation | 5 | Align docs with working code, remove overclaims, add architecture diagrams and runbooks. |
| Competition readiness | 3 | Prepare deck, pitch video, demo video, public URLs, technical appendix, and judge FAQ. |

## Product Wedge

Choose one primary use case for the MVP. Do not pitch Loom as universal internet infrastructure first.

Recommended wedge: limited-inventory agent commerce.

Example scenario:
- 1,000 shopping agents attempt to reserve the same limited product drop.
- Standard direct API calls create overbooking, retries, and vendor overload.
- Loom receives agent intent, verifies safety and authority, locks the resource atomically, and returns either a final lock or a negotiation payload.

Why this wedge works:
- It is easy to understand in a demo.
- It fits Retail and Consumer Goods, Financial Services, and Cybersecurity angles.
- It makes concurrency, safety, identity, and auditability visible.
- It avoids needing a real airline, hospital, or bank partnership for the first MVP.

## Architecture To Build

### 1. ATP Gateway

Files:
- `core/api/app.py`
- `core/api/routes.py`
- `core/models/packet.py`
- `core/models/result.py`
- `tests/api/test_gateway.py`

Requirements:
- Expose `POST /v1/handshake`.
- Validate packet schema with typed models.
- Return stable ATP status codes: `201 LOCKED`, `409 CONFLICT`, `403 UNSAFE_INTENT`, `401 INVALID_AUTHORITY`, `400 INVALID_PACKET`.
- Include correlation IDs in every response.
- Support local mode and Azure mode through configuration.

### 2. Microsoft AI Intent Gateway

Files:
- `core/ai/intent_parser.py`
- `core/ai/content_safety.py`
- `tests/ai/test_intent_parser.py`
- `tests/ai/test_content_safety.py`

Requirements:
- Use Azure AI Foundry or Azure OpenAI to convert raw agent text into structured intent fields.
- Use Azure AI Content Safety to classify malicious or unsafe transaction intent.
- Provide a deterministic local stub for offline tests.
- Log model/service metadata without logging private user secrets.

### 3. Atomic State Ledger

Files:
- `core/database/ledger.py`
- `core/database/cosmos_client.py`
- `tests/database/test_atomic_locks.py`

Requirements:
- Replace the in-memory dictionary with a Cosmos DB implementation using conditional create/upsert and ETag or unique-key semantics.
- Preserve a local in-memory ledger only as `LocalLedger` for tests and offline demos.
- Store lock owner, resource hash, expiry, packet hash, signature fingerprint, and audit timestamps.
- Add TTL-based expiry behavior.
- Prove one-winner semantics under concurrent load.

### 4. Identity And Proof

Files:
- `core/security/signing.py`
- `core/security/authority.py`
- `tests/security/test_signing.py`
- `docs/spec/security_model.md`

Requirements:
- Sign ATP packets with public/private key cryptography for local MVP.
- Add Entra ID verification path for Azure mode.
- Verify packet signature before intent execution.
- Add replay protection with nonce and timestamp.
- Document the trust model, failure modes, and what remains out of scope.

### 5. SDKs

Files:
- `sdk/python/loom_protocol/__init__.py`
- `sdk/python/loom_protocol/client.py`
- `sdk/python/README.md`
- `sdk/typescript/src/client.ts`
- `sdk/typescript/package.json`
- `sdk/typescript/README.md`
- `tests/sdk/test_python_client.py`

Requirements:
- Provide a clean client method such as `reserve(resource_id, intent, expiry_ms)`.
- Include signature support.
- Include retry handling for negotiation payloads.
- Add examples for Python and TypeScript agents.

### 6. Load And Demo Harness

Files:
- `tests/stress/test_concurrent_locks.py`
- `examples/scenarios/limited_inventory_drop.py`
- `examples/scenarios/report_metrics.py`
- `docs/demo/judge_demo_script.md`

Requirements:
- Simulate 100, 1,000, and 10,000 agents.
- Capture latency, conflict rate, successful locks, unsafe rejections, and retry outcomes.
- Output a judge-readable metrics summary.
- Keep the demo deterministic enough for a recorded video.

### 7. Cloud Deployment

Files:
- `infra/main.bicep`
- `infra/README.md`
- `.env.example`
- `.github/workflows/ci.yml`
- `docs/operations/deployment_runbook.md`

Requirements:
- Deploy API to Azure Functions or Azure Container Apps.
- Provision Cosmos DB and required app settings.
- Document Azure AI Foundry / Azure OpenAI and Content Safety setup.
- Add CI for linting, tests, and package checks.
- Provide a public demo endpoint or a reproducible deployment path.

## Evidence To Collect

### Founder-Led Validation

Files:
- `docs/validation/interview_summary.md`
- `docs/validation/personas.md`
- `docs/validation/experiment_log.md`
- `docs/validation/loi_or_pilot_tracker.md`

Minimum bar:
- 15 interviews with developers, marketplace operators, ecommerce founders, AI-agent builders, or platform/security engineers.
- 3 recurring pain patterns documented with quotes or paraphrased notes.
- 1 design partner, waitlist, pilot conversation, or letter of intent.
- Clear iteration log showing what changed because of feedback.

### Business Model

Files:
- `docs/business/wedge_strategy.md`
- `docs/business/pricing.md`
- `docs/business/competitive_landscape.md`

Minimum bar:
- Define initial buyer and user.
- Explain why this starts as middleware/API infrastructure, not a consumer app.
- Replace the broad "tax the agentic economy" claim with a credible early pricing model.
- Compare against direct vendor APIs, queues, payment pre-auth, distributed locks, and agent frameworks.

### Competition Package

Files:
- `docs/submission/pitch_deck_outline.md`
- `docs/submission/demo_video_script.md`
- `docs/submission/pitch_video_script.md`
- `docs/submission/judge_faq.md`
- `docs/submission/technical_appendix.md`

Minimum bar:
- 15-slide maximum deck.
- 3-minute pitch script.
- 2-minute product demo script.
- Architecture diagram and Microsoft technology list.
- Public demo URL and public video URLs.
- Short answers for likely judge objections.

## Documentation Corrections

Before submission, update existing docs so claims match implementation state.

Files:
- `README.md`
- `COMPLIANCE.md`
- `docs/spec/architecture.md`
- `docs/spec/atp_spec.md`

Required corrections:
- Remove broken `[cite_start]` artifacts.
- Stop calling simulated services fully implemented.
- Add a status table that distinguishes `Implemented`, `In progress`, and `Planned`.
- Add local setup, Azure setup, testing, and demo commands.
- Add exact Microsoft AI services used in the live product path.

## Test Strategy

Minimum automated tests:
- Packet schema validation.
- Unsafe intent rejection.
- Signature verification and replay rejection.
- One-winner lock behavior for local ledger.
- Cosmos conditional write behavior behind an integration-test flag.
- SDK request/response behavior.
- API status code and error contract.
- Stress harness metrics output.

Minimum manual checks:
- Local demo from clean clone.
- Hosted endpoint demo.
- Azure service logs visible.
- 2-minute demo recording completes without hidden setup.
- Judge can reproduce or understand every claim in the deck.

## Execution Order

1. Narrow the MVP to limited-inventory agent commerce.
2. Refactor current kernel into typed packet, result, ledger, safety, and parser modules.
3. Add real local tests before adding cloud dependencies.
4. Build the API gateway and local SDK.
5. Add packet signing and replay protection.
6. Implement real Azure Content Safety and Azure AI Foundry / Azure OpenAI integrations.
7. Replace mock ledger with Cosmos DB conditional writes in Azure mode.
8. Add load harness and metrics reports.
9. Add cloud deployment scripts and CI.
10. Update docs to match the working product.
11. Collect validation evidence and business proof.
12. Package deck, pitch video, demo video, and judge FAQ.

## Definition Of Done

The project can be considered 10/10-ready when:

- A judge can run the local demo from the README.
- A judge can watch a hosted demo using real Azure services.
- The product requires at least two Microsoft AI services in the real transaction path.
- The lock ledger proves one-winner behavior under concurrent load.
- Security claims are implemented or explicitly scoped.
- The SDKs work for at least one realistic agent integration.
- Tests and CI pass.
- Documentation contains no overclaims.
- Founder-led validation evidence is present.
- The pitch explains a specific buyer, market wedge, and business model.
- Submission materials are complete and public links work.

