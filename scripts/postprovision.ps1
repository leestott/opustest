#!/usr/bin/env pwsh
# Post-provision hook: seeds Cosmos DB and assigns RBAC for Azure AI.
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

# Assign Cognitive Services OpenAI User role to the container app managed identity
if ($env:APP_PRINCIPAL_ID -and $env:AZURE_AI_PROJECT_ENDPOINT) {
    Write-Host "Assigning Cognitive Services OpenAI User role..."
    $aiAccounts = az cognitiveservices account list --query "[?contains(properties.endpoint, '$($env:AZURE_AI_PROJECT_ENDPOINT)')].id" -o tsv 2>$null
    if ($aiAccounts) {
        $existing = az role assignment list --assignee $env:APP_PRINCIPAL_ID --role "Cognitive Services OpenAI User" --scope $aiAccounts --query "length(@)" -o tsv 2>$null
        if ($existing -eq "0" -or -not $existing) {
            az role assignment create --assignee $env:APP_PRINCIPAL_ID --role "Cognitive Services OpenAI User" --scope $aiAccounts 2>$null
            Write-Host "Role assigned successfully."
        } else {
            Write-Host "Role already assigned."
        }
    } else {
        Write-Warning "Could not find AI resource for endpoint $($env:AZURE_AI_PROJECT_ENDPOINT). Assign role manually."
    }
}
