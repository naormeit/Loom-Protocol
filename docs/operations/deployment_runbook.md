# Azure Deployment Runbook

This runbook captures the minimum Azure infrastructure needed to host the Loom ATP gateway in a production-style deployment. The current Bicep template provisions the Container Apps hosting surface and runtime configuration for a Loom image; Azure AI and Cosmos resources are required inputs until a later infra phase provisions them end to end.

## Required Azure resources

- Azure Container Apps environment for the API gateway, provisioned by `infra/main.bicep`.
- Azure Container App for the Loom API image, provisioned by `infra/main.bicep`.
- Azure Container Registry or another registry containing the built Loom API image.
- Azure OpenAI or Azure AI Foundry deployment for intent parsing.
- Azure AI Content Safety resource for safety screening.
- Azure Cosmos DB for NoSQL account with a database and container for lock state.
- Microsoft Entra ID or another identity mechanism for future authority verification.

The Cosmos container must use `/resource_id` as its partition key. The current template does not create Azure OpenAI, Content Safety, Cosmos DB, Entra ID, ACR, or registry pull role assignments.

## Required secrets and environment variables

Set the following values as Bicep parameters, GitHub Actions secrets, or Container Apps environment values:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`
- `CONTENT_SAFETY_ENDPOINT`
- `CONTENT_SAFETY_KEY`
- `CONTENT_SAFETY_BLOCK_THRESHOLD`
- `COSMOS_ENDPOINT`
- `COSMOS_KEY`
- `COSMOS_DATABASE`
- `COSMOS_CONTAINER`
- `LOOM_MODE`
- `LOOM_HOST`
- `LOOM_PORT`
- `LOOM_REQUIRE_SIGNATURE`
- `LOOM_SHARED_SECRET`

## Suggested deployment flow

1. Choose a release tag and build the Loom API image:
   ```powershell
   $tag = "v0.1.0"
   docker build --tag loom-protocol:$tag .
   ```
2. Create or select a registry and push the image:
   ```powershell
   $resourceGroup = "loom-protocol-rg"
   $location = "eastus"
   $acrName = "loomprotocolacr"
   $image = "$acrName.azurecr.io/loom-protocol:$tag"

   az group create --name $resourceGroup --location $location
   az acr create --resource-group $resourceGroup --name $acrName --sku Basic
   az acr login --name $acrName

   docker tag loom-protocol:$tag $image
   docker push $image
   ```
3. Confirm the required Azure service values are available:
   ```powershell
   $azureOpenAiEndpoint = "https://<resource>.openai.azure.com"
   $azureOpenAiDeployment = "<deployment>"
   $contentSafetyEndpoint = "https://<resource>.cognitiveservices.azure.com"
   $cosmosEndpoint = "https://<account>.documents.azure.com:443/"
   ```
4. Deploy the Container Apps environment and Loom API app:
   ```powershell
   az deployment group create `
     --resource-group $resourceGroup `
     --template-file infra/main.bicep `
     --parameters `
       image=$image `
       azureOpenAiEndpoint=$azureOpenAiEndpoint `
       azureOpenAiApiKey="<azure-openai-key>" `
       azureOpenAiDeployment=$azureOpenAiDeployment `
       contentSafetyEndpoint=$contentSafetyEndpoint `
       contentSafetyKey="<content-safety-key>" `
       cosmosEndpoint=$cosmosEndpoint `
       cosmosKey="<cosmos-key>" `
       cosmosDatabase="loom" `
       cosmosContainer="locks" `
       loomRequireSignature="false"
   ```
5. If the image is private, ensure the Container App can pull from the registry. For ACR, assign the app identity `AcrPull` or configure registry credentials before relying on the deployment for a live demo.
6. Verify the endpoint with a health check and a handshake request.

## Verification checklist

- The Container App starts successfully and responds on `/health`.
- The gateway boots with `LOOM_MODE=azure` and the Azure adapter configuration present.
- A handshake succeeds with one lock and follow-on conflicts in the Cosmos-backed ledger path.
- Azure OpenAI / Azure AI Foundry request metrics show intent parsing calls.
- Azure AI Content Safety metrics show screening calls.
- Cosmos DB metrics show writes against the configured `locks` container.

## Current limitations

- `infra/main.bicep` wires the Loom container and runtime configuration, but does not yet provision Azure OpenAI, Content Safety, Cosmos DB, Entra ID, ACR, or ACR pull role assignments.
- Live Azure evidence still needs to be captured separately: deployed URL, `/health` response, scenario output, and Azure service metrics.
- For local-only demos, keep `LOOM_MODE=local`; do not present that as a live Azure deployment.
