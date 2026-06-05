# @openagents/overlord

A portable **overlord / overseer login + privilege hierarchy** for the AgenticPlace / mindX ecosystem. Pure [viem](https://viem.sh) — no RainbowKit/wagmi dependency (RainbowKit-*style* UX only). cypherpunk2048-aligned (see `openagents/w3d/thirdweb_openzepellin_integration_definitive.md`): identity by signature (ECDSA + ERC-1271), holdings via `readContract`, no retained admin keys.

## The model

One privilege axis. **Public** is the floor — *privilege is the access the public does not have.* Each role carries **levels**.

| role | who | how proven | levels | can it destroy? |
|---|---|---|---|---|
| `public` | anyone | — | — | no access |
| `member` | holds the qualifying asset | on-chain holding | `f(amount, tenure)` | no |
| `overseer` | moderator / **distributor of privilege** | signature-proven address | yes | **no** (intentional) |
| `overlord` | admin (`SHADOW_OVERLORD_ADDRESS`) | signature-proven address | yes | yes |

- **Identity = a public wallet key proven by signature** — `recoverMessageAddress` (EOA) or ERC-1271 `isValidSignature` (smart accounts), mirroring `mindx_backend_service/bankon_vault/shadow_overlord.py`.
- **Privilege = on-chain holdings**, and a holding carries a **blockchain timestamp**: `getLogs(Transfer→owner)` → earliest block → `getBlock().timestamp`.
- **Tenure (held-since) is confirmed by chronos** — `GET /v1/oracle/time` (`agents/chronos_agent.py`), which correlates hardware (`cpu.oracle`) + multi-chain block time (`blocktime.oracle`) into a *promised time* with a consensus confidence (`correlated | degraded | drifted | offline`). Tenure is **never** measured with `Date.now()`; when chronos is unreachable the resolution records `consensus: offline`.
- **The overlord/overseer separation is structural**: in `capabilities.ts` the `DESTRUCTIVE` action set is overlord-only at any level — the overseer can distribute privilege and moderate but **cannot destroy system integrity**, and the overlord is not needed for day-to-day privilege distribution.

The resolved `{role, level}` is a **pure function** of `(address, signature, holdings, tenure, chronos)` — event-verified state.

## Usage (core, server- or client-side)

```ts
import { resolvePrivilege, can, buildChallenge, type OverlordConfig } from "@openagents/overlord";

const config: OverlordConfig = {
  overlord: SHADOW_OVERLORD_ADDRESS,
  overseers: [OVERSEER_ADDRESS],
  domain: "mindx.pythai.net",
  chronosBaseUrl: "https://mindx.pythai.net",
  holding: {
    chainId: 1, token: BANKON_TOKEN, standard: "erc20", threshold: 1n,
    levelBands: [
      { level: 1, minAmount: 1n,      minTenureSec: 0 },
      { level: 2, minAmount: 1n,      minTenureSec: 86_400 * 30 },   // 30d tenure
      { level: 3, minAmount: 1_000n,  minTenureSec: 86_400 * 90 },
    ],
  },
};

// message = the buildChallenge(...) the wallet signed; publicClient bound to holding.chainId
const priv = await resolvePrivilege({ claimed, message, signature, config, publicClient });
if (priv.privileged && can(priv.role, "act.member")) { /* ... */ }
```

## Usage (React reference view)

```tsx
import { OverlordLogin } from "@openagents/overlord/view";

<OverlordLogin config={config} rpcUrl={RPC} verifyUrl="/auth/verify"
  onResolved={(p) => console.log(p.role, p.level, p.privileged)} />
```

The view resolves privilege **client-side for preview**; the **authoritative** resolution + session belongs to the server (`verifyUrl`) — both run the same `resolvePrivilege`, so UX and policy never disagree.

## Configuration

Nothing is hardcoded. Set per deployment:
- `overlord` = the canonical `SHADOW_OVERLORD_ADDRESS`; `overseers` = your overseer address set.
- `holding` = the qualifying contract (`chainId`, `token`, `standard`), `threshold` (the public/privileged boundary), and `levelBands` (amount × chronos-verified tenure → level).
- `chronosBaseUrl` = where `GET /v1/oracle/time` lives (empty ⇒ same-origin).

## Integrating with boardroom-service / dojo-service

These services keep their challenge → verify → JWT → middleware flow; only the
tier-resolution shape changes. The `bridge` maps the overlord model onto their
existing six-tier (`observer..sovereign`) shape so adoption is incremental:

```ts
import { resolvePrivilege, privilegeToSession } from "@openagents/overlord";
// in /auth/verify, after verifyMessage succeeds:
const priv = await resolvePrivilege({ claimed, message, signature, config, publicClient });
const session = privilegeToSession(priv, scope); // { tier, tier_name, role, level, privileged, chronos }
// issueSession(session.address, session.tier, ...) — unchanged downstream
```

`public→0`, `member→2`, `overseer→4`, `overlord→5`; invitee(1)/seat(3) stay
invite-/room-scoped on top. The dojo `BonaFideOracle` (Algorand ASA personhood)
and the EVM-holdings axis here are **different sources of privilege**; replacing
the ASA oracle with `readHolding(...)` is a deliberate product change (config +
a viem client in the service) left as a reviewed follow-up — the package
provides `readHolding` / `acquisitionTimestamp` for it.

## Files

- `src/model.ts` — roles, levels, config, `Privilege`.
- `src/identity.ts` — challenge + signature proof (ECDSA + ERC-1271).
- `src/holdings.ts` — `balanceOf` + acquisition block timestamp (pure viem).
- `src/chronos.ts` — promised-time client + tenure.
- `src/resolver.ts` — `resolvePrivilege` (the pure function).
- `src/capabilities.ts` — `can(role, action)` + the overlord-only `DESTRUCTIVE` set.
- `view/OverlordLogin.tsx` — thin React reference login.

Tests: `npm test` (vitest; real signatures, fake chain client).

License: Apache-2.0.
