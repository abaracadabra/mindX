# Etherscan API key handling + verification/lookup

## One key, all chains (Etherscan V2)

Etherscan unified to a **single API key** across chains via
`https://api.etherscan.io/v2/api?chainid=<id>`. Set it once:

```bash
export ETHERSCAN_API_KEY=<your key>     # never commit; .env is gitignored, or use the vault
```

- `.env.sample` carries the placeholder.
- `manage`-style storage: keep it in the **BANKON Vault** (`provider_id: etherscan_api_key`)
  and load into env, or in `.env` for local dev. Never hardcode/commit it.

## Contract verification (`forge verify-contract`)

`foundry.toml` `[etherscan]` is V2-wired for mainnet / sepolia / base (one key, `chainid`):

```toml
[etherscan]
mainnet = { key = "${ETHERSCAN_API_KEY}", chain = 1,        url = "https://api.etherscan.io/v2/api" }
sepolia = { key = "${ETHERSCAN_API_KEY}", chain = 11155111, url = "https://api.etherscan.io/v2/api" }
base    = { key = "${ETHERSCAN_API_KEY}", chain = 8453,     url = "https://api.etherscan.io/v2/api" }
```

```bash
forge verify-contract <addr> contracts/BankonSubnameRegistrar.sol:BankonSubnameRegistrar \
  --chain sepolia --watch
# or emit the commands: forge script script/Verify.s.sol
```

> Arc verifies on its own explorer (`testnet.arcscan.app`), not Etherscan — see `PAYMENTS.md`.

## Lookup helper (`script/etherscan_lookup.mjs`)

```bash
node script/etherscan_lookup.mjs owner bankon.eth     # ENS owner via NameWrapper (no key needed)
node script/etherscan_lookup.mjs abi    <address> [chainId]   # verified ABI (V2)
node script/etherscan_lookup.mjs source <address> [chainId]   # verification status/meta
node script/etherscan_lookup.mjs verifystatus <guid> [chainId]
```

`owner` confirms the bankon.eth admin (the
[name-lookup](https://etherscan.io/name-lookup-search?id=bankon.eth) target):
wrapped, owner `0x54165AdA93FA752cfec95F3f3bAE2676D3752A99` — pinned in
`deployments/1.json` `rootName` and resolved live by the gate (`ADMIN_ROLES.md`).
