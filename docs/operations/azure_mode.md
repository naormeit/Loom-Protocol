# Azure Mode Runbook

This runbook describes how to run Loom with production Azure adapters.

## Required Resources

- Azure OpenAI or Azure AI Foundry project with a chat model deployment.
- Azure AI Content Safety resource.
- Azure Cosmos DB for NoSQL account.
- Cosmos database, default `loom`.
- Cosmos container, default `locks`, partition key `/resource_id`.

## Environment

```powershell
$env:LOOM_MODE="azure"
$env:AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com"
$env:AZURE_OPENAI_API_KEY="<key>"
$env:AZURE_OPENAI_API_VERSION="2024-10-21"
$env:AZURE_OPENAI_DEPLOYMENT="<deployment>"
$env:CONTENT_SAFETY_ENDPOINT="https://<resource>.cognitiveservices.azure.com"
$env:CONTENT_SAFETY_KEY="<key>"
$env:CONTENT_SAFETY_BLOCK_THRESHOLD="4"
$env:COSMOS_ENDPOINT="https://<account>.documents.azure.com:443/"
$env:COSMOS_KEY="<key>"
$env:COSMOS_DATABASE="loom"
$env:COSMOS_CONTAINER="locks"
```

## Run

```powershell
python -m core.api.server
```

Then, from another terminal:

```powershell
python examples\scenarios\limited_inventory_drop.py --agents 100
```

## Verification Evidence To Capture

- API startup logs showing `LOOM_MODE=azure`.
- Azure OpenAI request metrics for intent parsing.
- Azure AI Content Safety request metrics for intent screening.
- Cosmos DB item count and request metrics for the `locks` container.
- Scenario output showing one secured lock and negotiated conflicts.

## Failure Signals

- API fails to boot because a required Azure environment variable is missing.
- Content Safety rejects all benign test requests.
- Cosmos `create_item` succeeds for more than one active lock for the same `intent_hash`.
- Scenario returns zero successful locks.
