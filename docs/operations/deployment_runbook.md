# Azure Deployment Runbook

This runbook captures the minimum Azure infrastructure needed to host the Loom ATP gateway in a production-style deployment.

## Required Azure resources

- Azure Container Apps environment for the API gateway.
- Azure Container Registry (optional for private images, but recommended for production).
- Azure OpenAI or Azure AI Foundry deployment for intent parsing.
- Azure AI Content Safety resource for safety screening.
- Azure Cosmos DB for NoSQL account with a database and container for lock state.
- Microsoft Entra ID or another identity mechanism for future authority verification.

## Required secrets and environment variables

Set the following values in GitHub Actions secrets or the Container Apps environment:

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

1. Create a resource group and deploy the Bicep template:
   ```powershell
   az group create --name loom-protocol-rg --location eastus
   az deployment group create --resource-group loom-protocol-rg --template-file infra/main.bicep
   ```
2. Build and push the API image to ACR or another registry.
3. Update the Container App image reference to the pushed image.
4. Configure the runtime secrets listed above on the Container App.
5. Verify the endpoint with a health check and a handshake request.

## Verification checklist

- The Container App starts successfully and responds on `/health`.
- The gateway boots with `LOOM_MODE=azure` and the Azure adapter configuration present.
- A handshake succeeds with one lock and follow-on conflicts in the Cosmos-backed ledger path.
