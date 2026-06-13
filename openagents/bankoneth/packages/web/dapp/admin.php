<?php
// SPDX-License-Identifier: Apache-2.0
// admin.php — PHP-host variant of the admin console. The dApp is fully client-side,
// so PHP only serves the same static markup (no server-side trust). Real authority is
// enforced on-chain by the contracts; this wrapper exists for PHP-only hosting targets
// (e.g. shared cPanel / Hostinger). Optionally gate at the edge before serving.
header('Content-Type: text/html; charset=utf-8');
// (optional) edge allowlist — purely cosmetic; on-chain checks are authoritative:
//   if (!isset($_GET['k']) || $_GET['k'] !== getenv('ADMIN_EDGE_TOKEN')) { http_response_code(403); exit('forbidden'); }
readfile(__DIR__ . '/admin.html');
