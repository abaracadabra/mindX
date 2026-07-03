// SPDX-License-Identifier: Apache-2.0
//
// Resolver + capability tests. No network: a fake PublicClient supplies
// holdings + acquisition block; chronos time is injected via `now`. Signatures
// are real (viem privateKeyToAccount) so identity proof is exercised end-to-end.

import { describe, expect, it } from "vitest";
import { privateKeyToAccount } from "viem/accounts";
import type { Address, Hex, PublicClient } from "viem";
import {
  buildChallenge,
  can,
  capabilities,
  DESTRUCTIVE,
  memberLevel,
  privilegeToSession,
  resolvePrivilege,
  roleToTier,
  type ChronosTime,
  type OverlordConfig,
} from "../src/index.js";

// anvil dev keys (well-known; test only)
const PK_A = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d" as Hex;
const PK_B = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a" as Hex;
const acctA = privateKeyToAccount(PK_A);
const acctB = privateKeyToAccount(PK_B);

const TOKEN = "0x1111111111111111111111111111111111111111" as Address;

const NOW: ChronosTime = {
  unix: 1_900_000_000,
  consensus: "correlated",
  confidenceMs: 5,
  promisedBy: "chronos.agent",
};

function cfg(over: { overlord: Address; overseers?: Address[] }): OverlordConfig {
  return {
    overlord: over.overlord,
    overseers: over.overseers ?? [],
    domain: "test.local",
    chronosBaseUrl: "",
    holding: {
      chainId: 1,
      token: TOKEN,
      standard: "erc20",
      threshold: 100n,
      levelBands: [
        { level: 1, minAmount: 100n, minTenureSec: 0 },
        { level: 2, minAmount: 100n, minTenureSec: 86_400 * 30 }, // 30d
        { level: 3, minAmount: 1_000n, minTenureSec: 86_400 * 30 },
      ],
    },
  };
}

/** Minimal PublicClient stub: balanceOf + earliest Transfer block + its timestamp. */
function fakeClient(opts: { balance?: bigint; acquiredAt?: number | null }): PublicClient {
  const { balance = 0n, acquiredAt = null } = opts;
  return {
    readContract: async () => balance,
    getLogs: async () => (acquiredAt == null ? [] : [{ blockNumber: 42n }]),
    getBlock: async () => ({ timestamp: BigInt(acquiredAt ?? 0) }),
  } as unknown as PublicClient;
}

async function login(account: typeof acctA, config: OverlordConfig) {
  const message = buildChallenge({ domain: config.domain, address: account.address, scope: "s", nonce: "0xabc", issuedAt: 1 });
  const signature = (await account.signMessage({ message })) as Hex;
  return { message, signature };
}

describe("resolvePrivilege", () => {
  it("overlord address (signature-proven) → overlord", async () => {
    const config = cfg({ overlord: acctA.address });
    const { message, signature } = await login(acctA, config);
    const p = await resolvePrivilege({ claimed: acctA.address, message, signature, config, publicClient: fakeClient({}), now: NOW });
    expect(p.role).toBe("overlord");
    expect(p.privileged).toBe(true);
  });

  it("overseer address (signature-proven) → overseer", async () => {
    const config = cfg({ overlord: acctB.address, overseers: [acctA.address] });
    const { message, signature } = await login(acctA, config);
    const p = await resolvePrivilege({ claimed: acctA.address, message, signature, config, publicClient: fakeClient({}), now: NOW });
    expect(p.role).toBe("overseer");
  });

  it("no qualifying holding → public (not privileged)", async () => {
    const config = cfg({ overlord: acctB.address });
    const { message, signature } = await login(acctA, config);
    const p = await resolvePrivilege({ claimed: acctA.address, message, signature, config, publicClient: fakeClient({ balance: 0n }), now: NOW });
    expect(p.role).toBe("public");
    expect(p.privileged).toBe(false);
  });

  it("holding + tenure → member at the chronos-verified level", async () => {
    const config = cfg({ overlord: acctB.address });
    const { message, signature } = await login(acctA, config);
    // 500 tokens held 40 days → ≥ band-2 (100 + 30d), below band-3 (needs 1000)
    const acquiredAt = NOW.unix - 86_400 * 40;
    const p = await resolvePrivilege({ claimed: acctA.address, message, signature, config, publicClient: fakeClient({ balance: 500n, acquiredAt }), now: NOW });
    expect(p.role).toBe("member");
    expect(p.level).toBe(2);
    expect(p.holding?.tenureSec).toBe(86_400 * 40);
  });

  it("recent holding stays L1 until tenure accrues", async () => {
    const config = cfg({ overlord: acctB.address });
    const { message, signature } = await login(acctA, config);
    const acquiredAt = NOW.unix - 86_400; // 1 day
    const p = await resolvePrivilege({ claimed: acctA.address, message, signature, config, publicClient: fakeClient({ balance: 500n, acquiredAt }), now: NOW });
    expect(p.role).toBe("member");
    expect(p.level).toBe(1);
  });

  it("bad signature (wrong signer) → public, identity unproven", async () => {
    const config = cfg({ overlord: acctA.address });
    // sign with B but claim A
    const message = buildChallenge({ domain: config.domain, address: acctA.address, scope: "s", nonce: "0xabc", issuedAt: 1 });
    const signature = (await acctB.signMessage({ message })) as Hex;
    const p = await resolvePrivilege({ claimed: acctA.address, message, signature, config, publicClient: fakeClient({ balance: 999n }), now: NOW });
    expect(p.role).toBe("public");
    expect(p.reason).toMatch(/identity/);
  });
});

describe("capabilities — overlord/overseer separation", () => {
  it("destructive actions are overlord-only", () => {
    for (const a of DESTRUCTIVE) {
      expect(can("overlord", a)).toBe(true);
      expect(can("overseer", a)).toBe(false);
      expect(can("member", a)).toBe(false);
      expect(can("public", a)).toBe(false);
    }
  });

  it("overseer distributes privilege + moderates", () => {
    expect(can("overseer", "distribute.privilege")).toBe(true);
    expect(can("overseer", "moderate")).toBe(true);
    expect(can("member", "distribute.privilege")).toBe(false);
  });

  it("public sees only public reads", () => {
    expect(can("public", "read.public")).toBe(true);
    expect(can("public", "read.member")).toBe(false);
    expect(capabilities("public")).toEqual(["read.public"]);
  });
});

describe("bridge — overlord model → legacy 6-tier", () => {
  it("maps roles to the right tiers", () => {
    expect(roleToTier("public")).toBe(0);
    expect(roleToTier("member")).toBe(2);
    expect(roleToTier("overseer")).toBe(4);
    expect(roleToTier("overlord")).toBe(5);
  });
  it("privilegeToSession preserves role/level + chronos consensus", () => {
    const s = privilegeToSession(
      { role: "member", level: 3, privileged: true, address: acctA.address, reason: "x", asOf: NOW },
      "room-1",
    );
    expect(s.tier).toBe(2);
    expect(s.tier_name).toBe("person");
    expect(s.level).toBe(3);
    expect(s.privileged).toBe(true);
    expect(s.chronos.consensus).toBe("correlated");
  });
});

describe("memberLevel", () => {
  const bands = [
    { level: 1, minAmount: 100n, minTenureSec: 0 },
    { level: 2, minAmount: 100n, minTenureSec: 100 },
    { level: 3, minAmount: 1000n, minTenureSec: 100 },
  ];
  it("amount + tenure pick the highest qualifying band", () => {
    expect(memberLevel(bands, 100n, 0)).toBe(1);
    expect(memberLevel(bands, 100n, 200)).toBe(2);
    expect(memberLevel(bands, 2000n, 200)).toBe(3);
    expect(memberLevel(bands, 2000n, 50)).toBe(1); // tenure too short for L2/L3
  });
  it("null tenure only satisfies zero-tenure bands", () => {
    expect(memberLevel(bands, 5000n, null)).toBe(1);
  });
});
