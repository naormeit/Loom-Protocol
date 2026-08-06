# Live Azure Deployment Validation - 2026-08-06

## Objective

Validate the Loom API deployment path for a production-style Azure Container Apps deployment using the current repository state.

Companion report sheet: `docs/operations/live_azure_validation_report_2026-08-06.xlsx`.

## Local Baseline

- Unit test command: `python -m unittest discover -s tests -p "test*.py"`
- Result: passed, 16 tests.
- Docker image: `loom-protocol:validation-20260806`
- Docker image ID after adding Azure optional dependencies: `sha256:6ac3db7e9f4a8d10ef23e9d372a1e4809ae188dfcc53a5d3747434ffa9ca252e`
- Docker image size after adding Azure optional dependencies: `68963625` bytes.
- Container import check: `openai`, `azure.cosmos`, and `azure.ai.contentsafety` import successfully inside the image.

## Container Smoke Test

The image was run locally with Azure-style host binding:

```powershell
docker run --rm --detach `
  --name loom-validation-20260806 `
  --publish 18080:8080 `
  --env LOOM_MODE=local `
  --env LOOM_HOST=0.0.0.0 `
  loom-protocol:validation-20260806
```

Health probe:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:18080/health
```

Result:

```json
{
  "status": "ok",
  "service": "loom-atp"
}
```

Sequential handshake proof against resource `VALIDATION-DROP-SEQUENTIAL-20260806-B`:

- First request: `201`
- First response: `{"status": 201, "message": "Atomic Lock Secured.", "correlation_id": "44bae34d182f904c", "parsed_as": "PURCHASE ONE LIMITED VALIDATION ITEM"}`
- Second request: `409`
- Second response: `{"status": 409, "message": "Conflict Rejected: Resource currently locked by VALIDATION-AGENT-A.", "correlation_id": "551be90c51df342e", "conflict_with": "VALIDATION-AGENT-A", "negotiation_payload": {"action": "RENEGOTIATE", "suggested_alternative_resource": "VALIDATION-DROP-SEQUENTIAL-20260806-B_ALT", "retry_backoff_ms": 262}}`

## Azure Readiness Check

Available locally:

- Docker engine: `29.4.1`
- Azure CLI: `2.89.0`
- Loom container image builds successfully.
- `infra/main.bicep` sets `LOOM_HOST=0.0.0.0`, which is required for Container Apps ingress.
- `infra/main.bicep` now supports private ACR pull through a user-assigned managed identity instead of ACR admin credentials.

Missing locally:

- Azure Developer CLI: not found on PATH.
- Bicep CLI: not found on PATH.
- Azure PowerShell cmdlets: not found on PATH.
- PowerShell 7: not found on PATH.

Missing environment configuration:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `CONTENT_SAFETY_ENDPOINT`
- `CONTENT_SAFETY_KEY`
- `COSMOS_ENDPOINT`
- `COSMOS_KEY`
- `COSMOS_DATABASE`
- `COSMOS_CONTAINER`

## Azure Subscription

- Subscription: `Azure for Students`
- Subscription ID: `066baedd-7620-412b-b62d-f6c3a1e2e46e`
- Tenant: `Alliance University`
- Portal credit state observed in browser: `$100 out of $100`, expiring `2027-08-06`.

## Azure Resources Created

Resource group:

- `loom-validation-rg`

Resources:

- Azure Container Registry: `loomval0806a1e2e46e` in `centralindia`
- Cosmos DB account: `loom-cosmos-0806-a1e2e46e` in `centralindia`
- Cosmos SQL database: `loom`
- Cosmos SQL container: `locks`, partition key `/resource_id`
- User-assigned managed identity: `loom-acr-pull-id`
- Container Apps environment: `loom-validation-env`
- Container App: `loom-validation-api`

ACR image:

- `loomval0806a1e2e46e.azurecr.io/loom-protocol:validation-20260806`
- Push digest: `sha256:6ac3db7e9f4a8d10ef23e9d372a1e4809ae188dfcc53a5d3747434ffa9ca252e`

Container App:

- FQDN: `loom-validation-api.mangorock-aac0438b.centralindia.azurecontainerapps.io`
- Revision: `loom-validation-api--1fftnlh`
- Running status: `Running`
- Ingress: external, target port `8080`, transport `Http`
- Runtime mode for this hosted deployment: `LOOM_MODE=local`

Internal Azure health probe through `az containerapp exec`:

```json
{"status": "ok", "service": "loom-atp"}
```

## Live Azure Validation Blockers

Full `LOOM_MODE=azure` validation was not completed in this pass because Azure OpenAI could not be created in this student subscription:

- `centralindia` is permitted by the subscription policy, but Azure OpenAI has no listed SKU there.
- `swedencentral` lists Azure OpenAI `S0`, but resource creation is blocked by the subscription's region policy: `RequestDisallowedByAzure`.
- Standalone Content Safety is not available in `centralindia`; attempts in `southeastasia` and `westus2` were blocked by the same region policy.

Public endpoint validation from the local shell was also blocked by the shell network environment:

- `curl https://portal.azure.com` fails from the shell with TCP connection failure.
- `curl https://loom-validation-api.mangorock-aac0438b.centralindia.azurecontainerapps.io/health` also fails from the shell.
- The in-app browser could open Azure Portal but blocked direct navigation to the `azurecontainerapps.io` endpoint with `net::ERR_BLOCKED_BY_CLIENT`.

The Azure control plane reports the Container App as running, and an internal in-container `/health` probe succeeds.

## Cleanup Command

These validation resources can consume Azure credit while they exist. Remove the whole validation stack with:

```powershell
& 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd' group delete `
  --name loom-validation-rg `
  --yes `
  --no-wait
```

## Next Commands Once Azure OpenAI And Content Safety Are Available

Build and tag the image for ACR:

```powershell
$tag = "validation-20260806"
$resourceGroup = "loom-validation-rg"
$location = "centralindia"
$acrName = "loomval0806a1e2e46e"
$image = "$acrName.azurecr.io/loom-protocol:$tag"
$registryServer = "$acrName.azurecr.io"
$registryIdentityResourceId = "/subscriptions/066baedd-7620-412b-b62d-f6c3a1e2e46e/resourcegroups/loom-validation-rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/loom-acr-pull-id"

docker tag loom-protocol:validation-20260806 $image
az acr login --name $acrName
docker push $image
```

Deploy Container Apps:

```powershell
az deployment group create `
  --resource-group $resourceGroup `
  --template-file infra/main.bicep `
  --parameters `
    image=$image `
    registryServer=$registryServer `
    registryIdentityResourceId=$registryIdentityResourceId `
    loomMode="azure" `
    azureOpenAiEndpoint="$env:AZURE_OPENAI_ENDPOINT" `
    azureOpenAiApiKey="$env:AZURE_OPENAI_API_KEY" `
    azureOpenAiDeployment="$env:AZURE_OPENAI_DEPLOYMENT" `
    contentSafetyEndpoint="$env:CONTENT_SAFETY_ENDPOINT" `
    contentSafetyKey="$env:CONTENT_SAFETY_KEY" `
    cosmosEndpoint="$env:COSMOS_ENDPOINT" `
    cosmosKey="$env:COSMOS_KEY" `
    cosmosDatabase="$env:COSMOS_DATABASE" `
    cosmosContainer="$env:COSMOS_CONTAINER" `
    loomRequireSignature="false"
```

Capture the live endpoint:

```powershell
$healthUrl = az deployment group show `
  --resource-group $resourceGroup `
  --name main `
  --query properties.outputs.healthCheckUrl.value `
  --output tsv

Invoke-RestMethod -Uri $healthUrl
```

Run a live handshake smoke:

```powershell
$apiUrl = $healthUrl -replace "/health$",""
$body = @{
  agent_id = "AZURE-VALIDATION-AGENT-1"
  intent = "Purchase one limited validation item"
  intent_hash = "AZURE-VALIDATION-DROP-20260806"
  expiry = 5000
} | ConvertTo-Json

Invoke-WebRequest `
  -UseBasicParsing `
  -Uri "$apiUrl/v1/handshake" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

## Evidence Still Needed For Competition Claims

- Public Container Apps URL.
- `/health` response from the public URL.
- `201` lock and `409` conflict responses from the public URL in `LOOM_MODE=azure`.
- Azure OpenAI or Azure AI Foundry metrics showing intent parsing calls.
- Azure AI Content Safety metrics showing safety calls.
- Cosmos DB metrics or item evidence showing lock writes in the configured `locks` container.
