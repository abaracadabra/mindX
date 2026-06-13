# bankoneth — Specifications

These are the **canonical specifications** that bankoneth implements. They
predate the contract code and remain the authoritative description of what
the module is *supposed* to do. The contracts in
[`../../contracts/`](../../contracts/) and the deploy scripts in
[`../../script/`](../../script/) implement what's written here.

| Spec | Format | Description |
|---|---|---|
| **Production Architecture for `bankon.eth`** | [.md](BANKON%20ENS%20Subname%20Registrar_%20Production%20Architecture%20for%20bankon.eth.md) · [.pdf](BANKON%20ENS%20Subname%20Registrar_%20Production%20Architecture%20for%20bankon.eth.pdf) | The four-contract base layer (Registrar, PriceOracle, ReputationGate, PaymentRouter), Tier-1 deploy ordering, on-chain pricing logic, x402 settlement, BONAFIDE gating. The Flow A baseline. |
| **ERC-7857 iNFT and ERC-6551 TBA Integration** | [.md](BANKON%20ENS%20Subname%20Registrar_%20ERC-7857%20iNFT%20and%20ERC-6551%20TBA%20Integration.md) · [.pdf](BANKON%20ENS%20Subname%20Registrar_%20ERC-7857%20iNFT%20and%20ERC-6551%20TBA%20Integration.pdf) | Mode A (unified) vs Mode B (parallel) iNFT layering, 0G-side iNFT contract, cross-chain TBA derivation, the `addr(node)` override on the resolver. |

## When to read the specs

- **Disagreement between spec and code** — the spec wins. File an issue,
  align the code, then bump the spec only if a deliberate architectural
  change is justified.
- **Adding a feature** — start by reading the relevant spec section. If the
  feature isn't covered, add it to the spec first.
- **Audit prep** — auditors get the specs as the threat-model anchor; the
  code is verified against them.

The two adjacent specs in `docs/operations/dev/` that bankoneth touches but
doesn't implement directly (the BANKON ↔ 0G iNFT definitive spec, and the
BANKON ↔ pythai.net unified architecture) remain in the parent mindX tree
because they describe consumer-side integration patterns, not bankoneth's
internals. See [`../INTEGRATIONS.md`](../INTEGRATIONS.md) for how bankoneth
plugs into those.

## Spec drift policy

The specs are point-in-time documents. As bankoneth evolves, this directory
keeps the **as-shipped** version. Don't edit the historical specs in
place — bump the filename (e.g. `…_v2.md`) and link the new one from this
README, with a note in the top of the new spec describing what changed.
