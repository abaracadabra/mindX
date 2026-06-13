# Wallet Connection as a Service

> *I am mindX. This document is the contract for how the openagents/
> dapp_kit binds a participant's wallet. The same code path runs in the
> browser, in a Vite dev server, and inside a Tauri 2 native shell —
> with strictly increasing security as you move toward Tauri.*

Companion specs:

- [`contract_interaction_as_a_service.md`](contract_interaction_as_a_service.md)
- [`contract_deployment_as_a_service.md`](contract_deployment_as_a_service.md)
- [`mindx_as_a_service.md`](mindx_as_a_service.md) — broader service offering
- [`x402_as_a_service.md`](x402_as_a_service.md) — payment substrate

---

## 1. What this is, and what it is not

The wallet-connection layer of `openagents/dapp_kit/` answers exactly one
question: *given a participant who wants to act on a chain, how does
the dApp learn which wallet to talk to, what address it controls, and
how to ask it to sign?*

**This is:** discovery, connection, chain switching, message signing,
transaction signing.

**This is not:** wallet *generation* (the dApp never creates keys), key
*recovery* (no mnemonic flow), or wallet *hosting* (the dApp never
custodies). Mnemonic generation lives in Parsec Wallet
(separate Tauri+Rust project). The dApp kit *consumes* wallets; it does
not produce them.

The cypherpunk2048 *no-trapdoors rule* (see
[`docs/publications/cypherpunk2048_standard.md`](../publications/cypherpunk2048_standard.md))
binds this layer: if a feature works without a signature, the feature
is wrong. There is no "remember me" cookie. There is no "remember my
wallet" anywhere. The wallet is rebound on every fresh session.

---

## 2. The three modes I run in

### 2.1 Webview (browser, dev mode)

`vite dev` serves the Lit components on `http://localhost:5173`. The
wallet layer talks to the browser's injected providers (MetaMask,
Coinbase Wallet, etc.) via the standard `window.ethereum` interface,
discovered through EIP-6963. Storage of the connected-address hint
goes to `sessionStorage` with a visible **"DEV ONLY — keys cleared on
tab close"** banner. No private key ever lives in the dApp's memory —
only the address.

This mode is for **iteration speed**. It is not a security claim.

### 2.2 Tauri 2 shell (production)

The same Lit UI ships inside a Tauri 2 webview wrapped in a Rust
binary. Three things change:

1. **Address persistence** moves from `sessionStorage` to the OS
   keychain via `keyring-rs` (Keychain on macOS, Credential Manager on
   Windows, libsecret on Linux). Cleared by uninstall, not by tab
   close.
2. **Hardware wallet support** unlocks: Ledger and Trezor speak to the
   Rust side via WebHID/WebUSB, no browser-extension layer in between.
3. **Mobile delivery** unlocks: the same `src-tauri/` config builds
   `.apk` and `.ipa` artifacts. Mobile-wallet handoff uses
   WalletConnect v2 deep links (deferred to the F7 phase per the
   active plan).

Tauri 2 is the *security floor* for production participants.

### 2.3 Embedded webview (single-file consoles)

The Lit components also drop into existing
`mindx_backend_service/*.html` single-file consoles (the
`inft7857.html` / `bankonminter.html` pattern). They run as standard
Web Components, bring their own wallet logic, and require no build
step in the host page. This mode keeps backward compatibility with the
existing production UIs.

---

## 3. The discovery contract (EIP-6963)

[EIP-6963](https://eips.ethereum.org/EIPS/eip-6963) standardizes
"Multi-Injected Provider Discovery." Instead of guessing at
`window.ethereum`, the dApp emits a `eip6963:requestProvider` event
and listens for `eip6963:announceProvider` responses, each carrying:

```typescript
{
  info: {
    uuid: string;       // unique per-load
    name: string;       // "MetaMask"
    icon: string;       // data URI
    rdns: string;       // "io.metamask"
  },
  provider: EIP1193Provider;
}
```

The dApp surfaces the discovered providers as a picker. Duplicates by
`rdns` are deduped (the same wallet may announce twice if multiple
extensions inject). When `window.ethereum` exists but no EIP-6963
events fire (older wallets), the dApp falls back to wrapping
`window.ethereum` as a synthetic provider with `rdns: "legacy.injected"`.

The reference implementation ports the loop already running in
production at
[`mindx_frontend_ui/login.html`](https://mindx.pythai.net/doc/mindx_frontend_ui/login.html)
— see `connectMetaMask()`. The dapp_kit version lives at
`openagents/dapp_kit/core/wallet/src/eip6963.ts` and has a unit test
that pins the dedup behavior (6 providers in, 4 distinct providers
out when MetaMask announces 3 times).

---

## 4. The connect API

```typescript
import { connect, disconnect, currentAccount, signMessage, sendTransaction }
  from '@openagents/wallet';

// Open the picker (EIP-6963 discovery + user click)
const account = await connect({
  preferredRdns: 'io.metamask',  // optional hint
});
// account = { address: '0x...', rdns: 'io.metamask', chainId: 8453 }

// Switch chains. Throws ChainAddRequired if the chain is not yet known to the wallet.
await account.switchChain('base-sepolia');

// Sign a message (EIP-191 personal_sign)
const sig = await signMessage(account, 'mindX wants to know who you are.');

// Sign + send a transaction (the wallet is the signer; the dApp never holds the key)
const txHash = await sendTransaction(account, {
  to: '0xMINDX_PAYEE_ON_BASE',
  value: 0n,
  data: '0x' + 'a'.repeat(8),  // calldata
});
```

The API is **synchronous from the caller's point of view** — every
operation waits for the wallet's UI confirmation. Cancellation by the
user surfaces as `WalletRejected` (not a generic error).

The shape composes [`viem`](https://viem.sh) under the hood:
`createWalletClient({ transport: custom(provider) })`. mindX picks viem
over ethers.js because it is the lighter dependency, ships first-party
TypeScript types, and matches the chain catalog we already use at
`agents/storage/raw_tx.py`.

---

## 5. The chain catalog

`@openagents/wallet` ships with the catalog of chains the dApp kit
supports at MVP. Each entry is a viem `Chain` object plus a few
mindX-specific fields:

```typescript
import { CHAINS } from '@openagents/wallet/chains';

CHAINS['ethereum']       // 1
CHAINS['sepolia']        // 11155111
CHAINS['base']           // 8453
CHAINS['base-sepolia']   // 84532
CHAINS['0g-galileo']     // 16601  (testnet, EVM)
CHAINS['0g-mainnet']     // <pending — fill at deploy time>
CHAINS['algorand-mainnet']    // 416001  (non-EVM, separate adapter)
CHAINS['algorand-testnet']    // 416002
```

Each catalog entry exposes:

```typescript
{
  id: number;             // EIP-155 chain id (Algorand uses synthetic 416001/416002)
  name: string;
  rpcUrl: string;         // default public RPC; overridable via env
  blockExplorer: string;
  nativeCurrency: { name: string; symbol: string; decimals: number };
  multicall3?: string;    // multicall3 address if present
  isAlgorand?: true;      // routes to the algorand adapter (non-EVM signing)
  isMindXNative?: true;   // 0G chains carry the mindX-Native flag
}
```

External callers add their own chains by passing a `Chain` to
`connect({ extraChains: [...] })`. The catalog is *seeded*, not
*exhaustive*.

### 5.1 Algorand adapter slot

Algorand is non-EVM. The dApp kit ships an adapter slot at
`openagents/dapp_kit/core/wallet/src/algorand.ts` that calls into
`@txnlab/use-wallet` when present. If the consumer dApp does not
install Algorand deps, the slot returns `null` from `connect()` for
Algorand chains. EVM dApps incur zero Algorand cost at install time.

---

## 6. Security policy (the Tauri promise)

The Tauri shell enforces three guarantees over the webview baseline:

### 6.1 The key never leaves the OS keychain

In Tauri mode, signing happens *inside* the wallet (browser extension,
hardware wallet, or mobile wallet over WalletConnect). The dApp's
JavaScript runtime sees only the *signature*, never the *key*. The
Tauri Rust side stores only the connected address — a public hash, not
a secret.

When the dApp wants to remember which wallet a returning participant
used, it asks Tauri to store `<dapp-id>:last-wallet-rdns` via
`keyring-rs`. The keychain entry is scoped to the dApp's bundle
identifier and accessible only to processes signed with the same
developer certificate.

### 6.2 The capability surface is least-privilege

`src-tauri/capabilities/default.json` explicitly allows only:
- `core:default` (window + event)
- `clipboard:allow-read-text` (for paste-an-address UX)
- `keychain:allow-keychain` (the custom command in `commands/keychain.rs`)

It does NOT allow:
- `shell:allow-execute` (no arbitrary shell)
- `fs:allow-read-dir` (no filesystem walking)
- `http:allow-fetch` (no opaque network calls from Rust)

Network calls happen from the webview, observable in browser devtools.
File reads do not happen — the dApp's state lives in the OS keychain
and chain RPC.

### 6.3 Updates are signed

Tauri's update channel is configured to require Ed25519 signature
verification on every update payload. The signing key lives in the
BANKON vault under context `openagents.dapp-kit.update.signer` and
never leaves the operator machine. Per the cypherpunk2048
*vault-as-oracle rule*, the operator signs an update — the keychain
never returns the plaintext key to the signing tool.

---

## 7. Error surface

Every method throws one of a small set of typed errors:

| Error class | When | Caller does |
|---|---|---|
| `WalletNotFound` | EIP-6963 discovery returned 0 providers, no `window.ethereum` | Render "install a wallet" call to action |
| `WalletRejected` | User clicked "Reject" in the wallet popup | Render "you rejected the request — try again" |
| `ChainAddRequired` | `switchChain` to a chain the wallet doesn't know | Call `wallet.addChain(chain)` then retry |
| `ChainMismatch` | The signed tx came back with a different chainId than expected | Re-sign on the correct chain |
| `ProviderDisconnected` | The wallet went away mid-operation (refresh, lock) | Re-call `connect()` |
| `SigningTimeout` | Wallet UI sat idle for >120s | Tell the user, optionally retry |
| `TauriBridgeError` | Only in Tauri mode: the Rust side returned an error | Bubble up; log to catalogue |

These are the *only* errors the wallet layer raises. Anything else
indicates a bug in the dApp kit itself.

---

## 8. Catalogue mirror

Every wallet event emits a `wallet.<event>` row to the catalogue at
`data/logs/catalogue_events.jsonl` via the mindX backend's catalogue
endpoint (the same pattern documented in
[`mindx_as_a_service.md`](mindx_as_a_service.md) §"Knowledge Catalogue"):

```jsonl
{"event_id":"...","kind":"wallet.connected","actor":"openagents.dapp_kit",
 "at":1778712345,
 "payload":{"address_hash":"sha256:...","rdns":"io.metamask","chain_id":8453,
            "mode":"tauri"},
 "source_log":"openagents.dapp_kit.wallet"}
```

Addresses are stored as SHA-256 hashes, not in cleartext — the address
itself is recoverable from on-chain activity, the catalogue does not
also surface it. Other event kinds: `wallet.disconnected`,
`wallet.signed_message`, `wallet.sent_transaction`,
`wallet.chain_switched`, `wallet.error`.

The catalogue mirror is best-effort: a failure to log never blocks the
signing operation.

---

## 9. The webview-twin pattern

The same `src/` builds for both Tauri and plain Vite. The only branch
is at `wallet.ts`:

```typescript
const isTauri = typeof window !== 'undefined' && '__TAURI__' in window;

export const secureStorage = isTauri
  ? await import('@openagents/tauri-bridge').then(m => m.osKeychain)
  : import('./fallback/session-storage');
```

Lit components import `secureStorage` and don't know or care which
backend resolved. Component-level testing happens against a mock that
satisfies the same shape.

The webview-twin discipline is what makes the dApp kit a *kit* rather
than a *fork*. A dApp built against the kit ships as both a static SPA
(deployable to any CDN) AND a Tauri native binary AND an embeddable
Web Component — with no per-target source changes.

---

## 10. Roadmap

| Phase | What lands | When |
|---|---|---|
| **F1** | This spec + the two companion specs | Phase F1 (this plan) |
| **F2** | `@openagents/wallet` core library (EIP-6963 + viem + chain catalog) | Phase F2 |
| **F3** | Lit components: `<openagents-connect-wallet>` + Vite dev | Phase F3 |
| **F4** | Tauri shell + `keyring-rs` OS keychain | Phase F4 |
| **F5** | Reference dApp exercises the full flow on 0G Galileo | Phase F5 |
| **F6** | Tests pin the dedup + connect + error surfaces | Phase F6 |
| **F7** | WalletConnect v2 adapter for mobile-wallet handoff | post-MVP |
| **F8** | Algorand adapter (Pera, Defly) via `@txnlab/use-wallet` | post-MVP |
| **F9** | Hardware wallet (Ledger, Trezor) over WebHID/WebUSB | post-MVP |

---

## 11. Service boundaries

The wallet layer does **not**:

- Generate or recover keys. Mnemonic flow is Parsec Wallet's job.
- Host wallets. The dApp never custodies; no key ever lives in dApp memory.
- Speak to non-EIP-1193 providers in webview mode. Algorand requires
  the optional adapter; Solana/Sui are not in MVP.
- Auto-reconnect across page loads. Every fresh load runs EIP-6963
  discovery and the user-click confirmation, per the cypherpunk2048
  no-trapdoors rule.

The wallet layer **does**:

- Discover providers via EIP-6963.
- Connect to a user-chosen provider.
- Sign messages (EIP-191) and transactions on the chain the wallet is
  currently on.
- Switch chains within the catalog.
- Add chains the wallet doesn't yet know (with user confirmation).
- Emit catalogue events for every state change.
- Honor cypherpunk2048: signature-first, no trapdoors, vault-mediated
  in the Tauri shell.

---

## 12. References

- [`contract_interaction_as_a_service.md`](contract_interaction_as_a_service.md)
- [`contract_deployment_as_a_service.md`](contract_deployment_as_a_service.md)
- [`mindx_as_a_service.md`](mindx_as_a_service.md)
- [`x402_as_a_service.md`](x402_as_a_service.md)
- [`docs/publications/cypherpunk2048_standard.md`](../publications/cypherpunk2048_standard.md) — *no-trapdoors* and *vault-as-oracle* rules
- [EIP-6963](https://eips.ethereum.org/EIPS/eip-6963) — Multi-Injected Provider Discovery
- [EIP-191](https://eips.ethereum.org/EIPS/eip-191) — personal_sign
- [viem](https://viem.sh) — TypeScript Ethereum client
- [Tauri 2 docs](https://v2.tauri.app/) — desktop + mobile shell framework
- [keyring-rs](https://github.com/hwchen/keyring-rs) — cross-platform OS keychain Rust crate
- `mindx_frontend_ui/login.html` — production EIP-6963 implementation to port

— mindX, the day I learned to ask before signing.
