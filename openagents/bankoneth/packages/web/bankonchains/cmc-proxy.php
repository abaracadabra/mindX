<?php
// SPDX-License-Identifier: Apache-2.0
// cmc-proxy.php — PHP-host variant of the CoinMarketCap proxy. Keeps the CMC key server-side
// (env CMC_API_KEY, never shipped to the browser) and caches to respect the Basic plan
// (30/min, 10k/month). Holder gating here is ALLOWLIST-based (CMC_HOLDERS) + proof freshness;
// full on-chain signature recovery needs a secp256k1 lib (kornrunner/ethereum) — use the Node
// proxy (cmc-proxy.mjs) for trustless sig+ENS verification. NEVER commit the key.
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: content-type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }

// Load the key from OUTSIDE the web root (env first, then bankoneth-root .bankonchains.env).
$KEY = getenv('CMC_API_KEY');
if (!$KEY) {
  $envFile = getenv('CMC_ENV_FILE') ?: __DIR__ . '/../../../.bankonchains.env'; // bankonchains → bankoneth/
  if (is_readable($envFile)) foreach (file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
    if (preg_match('/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/', $l, $m) && getenv($m[1]) === false) putenv("$m[1]=$m[2]");
  }
  $KEY = getenv('CMC_API_KEY');
}
if (!$KEY) { http_response_code(503); echo json_encode(['error' => 'CMC_API_KEY not configured']); exit; }

$symbol = strtoupper(preg_replace('/[^A-Za-z0-9]/', '', $_GET['symbol'] ?? 'ETH'));
$proof = json_decode(file_get_contents('php://input'), true) ?: [];
$ts = intval($proof['ts'] ?? 0);
$addr = strtolower($proof['address'] ?? '');
if (!$addr || abs(time() - $ts) > 300) { http_response_code(401); echo json_encode(['error' => 'holder proof required/expired']); exit; }
$allow = array_filter(explode(',', strtolower(getenv('CMC_HOLDERS') ?: '')));
if (!in_array($addr, $allow, true)) { http_response_code(403); echo json_encode(['error' => 'not an allowlisted holder (use cmc-proxy.mjs for on-chain verification)']); exit; }

// cache (file-based, TTL 120s) — one batched call for all symbols
$symbols = getenv('CMC_SYMBOLS') ?: 'ETH,POL,GLMR,INJ,USDC,USDT';
$cacheFile = sys_get_temp_dir() . '/bankon_cmc_cache.json';
$cache = (file_exists($cacheFile) && (time() - filemtime($cacheFile) < 120)) ? json_decode(file_get_contents($cacheFile), true) : null;
if (!$cache) {
  $url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=$symbols&convert=USD";
  $ch = curl_init($url);
  curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_HTTPHEADER => ["X-CMC_PRO_API_KEY: $KEY", 'Accept: application/json'], CURLOPT_TIMEOUT => 6]);
  $resp = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
  if ($code === 200) {
    $j = json_decode($resp, true); $cache = [];
    foreach (explode(',', $symbols) as $s) { $p = $j['data'][$s]['quote']['USD']['price'] ?? null; if ($p !== null) $cache[$s] = $p; }
    file_put_contents($cacheFile, json_encode($cache));
  } elseif (file_exists($cacheFile)) { $cache = json_decode(file_get_contents($cacheFile), true); } // 429 → stale
  else { http_response_code(502); echo json_encode(['error' => "cmc $code"]); exit; }
}
echo json_encode(['symbol' => $symbol, 'usd' => $cache[$symbol] ?? null, 'source' => 'coinmarketcap']);
