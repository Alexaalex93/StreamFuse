<?php
header('Content-Type: application/json; charset=utf-8');

$cfgFile = '/boot/config/plugins/streamfuse-widget/streamfuse-widget.cfg';
$defaults = [
  'backend_url' => 'http://127.0.0.1:8000',
  'app_url' => 'http://127.0.0.1:5173',
  'refresh_seconds' => 10,
  'session_limit' => 5,
];

$cfg = $defaults;

if (is_file($cfgFile) && is_readable($cfgFile)) {
  $lines = @file($cfgFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
  if (is_array($lines)) {
    foreach ($lines as $line) {
      $line = trim($line);
      if ($line === '' || $line[0] === '#') continue;
      $parts = explode('=', $line, 2);
      if (count($parts) !== 2) continue;
      $k = trim($parts[0]);
      $v = trim($parts[1]);
      $v = trim($v, "\"'");
      if ($k !== '') $cfg[$k] = $v;
    }
  }
}

$refresh = (int)($cfg['refresh_seconds'] ?? 10);
$limit = (int)($cfg['session_limit'] ?? 5);
if ($refresh < 3) $refresh = 3;
if ($refresh > 120) $refresh = 120;
if ($limit < 1) $limit = 1;
if ($limit > 20) $limit = 20;

echo json_encode([
  'backend_url' => (string)($cfg['backend_url'] ?? $defaults['backend_url']),
  'app_url' => (string)($cfg['app_url'] ?? $defaults['app_url']),
  'refresh_seconds' => $refresh,
  'session_limit' => $limit,
], JSON_UNESCAPED_SLASHES);
