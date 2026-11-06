# Loom Protocol: Imagine Cup 2027 Plan

Rewritten 2026-11-05 against the Imagine Cup 2027 Official Rules (https://aka.ms/ImagineCup2027TCs). Earlier versions of this plan assumed the pre-2027 student format. That format is gone.

## What the 2027 competition actually is

- A startup competition run through Microsoft for Startups. Entries go through Award Force and close **2027-02-28 23:59 CST**. Entries cannot be edited after submission.
- The entrant must be a **legal entity founded on or after 2024-11-02**, privately held, for-profit, with at most four official team members, each 18 or older.
- By the deadline the startup must be **using at least ten Azure services** on one Azure subscription, with **at least USD 1.00 of usage on each**. Free tiers and free grants that bill 0.00 do not count.
- Stages: Stage 1 application scoring (rolling to Feb 28), top 30 per category to expert review (Mar 1-12), top 10 to recorded live interviews (Mar 16-31), final judging in April, World Championship May-June.
- Category: **Student Startup**. Every founding team member must be enrolled at an accredited institution at some point between 2026-09-30 and 2027-05-31. Student entries cannot be Finalists; the Student Prize is the ceiling (USD 25,000 plus credits). Industry categories add a 100-point category rubric that scores funding, ARR and contract value, which Loom cannot compete on this cycle.
- Entry materials: Stage 1 written responses (product, problem, target user, market, business model, traction, go-to-market, Microsoft technologies used); Stage 2 pitch deck, 2-3 minute demo video, Azure architecture diagram, production-architecture and differentiation responses. Everything in English.
- IP stays with the entrant. Microsoft takes a broad license to use the entry for the competition and its promotion.

## Stage 1 (Student) rubric and where Loom stands

| Criterion | Points | Scored on | Loom today |
| --- | ---: | --- | --- |
| Product and Technical Approach | 40 | customer validation, technical progress, cloud and AI use, Azure production maturity | Strong local MVP. Hosted deployment is `LOOM_MODE=local` only. No customer validation. |
| Business and Startup Profile | 25 | stage, business model, funding | No pricing or buyer defined. |
| Team and Execution Potential | 20 | team makeup and commitment | Confirm team size and roles; up to four members, all enrolled students. |
| Problem and Market Opportunity | 15 | users or customers, clarity of problem and target customer | Problem is clear. No users or customers yet. |

Stage 2 (100 points): pitch deck 20, demo video 15, Azure architecture diagram 20, production architecture response 20, customer differentiation 10, Microsoft growth alignment 15.

## Hard gates (nothing else matters until these are done)

1. **Incorporate.** Register a private limited company (MCA SPICe+). Assign Loom IP from personal ownership to the company. Obtain a registration number and tax details that will match business verification.
2. **Register on Award Force**, select Student Startup, and wait for the eligibility email and the unique Microsoft for Startups referral code (generally within 24 business hours).
3. **Redeem the code, enroll in Microsoft for Startups**, complete business verification, and create or connect the Azure subscription for Loom. Do not submit the Azure for Students subscription; it is not the startup subscription and it is the subscription that blocks Azure OpenAI and Content Safety.
4. **Reach ten billing Azure services with USD 1+ each** (see below), kept above the threshold continuously through judging.

## Ten-service Azure plan

Count a service only if Cost Analysis shows at least USD 1.00 for it on the submitted subscription. Confirm each service is on Microsoft's eligible list before relying on it.

| # | Service | Role in Loom | Notes |
| ---: | --- | --- | --- |
| 1 | Azure Container Apps | ATP gateway | Already deployed (local mode). |
| 2 | Azure Container Registry (Basic) | Loom image | Fixed daily charge. |
| 3 | Azure Cosmos DB | Conditional-write lock ledger | Free tier off, or usage may bill 0.00. |
| 4 | Azure OpenAI / Foundry | Structured intent parsing | Needs a subscription and region that allow it. |
| 5 | Azure AI Content Safety | Intent risk screening | Same region constraint. |
| 6 | Azure Key Vault | Signing keys and service secrets | Premium if a HSM-backed key is used. |
| 7 | Application Insights / Log Analytics | Correlation-ID tracing, audit queries | Free ingestion allowance can leave cost at 0.00. |
| 8 | Azure Cache for Redis (Basic) | Nonce replay cache | Fixed hourly charge. |
| 9 | Azure Load Testing | 100 / 1,000 / 10,000 agent runs | Also produces the metrics evidence below. |
| 10 | Azure Functions or Event Hubs | Lock-expiry sweeper or audit event stream | Pick the one with a real role. |

Microsoft Entra ID is in the architecture narrative but is not implemented. Do not count or claim it until token validation exists.

## Engineering work that scores

Ordered by value to the rubric.

1. **Real `LOOM_MODE=azure` deployment** with Foundry intent parsing, Content Safety, and Cosmos locks on the startup subscription. Evidence: public `/health`, one 201 and one 409 for the same resource, Azure-side usage metrics, Cosmos lock records. Keep local, hosted-local, and Azure-mode proof clearly separated.
2. **Infrastructure as code for all ten services** in `infra/main.bicep`. Today it defines only the Container Apps environment and app; ACR and Cosmos were created by hand.
3. **Load metrics.** 100 and 1,000 agent runs first, then 10,000. Save latency, conflict rate, and lock counts as JSON and Markdown. Run them with Azure Load Testing so they also count toward the usage requirement. Local runs at 100, 1,000 and 10,000 agents are done (6 Nov 2026; see [`docs/performance/README.md`](../performance/README.md)); the run against the Azure deployment remains.
4. **Security claims that match code.**
   - Replace shared-secret HMAC with public-key signatures (Ed25519), keys in Key Vault, before using the word "non-repudiation". Until then, describe the current scheme as authenticated and replay-protected only.
   - Add a persistent audit trail (packet fingerprint, decision, timestamps, model metadata).
   - Add rate limiting.
   - Either implement Entra ID token validation or scope it out explicitly.
5. **Website.** `?api=` query parameter now selects the backend, and `LOOM_ALLOWED_ORIGINS` lets the API accept the hosted site's origin. Remaining: make visual-fallback mode unmistakable, and publish the site on a real domain (the application asks for a company website).
6. **TypeScript SDK** and a minimal agent integration sample.
7. **CI:** add website browser smoke check, replace kernel `print` output with logging.

## Evidence that scores (currently zero)

- **Customer validation.** 15 interviews with marketplace operators, ecommerce platform engineers, and agent builders. Three recurring pain patterns. One design partner, pilot, waitlist, or LOI. An iteration log showing what changed.
- **Campus pilot** at the university for users and MAU, as originally planned for fall 2026.
- **Business model.** Name the first buyer and user. Replace the "Loom Tax" and "monopoly" framing with a credible early pricing model. Compare against vendor APIs, queues, payment pre-authorization, distributed locks, and agent frameworks. A first draft of buyers, pricing models and the questions to ask is in [`docs/business/buyer_and_pricing_hypotheses.md`](../business/buyer_and_pricing_hypotheses.md); it is unvalidated until the conversations happen.
- **Team.** Document roles, time commitment, and technical composition. Confirm every founder meets the student-enrollment window.

## Submission package

- Written responses for Stage 1 and Stage 2, in English, with claims tied to evidence in the repo.
- Pitch deck (15 slides maximum), 2-3 minute demo video, Azure architecture diagram, production-architecture response, differentiation response, Microsoft growth-alignment response.
- Judge FAQ and technical appendix.
- Prepare everything before 2027-02-28 even though Stage 2 materials are requested later.

## Timeline

| Window | Goal |
| --- | --- |
| Nov 2026 | Start incorporation. Register on Award Force (Student Startup). Begin interviews and campus pilot. Align Spec and Master docs with the Overview (drop unsupported claims). |
| Dec 2026 | Redeem code, enroll, business verification, create startup subscription. Deploy Azure mode. Capture 201 / 409 evidence. |
| Jan 2027 | Bicep for all ten services. Load-test reports. Public-key signing, audit trail. Validation and pricing docs. |
| Feb 1-20, 2027 | Deck, demo video, architecture diagram, written responses. Public hosted demo and domain. |
| Feb 20-28, 2027 | Verify Cost Analysis shows USD 1+ on each of the ten services. Re-read every claim against the repo. Submit. |

## Definition of done

- Incorporated entity with matching business verification.
- Startup Azure subscription showing USD 1+ on ten services.
- Public hosted demo running in Azure mode with live evidence.
- Load-test metrics for at least 100 and 1,000 agents.
- No security or architecture claim that the code does not back.
- Interview, pilot, and pricing evidence in the repo.
- Complete written responses and Stage 2 materials in English.
