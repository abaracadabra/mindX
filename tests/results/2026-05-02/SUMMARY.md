# Test Results — 2026-05-02 (ETHGlobal Open Agents submission)

> Captured at end of session, 2026-05-02 UTC. All seven test suites green.
> Re-run any of these with the commands in the "Reproduce" column.
> Companion: [`runtime_proof.txt`](runtime_proof.txt) — captured live cryptographic proof of the Cabinet signing-oracle invariant.

---

## Aggregate

**Total: 164 tests passing across 7 suites · 0 failures · 0 skips · 80% line coverage on Cabinet code**

| Suite | Tests | Result | Time | Output file |
|---|---|---|---|---|
| Cabinet pytest (Python) | 25 | ✅ pass | 3.13s | [`cabinet_pytest.txt`](cabinet_pytest.txt) |
| Conclave Python protocol | 9 | ✅ pass | 0.16s | [`conclave_python.txt`](conclave_python.txt) |
| Conclave Solidity (Foundry) | 10 | ✅ pass | 30.5ms | [`conclave_solidity.txt`](conclave_solidity.txt) |
| iNFT-7857 (Foundry) | 57 | ✅ pass | 80.5ms | [`inft_7857_forge.txt`](inft_7857_forge.txt) |
| BANKON v1 ENS (Foundry) | 29 | ✅ pass | 324.9ms | [`bankon_forge.txt`](bankon_forge.txt) |
| THOT v1 (Foundry) | 14 | ✅ pass | 9.7ms | [`thot_forge.txt`](thot_forge.txt) |
| AgentRegistry ERC-8004 (Foundry) | 20 | ✅ pass | 9.6ms | [`agentregistry_forge.txt`](agentregistry_forge.txt) |

---

## Coverage

### Python — Cabinet code (80% line · CI-gated at 75%)

```
Module                                                    Stmts   Miss  Cover
─────────────────────────────────────────────────────────────────────────────
mindx_backend_service/bankon_vault/admin_routes.py          108     10    89%
mindx_backend_service/bankon_vault/cabinet.py               160     35    73%
mindx_backend_service/bankon_vault/shadow_overlord.py       169     30    80%
mindx_backend_service/bankon_vault/sign_routes.py            39      3    88%
─────────────────────────────────────────────────────────────────────────────
TOTAL                                                       476     78    80%
```

Full report: [`cabinet_coverage.txt`](cabinet_coverage.txt). Reproduce: `pytest --cov=mindx_backend_service.bankon_vault.{shadow_overlord,cabinet,admin_routes,sign_routes} --cov-report=term-missing`. CI gate: 75% minimum.

### Solidity — all 6 submission contracts

```
Contract                                                Line %  Func %
─────────────────────────────────────────────────────────────────────
daio/contracts/inft/iNFT_7857.sol                       95.65%  91.67%
daio/contracts/ens/v1/BankonSubnameRegistrar.sol        94.85%  94.74%
daio/contracts/THOT/v1/THOT.sol                         93.75%  85.71%
daio/contracts/agentregistry/AgentRegistry.sol          89.86%  76.92%
openagents/conclave/contracts/src/Conclave.sol          84.00%  81.82%
openagents/conclave/contracts/src/ConclaveBond.sol      54.29%  66.67%
```

Full report: [`solidity_coverage.txt`](solidity_coverage.txt). Reproduce: `forge coverage --report summary` per profile.

The four daio contracts all clear 89% line. Conclave.sol clears 84%. ConclaveBond at 54% is an honest test gap (the on-chain slashing recovery paths are exercised only on the AXL-mesh side); Slither found 0 findings on this contract.

---

## Reproduce all of these in 60 seconds

```bash
cd /home/hacker/mindX

# Python tests (Cabinet — 20)
.mindx_env/bin/python -m pytest \
    tests/bankon_vault/test_shadow_overlord.py \
    tests/bankon_vault/test_cabinet.py \
    -c /dev/null -v

# Conclave Python protocol tests (9)
cd openagents/conclave
.mindx_env/bin/python -m pytest tests/ -c /dev/null -v

# Conclave Solidity (10)
cd contracts && forge test
cd ../..

# All four daio Solidity profiles (120 total)
cd ../daio/contracts
FOUNDRY_PROFILE=inft           forge test  # 57
FOUNDRY_PROFILE=bankon         forge test  # 29
FOUNDRY_PROFILE=thot           forge test  # 14
FOUNDRY_PROFILE=agentregistry  forge test  # 20
```

---

## Per-suite headlines

### Cabinet pytest (25/25 — `cabinet_pytest.txt`)

The headline tests for the BANKON Vault shadow-overlord admin tier:
- `test_sign_as_agent_returns_valid_sig_no_pk_leak` — proves the vault signs on the agent's behalf without leaking the private key
- `test_addresses_match_pk_derivation` — proves every public address in the registry derives from the matching vault-stored pk
- `test_release_key_returns_pk_with_correct_confirm` — emergency-release path returns plaintext pk; derives back to the same address
- `test_release_key_rejects_wrong_confirm` — confirms the literal-string confirm gate prevents accidental release
- `test_provision_creates_8_wallets_and_registry_block` — 16 vault entries (8 pk + 8 addr) per cabinet
- `test_replay_rejected`, `test_wrong_signer_rejected`, `test_scope_mismatch_rejected`, `test_params_tamper_rejected` — replay/tamper guards

### Conclave Python (9/9 — `conclave_python.txt`)

Protocol-level tests for the Cabinet-pattern P2P mesh:
- `test_envelope_signing_round_trip`, `test_canonical_cbor_deterministic` — ed25519 envelope crypto
- `test_quorum_passes_at_threshold`, `test_trade_secret_treats_abstain_as_nay` — voting math
- `test_seq_replay_rejected` — anti-replay in session FSM

### Conclave Solidity (10/10 — `conclave_solidity.txt`)

On-chain anchoring + slashing tests:
- `test_register_and_seated`, `test_register_rejects_duplicate` — membership gating
- `test_record_resolution_with_quorum`, `test_double_anchor_reverts` — anchor mechanics
- `test_slash_unseats_and_burns_bond` — punishment path

### iNFT-7857 (57/57 — `inft_7857_forge.txt`)

ERC-7857 sealed-key transfer + re-encryption tests:
- 54 unit tests + 3 fuzz tests @ 256 runs each
- Headline: `test_TransferWithSealedKey_succeeds_andRotatesKey`, `test_TransferWithSealedKey_revertsWhenCallerNotApproved`

### BANKON v1 (29/29 — `bankon_forge.txt`)

ENS NameWrapper subname registrar — including 5 fuzz tests:
- Soulbound transfer rules, ERC-8004 bundled mint, EIP-712 voucher, length-tier pricing, multi-chain x402

### THOT v1 (14/14 — `thot_forge.txt`)

Pillar-gated memory anchor primitive — anchors `(rootHash, chatID, parentRootHash)` triples on chain.

### AgentRegistry (20/20 — `agentregistry_forge.txt`)

ERC-8004 identity + capability layer:
- Schema fields: owner, agentId, linkedINFT_7857, capabilityBitmap, attestationURI, attestorCount, soulbound
- Tests cover all combinations of soulbound / mutability / attestation replay / capability querying

---

## Cryptographic proof (live transcript)

See [`runtime_proof.txt`](runtime_proof.txt). Captured live during this session. Demonstrates:

1. Two distinct wallets — shadow-overlord ≠ CFO.
2. Server response body is shown verbatim (335 chars). String-search for `private_key`, `private_key_hex`, and `"pk"` all return `False`.
3. Independent `Account.recover_message` from the (message, signature) pair recovers the CFO's published address byte-for-byte.

Conclusion: the signature was produced by the CFO's secp256k1 private key. That key lives only in the BANKON Vault. The response carries no field through which it could leak.

---

## Re-derive the proof yourself

Anyone can verify the cryptographic claim externally with `eth_account` only — no mindX, no BANKON Vault required:

```python
from eth_account import Account
from eth_account.messages import encode_defunct

msg = "PYTHAI CFO endorses 2026-Q2 budget plan"
sig = "0xb35e7dc1899c7cdf655be659ff4e6c55f1818894e5c7cb0e2790b411008abb3f610c960255d97d9632d0d9f43191483df099817acbfa6d3cd38df7327e72c3d91b"
expected = "0x2CF6D5D4C0422cEe39435155FA1C4c36b7CeDc95"

assert Account.recover_message(encode_defunct(text=msg), signature=sig) == expected
print("VERIFIED")
```

If this assertion holds, the property holds.
