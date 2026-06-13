// deploy.js — Hardhat deploy of SoundWaveToken with automatic ABI/address export.
//
// After deploying, writes ../../dapp/deployments/<chainId>.json and runs the shared
// export-abis generator, so the dApp picks up the new address with no code change.
const hre = require("hardhat");
const { writeFileSync, mkdirSync, existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const { execFileSync } = require("node:child_process");

async function main() {
  const net = await hre.ethers.provider.getNetwork();
  const chainId = Number(net.chainId);

  const Factory = await hre.ethers.getContractFactory("SoundWaveToken");
  const wav = await Factory.deploy();
  await wav.waitForDeployment();
  const address = await wav.getAddress();

  console.log(`SoundWaveToken (SND/WAV) deployed to ${address} on chain ${chainId}`);
  console.log(`MAX_SUPPLY cap: ${await wav.MAX_SUPPLY()}  genesis: ${await wav.totalSupply()}`);

  // write deployments/<chainId>.json (addresses live here, never in abi.js)
  const depDir = join(__dirname, "..", "..", "..", "dapp", "deployments");
  mkdirSync(depDir, { recursive: true });
  const depPath = join(depDir, `${chainId}.json`);
  const dep = existsSync(depPath) ? JSON.parse(readFileSync(depPath, "utf8")) : {};
  dep.SoundWaveToken = address;
  writeFileSync(depPath, JSON.stringify(dep, null, 2) + "\n");

  // regenerate abi.js from artifacts (Foundry out/ is the source; build it first if needed)
  try {
    execFileSync("node", [join(__dirname, "..", "..", "script", "export-abis.mjs")], { stdio: "inherit" });
  } catch (e) {
    console.warn("export-abis skipped:", e.message, "(run `forge build && node script/export-abis.mjs`)");
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
