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

Write-Host "Seeding Cosmos DB (creates database/container if needed)..."
python scripts/seed_cosmos.py
