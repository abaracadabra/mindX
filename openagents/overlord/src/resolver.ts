// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — resolver.ts
//
// resolvePrivilege() — the heart of the template. A pure function of
// (address, signature, holdings, tenure, chronos) → {role, level}. State is
// event-verified: the signature proves identity; the address-set match yields
// overlord/overseer; otherwise the chronos-verified holding yields member+level
// or, with no qualifying holding, public.

import { getAddress, type Address, type Hex, type PublicClient } from "viem";
import type {
  ChronosTime,
  LevelBand,
  OverlordConfig,
  Privilege,
  Role,
} from "./model.js";
import { proveIdentity } from "./identity.js";
import { acquisitionTimestamp, readHolding } from "./holdings.js";
import { promisedNow, tenureSec } from "./chronos.js";

function addrIn(set: readonly string[], a: string): boolean {
  let x: string;
  try {
    x = getAddress(a);
  } catch {
    return false;
  }
  return set.some((s) => {
    try {
      return getAddress(s) === x;
    } catch {
      return false;
    }
  });
}

/** Highest band the holder qualifies for by amount AND chronos-verified tenure. */
export function memberLevel(
  bands: LevelBand[],
  amount: bigint,
  tenure: number | null,
): number {
  let lvl = 1;
  for (const b of [...bands].sort((a, c) => a.level - c.level)) {
    const tenureOk = tenure == null ? b.minTenureSec === 0 : tenure >= b.minTenureSec;
    if (amount >= b.minAmount && tenureOk) lvl = Math.max(lvl, b.level);
  }
  return lvl;
}

export interface ResolveInput {
  claimed: Address;
  message: string;
  signature: Hex;
  config: OverlordConfig;
  /** viem PublicClient bound to config.holding.chainId. */
  publicClient: PublicClient;
  /** Injectable for tests; otherwise fetched from chronos. */
  now?: ChronosTime;
  fetchImpl?: typeof fetch;
}

export async function resolvePrivilege(input: ResolveInput): Promise<Privilege> {
  const { claimed, message, signature, config, publicClient } = input;
  const now = input.now ?? (await promisedNow(config.chronosBaseUrl, input.fetchImpl));

  // 1. Identity — the signature must prove the claimed public key (EOA or 1271).
  const id = await proveIdentity({ claimed, message, signature, publicClient });
  if (!id.proven) {
    return mk("public", 0, getAddrSafe(claimed), "signature did not prove identity", now);
  }
  const addr = getAddress(claimed);

  // 2. Admin axis — signature-proven address match.
  if (addrIn([config.overlord], addr)) {
    return mk("overlord", 1, addr, "overlord address (signature-proven)", now);
  }
  if (addrIn(config.overseers, addr)) {
    return mk("overseer", 1, addr, "overseer address (signature-proven)", now);
  }

  // 3. Member axis — privilege from holdings + chronos-verified tenure.
  const amount = await readHolding(publicClient, config.holding, addr);
  if (amount < config.holding.threshold) {
    return mk("public", 0, addr, "no qualifying holding", now, {
      amount,
      acquiredAt: null,
      tenureSec: null,
    });
  }
  const acquiredAt = await acquisitionTimestamp(publicClient, config.holding, addr, {
    fromBlock: config.holding.fromBlock,
  });
  const tn = tenureSec(now, acquiredAt);
  const level = memberLevel(config.holding.levelBands, amount, tn);
  return mk("member", level, addr, "qualifying holding (chronos-verified tenure)", now, {
    amount,
    acquiredAt,
    tenureSec: tn,
  });
}

function getAddrSafe(a: string): Address {
  try {
    return getAddress(a);
  } catch {
    return "0x0000000000000000000000000000000000000000" as Address;
  }
}

function mk(
  role: Role,
  level: number,
  address: Address,
  reason: string,
  asOf: ChronosTime,
  holding?: Privilege["holding"],
): Privilege {
  return { role, level, privileged: role !== "public", address, reason, asOf, holding };
}
