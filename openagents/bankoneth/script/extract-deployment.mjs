#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
//
// extract-deployment.mjs — read a Foundry broadcast and write the deployed
// addresses into deployments/<network>.json (+ mirror into the dApp's public/),
// so the static dApp goes pseudo-live against a freshly-deployed chain.
//
// Usage:  node script/extract-deployment.mjs <chainId> [network]
//   e.g.  node script/extract-deployment.mjs 31337 local
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const chainId = process.argv[2] || "31337";
const network = process.argv[3] || (chainId === "1" ? "mainnet" : chainId === "11155111" ? "sepolia" : "local");

// contractName (as it appears in the broadcast) → deployments[].bankon key
const NAME_TO_KEY = {
  BankonPriceOracle: "priceOracle",
  BankonReputationGate: "reputationGate",
  BankonPaymentRouter: "paymentRouter",
  AgentRegistry: "agentRegistry",
  BankonX402Attestor: "x402Attestor",
  BankonAgenticPlaceHook: "agenticPlaceHook",
  BankonSubnameResolver: "resolver",
  BankonSubnameResolverV2: "resolverV2",
  BankonInftAdapter: "inftAdapter",
  BankonSubnameRegistrar: "subnameRegistrar",
  BankonEthRegistrar: "ethRegistrar",
  BankonDomainHosting: "domainHosting",
};

const broadcast = join(ROOT, "broadcast", "DeployEthereum.s.sol", chainId, "run-latest.json");
if (!existsSync(broadcast)) {
  console.error(`No broadcast at ${broadcast}\n  → run the deploy first (forge script … --broadcast).`);
  process.exit(1);
}
const txs = JSON.parse(readFileSync(broadcast, "utf8")).transactions || [];

const found = {};
for (const t of txs) {
  if (t.transactionType !== "CREATE") continue;
  const key = NAME_TO_KEY[t.contractName];
  if (key && t.contractAddress) found[key] = t.contractAddress;
}

const depPath = join(ROOT, "deployments", `${chainId === "31337" ? "local" : chainId}.json`);
const dep = JSON.parse(readFileSync(depPath, "utf8"));
dep.network = network;
let n = 0;
for (const [key, addr] of Object.entries(found)) { dep.bankon[key] = addr; n++; }
const out = JSON.stringify(dep, null, 2) + "\n";
writeFileSync(depPath, out);

// mirror into the served dApp dir
const pub = join(ROOT, "packages", "web", "public", "deployments", `${chainId === "31337" ? "local" : chainId}.json`);
if (existsSync(dirname(pub))) writeFileSync(pub, out);

console.log(`Wrote ${n} addresses → ${depPath} (+ public mirror).`);
for (const [k, a] of Object.entries(found)) console.log(`  ${k.padEnd(18)} ${a}`);
const missing = Object.values(NAME_TO_KEY).filter((k) => !found[k]);
if (missing.length) console.log(`  (still zero: ${missing.join(", ")})`);
