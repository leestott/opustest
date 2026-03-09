#!/bin/bash
# Post-provision hook: seeds Cosmos DB and assigns RBAC for Azure AI.
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

# Assign Cognitive Services OpenAI User role to the container app managed identity
if [ -n "$APP_PRINCIPAL_ID" ] && [ -n "$AZURE_AI_PROJECT_ENDPOINT" ]; then
    echo "Assigning Cognitive Services OpenAI User role..."
    AI_RESOURCE_ID=$(az cognitiveservices account list \
        --query "[?contains(properties.endpoint, '$AZURE_AI_PROJECT_ENDPOINT')].id" -o tsv 2>/dev/null)
    if [ -n "$AI_RESOURCE_ID" ]; then
        EXISTING=$(az role assignment list --assignee "$APP_PRINCIPAL_ID" \
            --role "Cognitive Services OpenAI User" --scope "$AI_RESOURCE_ID" \
            --query "length(@)" -o tsv 2>/dev/null)
        if [ "$EXISTING" = "0" ] || [ -z "$EXISTING" ]; then
            az role assignment create --assignee "$APP_PRINCIPAL_ID" \
                --role "Cognitive Services OpenAI User" --scope "$AI_RESOURCE_ID" 2>/dev/null
            echo "Role assigned successfully."
        else
            echo "Role already assigned."
        fi
    else
        echo "WARNING: Could not find AI resource for endpoint $AZURE_AI_PROJECT_ENDPOINT. Assign role manually."
    fi
fi
