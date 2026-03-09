<#
.SYNOPSIS
    Deploy the Code Verification System to Azure Container Apps.

.DESCRIPTION
    This script provisions all Azure resources (Cosmos DB, ACR, Container Apps)
    using azd/Bicep, builds and pushes the Docker image, deploys the container,
    and optionally seeds the Cosmos DB with sample data.

.PARAMETER EnvironmentName
    The azd environment name (used for resource naming).

.PARAMETER Location
    Azure region for all resources (e.g. eastus, westeurope).

.PARAMETER AzureAiProjectEndpoint
    Azure OpenAI project endpoint URL.

.PARAMETER AzureAiModelDeploymentName
    Azure OpenAI model deployment name (default: gpt-4o).

.PARAMETER SkipSeed
    Skip seeding sample data into Cosmos DB.

.EXAMPLE
    .\scripts\deploy.ps1 -EnvironmentName codeverify -Location eastus `
        -AzureAiProjectEndpoint "https://myproject.openai.azure.com/"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$EnvironmentName,

    [Parameter(Mandatory = $true)]
    [string]$Location,

    [Parameter(Mandatory = $true)]
    [string]$AzureAiProjectEndpoint,

    [Parameter()]
    [string]$AzureAiModelDeploymentName = "gpt-4o",

    [Parameter()]
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Msg) Write-Host "    $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "    $Msg" -ForegroundColor Yellow }

# ---------------------------------------------------------------
# 0. Pre-flight checks
# ---------------------------------------------------------------
Write-Step "Checking prerequisites..."

foreach ($cmd in @("az", "azd", "docker")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Required command '$cmd' not found. Please install it before running this script."
    }
}
Write-Ok "az, azd, docker found."

# Ensure logged in
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Not logged in to Azure CLI. Run 'az login' first."
}
Write-Ok "Azure CLI authenticated."

# ---------------------------------------------------------------
# 1. Initialise azd environment
# ---------------------------------------------------------------
Write-Step "Initialising azd environment '$EnvironmentName'..."

azd env new $EnvironmentName --no-prompt 2>$null
azd env set AZURE_LOCATION $Location
azd env set AZURE_AI_PROJECT_ENDPOINT $AzureAiProjectEndpoint
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME $AzureAiModelDeploymentName

Write-Ok "azd environment configured."

# ---------------------------------------------------------------
# 2. Provision infrastructure (Cosmos DB, ACR, Container Apps)
# ---------------------------------------------------------------
Write-Step "Provisioning Azure resources..."

azd provision --no-prompt
if ($LASTEXITCODE -ne 0) { throw "azd provision failed." }

Write-Ok "Infrastructure provisioned."

# ---------------------------------------------------------------
# 3. Retrieve outputs
# ---------------------------------------------------------------
Write-Step "Retrieving deployment outputs..."

$rgName            = azd env get-value AZURE_RESOURCE_GROUP
$acrName           = azd env get-value ACR_NAME
$acrLoginServer    = azd env get-value ACR_LOGIN_SERVER
$cosmosEndpoint    = azd env get-value COSMOS_ENDPOINT
$cosmosAccountName = azd env get-value COSMOS_ACCOUNT_NAME
$cosmosDatabaseName   = azd env get-value COSMOS_DATABASE_NAME
$cosmosContainerName  = azd env get-value COSMOS_CONTAINER_NAME
$appName           = azd env get-value APP_NAME
$appFqdn           = azd env get-value APP_FQDN

Write-Ok "Resource Group : $rgName"
Write-Ok "ACR            : $acrLoginServer"
Write-Ok "Cosmos Endpoint: $cosmosEndpoint"
Write-Ok "Container App  : $appName"

# ---------------------------------------------------------------
# 4. Build and push Docker image
# ---------------------------------------------------------------
Write-Step "Building and pushing Docker image..."

$imageName = "code-verification:latest"
$remoteImage = "$acrLoginServer/$imageName"

az acr login --name $acrName
docker build -t $imageName .
docker tag $imageName $remoteImage
docker push $remoteImage

Write-Ok "Image pushed: $remoteImage"

# ---------------------------------------------------------------
# 5. Update Container App with the new image
# ---------------------------------------------------------------
Write-Step "Updating Container App with new image..."

az containerapp update `
    --name $appName `
    --resource-group $rgName `
    --image $remoteImage

if ($LASTEXITCODE -ne 0) { throw "Container App update failed." }

Write-Ok "Container App updated."

# ---------------------------------------------------------------
# 6. Seed Cosmos DB (optional)
# ---------------------------------------------------------------
if (-not $SkipSeed) {
    Write-Step "Seeding Cosmos DB with sample data..."

    $cosmosKey = az cosmosdb keys list `
        --name $cosmosAccountName `
        --resource-group $rgName `
        --query "primaryMasterKey" -o tsv

    $env:COSMOS_ENDPOINT       = $cosmosEndpoint
    $env:COSMOS_KEY            = $cosmosKey
    $env:COSMOS_DATABASE_NAME  = $cosmosDatabaseName
    $env:COSMOS_CONTAINER_NAME = $cosmosContainerName

    python scripts/seed_cosmos.py
    if ($LASTEXITCODE -ne 0) { Write-Warn "Seed script returned non-zero exit code." }

    Write-Ok "Cosmos DB seeded."
} else {
    Write-Warn "Skipping Cosmos DB seed (use without -SkipSeed to populate sample data)."
}

# ---------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------
Write-Step "Deployment complete!"
Write-Host ""
Write-Host "  Application URL: https://$appFqdn" -ForegroundColor Green
Write-Host "  Resource Group : $rgName" -ForegroundColor Gray
Write-Host "  Cosmos Endpoint: $cosmosEndpoint" -ForegroundColor Gray
Write-Host "  ACR            : $acrLoginServer" -ForegroundColor Gray
Write-Host ""
Write-Host "To redeploy after code changes:" -ForegroundColor Yellow
Write-Host "  docker build -t $imageName ." -ForegroundColor Yellow
Write-Host "  docker tag $imageName $remoteImage" -ForegroundColor Yellow
Write-Host "  docker push $remoteImage" -ForegroundColor Yellow
Write-Host "  az containerapp update --name $appName --resource-group $rgName --image $remoteImage" -ForegroundColor Yellow
Write-Host ""
