@description('Name of the Azure Container Apps environment')
param environmentName string = 'loom-protocol-env'

@description('Name of the Azure Container App')
param appName string = 'loom-protocol-api'

@description('Loom API container image to deploy, for example <registry>.azurecr.io/loom-protocol:<tag>')
@minLength(1)
param image string

@description('Location for the deployment resources')
param location string = resourceGroup().location

@description('Runtime mode for the Loom API. Use azure for production-style deployments.')
@allowed([
  'local'
  'azure'
])
param loomMode string = 'azure'

@description('Whether the API should require signed ATP packets.')
@allowed([
  'true'
  'false'
])
param loomRequireSignature string = 'false'

@description('Shared signing secret for ATP packet verification. Required when loomRequireSignature is true.')
@secure()
param loomSharedSecret string = ''

@description('Azure OpenAI or Azure AI Foundry endpoint used by the Loom intent parser.')
param azureOpenAiEndpoint string = ''

@description('Azure OpenAI API key.')
@secure()
param azureOpenAiApiKey string = ''

@description('Azure OpenAI API version.')
param azureOpenAiApiVersion string = '2024-10-21'

@description('Azure OpenAI deployment name.')
param azureOpenAiDeployment string = ''

@description('Azure AI Content Safety endpoint.')
param contentSafetyEndpoint string = ''

@description('Azure AI Content Safety key.')
@secure()
param contentSafetyKey string = ''

@description('Content Safety severity threshold that blocks an intent.')
param contentSafetyBlockThreshold int = 4

@description('Azure Cosmos DB for NoSQL endpoint.')
param cosmosEndpoint string = ''

@description('Azure Cosmos DB key.')
@secure()
param cosmosKey string = ''

@description('Cosmos database used by the Loom ledger.')
param cosmosDatabase string = 'loom'

@description('Cosmos container used by the Loom ledger. Use partition key /resource_id.')
param cosmosContainer string = 'locks'

resource managedEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {}
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
      }
      registries: []
      secrets: [
        {
          name: 'azure-openai-api-key'
          value: azureOpenAiApiKey
        }
        {
          name: 'content-safety-key'
          value: contentSafetyKey
        }
        {
          name: 'cosmos-key'
          value: cosmosKey
        }
        {
          name: 'loom-shared-secret'
          value: loomSharedSecret
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'loom-api'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'LOOM_MODE'
              value: loomMode
            }
            {
              name: 'LOOM_HOST'
              value: '0.0.0.0'
            }
            {
              name: 'LOOM_PORT'
              value: '8080'
            }
            {
              name: 'LOOM_REQUIRE_SIGNATURE'
              value: loomRequireSignature
            }
            {
              name: 'LOOM_SHARED_SECRET'
              secretRef: 'loom-shared-secret'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAiEndpoint
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: azureOpenAiApiVersion
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT'
              value: azureOpenAiDeployment
            }
            {
              name: 'CONTENT_SAFETY_ENDPOINT'
              value: contentSafetyEndpoint
            }
            {
              name: 'CONTENT_SAFETY_KEY'
              secretRef: 'content-safety-key'
            }
            {
              name: 'CONTENT_SAFETY_BLOCK_THRESHOLD'
              value: string(contentSafetyBlockThreshold)
            }
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmosEndpoint
            }
            {
              name: 'COSMOS_KEY'
              secretRef: 'cosmos-key'
            }
            {
              name: 'COSMOS_DATABASE'
              value: cosmosDatabase
            }
            {
              name: 'COSMOS_CONTAINER'
              value: cosmosContainer
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output healthCheckUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}/health'
