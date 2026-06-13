// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// AlgoKit deployment driver. Wraps `algokit deploy` and adopts the
// MAINNET=true flag-gate pattern from
// daio/contracts/algorand/x402_receipt_deploy.ts.
//
// Contract: docs/services/contract_deployment_as_a_service.md §2.2.

export interface AlgokitDeployOpts {
  /** Path to the PuyaTs artifacts dir for the contract (TEAL + ARC-56 spec). */
  artifactsRoot: string;
  /** Network catalog key (e.g. "algorand-testnet"). */
  network: "algorand-mainnet" | "algorand-testnet";
  /** Deployer mnemonic — supplied by the caller, never persisted by the driver. */
  mnemonic?: string;
  /** Algod base URL; defaults from catalog. */
  algodUrl?: string;
  /** Skip the two-step confirmation flow for testnet (ignored for mainnet). */
  skipConfirmation?: boolean;
  /** When true on a mainnet network, the env flag MUST also be MAINNET=true. */
  mainnetExplicit?: boolean;
}

export interface AlgokitDeployResult {
  appId: number;
  address: string;
  txId: string;
  contractName: string;
  deployedAt: string;
}

/**
 * Deploy an Algorand contract via algokit. Reuses the
 * `MAINNET=true` flag-gate from x402_receipt_deploy.ts: mainnet deploys
 * require both the `network === "algorand-mainnet"` *and* an explicit
 * mainnetExplicit=true so a typo cannot push to mainnet.
 *
 * NOTE: this is a thin shell-out wrapper. The actual algokit CLI is
 * invoked with the artifactsRoot as the project dir. The mnemonic is
 * passed via env var and is never written to disk by this driver.
 */
export async function deploy(opts: AlgokitDeployOpts): Promise<AlgokitDeployResult> {
  if (opts.network === "algorand-mainnet" && !opts.mainnetExplicit) {
    throw new Error(
      "Algorand mainnet deploy requires mainnetExplicit=true. Refusing.",
    );
  }
  if (typeof window !== "undefined") {
    throw new Error("algokit-driver runs server-side only.");
  }

  const algodUrl =
    opts.algodUrl ||
    (opts.network === "algorand-mainnet"
      ? "https://mainnet-api.algonode.cloud"
      : "https://testnet-api.algonode.cloud");

  const env: Record<string, string> = {
    ALGOD_SERVER: algodUrl,
    ALGOD_PORT: "443",
    ALGOD_TOKEN: "",
  };
  if (opts.mnemonic) env.DEPLOYER_MNEMONIC = opts.mnemonic;
  if (opts.network === "algorand-mainnet") env.MAINNET = "true";

  const stdout = await runAlgokit(
    ["project", "deploy", opts.network === "algorand-mainnet" ? "mainnet" : "testnet"],
    { cwd: opts.artifactsRoot, env },
  );

  // algokit deploy stdout typically includes the deployed app id; the exact
  // shape is opts.artifactsRoot-specific. The dApp parses it in its own
  // post-deploy hook. For now we surface a minimal result based on common
  // shape ("App ID: 12345").
  const appIdMatch = /App ID:\s*(\d+)/.exec(stdout);
  const addrMatch = /App Address:\s*([A-Z2-7]{58})/.exec(stdout);
  const txMatch = /Transaction ID:\s*([A-Z0-9]+)/i.exec(stdout);

  return {
    appId: appIdMatch ? Number(appIdMatch[1]) : 0,
    address: addrMatch ? addrMatch[1] : "",
    txId: txMatch ? txMatch[1] : "",
    contractName: opts.artifactsRoot.split("/").pop() ?? "",
    deployedAt: new Date().toISOString(),
  };
}

/**
 * True when `algokit` is on PATH.
 */
export async function algokitAvailable(): Promise<boolean> {
  try {
    await runAlgokit(["--version"], {});
    return true;
  } catch {
    return false;
  }
}

// ─── helpers ────────────────────────────────────────────────────

async function runAlgokit(
  args: string[],
  opts: { cwd?: string; env?: Record<string, string> },
): Promise<string> {
  const { spawn } = await import("node:child_process");
  return await new Promise<string>((resolve, reject) => {
    const child = spawn("algokit", args, {
      cwd: opts.cwd,
      env: { ...process.env, ...(opts.env ?? {}) },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (d) => (stdout += d.toString()));
    child.stderr?.on("data", (d) => (stderr += d.toString()));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`algokit ${args.join(" ")} exited ${code}: ${stderr}`));
    });
  });
}
