param(
  [Parameter(Mandatory=$true)][string]$DockerUser,
  [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

Write-Host "Building images..."
docker compose build backend frontend

$backendSrc = "streamfuse-backend:latest"
$frontendSrc = "streamfuse-frontend:latest"
$backendDst = "$DockerUser/streamfuse-backend:$Tag"
$frontendDst = "$DockerUser/streamfuse-frontend:$Tag"

Write-Host "Tagging images..."
docker tag $backendSrc $backendDst
docker tag $frontendSrc $frontendDst

Write-Host "Pushing images..."
docker push $backendDst
docker push $frontendDst

Write-Host "Done."
Write-Host "Backend: $backendDst"
Write-Host "Frontend: $frontendDst"