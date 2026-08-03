@description('Name of the Azure Container Registry instance')
param acrName string = 'loomprotocolacr${uniqueString(resourceGroup().id)}'

@description('Name of the Azure Container Apps environment')
param environmentName string = 'loom-protocol-env'

@description('Name of the Azure Container App')
param appName string = 'loom-protocol-api'

@description('Container image to deploy, for example myregistry.azurecr.io/loom-protocol:latest')
param image string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Location for the deployment resources')
param location string = resourceGroup().location

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
              value: 'azure'
            }
            {
              name: 'LOOM_HOST'
              value: '0.0.0.0'
            }
            {
              name: 'LOOM_PORT'
              value: '8080'
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
