#!/bin/bash
# Post-provision hook: seeds Cosmos DB with sample code examples.
# Called automatically by `azd provision` / `azd up`.

set -e

echo "Fetching Cosmos DB key..."
COSMOS_KEY=$(az cosmosdb keys list \
    --name "$COSMOS_ACCOUNT_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --query "primaryMasterKey" -o tsv)

if [ -z "$COSMOS_KEY" ]; then
    echo "ERROR: Failed to retrieve Cosmos DB key." >&2
    exit 1
fi
export COSMOS_KEY

echo "Ensuring Cosmos DB database and container exist..."
az cosmosdb sql database create \
    --account-name "$COSMOS_ACCOUNT_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$COSMOS_DATABASE_NAME" 2>/dev/null || true

az cosmosdb sql container create \
    --account-name "$COSMOS_ACCOUNT_NAME" \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --database-name "$COSMOS_DATABASE_NAME" \
    --name "$COSMOS_CONTAINER_NAME" \
    --partition-key-path "/language" 2>/dev/null || true

echo "Seeding Cosmos DB..."
python scripts/seed_cosmos.py
