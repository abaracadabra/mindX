// SPDX-License-Identifier: Apache-2.0
//
// bankon.js — BANKON identity / privilege layer. Determines whether a connected wallet
// is a HOLDER (owns bankon.eth, or a *.bankon.eth subname) and mints a signed, freshness-
// bounded "holder proof" the CMC price proxy verifies. Privilege model:
//   • PUBLIC (index.html + wallet connect) → keyless prices, public dApp surface.
//   • HOLDER (*.bankon.eth / bankon.eth)   → CoinMarketCap prices (via cmc-proxy) + any
//     holder-gated features. The CMC API key never touches the client.
// dapp.js consumes this to unlock the privileged price tier.
import { ethers } from "./vendor/ethers.min.js";
import { CHAINS } from "./chains.js";

const L1 = () => new ethers.JsonRpcProvider(CHAINS[1].rpc); // ENS resolves on mainnet

export const Bankon = {
  async ownerOfBankonEth() { try { return await L1().resolveName("bankon.eth"); } catch { return null; } },

  // Holder = owns bankon.eth OR the address's primary ENS name ends in `.bankon.eth`.
  // (Extension point: also check the subname registrar / an indexer for held subnames.)
  async checkHolder(address) {
    if (!address) return { holder: false };
    const [owner, name] = await Promise.all([
      this.ownerOfBankonEth(),
      L1().lookupAddress(address).catch(() => null),
    ]);
    const isOwner = !!owner && owner.toLowerCase() === address.toLowerCase();
    const isSub = !!name && /\.bankon\.eth$/i.test(name);
    return { holder: isOwner || isSub, name: name || null, isOwner, isSub };
  },

  // Sign a freshness-bounded proof the CMC proxy verifies (recovers signer, checks ts,
  // re-checks holder on-chain). Canonical message must match the proxy.
  async proveHolder(signer, address) {
    const ts = Math.floor(Date.now() / 1000);
    const sig = await signer.signMessage(`BANKON holder proof ${ts}`);
    return { address, ts, sig };
  },
};
