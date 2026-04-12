<?php
$cfgFile = '/boot/config/plugins/streamfuse-widget/streamfuse-widget.cfg';
$backend = 'http://127.0.0.1:8000';

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
    }
  }
}

$u = isset($_GET['u']) ? (string)$_GET['u'] : '';
if ($u === '') {
  http_response_code(404);
  exit;
}

$backend = rtrim($backend, '/');
if (preg_match('/^https?:\/\//i', $u)) {
  $url = $u;
} else {
  if ($u[0] !== '/') $u = '/' . $u;
  $url = $backend . $u;
}

$ctx = stream_context_create(['http' => ['timeout' => 6]]);
$data = @file_get_contents($url, false, $ctx);
if ($data === false) {
  http_response_code(404);
  exit;
}

$contentType = 'image/jpeg';
if (isset($http_response_header) && is_array($http_response_header)) {
  foreach ($http_response_header as $h) {
    if (stripos($h, 'Content-Type:') === 0) {
      $contentType = trim(substr($h, strlen('Content-Type:')));
      break;
    }
  }
}

header('Content-Type: ' . $contentType);
header('Cache-Control: public, max-age=60');
echo $data;
