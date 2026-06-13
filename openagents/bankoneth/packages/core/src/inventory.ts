// SPDX-License-Identifier: Apache-2.0
//
// Inventory helpers — thin wrapper over @ensdomains/ensjs subgraph reads.
//
// Powers the <b-my-names> dashboard and the "subnames of X" listing in
// <b-records-editor>. Talks to the canonical ENS subgraph by default;
// host your own indexer later by passing a different `subgraphUrl`.

import { createEnsPublicClient } from "@ensdomains/ensjs";
import type { Address, PublicClient } from "viem";

import { normalize } from "./normalize";

/** A name owned (or controlled) by an address. */
export interface OwnedName {
  /** Full ENS name, e.g. "alice.eth" or "alice.bankon.eth". */
  name: string;
  /** Wrapped-NFT owner address (zero when not wrapped). */
  owner: Address;
  /** Unix-seconds expiry (0 = no expiry / not minted). */
  expiry: number;
  /** Burned fuse bitmask (0 for legacy unwrapped names). */
  fuses: number;
  /** True if the name is currently wrapped in NameWrapper. */
  wrapped: boolean;
}

/** A subname under a parent. Subset of OwnedName plus the parent name. */
export interface SubnameEntry extends OwnedName {
  /** Parent name, e.g. "bankon.eth". */
  parent: string;
}

/** A single historical event on a name. */
export interface NameHistoryEvent {
  /** Event kind: "registered" | "renewed" | "transferred" | "set-resolver" | "set-addr" | "set-text" | ... */
  kind: string;
  /** Block number (string for jsonification stability). */
  blockNumber: string;
  /** Transaction hash. */
  txHash: string;
  /** Optional event-specific payload (e.g. text key + value). */
  data?: Record<string, unknown>;
}

interface ClientArgs {
  /** Existing viem PublicClient — its chain determines the subgraph used. */
  client: PublicClient;
}

/** Wrap a viem PublicClient into an ensjs-augmented client (caches per chain). */
function ensClient(client: PublicClient) {
  // @ensdomains/ensjs's createEnsPublicClient is a thin wrapper that adds the
  // ENS action namespace to a viem-style client. It dispatches subgraph reads
  // to the canonical ENS hosted subgraph per chain id by default.
  // Cast through `any` because ensjs's PublicClient type is structurally
  // identical to viem's but exported under its own type alias.
  return createEnsPublicClient({
    chain:     client.chain,
    transport: client.transport,
  } as any);
}

/** Names owned by an address (wrapped + unwrapped, sorted by expiry desc). */
export async function getNamesForAddress(args: ClientArgs & { address: Address; pageSize?: number }): Promise<OwnedName[]> {
  const c = ensClient(args.client);
  const res = await c.getNamesForAddress({
    address: args.address,
    pageSize: args.pageSize ?? 50,
  });

  return res.map(n => ({
    name:    n.name ?? "",
    owner:   (n.owner ?? "0x0000000000000000000000000000000000000000") as Address,
    expiry:  n.expiryDate ? Math.floor(new Date(n.expiryDate.date).getTime() / 1000) : 0,
    fuses:   (n.fuses as unknown as number) ?? 0,
    wrapped: Boolean(n.wrappedOwner),
  }));
}

/** Subnames issued under a parent (e.g. all `*.bankon.eth`). */
export async function getSubnames(args: ClientArgs & { name: string; pageSize?: number }): Promise<SubnameEntry[]> {
  const parent = normalize(args.name);
  const c = ensClient(args.client);
  const res = await c.getSubnames({
    name: parent,
    pageSize: args.pageSize ?? 100,
  });

  return res.map(n => ({
    parent,
    name:    n.name ?? "",
    owner:   (n.owner ?? "0x0000000000000000000000000000000000000000") as Address,
    expiry:  n.expiryDate ? Math.floor(new Date(n.expiryDate.date).getTime() / 1000) : 0,
    fuses:   (n.fuses as unknown as number) ?? 0,
    wrapped: Boolean(n.wrappedOwner),
  }));
}

/** Full event history for a single name (best-effort — depends on subgraph coverage). */
export async function getNameHistory(args: ClientArgs & { name: string }): Promise<NameHistoryEvent[]> {
  const name = normalize(args.name);
  const c = ensClient(args.client);
  const res = await c.getNameHistory({ name }).catch(() => null);
  if (!res) return [];

  const events: NameHistoryEvent[] = [];

  // ensjs returns a fielded history object; flatten into our normalized shape.
  for (const [bucket, items] of Object.entries(res)) {
    if (!Array.isArray(items)) continue;
    for (const ev of items as Array<Record<string, unknown>>) {
      events.push({
        kind: bucket,
        blockNumber: String(ev.blockNumber ?? ""),
        txHash:      String(ev.transactionID ?? ev.txHash ?? ""),
        data:        ev,
      });
    }
  }

  // Sort newest first.
  events.sort((a, b) => Number(b.blockNumber || 0) - Number(a.blockNumber || 0));
  return events;
}
