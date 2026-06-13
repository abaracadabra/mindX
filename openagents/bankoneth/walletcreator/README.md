# walletcreator — wallet-creation services

Wallet-creation services for the BANKON allchain, built on the always-open-source
**bankon-vault**. Part of [bankoneth](../); pairs with the [pay2play](../pay2play)
rails (wallet/vault creation is a fee service).

© BANKON — all rights preserved.

## Files

| File | What |
|------|------|
| [`bankon_vault.py`](bankon_vault.py) | the clean, single-file, **always-open-source** private-key vault. AES-256-GCM + HKDF-SHA512, per-entry domain separation. Passphrase **or** participant-key bound (`from_participant_signature`). Folder encryption (`encrypt_folder`). Airgap diagnostic (`airgap_advisory`). |
| [`wallet_creator.py`](wallet_creator.py) | mints wallets across the allchain (one EVM keypair for every EVM chain + Algorand ed25519), vaults the keys, signs (proof of identity). Anvil dev keys for testing. |
| [`CLIENT_VAULT_SPEC.md`](CLIENT_VAULT_SPEC.md) | the **client-side dApp** model: parsec origin, participant-key binding, Tauri + web non-custodial, folder choice, airgap-first, and the DEPLOY → LAUNCH → RETURN deploy flow. |

## The one rule

The bankon-vault handles **private keys**, so it is — and will always be — **open
source**, and in production it runs **client-side** (Tauri / browser) bound to the
participant's own private key. BANKON, and any other host, can never read it. The
value is the service and the contracts, never hidden code.

## Quick use (reference / testing)

```python
from bankon_vault import BankonVault, airgap_advisory
from wallet_creator import WalletCreator

print(airgap_advisory())                 # airgap-first check (the client gates on this)

vault = BankonVault("wallets.vault", "passphrase")     # or .from_participant_signature(path, sig)
wc = WalletCreator(vault)

w = wc.create_allchain_wallet("alice")   # a wallet on every chain on allchain.html
sig = wc.sign_message(w["evm"]["vault_id"], "BANKON pay2play login")   # proof of identity
```

Test with Anvil dev keys (`wc.import_anvil(0)`) or let mindX create a fresh wallet
(`wc.create_evm_wallet()`). The vault file is client-side; secrets never leave it
except to sign.

## Production note

The Python here is the **auditable reference**. The participant-facing flow runs in
the dApp (Tauri + web) — keys are generated on the participant's device, the vault
key is derived from the participant's wallet signature, and the first run is advised
**airgapped** with a "network is connected, do you want to proceed?" gate. See
[`CLIENT_VAULT_SPEC.md`](CLIENT_VAULT_SPEC.md).
