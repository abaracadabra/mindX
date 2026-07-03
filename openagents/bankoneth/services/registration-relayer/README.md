# bankon registration relayer (x402 → EIP-712 voucher)

The missing L1 service piece for **bankon.eth subname-as-a-service**. The
on-chain `BankonSubnameRegistrar.register()` is gated by a voucher signed by a
key holding `GATEWAY_SIGNER_ROLE`, binding `(label, owner, expiry,
paymentReceiptHash, deadline)`. Payment settles **off-chain via x402**; this
relayer takes the payment and issues the voucher. The user then submits
`register(...)` on L1 with the voucher.

**Fee model: take it, own it.** A subname is a **one-time purchase**, permanent
ownership, no annual renewal. The voucher requests the maximum expiry (ENS
NameWrapper caps it to the `bankon.eth` parent), so the name is owned for as long
as the operator keeps `bankon.eth` alive. There is no `/renew`.

```
customer → GET /quote → POST /register (402 → pay x402 → voucher)
        → register(label,owner,expiry,receiptHash,deadline,gatewaySig,meta) on mainnet
```

## Endpoints

| Route | Purpose |
|---|---|
| `GET /health` | signer address, chain, registrar, x402 mode |
| `GET /quote?label=` | one-time price (USD, from `BankonPriceOracle` or length tiers) |
| `POST /register` | `{label, owner}` → **402** with x402 payment requirements, or (once paid) the signed **Registration** voucher |

The voucher response carries `{label, owner, expiry, paymentReceiptHash,
deadline, gatewaySig, registrar, chainId}` — the exact args for `register()`.

## The voucher is exact (tested)

The EIP-712 domain and type match the contract verbatim:
`EIP712("BankonSubnameRegistrar","1")` +
`Registration(string label,address owner,uint64 expiry,bytes32 paymentReceiptHash,uint256 deadline)`.
`bun test` proves the relayer's `hashTypedData` equals the contract's
`_hashTypedDataV4(keccak256(abi.encode(REGISTRATION_TYPEHASH, …)))` byte-for-byte
and that the signature recovers to the gateway signer — so `register()` accepts
it, given that address holds `GATEWAY_SIGNER_ROLE`.

## Run

```bash
REGISTRAR_ADDR=0x…            # BankonSubnameRegistrar (mainnet, from the identity-ens deploy)
GATEWAY_SIGNER_PK=0x…         # a key GRANTED GATEWAY_SIGNER_ROLE on the registrar
CHAIN_ID=1
RPC_URL=https://…            # optional — enables live BankonPriceOracle reads
PRICE_ORACLE_ADDR=0x…        # optional
X402_MODE=facilitator        # or trusted-header (dev); never `none` in prod
X402_FACILITATOR=https://facilitator.goplausible.xyz
X402_ASSET=31566704          # USDC ASA (Algorand)
X402_PAYTO=…                 # BANKON treasury on the rail
bun run src/index.ts
```

## Operator setup (one-time)

After deploying `BankonSubnameRegistrar`, grant the relayer key the role:

```solidity
registrar.grantRole(GATEWAY_SIGNER_ROLE, <relayer signer address>);
```

(`script/GrantOwnerRoles.s.sol` is the canonical place to wire this.) The signer
key lives only in the relayer's env / vault mount — never on the wire, never in
the client.

## x402 payment modes

- `facilitator` — verifies the receipt against the x402 facilitator (settled +
  unspent) before issuing. Production.
- `trusted-header` — accepts a settled receipt id from a trusted upstream (the
  x402 middleware / `BankonX402Attestor` flow). For staged deploys.

`paymentReceiptHash = keccak256(receiptId)` binds the payment to the voucher;
replay is enforced on-chain (`usedReceipts`) and locally (issued set).

## Wiring

`DeltaVerse/deploy/ens-service.json` → `backends.l1canonical.relayerUrl` points
the storefront (`pages/ens-mint.html`) at this service; the L1 mint path
activates once `registrar` is filled there. The multichain path
(`DvEnsSubnameRegistry`) needs no relayer.
