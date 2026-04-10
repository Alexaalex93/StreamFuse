param(
  [string]$RepoRoot = "C:\src\StreamFuse"
)

$ErrorActionPreference = "Stop"

$pluginRoot = Join-Path $RepoRoot "plugin-unraid"
$runtimeDir = Join-Path $pluginRoot "runtime"
$releaseDir = Join-Path $pluginRoot "release"
$archivePath = Join-Path $releaseDir "streamfuse-widget-unraid.tar.gz"

if (-not (Test-Path $runtimeDir)) {
  throw "Runtime folder not found: $runtimeDir"
}

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
if (Test-Path $archivePath) {
  Remove-Item $archivePath -Force
}

tar -czf $archivePath -C $runtimeDir .

Write-Host "Created: $archivePath"
