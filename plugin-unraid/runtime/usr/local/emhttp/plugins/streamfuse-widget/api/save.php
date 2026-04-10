<?php
header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405);
  echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
  exit;
}

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data)) {
  http_response_code(400);
  echo json_encode(['ok' => false, 'error' => 'Invalid payload']);
  exit;
}

$backend = trim((string)($data['backend_url'] ?? 'http://127.0.0.1:8000'));
$app = trim((string)($data['app_url'] ?? 'http://127.0.0.1:5173'));
$refresh = (int)($data['refresh_seconds'] ?? 10);
$limit = (int)($data['session_limit'] ?? 5);

if ($refresh < 3) $refresh = 3;
if ($refresh > 120) $refresh = 120;
if ($limit < 1) $limit = 1;
if ($limit > 20) $limit = 20;

$cfgDir = '/boot/config/plugins/streamfuse-widget';
$cfgFile = $cfgDir . '/streamfuse-widget.cfg';

if (!is_dir($cfgDir)) {
  @mkdir($cfgDir, 0777, true);
}

$content = "backend_url=\"" . addslashes($backend) . "\"\n"
         . "app_url=\"" . addslashes($app) . "\"\n"
         . "refresh_seconds=\"" . $refresh . "\"\n"
         . "session_limit=\"" . $limit . "\"\n";

if (@file_put_contents($cfgFile, $content) === false) {
  http_response_code(500);
  echo json_encode(['ok' => false, 'error' => 'Cannot write config file']);
  exit;
}

echo json_encode(['ok' => true]);
