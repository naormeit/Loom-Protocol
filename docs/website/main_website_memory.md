# Main Website Memory

Last updated: 2026-08-03

## Scope For This Chat

- Work only on the main Loom Protocol website unless the user explicitly redirects.
- Treat Microsoft Imagine Cup 2027 registration as initiated manually by the user through the official site.
- Do not store account, registration, or private submission details in this repository unless the user provides explicit public-safe content.

## Project Context

- Product: Loom Protocol.
- Core thesis: atomic reservation middleware for AI agents competing over scarce resources.
- Primary wedge: limited-inventory agent commerce.
- Main demo story: many shopping agents race for one scarce resource; Loom returns one `201` lock and structured `409` conflict negotiation for the others.
- Important endpoint: `POST /v1/handshake`.
- Current implementation baseline: Python local kernel, HTTP API gateway, local safety and intent services, packet signing/replay protection, local atomic ledger, Python SDK, stress/demo scripts, and Azure-mode adapter paths.
- Azure path to be proven: Azure OpenAI or Azure AI Foundry, Azure AI Content Safety, Azure Cosmos DB, Azure Functions or Container Apps, and Microsoft Entra ID.

## Website Baseline

- Website folder: `website/`.
- Current entry point: `website/index.html`.
- Root redirect: `index.html` sends Live Server root visitors to `website/`.
- Styling: `website/styles.css`.
- Interaction: `website/app.js`.
- The site is static and can be opened directly in a browser.
- First-screen experience: product positioning plus an interactive agent drop simulator.
- Simulator contract: checks `http://127.0.0.1:8080/health`; when the Python API is running, it sends real `POST /v1/handshake` packets and displays actual lock/conflict counts; otherwise it must clearly label visual fallback mode.

## Messaging Guardrails

- Be judge-ready and precise, not inflated.
- Phrase Azure services as production path or target until live credentials, deployed resources, and integration testing exist.
- Keep the wedge narrow: limited-inventory agent commerce first, broader protocol vision second.
- Prioritize proof artifacts: demo, API contract, metrics, validation evidence, and Microsoft AI usage.
- Always distinguish `Implemented locally`, `Verified in repo`, and `Production path` when presenting judge-facing claims.

## Near-Term Website Tasks

- Add a public demo script section once the local and hosted demo flows are finalized.
- Add real metrics after running stress scenarios at 100, 1,000, and 10,000 agents.
- Add validation quotes or paraphrased interview evidence when public-safe notes exist.
- Add submission links only after the official Imagine Cup assets are ready.
