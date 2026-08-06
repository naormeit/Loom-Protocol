# Azure Mode Runbook

This runbook describes how to run Loom with production Azure adapters. Use it together with `docs/operations/deployment_runbook.md` when deploying the API image to Azure Container Apps.

## Required Resources

- Azure OpenAI or Azure AI Foundry project with a chat model deployment.
- Azure AI Content Safety resource.
- Azure Cosmos DB for NoSQL account.
- Cosmos database, default `loom`.
- Cosmos container, default `locks`, partition key `/resource_id`.
- Loom API container image built from this repository and pushed to a reachable registry.

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

## Deploy Through Container Apps

The Bicep template expects the real Loom image as the required `image` parameter:

```powershell
az deployment group create `
  --resource-group loom-protocol-rg `
  --template-file infra/main.bicep `
  --parameters `
    image="<registry>.azurecr.io/loom-protocol:<tag>" `
    registryServer="<registry>.azurecr.io" `
    registryIdentityResourceId="<user-assigned-identity-resource-id>" `
    azureOpenAiEndpoint="$env:AZURE_OPENAI_ENDPOINT" `
    azureOpenAiApiKey="$env:AZURE_OPENAI_API_KEY" `
    azureOpenAiDeployment="$env:AZURE_OPENAI_DEPLOYMENT" `
    contentSafetyEndpoint="$env:CONTENT_SAFETY_ENDPOINT" `
    contentSafetyKey="$env:CONTENT_SAFETY_KEY" `
    cosmosEndpoint="$env:COSMOS_ENDPOINT" `
    cosmosKey="$env:COSMOS_KEY" `
    cosmosDatabase="$env:COSMOS_DATABASE" `
    cosmosContainer="$env:COSMOS_CONTAINER"
```

If the image lives in private ACR, grant `AcrPull` to the user-assigned identity passed as `registryIdentityResourceId`. This phase wires the app and environment values; it does not yet provision the Azure AI, Cosmos, Entra, registry, or identity resources themselves.

## Verification Evidence To Capture

- API startup logs showing `LOOM_MODE=azure`.
- Azure OpenAI request metrics for intent parsing.
- Azure AI Content Safety request metrics for intent screening.
- Cosmos DB item count and request metrics for the `locks` container.
- Scenario output showing one secured lock and negotiated conflicts.
- Deployed Container App URL from the Bicep `containerAppUrl` output.
- Health check output from the Bicep `healthCheckUrl` output.

## Failure Signals

- API fails to boot because a required Azure environment variable is missing.
- Content Safety rejects all benign test requests.
- Cosmos `create_item` succeeds for more than one active lock for the same `intent_hash`.
- Scenario returns zero successful locks.
