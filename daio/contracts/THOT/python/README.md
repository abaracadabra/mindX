# THOT Python reference codec

Off-chain codec for the THOT family. Generates Keccak-256 Merkle roots,
Matryoshka prefix proofs, and the dedicated THOT8 ternary-head sub-leaf
that the Solidity layer (`daio/contracts/THOT/libraries/THOTLib.sol` +
`daio/contracts/THOT/commitment/THOTCommitmentRegistry.sol`) verifies.

## Byte-parity guarantee

This codec and `THOTLib.sol` must produce **byte-identical** roots, leaf
hashes, and prefix proofs for the same input. The contract pieces that
enforce this:

| Solidity | Python |
|---|---|
| `LEAF_DOMAIN_4096 = keccak256("THOT4096/leaf/v1")` | `LEAF_DOMAIN_4096 = _keccak(b"THOT4096/leaf/v1")` |
| `LEAF_DOMAIN_THOT8 = keccak256("THOT8/head/v1")` | `LEAF_DOMAIN_THOT8 = _keccak(b"THOT8/head/v1")` |
| `TOMBSTONE = keccak256("THOT/tombstone/v1")` | `TOMBSTONE = _keccak(b"THOT/tombstone/v1")` |
| `NODE_PREFIX = 0x01` (RFC-6962) | `NODE_PREFIX = b"\x01"` |
| `hashLeaf4096(idx, dimStart, dimEnd, chunk)` uses `abi.encodePacked` with `uint32`/`uint16`/`uint16` big-endian | `hash_leaf_4096` uses `struct.pack(">I", ...)` + `struct.pack(">H", ...)` |
| Ternary head: `keccak256(LEAF_DOMAIN_THOT8 ‖ bytes2 ‖ bytes30(0))` | `ternary_head_leaf(t)` uses identical layout |
| THOT8 codon packing: LSB-first into a `uint16` | `THOT8.pack()` uses `to_bytes(2, "little")` with codons LSB-first |

Both sides reject the reserved ternary codon `0b11`.

## Layout

```
daio/contracts/THOT/python/
├── README.md             (this file)
├── pyproject.toml        (deps: numpy, pycryptodome)
├── validate.py           (end-to-end smoke; reproduces known-good roots)
└── thot/
    ├── __init__.py
    ├── merkle.py         (leaf hashing + tombstone-padded Merkle root)
    ├── matryoshka.py     (prefix proof build + verify, modes A/B/C)
    ├── thot8_cpu.py      (ternary codec, dot/cosine, leaf hash)
    └── builder.py        (THOT4096 → commitment bundle convenience)
```

## Quick start

```bash
cd daio/contracts/THOT/python
python -m venv .venv && source .venv/bin/activate
pip install -e .                            # numpy + pycryptodome only

python validate.py                          # exit 0; prints parent root + 4 prefix proofs
```

Known-good output for seed 42 (used by `test/thot/THOTLib.t.sol` as the
on-chain parity fixture):

```
Parent root : 0x73f2be604d05e8e3832f72bb0823b7ce65a9be92d04876a139195f30c35463f7
Ternary head: 0x082a79ac6f4dc8b39325d907066f368be315954631a28f163270a6a15d0c4a25
THOT8 packed: 0x599a
THOT8 values: (1, -1, 1, 1, -1, -1, 1, -1)
```

If these change without a corresponding update to the test fixture, the
on-chain/off-chain contract has drifted — investigate before merging.

## On-chain integration

Once a THOT4096 commitment is built:

```python
from thot.builder import build_thot_bundle
import numpy as np
vec = np.random.default_rng(42).standard_normal(4096).astype(np.float16)
bundle = build_thot_bundle(vec)

print(f"root  = 0x{bundle.commitment.root.hex()}")
print(f"head  = 0x{bundle.commitment.ternary_head_leaf.hex()}")
print(f"index = {bundle.commitment.ternary_head_index}")
```

Issue on-chain:

```bash
cast send $REGISTRY \
  "issueTHOT4096(bytes32,bytes32,uint256,string,string)" \
  0x<root> 0x<head> 255 "ipfs://payload" "ipfs://meta" \
  --rpc-url $SEPOLIA_RPC --private-key $ISSUER_KEY
```

Then for any prefix variant:

```python
proof = bundle.prefix_proofs[1024]
print({
    "parent": "0x" + proof.parent_root.hex(),
    "prefix": "0x" + proof.prefix_root.hex(),
    "leaves":     ["0x" + h.hex() for h in proof.prefix_leaves],
    "co_witness": ["0x" + h.hex() for h in proof.co_witness_leaves],
    "siblings":   ["0x" + h.hex() for h in proof.right_siblings],
})
```

Feed the same arrays to `THOTCommitmentRegistry.registerPrefix(...)`.

## License

Apache-2.0. Companion Solidity at `../libraries/THOTLib.sol` and
`../commitment/THOTCommitmentRegistry.sol`.
