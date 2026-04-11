<?php
header('Content-Type: application/json; charset=utf-8');

$cfgFile = '/boot/config/plugins/streamfuse-widget/streamfuse-widget.cfg';
$backend = 'http://127.0.0.1:8000';
$limit = 5;

if (is_file($cfgFile) && is_readable($cfgFile)) {
  $lines = @file($cfgFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
  if (is_array($lines)) {
    foreach ($lines as $line) {
      $line = trim($line);
      if ($line === '' || $line[0] === '#') continue;
      $parts = explode('=', $line, 2);
      if (count($parts) !== 2) continue;
      $k = trim($parts[0]);
      $v = trim(trim($parts[1]), "\"'");
      if ($k === 'backend_url' && $v !== '') $backend = $v;
      if ($k === 'session_limit') $limit = (int)$v;
    }
  }
}

$backend = rtrim($backend, '/');
if ($limit < 1) $limit = 1;
if ($limit > 20) $limit = 20;

$url = $backend . '/api/dashboard/widget?limit=' . $limit;

$output = '';
$cmd = '/usr/bin/curl -fsS --max-time 5 ' . escapeshellarg($url) . ' 2>/dev/null';
if (is_executable('/usr/bin/curl')) {
  $output = (string)@shell_exec($cmd);
}

if (!$output) {
  $ctx = stream_context_create(['http' => ['timeout' => 5]]);
  $fallback = @file_get_contents($url, false, $ctx);
  if ($fallback !== false) $output = $fallback;
}

if (!$output) {
  http_response_code(502);
  echo json_encode(['error' => 'Cannot reach StreamFuse backend', 'url' => $url]);
  exit;
}

$data = json_decode($output, true);
if (!is_array($data)) {
  http_response_code(502);
  echo json_encode(['error' => 'Invalid response from StreamFuse backend', 'url' => $url]);
  exit;
}

echo json_encode($data, JSON_UNESCAPED_SLASHES);
