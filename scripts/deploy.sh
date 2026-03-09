#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy.sh — Deploy the Code Verification System to Azure Container Apps
#
# Usage:
#   ./scripts/deploy.sh \
#       --env-name codeverify \
#       --location eastus \
#       --ai-endpoint "https://myproject.openai.azure.com/" \
#       [--ai-model gpt-4o] \
#       [--skip-seed]
# ---------------------------------------------------------------------------

set -euo pipefail

# ---- defaults ----
AI_MODEL="gpt-4o"
SKIP_SEED=false

# ---- parse args ----
while [[ $# -gt 0 ]]; do
  case $1 in
    --env-name)    ENV_NAME="$2";     shift 2 ;;
    --location)    LOCATION="$2";     shift 2 ;;
    --ai-endpoint) AI_ENDPOINT="$2";  shift 2 ;;
    --ai-model)    AI_MODEL="$2";     shift 2 ;;
    --skip-seed)   SKIP_SEED=true;    shift   ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

for var in ENV_NAME LOCATION AI_ENDPOINT; do
  if [ -z "${!var:-}" ]; then
    echo "Error: --$(echo $var | tr '_' '-' | tr '[:upper:]' '[:lower:]') is required."
    exit 1
  fi
done

step() { echo -e "\n\033[36m==> $1\033[0m"; }
ok()   { echo -e "    \033[32m$1\033[0m"; }
warn() { echo -e "    \033[33m$1\033[0m"; }

# ---- 0. Pre-flight ----
step "Checking prerequisites..."
for cmd in az azd docker python; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "'$cmd' not found — please install it."; exit 1; }
done
az account show >/dev/null 2>&1 || { echo "Not logged in. Run 'az login' first."; exit 1; }
ok "az, azd, docker, python found."

# ---- 1. azd environment ----
step "Initialising azd environment '$ENV_NAME'..."
azd env new "$ENV_NAME" --no-prompt 2>/dev/null || true
azd env set AZURE_LOCATION "$LOCATION"
azd env set AZURE_AI_PROJECT_ENDPOINT "$AI_ENDPOINT"
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME "$AI_MODEL"
ok "azd environment configured."

# ---- 2. Provision ----
step "Provisioning Azure resources..."
azd provision --no-prompt
ok "Infrastructure provisioned."

# ---- 3. Retrieve outputs ----
step "Retrieving deployment outputs..."
RG_NAME=$(azd env get-value AZURE_RESOURCE_GROUP)
ACR_NAME=$(azd env get-value ACR_NAME)
ACR_LOGIN=$(azd env get-value ACR_LOGIN_SERVER)
COSMOS_ENDPOINT=$(azd env get-value COSMOS_ENDPOINT)
COSMOS_ACCOUNT=$(azd env get-value COSMOS_ACCOUNT_NAME)
COSMOS_DB=$(azd env get-value COSMOS_DATABASE_NAME)
COSMOS_CONTAINER=$(azd env get-value COSMOS_CONTAINER_NAME)
APP_NAME=$(azd env get-value APP_NAME)
APP_FQDN=$(azd env get-value APP_FQDN)

ok "Resource Group : $RG_NAME"
ok "ACR            : $ACR_LOGIN"
ok "Cosmos Endpoint: $COSMOS_ENDPOINT"
ok "Container App  : $APP_NAME"

# ---- 4. Build & push ----
step "Building and pushing Docker image..."
IMAGE="code-verification:latest"
REMOTE_IMAGE="$ACR_LOGIN/$IMAGE"

az acr login --name "$ACR_NAME"
docker build -t "$IMAGE" .
docker tag "$IMAGE" "$REMOTE_IMAGE"
docker push "$REMOTE_IMAGE"
ok "Image pushed: $REMOTE_IMAGE"

# ---- 5. Update Container App ----
step "Updating Container App with new image..."
az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RG_NAME" \
    --image "$REMOTE_IMAGE"
ok "Container App updated."

# ---- 6. Seed Cosmos DB ----
if [ "$SKIP_SEED" = false ]; then
  step "Seeding Cosmos DB with sample data..."
  COSMOS_KEY=$(az cosmosdb keys list \
      --name "$COSMOS_ACCOUNT" \
      --resource-group "$RG_NAME" \
      --query "primaryMasterKey" -o tsv)

  export COSMOS_ENDPOINT
  export COSMOS_KEY
  export COSMOS_DATABASE_NAME="$COSMOS_DB"
  export COSMOS_CONTAINER_NAME="$COSMOS_CONTAINER"

  python scripts/seed_cosmos.py
  ok "Cosmos DB seeded."
else
  warn "Skipping Cosmos DB seed."
fi

# ---- 7. Summary ----
step "Deployment complete!"
echo ""
echo "  Application URL: https://$APP_FQDN"
echo "  Resource Group : $RG_NAME"
echo "  Cosmos Endpoint: $COSMOS_ENDPOINT"
echo "  ACR            : $ACR_LOGIN"
echo ""
echo "To redeploy after code changes:"
echo "  docker build -t $IMAGE ."
echo "  docker tag $IMAGE $REMOTE_IMAGE"
echo "  docker push $REMOTE_IMAGE"
echo "  az containerapp update --name $APP_NAME --resource-group $RG_NAME --image $REMOTE_IMAGE"
echo ""
