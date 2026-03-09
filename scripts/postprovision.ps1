#!/usr/bin/env pwsh
# Post-provision hook: seeds Cosmos DB with sample code examples.
# Called automatically by `azd provision` / `azd up`.

Write-Host "Fetching Cosmos DB key..."
$cosmosKey = az cosmosdb keys list `
    --name $env:COSMOS_ACCOUNT_NAME `
    --resource-group $env:AZURE_RESOURCE_GROUP `
    --query "primaryMasterKey" -o tsv

if (-not $cosmosKey) {
    Write-Error "Failed to retrieve Cosmos DB key."
    exit 1
}

$env:COSMOS_KEY = $cosmosKey

Write-Host "Ensuring Cosmos DB database and container exist..."
az cosmosdb sql database create `
    --account-name $env:COSMOS_ACCOUNT_NAME `
    --resource-group $env:AZURE_RESOURCE_GROUP `
    --name $env:COSMOS_DATABASE_NAME 2>$null

az cosmosdb sql container create `
    --account-name $env:COSMOS_ACCOUNT_NAME `
    --resource-group $env:AZURE_RESOURCE_GROUP `
    --database-name $env:COSMOS_DATABASE_NAME `
    --name $env:COSMOS_CONTAINER_NAME `
    --partition-key-path "/language" 2>$null

Write-Host "Seeding Cosmos DB..."
python scripts/seed_cosmos.py
