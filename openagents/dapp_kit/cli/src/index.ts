// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// openagents-dapp CLI router.
// Sub-commands: new, dev, build, deploy.
// Contract: docs/services/contract_deployment_as_a_service.md §10 (Phase F3).

import { newCmd } from "./new.js";
import { devCmd } from "./dev.js";
import { buildCmd } from "./build.js";
import { deployCmd } from "./deploy.js";

async function main(argv: string[]): Promise<number> {
  const cmd = argv[2];
  const rest = argv.slice(3);
  switch (cmd) {
    case "new":
      return await newCmd(rest);
    case "dev":
      return await devCmd(rest);
    case "build":
      return await buildCmd(rest);
    case "deploy":
      return await deployCmd(rest);
    case "-h":
    case "--help":
    case undefined:
      printHelp();
      return 0;
    default:
      console.error(`Unknown command: ${cmd}`);
      printHelp();
      return 2;
  }
}

function printHelp(): void {
  console.log(`openagents-dapp — openagents/ dApp kit CLI

Usage:
  openagents-dapp new <project-dir>          Scaffold a new dApp from the lit-vite template.
  openagents-dapp dev                        Run vite dev server (webview mode).
  openagents-dapp build [--tauri]            Build for production. With --tauri, also runs tauri build.
  openagents-dapp deploy <network> <script>  Deploy contracts to a network using @openagents/deploy.

Examples:
  openagents-dapp new my-dapp
  cd my-dapp && openagents-dapp dev
  openagents-dapp deploy base-sepolia DeployTier1.s.sol

Contract: docs/services/contract_deployment_as_a_service.md
`);
}

void main(process.argv).then((code) => process.exit(code));
