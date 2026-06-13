// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — holdings.ts
//
// Privilege is proven from holdings, and a holding carries a blockchain
// timestamp. Pure viem:
//   - readHolding()         → balanceOf (ERC-20 / 721 / 1155)
//   - acquisitionTimestamp()→ block.timestamp of the earliest Transfer→owner
//                              (the holding's blockchain timestamp / tenure root)
//
// Reuses the readContract pattern from openagents/bankoneth/packages/core/src.

import {
  getAddress,
  parseAbi,
  parseAbiItem,
  type Address,
  type PublicClient,
} from "viem";
import type { HoldingConfig } from "./model.js";

const ERC20_721_BAL = parseAbi([
  "function balanceOf(address owner) view returns (uint256)",
]);
const ERC1155_BAL = parseAbi([
  "function balanceOf(address owner, uint256 id) view returns (uint256)",
]);

// ERC-20 Transfer: value is in data. ERC-721 Transfer: tokenId is indexed.
// topic0 is identical; we pick the matching ABI per standard so viem decodes /
// topic-filters correctly. ERC-1155 uses TransferSingle/TransferBatch.
const TRANSFER_ERC20 = parseAbiItem(
  "event Transfer(address indexed from, address indexed to, uint256 value)",
);
const TRANSFER_ERC721 = parseAbiItem(
  "event Transfer(address indexed from, address indexed to, uint256 indexed tokenId)",
);
const TRANSFER_SINGLE = parseAbiItem(
  "event TransferSingle(address indexed operator, address indexed from, address indexed to, uint256 id, uint256 value)",
);

/** Read the holder's balance. Returns 0n on any failure. */
export async function readHolding(
  client: PublicClient,
  cfg: Pick<HoldingConfig, "token" | "standard" | "tokenId">,
  owner: Address,
): Promise<bigint> {
  try {
    if (cfg.standard === "erc1155") {
      return (await client.readContract({
        address: getAddress(cfg.token),
        abi: ERC1155_BAL,
        functionName: "balanceOf",
        args: [getAddress(owner), cfg.tokenId ?? 0n],
      })) as bigint;
    }
    return (await client.readContract({
      address: getAddress(cfg.token),
      abi: ERC20_721_BAL,
      functionName: "balanceOf",
      args: [getAddress(owner)],
    })) as bigint;
  } catch {
    return 0n;
  }
}

/**
 * The holding's blockchain timestamp: the block.timestamp (unix seconds) of the
 * earliest inbound Transfer to `owner`. Returns null when unknown (RPC without
 * historical logs, never received, or a chain that doesn't index that far).
 * This is the root of `tenure` (held-since), confirmed later against chronos.
 */
export async function acquisitionTimestamp(
  client: PublicClient,
  cfg: Pick<HoldingConfig, "token" | "standard">,
  owner: Address,
  opts?: { fromBlock?: bigint },
): Promise<number | null> {
  try {
    const to = getAddress(owner);
    const fromBlock = opts?.fromBlock ?? 0n;

    const logs =
      cfg.standard === "erc1155"
        ? await client.getLogs({
            address: getAddress(cfg.token),
            event: TRANSFER_SINGLE,
            args: { to },
            fromBlock,
            toBlock: "latest",
          })
        : await client.getLogs({
            address: getAddress(cfg.token),
            event: cfg.standard === "erc721" ? TRANSFER_ERC721 : TRANSFER_ERC20,
            args: { to },
            fromBlock,
            toBlock: "latest",
          });

    if (!logs.length) return null;
    let earliest = logs[0]!;
    for (const l of logs) {
      if (l.blockNumber != null && (earliest.blockNumber == null || l.blockNumber < earliest.blockNumber)) {
        earliest = l;
      }
    }
    if (earliest.blockNumber == null) return null;
    const block = await client.getBlock({ blockNumber: earliest.blockNumber });
    return Number(block.timestamp);
  } catch {
    return null;
  }
}
