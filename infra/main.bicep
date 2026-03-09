targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment used to generate a unique resource name.')
param environmentName string

@minLength(1)
@description('Primary location for all resources.')
param location string

@description('Name of the Cosmos DB database.')
param cosmosDatabaseName string = 'code-examples'

@description('Name of the Cosmos DB container for code examples.')
param cosmosContainerName string = 'examples'

@description('Azure OpenAI project endpoint.')
param azureAiProjectEndpoint string = ''

@description('Azure OpenAI model deployment name.')
param azureAiModelDeploymentName string = 'gpt-5.2'

@description('Full resource ID of the Azure AI / Cognitive Services account for RBAC. Leave empty to skip role assignment.')
param azureAiResourceId string = ''

@description('Docker image name with tag to deploy.')
param imageName string = 'code-verification:latest'

var abbrs = loadJsonContent('abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: '${abbrs.resourceGroup}${environmentName}'
  location: location
  tags: tags
}

// Cosmos DB account
module cosmos 'modules/cosmos.bicep' = {
  name: 'cosmos'
  scope: rg
  params: {
    accountName: '${abbrs.cosmosAccount}${resourceToken}'
    location: location
    tags: tags
    databaseName: cosmosDatabaseName
    containerName: cosmosContainerName
  }
}

// Azure Container Registry
module acr 'modules/acr.bicep' = {
  name: 'acr'
  scope: rg
  params: {
    registryName: '${abbrs.acr}${resourceToken}'
    location: location
    tags: tags
  }
}

// Container Apps hosting
module app 'modules/container-app.bicep' = {
  name: 'container-app'
  scope: rg
  params: {
    envName: '${abbrs.containerAppsEnv}${resourceToken}'
    appName: '${abbrs.containerApp}${resourceToken}'
    location: location
    tags: tags
    acrLoginServer: acr.outputs.loginServer
    imageName: imageName
    acrUsername: acr.outputs.adminUsername
    acrPassword: acr.outputs.adminPassword
    azureAiProjectEndpoint: azureAiProjectEndpoint
    azureAiModelDeploymentName: azureAiModelDeploymentName
    cosmosEndpoint: cosmos.outputs.endpoint
    cosmosKey: cosmos.outputs.primaryKey
    cosmosDatabaseName: cosmosDatabaseName
    cosmosContainerName: cosmosContainerName
  }
}

// Outputs consumed by azd and the deployment script
output COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output COSMOS_ACCOUNT_NAME string = cosmos.outputs.accountName
output COSMOS_DATABASE_NAME string = cosmosDatabaseName
output COSMOS_CONTAINER_NAME string = cosmosContainerName
output ACR_LOGIN_SERVER string = acr.outputs.loginServer
output ACR_NAME string = acr.outputs.registryName
output APP_FQDN string = app.outputs.fqdn
output APP_NAME string = app.outputs.appName
output APP_PRINCIPAL_ID string = app.outputs.principalId
output AZURE_RESOURCE_GROUP string = rg.name
