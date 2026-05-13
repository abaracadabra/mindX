# `daio/contracts/script/` — deployment scripts

Forge `Script` contracts. Each `*.s.sol` here is callable with
`forge script <path> --rpc-url … --broadcast`.

| Script | Purpose |
|---|---|
| `Counter.s.sol` | Stock Foundry counter example |
| `DeployTier1.s.sol` | Tier-1 ecosystem rollout (legacy) |
| `DeployTHOTCommitment.s.sol` | THOT cryptographic commitment registry + wires it into an existing iNFT_7857 |

---

## `DeployTHOTCommitment.s.sol` — Sepolia → mainnet runbook

### Pre-flight

1. iNFT_7857 already deployed on the target chain — capture its address
   as `$INFT_7857_ADDR`.
2. BANKON identity gate (the multisig or EOA that authorizes issuers)
   known and funded — capture as `$BANKON_GATE`.
3. THOT admin multisig (3-of-5 in production, holds CENSURA_ROLE) known
   — capture as `$THOT_ADMIN_MULTISIG`. On Sepolia a single dev key is
   acceptable for the soak.
4. The broadcast key (the `--private-key` Forge will use) holds
   `DEFAULT_ADMIN_ROLE` on the target `iNFT_7857`. On mainnet, this is
   the multisig itself signing.

### Deploy to Sepolia (chain-id 11155111)

```bash
export BANKON_GATE=0x...
export THOT_ADMIN_MULTISIG=0x...
export INFT_7857_ADDR=0x...
export SEPOLIA_RPC=https://eth-sepolia.g.alchemy.com/v2/<key>
export ETHERSCAN_API_KEY=...

FOUNDRY_PROFILE=thot_commitment forge script script/DeployTHOTCommitment.s.sol \
  --rpc-url $SEPOLIA_RPC \
  --broadcast \
  --verify \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  --private-key $DEPLOYER_KEY
```

Console output captures the registry address. Save it to
`deployments/sepolia.json`.

### 7–14 day Sepolia soak — operator checklist

The point of the soak is to exercise the full intended flow at least
once for each load-bearing path before mainnet.

1. **Authorize an issuer** from the BANKON gate:
   ```bash
   cast send $REGISTRY "authorizeIssuer(address)" $ISSUER_ADDR \
     --rpc-url $SEPOLIA_RPC --private-key $BANKON_GATE_KEY
   ```

2. **Generate canonical root** off-chain via the Python codec:
   ```bash
   cd daio/contracts/THOT/python
   python validate.py
   # Captures: parent root, ternary head, 4 prefix proofs.
   ```

3. **Issue THOT4096** on-chain:
   ```bash
   cast send $REGISTRY \
     "issueTHOT4096(bytes32,bytes32,uint256,string,string)" \
     $PARENT_ROOT $TERNARY_HEAD 255 \
     "ipfs://<payload-cid>" "ipfs://<metadata-cid>" \
     --rpc-url $SEPOLIA_RPC --private-key $ISSUER_KEY
   ```

4. **Mint an iNFT** + **attach the root**:
   ```bash
   # 1. mintAgent (existing iNFT_7857 flow)
   cast send $INFT_7857 "mintAgent(...)" ... --rpc-url $SEPOLIA_RPC

   # 2. attachThotRoot (MINTER_ROLE)
   cast send $INFT_7857 "attachThotRoot(uint256,bytes32)" \
     $TOKEN_ID $PARENT_ROOT \
     --rpc-url $SEPOLIA_RPC --private-key $MINTER_KEY
   ```

5. **Verify the binding** by reading state:
   ```bash
   cast call $INFT_7857 "thotRootOf(uint256)(bytes32)" $TOKEN_ID
   # Must return PARENT_ROOT
   ```

6. **Register a prefix** (THOT1024 or THOT768) using the Python proof
   output. Take the `prefix_leaves`, `co_witness_leaves`, `right_siblings`
   arrays from `python validate.py` and feed them into:
   ```bash
   cast send $REGISTRY \
     "registerPrefix(bytes32,uint16,bytes32,bytes32[],bytes32[],bytes32[])" \
     ... --rpc-url $SEPOLIA_RPC
   ```

7. **Exercise the revoke gate** (load-bearing security property):
   ```bash
   # As CENSURA_ROLE:
   cast send $REGISTRY "revoke(bytes32,string)" \
     $PARENT_ROOT "test revocation" \
     --rpc-url $SEPOLIA_RPC --private-key $CENSURA_KEY

   # Now attempt a transfer — must revert with ThotRootRevoked.
   cast send $INFT_7857 "transferWithSealedKey(...)" ... \
     --rpc-url $SEPOLIA_RPC
   ```

8. **Record gas costs** in `SOAK_REPORT.md` and compare to mainnet
   estimates via `forge snapshot`.

### Mainnet promotion criteria

Promote to mainnet only after **all six** of these hold:

- [ ] 7+ successful end-to-end transactions on Sepolia
- [ ] 0 unexpected reverts
- [ ] One revocation exercised end-to-end on Sepolia
- [ ] One prefix registration verified on Sepolia (Python ↔ Solidity parity)
- [ ] Multisig is 3-of-5 on a known set of keys
- [ ] A second human reviews deployed bytecode against verified source
      via `forge inspect bytecode` vs Etherscan

### Mainnet deploy

Identical command as Sepolia, but with mainnet RPC and `--private-key`
sourced from the multisig (Safe / Gnosis flow). After confirmation:

```bash
# Document in deployments/mainnet.json
echo "{\"chainId\": 1, \"registry\": \"0x...\", \"deployedAt\": $(date +%s)}" \
  > deployments/mainnet.json
```

Transfer admin roles to the multisig immediately if not already there.

### Disable / detach (incident response)

If the registry needs to be detached from `iNFT_7857` in a hurry — for
example, a wrong gate was wired in or a critical issue is discovered —
the admin can call:

```bash
cast send $INFT_7857 "setCommitmentRegistry(address)" 0x000...000 \
  --rpc-url $RPC --private-key $ADMIN_KEY
```

This sets the registry to `address(0)`. Existing `thotRootOf` entries
are preserved (for off-chain audit) but `attachThotRoot` becomes a hard
revert and the transfer revoke-gate becomes a no-op.

---

## `DeployTier1.s.sol`

(Existing — see contract docstring.)

---

## Verify a freshly-deployed contract

```bash
forge verify-contract \
  --chain-id $CHAIN_ID \
  --etherscan-api-key $ETHERSCAN_API_KEY \
  $CONTRACT_ADDRESS \
  contracts/THOT/commitment/THOTCommitmentRegistry.sol:THOTCommitmentRegistry
```

Or run `script/verify_tier1.sh` for the Tier-1 set.
