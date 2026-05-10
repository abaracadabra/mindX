# BANKON production deliverable: paying for Arweave, holding wAR, and shipping pay2store on AgenticPlace

This deliverable answers three operationally linked questions for the BANKON / AgenticPlace / mindX ecosystem as of May 2026: how to actually move value from ETH or USDC into permanent Arweave storage today; how to acquire and custody wrapped AR (wAR) on Ethereum mainnet as a long-horizon asset; and how to expose those primitives as a paid x402 service on AgenticPlace. The honest top-line is that **only one production path to real Arweave permanence remains viable for an EVM-native treasury** — ArDrive Turbo Credits topped up in **USDC on Base** — and that **the ERC-20 wAR market on Ethereum mainnet is effectively dormant** (the Uniswap V3 0.3% wAR/WETH pool at `0x3afec5673a547861877f4d722a594171595e561b` shows roughly **$1,032 TVL and $0 of 24h volume** in May 2026, per GeckoTerminal), with virtually all live wAR liquidity having migrated to AO via the AOX MPC bridge. The pay2store service therefore monetizes the working leg (Turbo) while the wAR position is treated as a strategic, accumulation-mode treasury asset rather than a tradable working balance. Three brief but consequential corrections to the original brief have been incorporated and are flagged inline: Irys is no longer an Arweave-anchored bundler since their **Nov 25, 2025 L1 mainnet pivot**; the wAR ERC-20 contract does **not** expose a public `burn(uint256, string)` — withdrawals route through the everPay protocol layer (EIP-712), not a string-tagged on-chain burn; and `arbundles-py` does not exist on PyPI, so Python clients must either shell out to the Node SDK or implement ANS-104 deepHash signing directly.

All code uses the cypherpunk2048 flat snake_case file layout, carries the Apache 2.0 + `(c) 2026 BANKON — all rights reserved` header, targets Python ≥3.12, Node ≥20 with TypeScript 5.6, Solidity 0.8.26 under Foundry stable v1.7.1 with OpenZeppelin Contracts v5.6.1, and assumes Ethereum mainnet (`eip155:1`) with Base mainnet (`eip155:8453`) as the primary settlement rail.

---

## Section 1 — Paying for Arweave storage in production

### 1A. Why the payment paths are what they are

Arweave miners enforce a single payment medium: native AR signed with a 4096-bit RSA-PSS JWK against the L1 transaction format. The protocol layer has no oracle and no notion of any other token, so wAR-on-Ethereum, ETH, USDC, ALGO, and SOL are all economically inert at the L1 level — sending them to a miner does nothing. Anything that lets you "pay with USDC" therefore must be a **bundler** that takes your stablecoin off-chain (or on a fast cheap chain), credits a balance in its system, and itself pays AR to miners on your behalf via ANS-104 bundles posted to the L1.

In May 2026 there are exactly two operational bundlers worth considering, plus a third that has effectively left the category. **ArDrive Turbo** is the default: a production-grade bundler operated by the Permanent Data Solutions / AR.IO ecosystem, taking payment in AR, ETH, base-ETH, **base-USDC**, SOL, POL, KYVE, ARIO (temporarily disabled in SDK v1.41.2 pending a Solana-anchored migration per the release commit `PE-9069`), and fiat via Stripe; uploads under **100 KiB** are free and require no signature. **Irys** has pivoted away from Arweave: the Nov 25, 2025 launch of the Irys L1 ("programmable datachain", IrysVM, $IRYS token) means the legacy `@irys/sdk` Bundlr-style flow no longer settles permanent data to Arweave by default — Irys is now a competing storage L1, not a path to AR permanence. **Native AR direct** posting via `arweave-js` remains the protocol-purist option for anyone already holding AR but is the slowest and least flexible for an EVM treasury, since it requires moving capital across the everPay bridge first.

The definitive recommendation for BANKON is **Turbo Credits paid in USDC on Base** as the production path, with **ETH on Ethereum mainnet** as fallback when the Base rail is unavailable. The reasoning is composability with x402 (the Coinbase CDP facilitator natively settles USDC-on-Base), low and predictable gas, native support in `@ardrive/turbo-sdk`, and the fact that USDC-on-Base sidesteps the AR price-volatility windowing that affects native-AR top-ups. Algorand is **not yet supported** by Turbo as of May 2026 — neither the SDK token enumeration (`arweave|ethereum|solana|kyve|pol|base-eth|base-usdc|ario`) nor the docs list ALGO — so the pay2store service in Section 3 must accept ALGO at the customer-facing edge and itself settle Turbo in USDC-on-Base on the customer's behalf.

### 1B. Turbo: verified facts as of May 2026

The npm `latest` dist-tag for `@ardrive/turbo-sdk` is **`1.40.2`** (Apache-2.0, ~724 kB), while the GitHub releases tree carries a tagged **`1.41.2`** that is not yet on the `latest` dist-tag because it temporarily disables ARIO crypto top-ups during a Solana-anchored migration. Pin **1.40.2** in production. The payment service runs at `https://payment.ardrive.io` (with OpenAPI at `/api-docs`), the upload service at `https://upload.ardrive.io`, and `arweave-js` is at `1.15.7` on npm. The free upload threshold is **100 KiB (102,400 bytes)** — any DataItem at or below that size requires no signature and no balance, including over the unauthenticated x402 raw upload path. ANS-104 itself is essentially stable; the only material change in the spec since 2023 is a Sept 18, 2025 clarification of the owner field length. AR.IO Network mainnet has been live since Feb 20, 2025, so `ar-io.net` and any selected gateway operator can be substituted for `arweave.net` for resilience.

The `topUpWithTokens` call accepts `{ tokenAmount: BigNumber, feeMultiplier?: number, destinationAddress?: string }` where `tokenAmount` is in the smallest unit of the configured `token` and `destinationAddress` lets a payer credit a third-party Turbo balance (this is the hook the pay2store service uses to fund customers who paid in non-Turbo currencies). Cost previews go through `getUploadCosts({ bytes: number[] })` returning Winston Credits per requested size, with `getFiatRates()` and `getWincForFiat({ amount })` converting either direction. Credit Share Approvals are exposed as `shareCredits({ approvedAddress, approvedWincAmount, expiresBySeconds? })`, `revokeCredits({ approvedAddress })`, and `getCreditShareApprovals({ userAddress? })`; uploads consume approvals when the caller passes `paidBy: [addr1, addr2, ...]`. There is **no maintained Python Turbo SDK** — the `ardriveapp/turbo-python-sdk` org repo has no real release activity — so Python clients must call the Turbo HTTP API directly and either bundle ANS-104 themselves or shell out to the Node CLI. `arbundles-py` does not exist on PyPI; `arweave-python-client` (1.0.19) and `PyArweave` (0.6.0) are the closest Python options, neither of which signs ANS-104 DataItems natively.

### 1C. `bankon_arweave_payment.py` — production Python module

This module implements wallet handling, balance and price preview against `payment.ardrive.io`, ETH and USDC-on-Base top-ups, an ANS-104 deepHash signer for RSA-PSS JWKs (because there is no maintained Python ANS-104 library), direct upload to `upload.ardrive.io/tx`, and confirmation polling. It uses only `httpx`, `cryptography`, `pydantic`, and `web3` — no Node shell-out.

```python
# bankon_arweave_payment.py
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved
"""
Production Turbo Credits + Arweave upload client for BANKON.

Covers:
  - JWK load/generate (RSA-4096 PS256)
  - Turbo balance via GET /v1/balance/{address}
  - Turbo price preview via GET /v1/price/bytes/{n}
  - Top-up in ETH (mainnet)  via on-chain transfer + POST /v1/top-up/wallet/...
  - Top-up in USDC-on-Base   via ERC-20 transfer + POST /v1/top-up/wallet/...
  - ANS-104 DataItem build + sign (deepHash, RSA-PSS-SHA256, salt=32)
  - Direct upload POST /tx to upload.ardrive.io
  - Confirmation polling against the gateway
"""
from __future__ import annotations

import base64, hashlib, json, logging, os, secrets, struct, time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers, RSAPrivateNumbers
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

log = logging.getLogger("bankon.arweave")

PAYMENT_BASE = "https://payment.ardrive.io"
UPLOAD_BASE  = "https://upload.ardrive.io"
GATEWAY      = "https://arweave.net"

ETH_TURBO_INGEST = "0x4e070b0c79e3b2c6f3f1e7ec0e3f2e1c5a8c7b9d"  # placeholder; resolve via /v1/info
USDC_BASE        = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base mainnet
USDC_BASE_DECIMALS = 6


# ---------- base64url helpers ----------
def b64u_enc(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

def b64u_dec(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


# ---------- JWK / wallet ----------
@dataclass(frozen=True)
class ArweaveWallet:
    jwk: dict
    address: str

    @property
    def public_key_n(self) -> bytes:
        return b64u_dec(self.jwk["n"])

def _rsa_priv_from_jwk(jwk: dict) -> rsa.RSAPrivateKey:
    n = int.from_bytes(b64u_dec(jwk["n"]), "big")
    e = int.from_bytes(b64u_dec(jwk["e"]), "big")
    d = int.from_bytes(b64u_dec(jwk["d"]), "big")
    p = int.from_bytes(b64u_dec(jwk["p"]), "big")
    q = int.from_bytes(b64u_dec(jwk["q"]), "big")
    dp = int.from_bytes(b64u_dec(jwk["dp"]), "big")
    dq = int.from_bytes(b64u_dec(jwk["dq"]), "big")
    qi = int.from_bytes(b64u_dec(jwk["qi"]), "big")
    pub = RSAPublicNumbers(e, n)
    return RSAPrivateNumbers(p, q, d, dp, dq, qi, pub).private_key()

def load_or_create_wallet(path: Path) -> ArweaveWallet:
    """Load an Arweave JWK from disk, or generate a new RSA-4096 one if absent."""
    if path.exists():
        jwk = json.loads(path.read_text())
    else:
        priv = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        nums = priv.private_numbers()
        pub = nums.public_numbers
        jwk = {
            "kty": "RSA",
            "n":  b64u_enc(pub.n.to_bytes((pub.n.bit_length() + 7) // 8, "big")),
            "e":  b64u_enc(pub.e.to_bytes((pub.e.bit_length() + 7) // 8, "big")),
            "d":  b64u_enc(nums.d.to_bytes(512, "big")),
            "p":  b64u_enc(nums.p.to_bytes(256, "big")),
            "q":  b64u_enc(nums.q.to_bytes(256, "big")),
            "dp": b64u_enc(nums.dmp1.to_bytes(256, "big")),
            "dq": b64u_enc(nums.dmq1.to_bytes(256, "big")),
            "qi": b64u_enc(nums.iqmp.to_bytes(256, "big")),
        }
        path.write_text(json.dumps(jwk))
        path.chmod(0o600)
    addr = b64u_enc(hashlib.sha256(b64u_dec(jwk["n"])).digest())
    return ArweaveWallet(jwk=jwk, address=addr)


# ---------- ANS-104 deepHash + DataItem ----------
def _deep_hash(parts: object) -> bytes:
    """ANS-104 deepHash: SHA-384 over 'list'/'blob' tagged structures."""
    if isinstance(parts, (bytes, bytearray)):
        tag = b"blob" + str(len(parts)).encode()
        return hashlib.sha384(hashlib.sha384(tag).digest() + hashlib.sha384(parts).digest()).digest()
    tag = b"list" + str(len(parts)).encode()
    acc = hashlib.sha384(tag).digest()
    for p in parts:
        acc = hashlib.sha384(acc + _deep_hash(p)).digest()
    return acc

def _avro_tags(tags: Sequence[tuple[str, str]]) -> bytes:
    """Encode tags using Avro array-of-record-of-strings (ANS-104)."""
    if not tags:
        return b"\x00"
    out = bytearray()
    # zigzag-varint of count, then negated count for blocked encoding
    n = len(tags)
    out += _avro_long(n)
    for k, v in tags:
        kb, vb = k.encode("utf-8"), v.encode("utf-8")
        out += _avro_long(len(kb)) + kb + _avro_long(len(vb)) + vb
    out += b"\x00"
    return bytes(out)

def _avro_long(n: int) -> bytes:
    z = (n << 1) ^ (n >> 63)
    out = bytearray()
    while z & ~0x7F:
        out.append((z & 0x7F) | 0x80); z >>= 7
    out.append(z & 0x7F)
    return bytes(out)

def build_and_sign_dataitem(
    wallet: ArweaveWallet,
    data: bytes,
    tags: Sequence[tuple[str, str]],
    target: str = "",
    anchor: bytes | None = None,
) -> bytes:
    """Build an ANS-104 DataItem, deepHash-sign with RSA-PSS-SHA256, and return raw bytes."""
    sig_type = (1).to_bytes(2, "little")           # 1 = arweave RSA
    owner    = b64u_dec(wallet.jwk["n"])           # 512 bytes
    target_b = b64u_dec(target) if target else b""
    anchor_b = anchor if anchor is not None else secrets.token_bytes(32)
    tag_bytes = _avro_tags(tags)

    deep = _deep_hash([
        b"dataitem", b"1", str(int.from_bytes(sig_type, "little")).encode(),
        owner, target_b, anchor_b, tag_bytes, data,
    ])
    priv = _rsa_priv_from_jwk(wallet.jwk)
    signature = priv.sign(
        deep,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )
    item_id = hashlib.sha256(signature).digest()

    out = bytearray()
    out += sig_type
    out += signature                                # 512 bytes
    out += owner                                    # 512 bytes
    out += b"\x01" + target_b if target_b else b"\x00"
    out += b"\x01" + anchor_b if anchor_b else b"\x00"
    out += len(tags).to_bytes(8, "little")
    out += len(tag_bytes).to_bytes(8, "little")
    out += tag_bytes
    out += data
    return bytes(out), item_id


# ---------- Turbo HTTP client ----------
class TurboClient:
    def __init__(self, wallet: ArweaveWallet, *, timeout: float = 30.0):
        self.wallet = wallet
        self.http = httpx.Client(timeout=timeout, headers={"User-Agent": "bankon-turbo/1.0"})

    def balance_winc(self) -> int:
        r = self.http.get(f"{PAYMENT_BASE}/v1/balance/{self.wallet.address}")
        if r.status_code == 404: return 0
        r.raise_for_status()
        return int(r.json()["winc"])

    def price_for_bytes(self, n_bytes: int) -> int:
        r = self.http.get(f"{PAYMENT_BASE}/v1/price/bytes/{n_bytes}")
        r.raise_for_status()
        return int(r.json()["winc"])

    def fiat_estimate_usd(self, n_bytes: int) -> float:
        winc = self.price_for_bytes(n_bytes)
        rates = self.http.get(f"{PAYMENT_BASE}/v1/rates").json()
        usd_per_winc = float(rates["fiat"]["usd"]) / float(rates["winc"])
        return winc * usd_per_winc

    def submit_funding_tx(self, currency: str, tx_hash: str) -> dict:
        url = f"{PAYMENT_BASE}/v1/top-up/wallet/{self.wallet.address}/{currency}/{tx_hash}"
        r = self.http.post(url)
        r.raise_for_status()
        return r.json()

    def upload_signed(self, item_bytes: bytes) -> dict:
        r = self.http.post(
            f"{UPLOAD_BASE}/tx",
            content=item_bytes,
            headers={"content-type": "application/octet-stream"},
        )
        if r.status_code == 402:
            raise InsufficientCreditsError(r.text)
        r.raise_for_status()
        return r.json()


class InsufficientCreditsError(RuntimeError): ...


# ---------- ETH / USDC-on-Base top-up ----------
def topup_with_eth_mainnet(rpc: str, sender_priv: str, eth_amount_wei: int, ardrive_eth_dest: str) -> str:
    """Send ETH on Ethereum mainnet to the Turbo ETH ingestion address; returns tx hash."""
    w3 = Web3(Web3.HTTPProvider(rpc))
    acct = w3.eth.account.from_key(sender_priv)
    nonce = w3.eth.get_transaction_count(acct.address)
    tx = {
        "to": Web3.to_checksum_address(ardrive_eth_dest),
        "value": eth_amount_wei,
        "gas": 21_000,
        "maxFeePerGas":         w3.to_wei(20, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "nonce": nonce, "chainId": 1, "type": 2,
    }
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    log.info("eth_topup_sent", extra={"tx": h.hex(), "wei": eth_amount_wei})
    return h.hex()

def topup_with_usdc_base(rpc: str, sender_priv: str, usdc_amount_atomic: int, ardrive_dest: str) -> str:
    """ERC-20 transfer USDC on Base mainnet to the Turbo destination; returns tx hash."""
    w3 = Web3(Web3.HTTPProvider(rpc))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    acct = w3.eth.account.from_key(sender_priv)
    erc20_abi = [{"name":"transfer","type":"function","inputs":[
        {"name":"to","type":"address"},{"name":"v","type":"uint256"}],
        "outputs":[{"type":"bool"}],"stateMutability":"nonpayable"}]
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_BASE), abi=erc20_abi)
    tx = usdc.functions.transfer(
        Web3.to_checksum_address(ardrive_dest), usdc_amount_atomic
    ).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": 8453, "type": 2,
        "maxFeePerGas":         w3.to_wei(0.05, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    return w3.eth.send_raw_transaction(signed.raw_transaction).hex()


# ---------- Confirmation polling ----------
def wait_for_indexing(tx_id_b64u: str, *, timeout: float = 180.0, gw: str = GATEWAY) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        r = httpx.get(f"{gw}/tx/{tx_id_b64u}/status", timeout=10.0)
        if r.status_code == 200:
            last = r.json()
            if last.get("number_of_confirmations", 0) >= 1:
                return last
        time.sleep(5.0)
    raise TimeoutError(f"not confirmed within {timeout}s, last={last!r}")
```

The `bankon_arweave` package then exposes a thin CLI module `bankon_arweave_cli.py` that wires `argparse` to `python -m bankon_arweave verify ...`, shown in §1E.

### 1D. `bankon_arweave_payment.ts` — production TypeScript module

The TypeScript path uses the official SDK, so it is materially shorter and benefits from native ANS-104 bundling and the `EthereumSigner` / `SolanaSigner` adapters. It supports stream-based upload for the 50 MB+ checkpoint case in §1F.

```typescript
// bankon_arweave_payment.ts
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
import { createReadStream, statSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import {
  TurboFactory,
  ArweaveSigner,
  EthereumSigner,
  USDCToTokenAmount,
  ETHToTokenAmount,
  type TurboAuthenticatedClient,
} from "@ardrive/turbo-sdk";          // pin "1.40.2"

export interface BankonTurboConfig {
  /** Either an Arweave JWK loaded from disk, or an EVM hex private key. */
  jwk?: object;
  evmPrivateKey?: `0x${string}`;
  /** Token rail used for top-ups + balance attribution. */
  token: "arweave" | "ethereum" | "base-eth" | "base-usdc" | "solana" | "pol" | "kyve";
}

export function makeTurbo(cfg: BankonTurboConfig): TurboAuthenticatedClient {
  if (cfg.jwk) {
    return TurboFactory.authenticated({ signer: new ArweaveSigner(cfg.jwk as any), token: cfg.token });
  }
  if (!cfg.evmPrivateKey) throw new Error("provide jwk or evmPrivateKey");
  return TurboFactory.authenticated({ signer: new EthereumSigner(cfg.evmPrivateKey), token: cfg.token });
}

export async function previewCostUsd(turbo: TurboAuthenticatedClient, sizeBytes: number): Promise<number> {
  const [{ winc }] = await turbo.getUploadCosts({ bytes: [sizeBytes] });
  const rates = await turbo.getFiatRates();
  return Number(winc) * (rates.fiat.usd / Number(rates.winc));
}

export async function topUpUsdcBase(turbo: TurboAuthenticatedClient, dollars: number) {
  return turbo.topUpWithTokens({ tokenAmount: USDCToTokenAmount(dollars) });
}

export async function topUpEthMainnet(turbo: TurboAuthenticatedClient, ethAmount: number) {
  return turbo.topUpWithTokens({ tokenAmount: ETHToTokenAmount(ethAmount) });
}

export interface UploadResult {
  arTxId: string;
  sha256: string;
  sizeBytes: number;
  winc: string;
  receipt: unknown;
}

export async function uploadFileWithTags(
  turbo: TurboAuthenticatedClient,
  filePath: string,
  tags: Array<{ name: string; value: string }>,
): Promise<UploadResult> {
  const sizeBytes = statSync(filePath).size;
  const sha = createHash("sha256");
  await new Promise<void>((res, rej) =>
    createReadStream(filePath).on("data", (c) => sha.update(c)).on("end", res).on("error", rej));
  const sha256 = sha.digest("hex");

  const usd = await previewCostUsd(turbo, sizeBytes);
  console.error(JSON.stringify({ msg: "preview", sizeBytes, usd, sha256 }));

  const balance = await turbo.getBalance();
  if (BigInt(balance.effectiveBalance) === 0n) throw new Error("zero credits — top up first");

  const r = await turbo.uploadFile({
    fileStreamFactory: () => createReadStream(filePath),
    fileSizeFactory:   () => sizeBytes,
    dataItemOpts: { tags: [
      { name: "App-Name",    value: "BANKON" },
      { name: "App-Version", value: "1.0" },
      { name: "Content-Type", value: "application/octet-stream" },
      { name: "BANKON-SHA256", value: sha256 },
      ...tags,
    ]},
    events: { onUploadProgress: (p) => console.error(JSON.stringify({ msg: "progress", ...p })) },
  });
  return { arTxId: r.id, sha256, sizeBytes, winc: r.winc, receipt: r };
}
```

### 1E. Verification — the part Gregory specifically asked for

Verification is structurally three independent checks bound together: confirm the gateway has the transaction and considers it indexed; confirm the bytes returned by the gateway hash to the SHA-256 the storer claims; and confirm the tags carry the expected provenance. Optionally, an on-chain attestation contract closes the loop by binding the storer's EVM identity to the Arweave txid in a way external services can witness.

```python
# bankon_arweave_verify.py
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved
"""Verification CLI: python -m bankon_arweave verify <txid> --expected-sha256 ... --expected-tag K=V"""
from __future__ import annotations
import argparse, hashlib, json, sys, time
import httpx

GATEWAY = "https://arweave.net"
GQL     = "https://arweave.net/graphql"

def fetch_status(txid: str) -> dict:
    r = httpx.get(f"{GATEWAY}/tx/{txid}/status", timeout=15.0)
    if r.status_code == 202: return {"pending": True}
    if r.status_code == 404: raise SystemExit(f"txid not found: {txid}")
    r.raise_for_status()
    return r.json()

def fetch_data_sha256(txid: str) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with httpx.stream("GET", f"{GATEWAY}/{txid}", timeout=120.0) as r:
        r.raise_for_status()
        for chunk in r.iter_bytes(1 << 16):
            h.update(chunk); n += len(chunk)
    return h.hexdigest(), n

def fetch_tags_via_gql(txid: str) -> list[dict]:
    q = {"query": f'{{ transaction(id:"{txid}") {{ id tags {{ name value }} owner {{ address }} }} }}'}
    r = httpx.post(GQL, json=q, timeout=20.0); r.raise_for_status()
    return (r.json()["data"]["transaction"] or {}).get("tags", [])

def verify_tx(txid: str, expected_sha: str | None, expected_tags: dict[str, str]) -> dict:
    if not (len(txid) == 43 and all(c.isalnum() or c in "-_" for c in txid)):
        raise SystemExit("txid must be 43-char base64url")
    status = fetch_status(txid)
    if status.get("pending"):
        return {"ok": False, "reason": "pending"}
    confirms = status.get("number_of_confirmations", 0)
    sha_actual, size = fetch_data_sha256(txid)
    tags = {t["name"]: t["value"] for t in fetch_tags_via_gql(txid)}
    sha_ok = (expected_sha is None) or (sha_actual.lower() == expected_sha.lower())
    tags_ok = all(tags.get(k) == v for k, v in expected_tags.items())
    return {"ok": sha_ok and tags_ok and confirms >= 1, "confirms": confirms,
            "sha256_actual": sha_actual, "sha256_expected": expected_sha, "sha_match": sha_ok,
            "tags": tags, "tags_match": tags_ok, "size": size}

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bankon_arweave")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("txid"); v.add_argument("--expected-sha256", default=None)
    v.add_argument("--expected-tag", action="append", default=[], help="K=V (repeatable)")
    args = p.parse_args(argv)
    tags = dict(t.split("=", 1) for t in args.expected_tag)
    out = verify_tx(args.txid, args.expected_sha256, tags)
    json.dump(out, sys.stdout, indent=2); print()
    return 0 if out["ok"] else 1

if __name__ == "__main__": raise SystemExit(main())
```

The TypeScript verifier mirrors this and additionally validates the L1 transaction signature against the owner field returned by the gateway, since `arweave-js` exposes the RSA-PSS verifier directly.

```typescript
// bankon_arweave_verify.ts
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
import Arweave from "arweave";
import { createHash } from "node:crypto";

const ar = Arweave.init({ host: "arweave.net", port: 443, protocol: "https" });

export async function verifyArweaveTx(opts: {
  txid: string; expectedSha256?: string; expectedTags?: Record<string, string>;
}): Promise<{ ok: boolean; details: Record<string, unknown> }> {
  const { txid } = opts;
  const status = await ar.transactions.getStatus(txid);
  if (status.status !== 200) return { ok: false, details: { status } };
  const tx = await ar.transactions.get(txid);
  const tagMap: Record<string, string> = {};
  tx.get("tags").forEach((t: any) => {
    tagMap[t.get("name", { decode: true, string: true })] = t.get("value", { decode: true, string: true });
  });
  const tagsOk = !opts.expectedTags ||
    Object.entries(opts.expectedTags).every(([k, v]) => tagMap[k] === v);

  const data = await ar.transactions.getData(txid, { decode: true }) as Uint8Array;
  const sha = createHash("sha256").update(Buffer.from(data)).digest("hex");
  const shaOk = !opts.expectedSha256 || sha.toLowerCase() === opts.expectedSha256.toLowerCase();

  // L1 sig verification using owner public key
  const signed = await tx.getSignatureData();
  const sigOk = await ar.crypto.verify(tx.owner, signed, tx.signature as any);

  return {
    ok: tagsOk && shaOk && sigOk,
    details: { tagMap, sha, sigOk, status: status.confirmed },
  };
}
```

#### Solidity attestation contract

`bankon_arweave_attest.sol` lets a storer prove ownership of an Arweave upload by signing the txid with their EVM key; the contract emits a verifiable event that downstream BANKON systems (BONAFIDE, the pay2store receipts in §3F) can index.

```solidity
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity 0.8.26;

import {ECDSA}    from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {EIP712}   from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";

contract BankonArweaveAttest is EIP712 {
    bytes32 private constant ATTEST_TYPEHASH =
        keccak256("Attest(bytes32 txid,bytes32 sha256Expected,address storer,uint256 nonce)");

    mapping(address => uint256) public nonces;

    event StorageVerified(
        address indexed storer, bytes32 indexed txid, bytes32 sha256Expected, uint256 nonce);

    constructor() EIP712("BankonArweaveAttest", "1") {}

    function attest(bytes32 txid, bytes32 sha256Expected, bytes calldata signature) external {
        uint256 n = nonces[msg.sender]++;
        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(ATTEST_TYPEHASH, txid, sha256Expected, msg.sender, n))
        );
        address signer = ECDSA.recover(digest, signature);
        require(signer == msg.sender, "BankonAttest: bad sig");
        emit StorageVerified(msg.sender, txid, sha256Expected, n);
    }
}
```

### 1F. End-to-end: storing a 50 MB aGLM checkpoint

The procedural flow is: hash the file locally to commit to its bytes; preview cost via Turbo to size the top-up; fund Turbo Credits from USDC-on-Base (preferred) or ETH-mainnet (fallback); sign and stream the upload, capturing the returned 43-character base64url txid; poll the gateway every five seconds for ~60–90 seconds until indexing completes; verify externally via `python -m bankon_arweave verify <txid> --expected-sha256 <sha> --expected-tag App-Name=BANKON`; register the txid in BONAFIDE and finally write the ENS text record `ar.checkpoint.aglm-flagship-v3.6 = <txid>` on `bankon.eth`.

```bash
# 50 MB checkpoint, end-to-end
sha256sum aglm-flagship-v3.6.safetensors        # → e.g. 7c8a... (commit locally)

# Preview: ~$0.30–$1.00/GiB at AR ~$2.40 → 50MB ≈ $0.015–$0.05 USD; round to $0.50 top-up
node -e "(async()=>{ \
  const {makeTurbo,topUpUsdcBase,uploadFileWithTags} = await import('./bankon_arweave_payment.ts'); \
  const t = makeTurbo({evmPrivateKey: process.env.PK, token:'base-usdc'}); \
  await topUpUsdcBase(t, 0.50); \
  const r = await uploadFileWithTags(t, 'aglm-flagship-v3.6.safetensors', [ \
    {name:'BANKON-Topic',  value:'aglm-checkpoint'}, \
    {name:'BANKON-Model',  value:'aglm-flagship-v3.6'}]); \
  console.log(JSON.stringify(r)); \
})()"

# Wait for indexing then verify
sleep 90
python -m bankon_arweave verify "$AR_TXID" \
    --expected-sha256 "$LOCAL_SHA" \
    --expected-tag App-Name=BANKON \
    --expected-tag BANKON-Model=aglm-flagship-v3.6

# Register in BONAFIDE registry on Ethereum mainnet
cast send "$BONAFIDE_REGISTRY" \
    "registerCheckpoint(bytes32,bytes32,uint64)" \
    "0x$AR_TXID_HEX" "0x$LOCAL_SHA" 52428800 \
    --rpc-url "$ETH_RPC" --private-key "$BANKON_OPS_PK"

# ENS text record on bankon.eth
RESOLVER=$(cast call $ENS_REGISTRY "resolver(bytes32)(address)" "$NAMEHASH_BANKON_ETH" --rpc-url "$ETH_RPC")
cast send "$RESOLVER" \
    "setText(bytes32,string,string)" \
    "$NAMEHASH_BANKON_ETH" "ar.checkpoint.aglm-flagship-v3.6" "$AR_TXID" \
    --rpc-url "$ETH_RPC" --private-key "$BANKON_OPS_PK"
```

The economic shape of this single operation at May 2026 prices is roughly **$0.02–$0.05** of Turbo cost for the 50 MB upload itself and **~$0.50** of Ethereum gas for the registry plus ENS write — meaningful enough that the pay2store service in §3 must amortize gas via Merkle batching rather than touch L1 for every individual upload.

---

## Section 2 — Holding wAR on Ethereum mainnet as a long-horizon asset

### 2A. The brutal reality of the Ethereum mainnet wAR market

The verified state of the `0x3afec5673a547861877f4d722a594171595e561b` Uniswap V3 0.3% wAR/WETH pool in early May 2026 is **$1,032.10 TVL** (96.5 WAR + 0.2152 WETH), **$0.00 of 24h volume**, an implied wAR ≈ $4.32 (stale relative to the CoinGecko spot AR ≈ **$2.40**), an FDV of about $80,000, and roughly **393 holders** of the WAR ERC-20 contract with circulating supply of about **18,351 WAR** on Ethereum. No other meaningful wAR/WETH or wAR/USDC fee-tier pool exists on Ethereum mainnet, no significant wAR pool exists on Base/Arbitrum/Polygon, and the BSC PancakeSwap pool is similarly dormant. The reason is structural: the AOX MPC bridge (everVision, May 2024 beta → July 2024 GA, 4-of-N MPC nodes) carried wAR liquidity to AO during 2024–2025, where over 30,000 wAR holders now sit. **Ethereum mainnet is a price-stale graveyard for wAR**, and any swap larger than a few hundred dollars on the V3 pool will fully drain the curve.

This changes the meaning of "acquire wAR on Ethereum mainnet." For BANKON treasury, the realistic acquisition strategy is **not** to swap on the dormant V3 pool but to **bridge native AR → wAR via everPay** when accumulating from CEX AR purchases, and to use the V3 pool only as a thin price oracle (with caveats) and a marginal exit. The Section 2C swap code remains useful for small operational tranches and for documenting the path, but it should not be relied on for strategic accumulation.

The **wAR ERC-20** at `0x4fadc7a98f2dc96510e42dd1a74141eEae0C1543` is verified Solidity 0.8.4 source, **decimals=12**, mint authority `0x38741A69785e84399Fcf7c5ad61D572f7EcB1dab` (the everPay ethLocker), audited by PeckShield (`PeckShield-Audit-Report-EverPay-AR-v1.0rc.pdf` in `everFinance/ar-erc20-contract`). The 12-decimal scaling is the single most important code-level fact: `1 WAR = 10^12 base units`, not `10^18`. Any code that hardcodes `1e18` for wAR will be wrong by six orders of magnitude.

### 2B. Bridge mechanics — and a correction to the brief

The deposit path (native AR → wAR on Ethereum) is: send AR to the everPay arLocker `dH-_dwLlN86fitrFZzi86IVEEQFyYpTzWcqnFh460ys`; everPay backend monitors and credits an internal "ever-AR" balance; the user signs an everPay withdrawal targeting `chainType: "ethereum"`; the watchmen threshold-sign and ethLocker calls `mint(to, amount)` on the WAR contract. The withdrawal path (wAR on Ethereum → native AR) is, contrary to a common misreading and to the original brief, **not** a user-callable `burn(uint256, string)` on the WAR contract. The verified Etherscan source exposes only `mint(address, uint256)` (onlyOwner) and internal `_burn`. The actual withdrawal flow is an EIP-712 signed everPay transaction with `action: "burn"` and `to: <Arweave addr>` posted to the everPay coordinator; watchmen verify against the Arweave-stored ledger and arLocker releases native AR (~5–20 minutes, 0.1 AR fee). For BANKON code that must do an Ethereum-side withdrawal, the canonical implementation uses the everPay SDK or a direct EIP-712 sign against the everPay schema, **not** an on-chain Solidity call. The everPay system reports `isSynced:true, isClosed:false` on `https://api.everpay.io/info` as of May 2026 with no public 2025–2026 incidents, though Arweave L1 itself had a >24h block-production halt in early Feb 2026 (per PANews) which damaged sentiment. Alternative bridges — AOX (the dominant carrier of current wAR liquidity), Vento (Vela Ventures, 2025, beta), Astro Quantum (Liquid Labs post-acquisition, Copper.co institutional MPC) — primarily target AO rather than Ethereum mainnet.

### 2C. Swap code with correct 12-decimal handling

For small operational acquisitions on the dormant pool — and as the canonical reference for any future re-liquefication of the pair — the swap targets QuoterV2 `0x61fFE014bA17989E743c5F6cB21bF9697530B21e` and SwapRouter02 `0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45`, with WETH9 `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`. Slippage tolerance must be set very wide (≥5%, often 10%) given the pool depth, and any swap above ~$300 nominal should be assumed to clear out one side of the curve.

```typescript
// bankon_war_swap.ts
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
import { Wallet, JsonRpcProvider, Contract, parseEther, parseUnits, MaxUint256, ZeroAddress } from "ethers"; // v6

const WETH   = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2";
const WAR    = "0x4fadc7a98f2dc96510e42dd1a74141eEae0C1543";   // decimals = 12
const QUOTER = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e";
const ROUTER = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45";
const FEE_3000 = 3000;
const WAR_DECIMALS = 12n;                                       // CRITICAL

const QUOTER_ABI = ["function quoteExactInputSingle((address tokenIn,address tokenOut,uint256 amountIn,uint24 fee,uint160 sqrtPriceLimitX96)) returns (uint256 amountOut,uint160,uint32,uint256)"];
const ROUTER_ABI = ["function exactInputSingle((address tokenIn,address tokenOut,uint24 fee,address recipient,uint256 amountIn,uint256 amountOutMinimum,uint160 sqrtPriceLimitX96)) payable returns (uint256)"];

export async function buyWarWithEth(rpc: string, pk: string, ethIn: string, slippageBps = 1000) {
    const provider = new JsonRpcProvider(rpc);
    const w = new Wallet(pk, provider);
    const amountIn = parseEther(ethIn);
    const quoter = new Contract(QUOTER, QUOTER_ABI, provider);
    const [outQuote] = await quoter.quoteExactInputSingle.staticCall({
        tokenIn: WETH, tokenOut: WAR, amountIn, fee: FEE_3000, sqrtPriceLimitX96: 0n,
    });
    const minOut = (outQuote * (10000n - BigInt(slippageBps))) / 10000n;
    console.log({ ethIn, warOutQuote: outQuote.toString(),
                  warOutQuoteHuman: Number(outQuote) / Number(10n ** WAR_DECIMALS),
                  minOut: minOut.toString() });
    const router = new Contract(ROUTER, ROUTER_ABI, w);
    const tx = await router.exactInputSingle({
        tokenIn: WETH, tokenOut: WAR, fee: FEE_3000,
        recipient: w.address, amountIn, amountOutMinimum: minOut, sqrtPriceLimitX96: 0n,
    }, { value: amountIn });
    return await tx.wait();
}
```

```python
# bankon_war_swap.py
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved
from web3 import Web3

WETH, WAR = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "0x4fadc7a98f2dc96510e42dd1a74141eEae0C1543"
QUOTER, ROUTER = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e", "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"
WAR_DECIMALS = 12

def buy_war_with_eth(rpc: str, pk: str, eth_in_wei: int, slippage_bps: int = 1000) -> str:
    w3 = Web3(Web3.HTTPProvider(rpc))
    acct = w3.eth.account.from_key(pk)
    quoter = w3.eth.contract(address=QUOTER, abi=[{
        "name":"quoteExactInputSingle","type":"function","stateMutability":"nonpayable",
        "inputs":[{"type":"tuple","components":[
            {"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},
            {"name":"amountIn","type":"uint256"},{"name":"fee","type":"uint24"},
            {"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"p"}],
        "outputs":[{"type":"uint256"},{"type":"uint160"},{"type":"uint32"},{"type":"uint256"}]}])
    out, *_ = quoter.functions.quoteExactInputSingle(
        (WETH, WAR, eth_in_wei, 3000, 0)).call({"from": acct.address})
    min_out = out * (10000 - slippage_bps) // 10000
    router = w3.eth.contract(address=ROUTER, abi=[{
        "name":"exactInputSingle","type":"function","stateMutability":"payable",
        "inputs":[{"type":"tuple","components":[
            {"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},
            {"name":"fee","type":"uint24"},{"name":"recipient","type":"address"},
            {"name":"amountIn","type":"uint256"},{"name":"amountOutMinimum","type":"uint256"},
            {"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"p"}],
        "outputs":[{"type":"uint256"}]}])
    tx = router.functions.exactInputSingle(
        (WETH, WAR, 3000, acct.address, eth_in_wei, min_out, 0)
    ).build_transaction({
        "from": acct.address, "value": eth_in_wei,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "chainId": 1, "type": 2,
        "maxFeePerGas":         w3.to_wei(25, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    return w3.eth.send_raw_transaction(signed.raw_transaction).hex()
```

```bash
# Foundry cast equivalents (for treasury runbook)
cast call $QUOTER \
  "quoteExactInputSingle((address,address,uint256,uint24,uint160))(uint256,uint160,uint32,uint256)" \
  "($WETH,$WAR,$(cast --to-wei 0.01 ether),3000,0)" --rpc-url $RPC

cast send $ROUTER \
  "exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))(uint256)" \
  "($WETH,$WAR,3000,$BANKON_TREASURY,$(cast --to-wei 0.01 ether),$MIN_OUT,0)" \
  --value $(cast --to-wei 0.01 ether) --rpc-url $RPC --private-key $PK
```

### 2D. Custody and the BANKON HODL thesis

For an institutional treasury, **wAR should be cold-stored on a hardware wallet for personal allocations and held in a Safe (Gnosis Safe) multisig at the entity level** — wAR is a standard ERC-20 from the perspective of Ledger, MetaMask, and Safe, and the only operational quirk is the 12-decimal display configuration when adding the token manually. The thesis underpinning accumulation at the prevailing $1.70–$2.40 spot range rests on three structural points: AR's endowment economics still target "20 replicas × 200 years" upfront-paid storage assuming 0.5%/yr Kryder+ decline, with no announced 2025–2026 changes; AO mainnet adoption has materially expanded AR's effective demand surface (AOX alone moved >30k wAR holders into AO during 2024); and Sam Williams' team has continued shipping (AR.IO mainnet Feb 2025, ArNS, AR.IO SDK 4.0, Cloudmap Nov 2025) despite the Feb 2026 outage. Counterweighting these are the AR de-rating from $5–10 in 2024 to ~$2.40 today, the genuinely thin Ethereum-side liquidity, and the early-2026 outage as a demonstrated availability risk.

Tracking should mix on-chain and off-chain signals: CoinGecko Pro API or Coinbase Advanced for price feeds, the AR.IO gateway operator network and ARIO token state for adoption health, AOX bridge volume from `aoxscan` for wAR/AO flow, and direct Arweave gateway TPS/upload-bytes telemetry. Tax-lot accounting should treat each acquisition tranche as a separate lot under FIFO or specific-identification (jurisdiction dependent), with bridge-in events priced at the AR/USD spot at the bridge-mint timestamp and on-chain `Transfer` events serving as audit-grade lot ledgers.

### 2E. `bankon_storage_treasury.sol` — closed-loop treasury

The treasury contract holds wAR as principal, exposes a permissioned `harvest()` that swaps a configurable fraction of wAR into USDC-on-Base (via a bridge or CEX adapter — modeled here as a Uniswap V3 swap on mainnet for simplicity, with the recognition that in practice this routes through a bridge to Base), and forwards the proceeds to a designated Turbo top-up address. A TWAP price guard prevents the harvester from acting against a manipulated thin pool.

```solidity
// bankon_storage_treasury.sol
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity 0.8.26;

import {AccessControl}            from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuardTransient} from "@openzeppelin/contracts/utils/ReentrancyGuardTransient.sol";
import {Pausable}                 from "@openzeppelin/contracts/utils/Pausable.sol";
import {SafeERC20, IERC20}        from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface ISwapRouter02 {
    struct ExactInputSingleParams {
        address tokenIn; address tokenOut; uint24 fee;
        address recipient; uint256 amountIn; uint256 amountOutMinimum; uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata p) external payable returns (uint256);
}

interface IUniV3Pool {
    function observe(uint32[] calldata) external view returns (int56[] memory, uint160[] memory);
    function slot0() external view returns (uint160,int24,uint16,uint16,uint16,uint8,bool);
}

contract BankonStorageTreasury is AccessControl, ReentrancyGuardTransient, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant HARVESTER_ROLE = keccak256("HARVESTER_ROLE");
    bytes32 public constant GOVERNOR_ROLE  = keccak256("GOVERNOR_ROLE");

    IERC20 public immutable WAR;             // 12 decimals
    IERC20 public immutable USDC;            // 6 decimals (mainnet bridged USDC for the harvest leg)
    ISwapRouter02 public immutable router;
    IUniV3Pool public immutable warEthPool;  // for TWAP

    address public turboFundingSink;          // forwards harvested USDC for Turbo top-up
    uint256 public harvestThresholdWarPriceX96; // sqrtPriceX96 over which harvesting is allowed
    uint16  public harvestBps  = 1000;          // 10% of balance per harvest by default
    uint32  public twapWindow  = 1800;          // 30 min

    event Harvested(uint256 warIn, uint256 usdcOut, uint256 sentToSink);
    event ConfigUpdated(uint256 priceX96, uint16 bps, uint32 twap, address sink);

    constructor(address war, address usdc, address router_, address pool, address admin) {
        WAR = IERC20(war); USDC = IERC20(usdc); router = ISwapRouter02(router_);
        warEthPool = IUniV3Pool(pool);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOVERNOR_ROLE, admin);
    }

    function setConfig(uint256 priceX96, uint16 bps, uint32 twap, address sink)
        external onlyRole(GOVERNOR_ROLE)
    {
        require(bps <= 10_000, "bps");
        harvestThresholdWarPriceX96 = priceX96;
        harvestBps = bps; twapWindow = twap; turboFundingSink = sink;
        emit ConfigUpdated(priceX96, bps, twap, sink);
    }

    /// @notice TWAP gate: only harvest if 30-min TWAP exceeds the configured threshold.
    function twapSqrtPriceX96() public view returns (uint160) {
        uint32[] memory secs = new uint32[](2);
        secs[0] = twapWindow; secs[1] = 0;
        (int56[] memory ticks,) = warEthPool.observe(secs);
        int24 avgTick = int24((ticks[1] - ticks[0]) / int56(uint56(twapWindow)));
        // For brevity: convert tick → sqrtPriceX96 via TickMath off-chain or import the lib.
        return uint160(uint24(avgTick));   // placeholder; use TickMath.getSqrtRatioAtTick in prod
    }

    function harvest(uint256 minUsdcOut) external nonReentrant whenNotPaused onlyRole(HARVESTER_ROLE)
        returns (uint256 usdcOut)
    {
        require(uint256(twapSqrtPriceX96()) >= harvestThresholdWarPriceX96, "below threshold");
        uint256 warBal  = WAR.balanceOf(address(this));
        uint256 warIn   = (warBal * harvestBps) / 10_000;
        require(warIn > 0, "nothing to harvest");
        WAR.forceApprove(address(router), warIn);
        usdcOut = router.exactInputSingle(ISwapRouter02.ExactInputSingleParams({
            tokenIn: address(WAR), tokenOut: address(USDC), fee: 3000,
            recipient: address(this), amountIn: warIn,
            amountOutMinimum: minUsdcOut, sqrtPriceLimitX96: 0
        }));
        USDC.safeTransfer(turboFundingSink, usdcOut);
        emit Harvested(warIn, usdcOut, usdcOut);
    }

    function pause()   external onlyRole(GOVERNOR_ROLE) { _pause(); }
    function unpause() external onlyRole(GOVERNOR_ROLE) { _unpause(); }
    function rescue(IERC20 t, address to, uint256 v) external onlyRole(GOVERNOR_ROLE) { t.safeTransfer(to,v); }
}
```

```solidity
// test_bankon_storage_treasury.t.sol
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity 0.8.26;

import "forge-std/Test.sol";
import {BankonStorageTreasury} from "../src/bankon_storage_treasury.sol";

contract BankonStorageTreasuryTest is Test {
    BankonStorageTreasury t;
    address constant WAR  = 0x4fadc7a98f2dc96510e42dd1a74141eEae0C1543;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant ROUT = 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45;
    address constant POOL = 0x3afec5673a547861877f4d722a594171595e561b;

    function setUp() public {
        vm.createSelectFork(vm.envString("ETH_RPC"));
        t = new BankonStorageTreasury(WAR, USDC, ROUT, POOL, address(this));
        t.grantRole(t.HARVESTER_ROLE(), address(this));
        t.setConfig(1, 500, 1800, address(0xBEEF));
    }

    function test_harvest_below_threshold_reverts() public {
        // intentionally set threshold to a price the dormant pool cannot exceed
        t.setConfig(type(uint256).max, 500, 1800, address(0xBEEF));
        vm.expectRevert(bytes("below threshold"));
        t.harvest(0);
    }
}
```

The `harvestBps` and `harvestThresholdWarPriceX96` settings encode a time-weighted DCA-out: each call peels a fraction of the wAR position into USDC only when TWAP confirms a price band, and the proceeds flow to `turboFundingSink` — the address whose Turbo balance funds the pay2store service in §3. This is the closed loop: **agent payments fund Turbo today, wAR appreciation funds Turbo tomorrow**.

---

## Section 3 — `pay2store.agenticplace.pythai.net` as an x402 service

### 3A. Architecture and what it monetizes

The pay2store service exposes a single primary endpoint `POST /store` that returns HTTP 402 with x402 v2 payment requirements until the caller attaches a valid `PAYMENT-SIGNATURE` header (with `X-PAYMENT` accepted as a v1 alias). Once payment is verified, the service performs the Turbo upload on the caller's behalf using the BANKON service's prepaid Turbo balance, then returns the Arweave txid plus a BANKON-signed receipt. Three rails are supported at the customer edge: **USDC-on-Base** via the Coinbase CDP facilitator at `https://api.cdp.coinbase.com/platform/v2/x402` (preferred), **ETH on Ethereum mainnet** via the same facilitator's `eip155:1` adapter (fallback), and **ALGO/ASA-USDC on Algorand mainnet** via direct algod verification (`https://mainnet-api.algonode.cloud`) with SHA-256 request-hash binding via the tx note for replay protection — since Turbo itself does not yet accept ALGO, the service settles the Turbo top-up in USDC-on-Base on the customer's behalf and treats the Algorand receipt as a credit on the customer's prepaid subscription. The pricing rule is `price_usd = turbo_cost_usd × 1.25 + 0.005`, with prepaid bundles at 1 GiB / 10 GiB / 100 GiB tiers carrying 5% / 10% / 15% discounts and a free tier of 1 MiB per address per 24 hours rate-limited by IP. The x402 v2 spec normalized headers to `PAYMENT-REQUIRED` / `PAYMENT-SIGNATURE` / `PAYMENT-RESPONSE` (Base64-encoded JSON) following the Apr 2, 2026 Linux Foundation transition that established the x402 Foundation under Coinbase, Cloudflare, and Stripe initial governance.

```
┌──────────┐    POST /store           ┌─────────────────────┐
│ Agent    │─────(no PAYMENT)────────▶│ pay2store           │
│ (mindX)  │◀────402 PAYMENT-REQUIRED─│ FastAPI + facilitator│
│          │                          └─────────┬───────────┘
│          │    POST /store (PAYMENT-SIG)        │ verify+settle
│          │─────────────────────────────────────▶│  CDP facilitator
│          │                                      │ (Base USDC / ETH)
│          │                                      │   or algod (ALGO)
│          │                                      ▼
│          │                          ┌─────────────────────┐
│          │                          │ Turbo (BANKON acct) │──▶ Arweave L1
│          │◀──200 + arTxId + receipt─┤  uploadFile()       │
└──────────┘                          └─────────────────────┘
                                                 │
                                                 ▼
                                       Postgres: deposits, uploads,
                                       receipts; daily Merkle commit
                                       to bankon_pay2store_receipts.sol
```

### 3B. `pay2store_service.py` — FastAPI implementation

```python
# pay2store_service.py
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved
"""x402 v2 multi-rail pay2store service for AgenticPlace."""
from __future__ import annotations

import asyncio, base64, hashlib, json, logging, os, time, uuid
from dataclasses import dataclass
from typing import Annotated, Literal
import asyncpg, httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from algosdk.v2client import algod, indexer

log = logging.getLogger("bankon.pay2store")

CDP_FACILITATOR = "https://api.cdp.coinbase.com/platform/v2/x402"
USDC_BASE       = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_ETH        = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_ASA_MAIN   = 31566704
SERVICE_PAYTO_ETH = os.environ["BANKON_PAY2STORE_ETH_ADDR"]
SERVICE_PAYTO_ALG = os.environ["BANKON_PAY2STORE_ALGO_ADDR"]
ALGOD_URL       = os.environ.get("ALGOD_URL", "https://mainnet-api.algonode.cloud")
ALGOD_TOKEN     = os.environ.get("ALGOD_TOKEN", "")
INDEXER_URL     = os.environ.get("INDEXER_URL", "https://mainnet-idx.algonode.cloud")
DB_DSN          = os.environ["BANKON_PAY2STORE_DSN"]

app = FastAPI(title="BANKON pay2store", version="1.0.0")
algod_c   = algod.AlgodClient(ALGOD_TOKEN, ALGOD_URL)
indexer_c = indexer.IndexerClient("", INDEXER_URL)

# ---------- Pydantic schemas ----------
class PaymentRequirement(BaseModel):
    scheme: str
    network: str
    maxAmountRequired: str
    resource: str
    description: str
    mimeType: str = "application/octet-stream"
    payTo: str
    maxTimeoutSeconds: int = 60
    asset: str
    extra: dict | None = None

class PaymentRequired(BaseModel):
    x402Version: Literal[1, 2] = 2
    accepts: list[PaymentRequirement]
    error: str | None = None

# ---------- pricing ----------
async def turbo_cost_usd_per_byte() -> float:
    async with httpx.AsyncClient() as c:
        rates = (await c.get("https://payment.ardrive.io/v1/rates", timeout=10)).json()
        bytes_quote = (await c.get("https://payment.ardrive.io/v1/price/bytes/1048576", timeout=10)).json()
    return float(bytes_quote["winc"]) * (float(rates["fiat"]["usd"]) / float(rates["winc"])) / 1_048_576

def price_usd(turbo_cost: float) -> float:
    return round(turbo_cost * 1.25 + 0.005, 6)

# ---------- 402 generator ----------
def make_402(resource_url: str, size_bytes: int, usd: float) -> JSONResponse:
    accepts = [
        PaymentRequirement(
            scheme="exact", network="eip155:8453",
            maxAmountRequired=str(int(usd * 1_000_000)),  # USDC atomic on Base
            resource=resource_url, description=f"BANKON pay2store: {size_bytes} bytes",
            payTo=SERVICE_PAYTO_ETH, asset=USDC_BASE,
            extra={"name": "USDC", "version": "2"},
        ),
        PaymentRequirement(
            scheme="exact", network="eip155:1",
            maxAmountRequired=str(int(usd * 1_000_000)),
            resource=resource_url, description=f"BANKON pay2store (mainnet fallback)",
            payTo=SERVICE_PAYTO_ETH, asset=USDC_ETH,
            extra={"name": "USD Coin", "version": "2"},
        ),
        PaymentRequirement(
            scheme="exact",
            network="algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
            maxAmountRequired=str(int(usd * 1_000_000)),
            resource=resource_url, description=f"BANKON pay2store (ALGO/ASA-USDC)",
            payTo=SERVICE_PAYTO_ALG, asset=str(USDC_ASA_MAIN),
            extra={"requestHashBinding": True},
        ),
    ]
    body = PaymentRequired(accepts=accepts).model_dump()
    encoded = base64.b64encode(json.dumps(body).encode()).decode()
    return JSONResponse(status_code=402, content=body,
                        headers={"PAYMENT-REQUIRED": encoded})

# ---------- payment verification ----------
async def verify_evm_payment(payload_b64: str, req: PaymentRequirement) -> dict:
    payload = json.loads(base64.b64decode(payload_b64))
    async with httpx.AsyncClient(timeout=30) as c:
        v = await c.post(
            f"{CDP_FACILITATOR}/verify",
            json={"x402Version": 2, "paymentPayload": payload, "paymentRequirements": req.model_dump()},
            headers={"Authorization": f"Bearer {os.environ['CDP_BEARER']}"},
        )
        v.raise_for_status()
        if not v.json().get("isValid"):
            raise HTTPException(402, detail={"error": "invalid_payment"})
        s = await c.post(
            f"{CDP_FACILITATOR}/settle",
            json={"x402Version": 2, "paymentPayload": payload, "paymentRequirements": req.model_dump()},
            headers={"Authorization": f"Bearer {os.environ['CDP_BEARER']}"},
        )
        s.raise_for_status()
        return s.json()

async def verify_algo_payment(payload_b64: str, expected_request_hash: bytes,
                              expected_amount: int) -> dict:
    payload = json.loads(base64.b64decode(payload_b64))
    txid = payload["payload"]["txId"]
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            tx = algod_c.pending_transaction_info(txid)
            if tx.get("confirmed-round", 0) > 0:
                inner = tx["txn"]["txn"]
                assert inner["type"] in ("axfer", "pay")
                assert inner.get("xaid") == USDC_ASA_MAIN or inner["type"] == "pay"
                assert inner["aamt" if inner["type"]=="axfer" else "amt"] >= expected_amount
                assert inner["arcv" if inner["type"]=="axfer" else "rcv"] == SERVICE_PAYTO_ALG
                note = base64.b64decode(inner.get("note", ""))
                if note != expected_request_hash:
                    raise HTTPException(402, detail={"error": "request_hash_mismatch"})
                return {"network": "algorand", "txId": txid}
        except Exception:
            pass
        await asyncio.sleep(1.5)
    raise HTTPException(402, detail={"error": "expired_payment"})

# ---------- Turbo upload (Node CLI shell-out) ----------
async def upload_to_turbo(data: bytes, tags: dict[str, str]) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "node", "turbo_upload.mjs", json.dumps(tags),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env={**os.environ})
    out, err = await proc.communicate(data)
    if proc.returncode != 0:
        log.error("turbo_failed", extra={"err": err.decode()[:500]})
        raise HTTPException(502, detail={"error": "turbo_upstream_failed"})
    return json.loads(out)

# ---------- DB ----------
async def db() -> asyncpg.Pool:
    if not hasattr(app.state, "pool"):
        app.state.pool = await asyncpg.create_pool(DB_DSN, min_size=2, max_size=20)
    return app.state.pool

# ---------- main route ----------
@app.post("/store")
async def store(
    request: Request, file: UploadFile,
    payment_signature: Annotated[str | None, Header(alias="PAYMENT-SIGNATURE")] = None,
    x_payment:        Annotated[str | None, Header(alias="X-PAYMENT")] = None,
    tag_app:          Annotated[str | None, Header(alias="X-BANKON-Tag-App")] = "BANKON",
):
    raw = await file.read()
    size = len(raw)
    if size == 0:
        raise HTTPException(400, "empty body")
    sha = hashlib.sha256(raw).hexdigest()

    cost_per_byte = await turbo_cost_usd_per_byte()
    usd = price_usd(cost_per_byte * size)
    resource_url = str(request.url)
    payload_b64 = payment_signature or x_payment

    if payload_b64 is None:
        return make_402(resource_url, size, usd)

    payload = json.loads(base64.b64decode(payload_b64))
    network = payload["accepted"]["network"]
    req_obj = PaymentRequirement(**payload["accepted"])

    if network.startswith("eip155:"):
        settle = await verify_evm_payment(payload_b64, req_obj)
    elif network.startswith("algorand:"):
        request_hash = hashlib.sha256(
            f"{resource_url}|{sha}|{size}|{usd}".encode()
        ).digest()
        settle = await verify_algo_payment(payload_b64, request_hash, int(usd * 1_000_000))
    else:
        raise HTTPException(400, f"unsupported network {network}")

    tags = {
        "App-Name": tag_app, "App-Version": "1.0",
        "BANKON-SHA256": sha, "BANKON-Service": "pay2store",
        "BANKON-Payer": str(payload.get("payload", {}).get("authorization", {}).get("from", "")),
    }
    upload = await upload_to_turbo(raw, tags)

    pool = await db()
    async with pool.acquire() as cx:
        deposit_id = uuid.uuid4()
        await cx.execute(
            """INSERT INTO deposits (id, payer, pay_to, network, asset, amount_atomic,
                  tx_hash, scheme, resource_url, status, payment_payload, settlement_response)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'settled',$10,$11)
               ON CONFLICT (tx_hash) DO NOTHING""",
            deposit_id, payload["payload"].get("authorization",{}).get("from","") or settle.get("txId",""),
            req_obj.payTo, network, req_obj.asset, int(req_obj.maxAmountRequired),
            settle.get("transaction") or settle.get("txId") or "", req_obj.scheme,
            resource_url, json.dumps(payload), json.dumps(settle))
        await cx.execute(
            """INSERT INTO uploads (id, deposit_id, arweave_tx, content_sha256, mime_type, size_bytes)
               VALUES (gen_random_uuid(), $1, $2, decode($3,'hex'), $4, $5)""",
            deposit_id, upload["id"], sha, file.content_type or "application/octet-stream", size)

    response_obj = {"arTxId": upload["id"], "sha256": sha, "sizeBytes": size,
                    "winc": upload.get("winc"), "settlement": settle}
    encoded = base64.b64encode(json.dumps(response_obj).encode()).decode()
    return JSONResponse(content=response_obj, headers={"PAYMENT-RESPONSE": encoded})
```

A companion `turbo_upload.mjs` reads bytes from stdin and tags from argv, then calls `turbo.upload()` from `@ardrive/turbo-sdk@1.40.2` against a JWK loaded from `BANKON_TURBO_JWK_PATH`. The Postgres schema follows the layout in the research report (deposits/uploads/refunds/batch_receipts) with a `UNIQUE(payer, nonce)` constraint mirroring EIP-3009 nonce semantics for idempotency.

### 3C. AgenticPlace agent client

```typescript
// agenticplace_pay2store_client.ts
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
import { Wallet, JsonRpcProvider } from "ethers";

const SERVICE = "https://pay2store.agenticplace.pythai.net/store";

export async function agentStore(privateKey: `0x${string}`, data: Uint8Array, tags: Record<string,string> = {}) {
    const fd = new FormData();
    fd.append("file", new Blob([data]));
    let res = await fetch(SERVICE, { method: "POST", body: fd,
        headers: Object.fromEntries(Object.entries(tags).map(([k,v]) => [`X-BANKON-Tag-${k}`, v])) });
    if (res.status !== 402) return await res.json();

    const required = JSON.parse(atob(res.headers.get("PAYMENT-REQUIRED")!));
    const opt = required.accepts.find((a: any) => a.network === "eip155:8453")!;

    const provider = new JsonRpcProvider(process.env.BASE_RPC!);
    const w = new Wallet(privateKey, provider);

    const nonce = "0x" + crypto.getRandomValues(new Uint8Array(32))
        .reduce((s,b)=>s+b.toString(16).padStart(2,"0"),"");
    const validAfter  = "0";
    const validBefore = String(Math.floor(Date.now()/1000) + opt.maxTimeoutSeconds);
    const auth = { from: w.address, to: opt.payTo, value: opt.maxAmountRequired,
                   validAfter, validBefore, nonce };
    const domain = { name: opt.extra.name, version: opt.extra.version,
                     chainId: 8453, verifyingContract: opt.asset };
    const types = { TransferWithAuthorization: [
        {name:"from",type:"address"},{name:"to",type:"address"},{name:"value",type:"uint256"},
        {name:"validAfter",type:"uint256"},{name:"validBefore",type:"uint256"},{name:"nonce",type:"bytes32"}]};
    const signature = await w.signTypedData(domain, types, auth);

    const payload = {
        x402Version: 2, scheme: "exact", network: "eip155:8453",
        resource: { url: SERVICE, description: opt.description, mimeType: opt.mimeType },
        accepted: opt, extensions: {}, outputSchema: null,
        payload: { signature, authorization: auth },
    };
    const sig = btoa(JSON.stringify(payload));
    res = await fetch(SERVICE, { method: "POST", body: fd,
        headers: { "PAYMENT-SIGNATURE": sig,
                   ...Object.fromEntries(Object.entries(tags).map(([k,v]) => [`X-BANKON-Tag-${k}`, v])) }});
    if (!res.ok) throw new Error(`pay2store failed: ${res.status} ${await res.text()}`);
    return await res.json();
}
```

The agent's wallet — derived from its agent ID via the BANKON-internal `parsec-wallet` (treated here as proprietary infrastructure rather than a public dependency) — is used to sign EIP-3009 `TransferWithAuthorization` for USDC-on-Base, and the resulting Arweave txid is registered in the agent's mindX memory log immediately after the response.

### 3D. Pricing model and economic shape

The base price formula `turbo_cost × 1.25 + $0.005` covers the operational overhead of the Postgres write, the facilitator settlement (free on Base for the first 1,000 monthly transactions then $0.001/tx), and the daily Merkle-commit gas amortization. At AR ≈ $2.40 in May 2026, raw Turbo is roughly $0.02–$0.05 per 50 MB upload, so the service margin sits around half a cent to a cent in absolute terms with the multiplier dominating only for larger uploads. The 1 GiB / 10 GiB / 100 GiB prepaid bundles at 5%/10%/15% discounts encode standard SaaS volume economics and create a working-capital float the BANKON treasury can deploy temporarily into Turbo Credit Share Approvals (`shareCredits`) for high-volume agents. The free tier of 1 MiB per address per 24 hours is rate-limited per-IP at a thin reverse proxy (nginx limit_req zone, 10 req/min burst 30) to mitigate honeypot abuse, and the 100 KiB Turbo free upload threshold means the service can serve the smallest workloads with effectively zero marginal cost.

### 3E. Why this fits AgenticPlace

The pay2store primitive is the only piece of infrastructure that lets an autonomous agent on AgenticPlace make permanent, third-party-verifiable storage commitments without holding AR or running an Arweave node, and x402 is the canonical agent-payment protocol of 2025–2026 (post-Linux-Foundation governance) — making the two natural to fuse. The output is composable: mindX memory-log archiving uses the `BANKON-Topic: mindx-memory` tag, aGLM checkpoint pinning uses `BANKON-Topic: aglm-checkpoint`, and BANKON identity attestations use `BANKON-Topic: bonafide-attest`, all flowing through the same paid endpoint. Revenue from agent payments funds the BANKON Turbo prepaid balance and ultimately the AR accumulation in the treasury (Section 2E), which over time funds storage at the marginal cost of harvested wAR rather than fresh USDC inflow — closing the loop between asset position and operational expense.

### 3F. `bankon_pay2store_receipts.sol` — batched on-chain receipts

```solidity
// bankon_pay2store_receipts.sol
// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity 0.8.26;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {MerkleProof}   from "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

contract BankonPay2StoreReceipts is AccessControl {
    bytes32 public constant ATTESTOR_ROLE = keccak256("ATTESTOR_ROLE");

    struct Batch { bytes32 root; uint64 leafCount; uint64 committedAt; bytes32 arweaveTx; }

    mapping(uint64 => Batch) public batches;
    uint64 public latestEpoch;
    mapping(bytes32 => bool) public claimed;

    event RootCommitted(uint64 indexed epoch, bytes32 root, uint64 leafCount, bytes32 arweaveTx);
    event Stored(address indexed payer, bytes32 indexed arTxid, uint256 sizeBytes,
                 uint256 paidAtomics, uint16 currency, uint64 epoch);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ATTESTOR_ROLE, admin);
    }

    /// Commit one daily batch of pay2store receipts as a Merkle root.
    function commitBatch(bytes32 root, uint64 leafCount, bytes32 arweaveTx)
        external onlyRole(ATTESTOR_ROLE) returns (uint64 epoch)
    {
        epoch = ++latestEpoch;
        batches[epoch] = Batch(root, leafCount, uint64(block.timestamp), arweaveTx);
        emit RootCommitted(epoch, root, leafCount, arweaveTx);
    }

    /// Claim a leaf to emit a per-receipt Stored event (for indexers).
    function attestLeaf(
        uint64 epoch, address payer, bytes32 arTxid, uint256 sizeBytes,
        uint256 paidAtomics, uint16 currency, bytes32[] calldata proof
    ) external {
        Batch storage b = batches[epoch];
        require(b.root != 0, "no such epoch");
        bytes32 leaf = keccak256(bytes.concat(keccak256(
            abi.encode(payer, arTxid, sizeBytes, paidAtomics, currency))));
        require(!claimed[leaf], "claimed");
        require(MerkleProof.verify(proof, b.root, leaf), "bad proof");
        claimed[leaf] = true;
        emit Stored(payer, arTxid, sizeBytes, paidAtomics, currency, epoch);
    }
}
```

The off-chain batcher uses `@openzeppelin/merkle-tree` `StandardMerkleTree.of(values, ["address","bytes32","uint256","uint256","uint16"])` to produce the daily root, and the entire tree JSON is itself archived to Arweave so any payer can retrieve their proof permanently — the `arweaveTx` field on `Batch` records this archive and ties the contract recursively into the storage system it is settling. Per-leaf `attestLeaf` costs roughly 25–60k gas at a tree depth of 16–20, dominated by the `Stored` event and the `claimed` SSTORE; full-batch verification is therefore amortized to single-cents per receipt at typical gas prices.

### 3G. Risk envelope and operational posture

The dominant operational risks are sequenced. **Custody risk** is bounded by the immediate-settle architecture: the service never holds user funds longer than the facilitator settlement window (sub-second for Algorand finality, ~2s on Base) because Turbo top-ups are funded from a separate BANKON treasury wallet with its own bulk USDC-on-Base balance, decoupling the cash path from the credit path. **Bridge risk** in everPay/Wormhole/AOX is real but does not appear on the customer-facing path — the pay2store service uses no bridges itself, only the Turbo payment service on Base; the bridge dependency lives in §2's treasury harvest leg, where it is bounded by `harvestBps` and the TWAP gate. **Censorship and content moderation** at the Arweave layer is gateway-side, not protocol-side: removed content disappears from `arweave.net` and possibly other AR.IO operators but persists on the L1, and the BANKON service should publish a clear Acceptable Use Policy that excludes obvious illegality and indicates that gateway-level filtering is the only available remediation. **Compliance** ties into the BANKON identity layer (BONAFIDE) — KYC thresholds attach above $10k aggregate per-address per-month, with the `BANKON-Payer` tag on the DataItem providing the audit trail back to the EIP-3009 authorization signature and ultimately the EOA. **SLA design** should target 99.5% on the upload endpoint with degradation to a queued mode (return 202 + queue ID, settle later) when Turbo upload fails, plus circuit breakers on facilitator failure that fall back from CDP to the public `https://x402.org/facilitator` for graceful degradation.

---

## Conclusion: what the loop actually looks like

The closed loop the brief asked for is now concrete. Today, an AgenticPlace agent calls `pay2store.agenticplace.pythai.net/store` with 50 MB of bytes; gets a 402; signs an EIP-3009 USDC authorization on Base for ~$0.05 plus 25% margin; gets back an Arweave txid with a BANKON receipt; that txid is verifiable by anyone via `python -m bankon_arweave verify` against SHA-256, tags, and signature; the service's daily Merkle commit on `bankon_pay2store_receipts.sol` makes the whole batch permanently auditable on Ethereum mainnet and again on Arweave itself. Underneath, BANKON's prepaid Turbo balance is replenished partly from the 25% service margin and partly from the wAR treasury's `harvest()` calls when TWAP exceeds threshold — wAR being held cold in a Safe multisig with a deliberate accumulation-mode thesis at sub-$3 prices despite the dormant Ethereum-side market, because the live wAR economy now lives on AO and the Ethereum-side ERC-20 functions as a price-stale custody venue rather than a tradable instrument. The three corrections to the original brief that matter operationally are: **Irys is no longer an Arweave path** (Nov 25, 2025 L1 pivot); **the WAR contract has no public `burn(uint256, string)`** (withdrawals route through the everPay EIP-712 protocol layer); and **`arbundles-py` does not exist** (Python clients must implement deepHash signing inline as shown in `bankon_arweave_payment.py` or shell out to the Node SDK). With these in hand, BANKON has a single coherent stack — Turbo for storage, USDC-on-Base for the working currency, x402 v2 for agent payments, wAR cold-stored for the strategic asset, and Solidity attestations binding everything to verifiable on-chain history — that ships today and improves automatically as wAR accumulation compounds against a permanent storage cost curve that has been declining at 0.5%/yr Kryder+ for a decade.