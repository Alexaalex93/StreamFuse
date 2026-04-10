param(
  [string]$RepoRoot = "C:\src\StreamFuse"
)

$ErrorActionPreference = "Stop"

$pluginRoot = Join-Path $RepoRoot "plugin-unraid"
$widgetDir = Join-Path $pluginRoot "widget"
$releaseDir = Join-Path $pluginRoot "release"
$archivePath = Join-Path $releaseDir "unraid-widget.tar.gz"

if (-not (Test-Path $widgetDir)) {
  throw "Widget folder not found: $widgetDir"
}

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
if (Test-Path $archivePath) {
  Remove-Item $archivePath -Force
}

tar -czf $archivePath -C $widgetDir .

Write-Host "Created: $archivePath"
