#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Bootstrap for `npx openagents-dapp <cmd>`. Routes to the compiled dist/.

import("../dist/index.js").catch((err) => {
  console.error("openagents-dapp: failed to load CLI:", err);
  process.exit(1);
});
