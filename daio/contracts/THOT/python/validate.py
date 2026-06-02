"""End-to-end smoke test for the THOT4096 Python reference."""

import sys
sys.path.insert(0, "src")

import numpy as np

from thot.builder import build_thot_bundle
from thot.matryoshka import verify_prefix_proof
from thot.thot8_cpu import (
    THOT8,
    cosine,
    dot,
    ternarize_first_eight,
    ternary_head_leaf,
)


def main() -> int:
    rng = np.random.default_rng(42)
    vec_4096 = rng.standard_normal(4096).astype(np.float32)
    vec_4096 = vec_4096 / np.linalg.norm(vec_4096)

    bundle = build_thot_bundle(vec_4096)
    print(f"Parent root : 0x{bundle.commitment.root.hex()}")
    print(f"Ternary head: 0x{bundle.commitment.ternary_head_leaf.hex()}")
    print(f"Prefix proofs constructed: {list(bundle.prefix_proofs.keys())}")
    print()

    all_ok = True
    for dim in (8, 768, 1024, 2048):
        proof = bundle.prefix_proofs[dim]
        ok = verify_prefix_proof(proof)
        all_ok &= ok
        co_w = len(proof.co_witness_leaves)
        rs = len(proof.right_siblings)
        print(
            f"  THOT{dim:<4}  prefix_root=0x{proof.prefix_root.hex()[:16]}…  "
            f"co_witness={co_w}  right_siblings={rs}  verify={ok}"
        )

    print()

    # THOT8 CPU sanity
    t8 = ternarize_first_eight(vec_4096.tolist())
    print(f"THOT8 values         : {t8.values}")
    packed = t8.pack()
    print(f"THOT8 packed         : 0x{packed.hex()}")
    print(f"THOT8 leaf hash      : 0x{ternary_head_leaf(t8).hex()}")
    t8b = THOT8.unpack(packed)
    print(f"THOT8 roundtrip ok   : {t8b.values == t8.values}")
    print(f"THOT8 dot(self,self) : {dot(t8, t8)}")
    print(f"THOT8 cos(self,self) : {cosine(t8, t8):.4f}")

    # Tamper check: corrupt a co-witness leaf and confirm verify fails.
    proof_768 = bundle.prefix_proofs[768]
    bad = list(proof_768.co_witness_leaves)
    bad[0] = b"\x00" * 32
    from thot.matryoshka import PrefixProof
    tampered = PrefixProof(
        parent_root=proof_768.parent_root,
        prefix_dim=768,
        prefix_root=proof_768.prefix_root,
        prefix_leaves=list(proof_768.prefix_leaves),
        co_witness_leaves=bad,
        right_siblings=list(proof_768.right_siblings),
    )
    tampered_ok = verify_prefix_proof(tampered)
    print()
    print(f"THOT768 tampered co-witness rejected: {not tampered_ok}")
    all_ok &= (not tampered_ok)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
