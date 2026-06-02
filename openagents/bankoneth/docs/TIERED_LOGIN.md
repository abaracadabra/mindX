# Tiered login — server-enforced hierarchy of access

The bankon.eth dApp is the single UI to **bankon.eth** and **bankon-vault**, with a
three-tier, holdings-based login. Tiers are resolved **on-chain** and enforced by a
**server gate** so lower tiers never receive the higher pages' markup.

```
admin    owns bankon.eth        → admin console (pricing, fees, hosting, registry, BANKON Vault)
member   holds *.bankon.eth     → member dashboard (names, records, agent identity)
visitor  neither                → storefront (buy a subname); admin/member pages are 302'd away
```

## How a tier is decided (live, never client-supplied)

`backend/tiers.py::resolve_tier(address)`:
- **admin** — `NameWrapper.ownerOf(namehash("bankon.eth")) == address`.
  bankon.eth is wrapped; the owner is read live, so a transfer moves admin automatically.
- **member** — holds any `*.bankon.eth`. No on-chain enumeration exists, so:
  1. explicit/manual label → `NameWrapper.ownerOf(namehash(label.bankon.eth)) == address`
     (registrar-independent; works for any wrapped subname), and/or
  2. auto-discovery → scan `BankonSubnameRegistrar.SubnameRegistered(owner indexed)` logs.
- **visitor** — otherwise.

## The flow

```
POST /auth/challenge {address}            → {nonce, message}
(wallet personal_sign the message — gas-free)
POST /auth/verify {address,nonce,signature,label?}
   → recover signer, assert == address, resolve_tier(signer) ON-CHAIN, issue tier JWT
   → httponly cookie `bankon_session`
```

`backend/gate.py::TierGate` maps each path to a minimum tier (`PUBLIC` / `MEMBER_PREFIXES`
`/member`, `ADMIN_PREFIXES` `/admin`,`/vault/`,`/cabinet`). A request below the required
tier is **302→`/`** (HTML) or **401** (API) *before* the static handler runs — so
`admin.html` / `member.html` are never delivered to non-holders. The bankon-vault routes
are additionally self-protected by `require_admin_tier` (defense in depth).

> True hiding requires the server. On-chain `AccessControl` independently enforces every
> *write*, so even a forged client cannot administer without the granted roles
> (see `ADMIN_ROLES.md`).

## Pages (packages/web/)

| Page | Tier | What |
|---|---|---|
| `index.html` | visitor | storefront: name search, quote, **buy** (any-denomination, `PAYMENTS.md`), resolve |
| `member.html` | member | names (event-scan + manual prove), records (`setText`/`addr`), agent identity |
| `admin.html` | admin | pricing/fees/hosting/registry setters + **BANKON Vault** (credentials/cabinet/sign) |
| `bankoneth.html`, `inft.html` | public | developer explorer + iNFT |

Styling: `styled.css` (BANKON "Sovereign Identity Infrastructure" brand) + `webgl-bg.js`
(optional shader background, graceful fallback) + `gfx/` art. Shared logic: `app-common.js`
(connect + `/auth` + routing) and `bankon-forms.js`.

Backend-less consumers (parsec-view, react) use `bankon-forms` `resolveTier()` for the same
client-side routing (cosmetic; writes still gated on-chain).

## Run

```bash
pip install -r vault_module/requirements-vault.txt fastapi uvicorn web3 eth-account pyjwt
export BANKON_GATE_SECRET=$(openssl rand -hex 24)
export BANKON_GATE_RPC=$MAINNET_RPC          # tier reads hit ENS NameWrapper
uvicorn backend.app:app --port 8800          # from openagents/bankoneth/
# open http://localhost:8800/
```
