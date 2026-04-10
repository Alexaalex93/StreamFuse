<?php
header('Content-Type: application/json; charset=utf-8');

$plugin = 'streamfuse-widget';
$cfg = parse_plugin_cfg($plugin, true);

$backend = $cfg['backend_url'] ?? 'http://127.0.0.1:8000';
$app = $cfg['app_url'] ?? 'http://127.0.0.1:5173';
$refresh = (int)($cfg['refresh_seconds'] ?? 10);
$limit = (int)($cfg['session_limit'] ?? 5);

if ($refresh < 3) $refresh = 3;
if ($refresh > 120) $refresh = 120;
if ($limit < 1) $limit = 1;
if ($limit > 20) $limit = 20;

echo json_encode([
  'backend_url' => $backend,
  'app_url' => $app,
  'refresh_seconds' => $refresh,
  'session_limit' => $limit,
], JSON_UNESCAPED_SLASHES);
