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

echo "Seeding Cosmos DB (creates database/container if needed)..."
python scripts/seed_cosmos.py
