// SPDX-License-Identifier: Apache-2.0
//
// cmc_cli.mjs — thin wrapper over the `cmc` Go CLI (github.com/openCMC/CoinMarketCap-CLI) for the
// KEYED CoinMarketCap ingestion path (bulk/structured pulls). Reuses the server-side key from
// bankonchains (.bankonchains.env or env CMC_API_KEY); the key is NEVER exposed to the browser.
// For keyless pay-per-call, use the x402 path (cmc_x402_ingest.mjs).
//
// Install the CLI:  brew install openCMC/CoinMarketCap-CLI/cmc
//   or             curl -sSfL https://raw.githubusercontent.com/openCMC/CoinMarketCap-CLI/main/install.sh | sh
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";

function loadKey() {
  if (process.env.CMC_API_KEY) return process.env.CMC_API_KEY;
  try { // bankoneth-root .bankonchains.env (outside web root): clients → x402evm → bankoneth/
    const f = new URL("../../.bankonchains.env", import.meta.url);
    for (const line of readFileSync(f, "utf8").split("\n")) {
      const m = line.match(/^\s*CMC_API_KEY\s*=\s*(.*?)\s*$/);
      if (m) return m[1];
    }
  } catch {}
  return "";
}

// Run `cmc <args...>` with JSON output; resolves the parsed JSON (or raw text).
export function cmc(args, { json = true } = {}) {
  const key = loadKey();
  const a = json && !args.includes("--format") ? [...args, "--format", "json"] : args;
  return new Promise((resolve, reject) => {
    const p = spawn("cmc", a, { env: { ...process.env, CMC_API_KEY: key } });
    let out = "", err = "";
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", (d) => (err += d));
    p.on("error", (e) => reject(new Error(e.code === "ENOENT" ? "`cmc` CLI not installed — see header" : e.message)));
    p.on("close", (code) => {
      if (code !== 0) return reject(new Error(`cmc exited ${code}: ${err.slice(0, 200)}`));
      if (!json) return resolve(out);
      try { resolve(JSON.parse(out)); } catch { resolve(out); }
    });
  });
}

export const price = (symbol) => cmc(["price", symbol]);
export const resolve = (symbol) => cmc(["resolve", symbol]);
export const markets = (opts = []) => cmc(["markets", ...opts]);

if (import.meta.url === `file://${process.argv[1]}`) {
  cmc(process.argv.slice(2)).then((d) => console.log(typeof d === "string" ? d : JSON.stringify(d, null, 2)))
    .catch((e) => { console.error(e.message); process.exit(1); });
}
