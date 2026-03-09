@description('Cosmos DB account name.')
param accountName string

@description('Location for the Cosmos DB account.')
param location string = resourceGroup().location

@description('Tags to apply to the Cosmos DB account.')
param tags object = {}

@description('Name of the database to create.')
param databaseName string

@description('Name of the container to create.')
param containerName string

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

// Database and container are created via CLI / seed script to work around
// ARM management-plane routing issues with serverless Cosmos DB accounts.
// They must exist before the first deployment:
//   az cosmosdb sql database create ...
//   az cosmosdb sql container create  ...

output endpoint string = cosmosAccount.properties.documentEndpoint
output accountName string = cosmosAccount.name

@description('Primary master key for Cosmos DB.')
output primaryKey string = cosmosAccount.listKeys().primaryMasterKey
