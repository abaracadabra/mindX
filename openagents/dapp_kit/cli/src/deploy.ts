// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// `openagents-dapp deploy <network> <script>` — wraps @openagents/deploy.

import { foundryDriver, configFor } from "@openagents/deploy";

export async function deployCmd(args: string[]): Promise<number> {
  const network = args[0];
  const scriptName = args[1];
  if (!network || !scriptName) {
    console.error("openagents-dapp deploy: usage: deploy <network> <scriptName>");
    return 2;
  }
  try {
    const cfg = configFor(network);
    const contractsRoot = process.env.CONTRACTS_ROOT || process.cwd();
    console.log(`Deploying ${scriptName} → ${network} (chain ${cfg.chainId})...`);

    if (cfg.isMainnet) {
      const it = await foundryDriver.intent({
        contractsRoot,
        scriptName,
        network,
        env: process.env as Record<string, string>,
      });
      console.log("Mainnet deploy intent:");
      console.log(`  id: ${it.id}`);
      console.log(`  summary: ${it.summary}`);
      console.log(`  expires at: ${new Date(it.expiresAt).toISOString()}`);
      console.log("");
      console.log("Set MAINNET_INTENT_CONFIRMED=" + it.id + " and re-run to execute.");
      if (process.env.MAINNET_INTENT_CONFIRMED !== it.id) return 0;
    }

    const result = await foundryDriver.runScript({
      contractsRoot,
      scriptName,
      network,
      env: process.env as Record<string, string>,
      broadcast: true,
      verify: !!process.env.VERIFY,
      verifierApiKey: process.env.BASESCAN_API_KEY || process.env.ETHERSCAN_API_KEY,
      skipConfirmation: !cfg.isMainnet,
    });
    console.log("Deployment complete.");
    if (result.receiptPath) console.log(`Receipt: ${result.receiptPath}`);
    return 0;
  } catch (err) {
    console.error(`Deploy failed: ${err instanceof Error ? err.message : String(err)}`);
    return 1;
  }
}
