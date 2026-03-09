@description('Azure Container Registry name.')
param registryName string

@description('Location for the ACR.')
param location string = resourceGroup().location

@description('Tags to apply.')
param tags object = {}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

output loginServer string = acr.properties.loginServer
output registryName string = acr.name

@description('ACR admin username.')
output adminUsername string = acr.listCredentials().username

@description('ACR admin password.')
output adminPassword string = acr.listCredentials().passwords[0].value
