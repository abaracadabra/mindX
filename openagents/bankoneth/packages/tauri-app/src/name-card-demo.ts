// SPDX-License-Identifier: Apache-2.0
//
// Standalone demo entry — renders <bankoneth-name-card> with a
// realistic mock NameLookup so the user can preview the design without a
// live RPC.
//
// Open at http://127.0.0.1:5173/name-card-demo.html

import "@bankoneth/ui";
import { type NameLookup, FUSE, namehash } from "@bankoneth/core";

const MOCK: NameLookup = {
  name:   "alice.bankon.eth",
  node:   namehash("alice.bankon.eth") as `0x${string}`,
  owner:  "0x5277D156E7cD71ebF22c8f81812A65493D1ce534",
  fuses:  FUSE.PARENT_CANNOT_CONTROL |
          FUSE.CANNOT_UNWRAP         |
          FUSE.CANNOT_TRANSFER       |
          FUSE.CAN_EXTEND_EXPIRY,
  expiry:  Math.floor(Date.now() / 1000) + 365 * 24 * 3600,
  addr:    "0x000000000000000000000000000000000000a91ce" as `0x${string}`,
  rawAddr: "0x5277D156E7cD71ebF22c8f81812A65493D1ce534",
  records: {
    avatar:                 "https://api.dicebear.com/8.x/identicon/svg?seed=alice.bankon.eth",
    url:                    "https://alice.example",
    description:            "Autonomous agent · long-form research + reactive ops",
    "com.twitter":          "@alice_bankon",
    "com.github":           "alice-bankon",
    email:                  "alice@bankon.eth",
    "mindx.endpoint":       "https://mindx.pythai.net/agent/alice",
    "bonafide.attestation": "0xfa7e9c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f",
    "agent.capabilities":   '{"audit":true,"deploy":true,"trade":false,"author":true}',
    "inft.uri":             "ipfs://bafkreih7sahxcaqkx7hrahbpgyjcm3afjcozs6jh4lapuyjjp5fxsx5z3y",
    "agenticplace.listing": "https://agenticplace.pythai.net/n/alice.bankon.eth",
    "x402.endpoint":        "https://x402.bankon.eth/svc",
    "algoid.did":           "did:algo:UWGGI...J38ASE57862DE",
  },
  tba: "0x000000000000000000000000000000000000a91ce" as `0x${string}`,
  isSoulbound: true,
  fetchedAt: Date.now(),
};

document.getElementById("app")!.innerHTML = `
  <div style="display:grid;gap:24px;max-width:760px;">
    <bankoneth-name-card id="card"></bankoneth-name-card>
    <pre style="background:#181a20;color:#9aa0a6;padding:16px;border-radius:8px;font-size:11px;overflow:auto;">${
      JSON.stringify(MOCK, null, 2)
    }</pre>
  </div>
`;
(document.getElementById("card") as any).lookup = MOCK;
