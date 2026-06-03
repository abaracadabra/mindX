# deployer/algorand — Algorand deployment tool (separate · non-EVM)

Algorand is **not** in `chains.xml` and **not** in the EVM deployer's launch cycle. The
AVM is not the EVM: no `window.ethereum`, no EIP-1193, no Solidity bytecode, no
`eth_sendTransaction`. Forcing it into the EVM path would break the doctrine. So it
lives here as a **separate modular tool** with the same *shape* (DEPLOY → LAUNCH →
RETURN) but its own rails:

| | EVM deployer (`../`) | Algorand tool (here) |
|---|---|---|
| identity | wallet public key / bankon.eth | Algorand address (Ed25519) |
| artifact | Foundry `out/*.json` (EVM bytecode) | ARC-56 appspec (`*.arc56.json`, TEAL) |
| transport | `eth_sendTransaction` | `algosdk` → algod |
| DEPLOY | arm: encode create tx | arm: build `ApplicationCreateTxn` from appspec |
| LAUNCH (value) | signature / token | sign + grouped fee payment |
| RETURN | tx hash + contract address | txid + **app id** + app address |
| fee → mindX/AgenticPlace | native / x402 | grouped `PaymentTxn` (atomic with create) |

Why separate is the *right* modularity: the same DEPLOY→LAUNCH→RETURN experience, but
each chain family keeps its own trust path. The EVM dApp never imports `algosdk`; this
tool never touches `window.ethereum`.

## What it deploys

`algorand.xml` is the Algorand "solution" — ARC-56 apps by topic. Seeded with the two
that have been **blocking** (see project memory): **dojo BONA FIDE** (personhood +
reputation = privilege) and **DAIO governance** on Algorand. Build the appspecs first,
then point the manifest at them.

## Usage

```bash
pip install py-algorand-sdk            # algosdk (the only dependency)
export BANKON_ALGO_MNEMONIC="25 words" # non-custodial; or load from the bankon-vault

# list the apps in the manifest
python algorand_deploy.py list

# DEPLOY → LAUNCH → RETURN on LocalNet (default), then TestNet
python algorand_deploy.py deploy dojo-bonafide --network localnet
python algorand_deploy.py deploy dojo-bonafide --network testnet
```

Non-custodial: the signing key comes from a mnemonic you hold (env or the client-side
`../walletcreator` bankon-vault), never from a server. Airgap-first for MainNet.

## Runtime companion

mindX agents can also reach Algorand at runtime via the `vibekit-mcp` MCP server
(`app_deploy`, `app_call`, `create_asset`, …). This tool is the **operator-facing**
deployer for the canonical app set; the MCP server is the **agent-facing** runtime.

Always open source · client-side. (c) BANKON all rights preserved.
