# blockchain.agents — minting mindX agents as iNFTs

> Derived from `docs/blockchain/`. A modular, agnostic expansion that turns a
> mindX agent into an on-chain, content-addressed, tradeable **ERC-7857
> Intelligent NFT** — listed on **AgenticPlace** and bound to **BANKON**.

mindX is one consumer of this module, not its only home. Every facet ships as a
composable peer; the pipeline depends on small reusable primitives that already
exist in the repo.

## The class: six sidecar facets

A blockchain agent `<name>` is a *class* expressed as six sibling files in
`agents/blockchain/`:

| Facet | Format | Authored / Derived | Holds |
|---|---|---|---|
| `<name>.agent` | plain-text CAPS (like `agents/solidity.foundry.agent`) | authored | spec: domain, capabilities, knowledge domains, `BLOCKCHAIN` pointer block |
| `<name>.model` | YAML | authored | **logical** model name + task class — never pins a provider; resolved by the self-aware selector |
| `<name>.persona` | JSON (like `agents/boardroom/ceo.persona`) | authored or synthesized | BDI persona (beliefs/desires/traits) |
| `<name>.walletpublickey` | one line | derived | the agent's checksummed EVM identity address (privkey stays in the BANKON vault) |
| `<name>.bankon` | JSON | derived | vault ref + `vaultRef` bytes32 + (v2) ENS subname + bind tx |
| `<name>.iNFT` | JSON | derived | `tokenId`, `contentRoot`, `storageURI`, `tx_hash`, AgenticPlace + registry receipts |

`template.agent` and `template.model` in the same directory are copy-from
starting points (`<name>` placeholders).

## Pipeline

`agents/blockchain/agent_factory.py :: BlockchainAgentFactory.mint_agent(name, dry_run=True, ...)`

```
1. wallet      IDManagerAgent.create_new_wallet("blockchain.agent.<name>")   -> <name>.walletpublickey
2. persona     existing <name>.persona, else synthesized                     -> <name>.persona
3. bundle      {.agent + .model + .persona + wallet} -> bytes
   IPFS        MultiProvider(Lighthouse, nft.storage).upload(...)            -> ipfs://CID
               (no provider configured -> local://<sha256> fallback)
   ── dry_run=True STOPS HERE (no broadcast) ──
4. mint        iNFT_7857.mintAgent(to=minter, contentRoot, storageURI,
               metadataRoot, dims=768, units=1, sealedKeyHash, tokenURI)     -> tokenId
5. list        iNFT_7857.offerOnAgenticPlace(tokenId, marketplace, price, true, 0x0)
6. bankon      iNFT_7857.bindBankonVault(tokenId, vault, vaultRef)           -> <name>.bankon
7. agentId     iNFT_7857.bindAgentId(tokenId, "blockchain.<name>")
8. registry    AgentRegistry.register(agentWallet, agentId, iNFT, capBitmap, storageURI)
9. write-back  all facets + append to data/identity/production_registry.json
```

### Custody (v1)

The iNFT is minted **to the minter EOA** (the operator/treasury holding
`MINTER_ROLE`). iNFT_7857's `offerOnAgenticPlace` / `bindBankonVault` /
`bindAgentId` require the caller to be the token owner, and moving an iNFT needs
a sealed-key oracle handoff — so custody-to-agent transfer is **v2**. The
agent's own wallet remains its cryptographic **identity** (recorded in the
ERC-8004 registry and the `walletpublickey` facet).

## Reused primitives (no new transport)

- `agents/storage/raw_tx.py` — `RawTxClient`, an EIP-1559 sender with **no
  web3.py** dependency.
- `agents/blockchain/abi_codec.py` — keccak selector (same approach as
  `agents/storage/anchor.py`) + `eth_abi.encode` for arguments.
- `agents/core/id_manager_agent.py` — wallet creation, vault-held keys.
- `agents/storage/multi_provider.py` — Lighthouse + nft.storage IPFS.

## Contracts (already in `daio/contracts/`)

| Contract | Function used |
|---|---|
| `inft/iNFT_7857.sol` | `mintAgent`, `offerOnAgenticPlace`, `bindBankonVault`, `bindAgentId` |
| `agentregistry/AgentRegistry.sol` | `register` (ERC-8004) |
| `THOT/marketplace/AgenticPlace.sol` | `offerSkill` (standalone marketplace; optional) |
| `daio/identity/IDNFT.sol` | `mintAgentIdentity` (v2) |
| `daio/governance/AgentFactory.sol` | `createAgent` — `onlyGovernance` (v2) |

Addresses resolve from `data/config/blockchain_addresses.json` (keyed by chain
id), falling back to the forge receipt at
`daio/contracts/deployments/<chainId>/tier1.json`.

## Run it

```bash
# dry-run (offline: wallet + persona + IPFS/local bundle, no broadcast)
curl -s -X POST localhost:8000/blockchain/agentfactory/mint \
  -H 'content-type: application/json' -d '{"name":"oracle-scout","dry_run":true}'

# bring up a local chain + deploy Tier1, then live-mint
bash scripts/blockchain/bootstrap_anvil.sh
curl -s -X POST localhost:8000/blockchain/agentfactory/mint \
  -H 'content-type: application/json' -H "Authorization: Bearer $ADMIN_JWT" \
  -d '{"name":"oracle-scout","dry_run":false,"list_price_wei":1000000000000000}'

# confirm on chain
cast call <inft7857> "ownerOf(uint256)(address)" <tokenId> --rpc-url http://127.0.0.1:8545
cat agents/blockchain/oracle-scout.iNFT
```

The live broadcast (`dry_run:false`) is admin-gated (shadow-overlord JWT),
mirroring `POST /storage/offload`.

## Scope (v1 → v2)

- **v1** (shipped): direct `iNFT_7857.mintAgent` + AgenticPlace listing +
  `bindBankonVault` + ERC-8004 `register`, live on Anvil-1337, sidecar facets,
  dry-run-default route.
- **v2** (deferred): governance-gated `AgentFactory.createAgent`; real ENS
  subname via `BankonSubnameRegistrar`; `IDNFT.mintAgentIdentity` soulbound
  identity; custody transfer to the agent wallet (sealed-key oracle handoff);
  public-testnet / mainnet config; THOT-merkle `contentRoot` semantics.
