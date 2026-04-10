<?php
header('Content-Type: application/json; charset=utf-8');

$plugin = 'streamfuse-widget';
$cfg = parse_plugin_cfg($plugin, true);

$backend = rtrim((string)($cfg['backend_url'] ?? 'http://127.0.0.1:8000'), '/');
$limit = (int)($cfg['session_limit'] ?? 5);
if ($limit < 1) $limit = 1;
if ($limit > 20) $limit = 20;

$url = $backend . '/api/dashboard/widget?limit=' . $limit;

$output = '';
$cmd = '/usr/bin/curl -fsS --max-time 5 ' . escapeshellarg($url) . ' 2>/dev/null';
if (is_executable('/usr/bin/curl')) {
  $output = (string)@shell_exec($cmd);
}

if (!$output) {
  $ctx = stream_context_create([
    'http' => ['timeout' => 5],
  ]);
  $fallback = @file_get_contents($url, false, $ctx);
  if ($fallback !== false) {
    $output = $fallback;
  }
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
