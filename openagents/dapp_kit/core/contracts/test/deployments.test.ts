// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved

import { describe, it, expect } from "vitest";
import { parseDeploymentRecord, addressOf } from "../src/deployments.js";

const FIXTURE = JSON.stringify({
  network: "0g-galileo",
  chain_id: 16601,
  rpc_url: "https://evmrpc-testnet.0g.ai",
  explorer: "https://chainscan-galileo.0g.ai",
  contracts: {
    AgentRegistry: {
      address: "0x000000000000000000000000000000000000dEaD",
      tx_hash: "0xabc",
      block_number: 1,
    },
    iNFT_7857: {
      address: "0x00000000000000000000000000000000DeaDBeeF",
      tx_hash: "0xdef",
      block_number: 2,
    },
  },
});

describe("parseDeploymentRecord", () => {
  it("parses a well-formed record", () => {
    const r = parseDeploymentRecord(FIXTURE);
    expect(r.network).toBe("0g-galileo");
    expect(r.chain_id).toBe(16601);
    expect(Object.keys(r.contracts)).toEqual(["AgentRegistry", "iNFT_7857"]);
  });

  it("rejects records missing 'network'", () => {
    expect(() => parseDeploymentRecord(JSON.stringify({ chain_id: 1, contracts: {} }))).toThrow(
      /missing 'network'/,
    );
  });

  it("rejects records missing 'contracts'", () => {
    expect(() =>
      parseDeploymentRecord(JSON.stringify({ network: "x", chain_id: 1 })),
    ).toThrow(/missing 'contracts'/);
  });
});

describe("addressOf", () => {
  it("returns the address when contract exists", () => {
    const r = parseDeploymentRecord(FIXTURE);
    expect(addressOf(r, "iNFT_7857").toLowerCase()).toBe(
      "0x00000000000000000000000000000000deadbeef",
    );
  });

  it("throws when contract is missing", () => {
    const r = parseDeploymentRecord(FIXTURE);
    expect(() => addressOf(r, "NotInCatalog")).toThrow(/not in deployment record/);
  });
});
