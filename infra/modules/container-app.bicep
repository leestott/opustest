@description('Container Apps Environment name.')
param envName string

@description('Container App name.')
param appName string

@description('Location for the resources.')
param location string = resourceGroup().location

@description('Tags to apply.')
param tags object = {}

@description('ACR login server (e.g. myacr.azurecr.io).')
param acrLoginServer string

@description('Docker image name including tag.')
param imageName string

@description('ACR admin username.')
@secure()
param acrUsername string

@description('ACR admin password.')
@secure()
param acrPassword string

@description('Azure OpenAI project endpoint.')
param azureAiProjectEndpoint string

@description('Azure OpenAI model deployment name.')
param azureAiModelDeploymentName string

@description('Cosmos DB endpoint.')
param cosmosEndpoint string

@description('Cosmos DB key.')
@secure()
param cosmosKey string

@description('Cosmos DB database name.')
param cosmosDatabaseName string

@description('Cosmos DB container name.')
param cosmosContainerName string

// Log Analytics workspace for Container Apps Environment
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${envName}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container Apps Environment
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acrLoginServer
          username: acrUsername
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acrPassword
        }
        {
          name: 'cosmos-key'
          value: cosmosKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'code-verification'
          image: '${acrLoginServer}/${imageName}'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'AZURE_AI_PROJECT_ENDPOINT', value: azureAiProjectEndpoint }
            { name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME', value: azureAiModelDeploymentName }
            { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
            { name: 'COSMOS_KEY', secretRef: 'cosmos-key' }
            { name: 'COSMOS_DATABASE_NAME', value: cosmosDatabaseName }
            { name: 'COSMOS_CONTAINER_NAME', value: cosmosContainerName }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output appName string = containerApp.name
output principalId string = containerApp.identity.principalId
