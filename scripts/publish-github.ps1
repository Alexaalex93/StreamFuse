param(
  [Parameter(Mandatory=$true)][string]$RepoUrl,
  [string]$Branch = "main",
  [string]$Message = "chore: streamfuse unraid widget integration"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path .git)) {
  git init
  git branch -M $Branch
}

if (-not (git remote | Select-String -SimpleMatch "origin" -Quiet)) {
  git remote add origin $RepoUrl
}

git add .
try {
  git commit -m $Message
} catch {
  Write-Host "No changes to commit or commit already exists."
}

git push -u origin $Branch

Write-Host "Pushed to $RepoUrl on branch $Branch"