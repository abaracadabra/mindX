# The One-Opcode Lever: OP_CAT, Satoshi's 2010 Disabling, and the BIP-347 Soft Fork Path to Post-Quantum Bitcoin

*A source-level technical reference.*

## Premise

There is a persistent piece of folklore that Satoshi described quantum-proofing Bitcoin as a "one line, one character" change. No such Satoshi correspondence exists. Satoshi's only on-record comment on cryptographic transition is the June 2010 BitcoinTalk thread *Dealing with SHA-256 Collisions*, which concerns **hashing**, not signatures, and describes a coordinated fork rather than a trivial edit ([SNI archive](https://satoshi.nakamotoinstitute.org/posts/bitcointalk/threads/68/), [original topic 191](https://bitcointalk.org/index.php?topic=191)).

The kernel of truth the folklore is reaching for is real and more interesting: a **single opcode** Satoshi removed in 2010 — `OP_CAT` — is the lever that, once re-enabled, makes hash-based post-quantum (Lamport) signatures expressible in Bitcoin Script. This document outlines both halves at the source level: the original disabling and the BIP-347 re-enable, with the exact code, the exact fork method, and an honest account of what it does and does not buy in terms of quantum resistance.

---

## Part I — The original opcode and Satoshi's disabling

### 1.1 OP_CAT as originally shipped

`OP_CAT` (opcode value **126 decimal / 0x7e hex**) was a "splice" operator present from the earliest public Bitcoin releases. It popped the top two stack elements, concatenated them, and pushed the result. The original implementation, as it lived in `script.cpp`:

```cpp
case OP_CAT:
{
    // (x1 x2 -- out)
    if (stack.size() < 2)
        return false;
    valtype& vch1 = stacktop(-2);
    valtype& vch2 = stacktop(-1);
    vch1.insert(vch1.end(), vch2.begin(), vch2.end());
    stack.pop_back();
}
break;
```

Canonical historical anchor (pre-disable blob, referenced by BIP-347 itself):
[`script.cpp#L381-L393` @ `01cd2fda`](https://github.com/bitcoin/bitcoin/blob/01cd2fdaf3ac6071304ceb80fb7436ac02b1059e/script.cpp#L381-L393)

### 1.2 The disabling — what Satoshi actually changed

The disabling was **not** an edit to the `OP_CAT` case body. It was a single guard block inserted near the top of `EvalScript()`, in commit [**4bd188c** ("misc changes", 25 Aug 2010)](https://github.com/bitcoin/bitcoin/commit/4bd188c4383d6e614e18f79dc337fbabe8464c82), that short-circuits sixteen opcodes to `return false` before evaluation reaches their case statements:

```cpp
if (opcode == OP_CAT ||
    opcode == OP_SUBSTR ||
    opcode == OP_LEFT ||
    opcode == OP_RIGHT ||
    opcode == OP_INVERT ||
    opcode == OP_AND ||
    opcode == OP_OR ||
    opcode == OP_XOR ||
    opcode == OP_2MUL ||
    opcode == OP_2DIV ||
    opcode == OP_MUL ||
    opcode == OP_DIV ||
    opcode == OP_MOD ||
    opcode == OP_LSHIFT ||
    opcode == OP_RSHIFT)
    return false;
```

Two technically important points for accuracy:

- **It was a deletion of capability, not merely a "disable."** Once this guard returns `false`, any script containing one of these opcodes is invalid. The opcodes were effectively removed from the language, not soft-gated.
- **The same commit tightened OP_CAT's own body.** In the disabling-era source, the `OP_CAT` case was simultaneously given an output-size ceiling (`if (stacktop(-1).size() > 520) return false;` in the 0.3.x line; earlier drafts used 5000). This is the residue of the documented motivation: a script repeating `OP_DUP OP_CAT` doubles a stack element each iteration, so ~40 iterations would reach >1 TB absent a size cap. The cap, not removal, is what neutralizes that DoS — a fact that becomes the entire basis for re-enabling later.

### 1.3 Where the gate lives today

In modern Bitcoin Core the sixteen-opcode guard has been refactored, but the behavior is unchanged. The disabled-opcode rejection now reads:

```cpp
return set_error(serror, SCRIPT_ERR_DISABLED_OPCODE); // Disabled opcodes (CVE-2010-5137).
```

File: [`src/script/interpreter.cpp`](https://github.com/bitcoin/bitcoin/blob/master/src/script/interpreter.cpp)
Opcode enum (`OP_CAT = 0x7e`): [`src/script/script.h`](https://github.com/bitcoin/bitcoin/blob/master/src/script/script.h)

---

## Part II — BIP-347: re-enabling OP_CAT as a soft fork

[**BIP-347 — "OP_CAT in Tapscript"**](https://github.com/bitcoin/bips/blob/master/bip-0347.mediawiki) — Ethan Heilman & Armin Sabouri. Status: **Complete (v1.0.0, 2026-03-01)**. Requires BIP-340/341/342.
Implementation: [Bitcoin Core PR #29247](https://github.com/bitcoin/bitcoin/pull/29247).

### 2.1 The activation mechanism (the fork method)

BIP-347 does **not** un-delete the legacy opcode. It redefines a *reserved* tapscript opcode that already shares OP_CAT's byte value:

- BIP-342 (tapscript) reserved a class of opcodes called **`OP_SUCCESSx`**. In tapscript, encountering any `OP_SUCCESSx` makes the script **unconditionally valid** — it succeeds immediately without further evaluation. This was deliberately designed as the upgrade hook.
- `OP_SUCCESS126` occupies value **126 / 0x7e — the exact value of the original OP_CAT.** BIP-347 redefines `OP_SUCCESS126` to mean `OP_CAT` *inside tapscript only*.

**Why this is a soft fork, not a hard fork.** Under the old rules, a tapscript spend using `OP_SUCCESS126` *always* succeeds, so any output it guards is spendable by anyone who can produce that script. Under the new rules, the same opcode now imposes real `OP_CAT` semantics, which can only ever make *fewer* scripts valid. New-rule-valid spends are a strict subset of old-rule-valid spends. Old nodes accept everything new nodes accept; therefore enforcing nodes never fork away from the chain non-enforcing nodes follow. That subset-tightening property is the definition of a soft fork.

**Activation parameters are out of scope of BIP-347.** The BIP specifies *semantics*, not *deployment*. The signaling mechanism (BIP-9 versionbits, BIP-8 LOT, or a Speedy-Trial-style window) is a separate decision made at deployment time. This separation is intentional and standard for Bitcoin consensus changes.

**Backwards compatibility.** Legacy (non-tapscript) `OP_CAT` continues to trigger `SCRIPT_ERR_DISABLED_OPCODE`. The change touches the tapscript execution path exclusively.

### 2.2 The reference implementation — the "13 lines"

This is the complete consensus-relevant change, verbatim from BIP-347:

```cpp
case OP_CAT:
{
  if (stack.size() < 2)
    return set_error(serror, SCRIPT_ERR_INVALID_STACK_OPERATION);
  valtype& vch1 = stacktop(-2);
  valtype& vch2 = stacktop(-1);
  if (vch1.size() + vch2.size() > MAX_SCRIPT_ELEMENT_SIZE)
    return set_error(serror, SCRIPT_ERR_PUSH_SIZE);
  vch1.insert(vch1.end(), vch2.begin(), vch2.end());
  stack.pop_back();
}
break;
```

`MAX_SCRIPT_ELEMENT_SIZE` is **520**.

Line-by-line:

1. `if (stack.size() < 2)` → underflow guard; a concat needs two operands. Fails with `SCRIPT_ERR_INVALID_STACK_OPERATION`.
2. `vch1 = stacktop(-2)`, `vch2 = stacktop(-1)` → references to the second-from-top and top elements. Stack order means the result is `x1 || x2` (lower element first).
3. `if (vch1.size() + vch2.size() > MAX_SCRIPT_ELEMENT_SIZE)` → **the one line that retires Satoshi's 2010 concern.** A concatenation that would exceed 520 bytes is rejected with `SCRIPT_ERR_PUSH_SIZE`. Because tapscript already enforces a 520-byte ceiling on every stack element, the exponential-blowup attack is structurally impossible — the cap is enforced at every step, so no sequence of `OP_DUP OP_CAT` can grow past 520 bytes. The original DoS vector is closed by the surrounding consensus rules, which is precisely why re-enabling is now safe.
4. `vch1.insert(... vch2 ...)` → in-place append of `vch2` onto `vch1`.
5. `stack.pop_back()` → drop the now-duplicated top element, leaving the concatenated result.

The modern version differs from the 2010 original in exactly two ways: it uses the structured `set_error` return convention instead of bare `return false`, and it checks the size limit **before** mutating rather than after. Functionally it is the original opcode minus its DoS footgun.

(An independent implementation exists in [Elements](https://github.com/ElementsProject/elements/commit/13e1103abe3e328c5a4e2039b51a546f8be6c60a).)

---

## Part III — The quantum claim, stated honestly

### 3.1 Why concatenation is the unlock

Lamport signatures are built from nothing but a hash function and the ability to **concatenate** values — you reveal preimages selected bit-by-bit from a committed set, and verification hashes and joins them. Bitcoin Script already has `OP_SHA256`; what it lacks in tapscript is a general concatenation primitive. `OP_CAT` supplies exactly that. With it, a Lamport-signature verifier can be written directly in tapscript, and a holder can place such a verifier in a Taproot **script-path leaf**.

This is the basis of Jeremy Rubin's 2021 framing, ["OP_CAT Makes Bitcoin Quantum Secure"](https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2021-July/019233.html), and the related observation that, because `OP_CAT` shipped in the original client, Bitcoin nominally "supported post-quantum cryptography out of the box" before Satoshi removed it.

### 3.2 The caveat the headline omits

BIP-347 itself is careful here, and any serious publication must reproduce the hedge rather than the slogan:

- **The Taproot key-path is the back door.** A Taproot output is spendable *either* by satisfying a script leaf *or* by a single signature against the output's internal key. A quantum adversary with a Shor-capable machine can recover the discrete log of that internal key and spend via the **key-path**, never touching your Lamport-protected script leaf. The hash-based leaf protects nothing if the key-path remains open.
- **NUMS points do not save you.** The standard trick for "disabling" the key-path is committing to a Nothing-Up-My-Sleeve point with no known discrete log. But NUMS security *rests on discrete-log hardness* — the very assumption quantum breaks. Against a quantum attacker a NUMS internal key is as recoverable as any other.
- **No key-path disable exists without a further soft fork.** BIP-347 explicitly states there is no known mechanism to disable a Taproot output's key-path without a separate soft-fork change to Taproot itself.
- **Open question on commitment preservation.** Whether wrapping a Lamport verifier inside a tapscript Merkle commitment even preserves Lamport's quantum resistance is, per the BIP, an open question.

**Net:** `OP_CAT` is necessary infrastructure for expressing post-quantum signatures in Bitcoin Script, and it is a genuinely small consensus change. It is **not**, by itself, a quantum-secure address scheme. A complete migration additionally requires a way to neutralize the key-path (a Taproot-level soft fork) and likely a purpose-built output type. The "one opcode quantum-proofs Bitcoin" compression is false in the same way the "one character" Satoshi quote is false — directionally evocative, technically incomplete.

---

## Part IV — Canonical reference table

| Artifact | Link |
|---|---|
| Satoshi on crypto transition (2010 thread) | [SNI · threads/68](https://satoshi.nakamotoinstitute.org/posts/bitcointalk/threads/68/) |
| Original OP_CAT implementation (pre-disable blob) | [`script.cpp#L381-L393`](https://github.com/bitcoin/bitcoin/blob/01cd2fdaf3ac6071304ceb80fb7436ac02b1059e/script.cpp#L381-L393) |
| Disabling commit 4bd188c ("misc changes", Aug 2010) | [bitcoin/bitcoin@4bd188c](https://github.com/bitcoin/bitcoin/commit/4bd188c4383d6e614e18f79dc337fbabe8464c82) |
| Modern disabled-opcode gate (interpreter.cpp) | [src/script/interpreter.cpp](https://github.com/bitcoin/bitcoin/blob/master/src/script/interpreter.cpp) |
| BIP-347 (OP_CAT in Tapscript) | [bip-0347.mediawiki](https://github.com/bitcoin/bips/blob/master/bip-0347.mediawiki) |
| BIP-347 implementation PR | [bitcoin/bitcoin#29247](https://github.com/bitcoin/bitcoin/pull/29247) |
| Rubin: "OP_CAT Makes Bitcoin Quantum Secure" (2021) | [bitcoin-dev, Jul 2021](https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2021-July/019233.html) |
| Elements alternate OP_CAT impl | [ElementsProject/elements@13e1103](https://github.com/ElementsProject/elements/commit/13e1103abe3e328c5a4e2039b51a546f8be6c60a) |

---

## Part V — Conclusion: a hypothetical reference template

The point of the writeup is that the *primitive* is small but the *complete* construction is not. Below is an illustrative, non-production sketch of what a full OP_CAT-based post-quantum spend path would look like end to end, so the gap between "one opcode" and "quantum-safe address" is concrete. Treat every block as pseudocode for exposition, not a deployable artifact.

### 5.1 Tapscript leaf — one Lamport bit, the OP_CAT role made literal

A Lamport one-time public key is 256 pairs of hash digests; a signature reveals one preimage per message-bit. Per bit, the on-stack check is just hash-and-compare. `OP_CAT`'s job is to fold the 256 verified chunks into a *single* committed value so the leaf script and witness stay compact instead of inlining 256 separate pushes.

```
# ---- HYPOTHETICAL tapscript leaf (one bit shown; real leaf loops 256x) ----
# witness supplies: <preimage_i>  (the revealed Lamport secret for bit i)
# leaf commits to:  <pk_hash_i>   (expected H(secret) for this bit/value)

OP_SHA256                      # H(preimage_i)
OP_DUP                         # keep a copy for the running accumulator
<pk_hash_i> OP_EQUALVERIFY     # bit i authenticated against committed pk chunk

# ---- accumulate into a single linear commitment using OP_CAT ----
# stack: <acc> <H(preimage_i)>
OP_CAT                         # acc := acc || H(preimage_i)
OP_SHA256                      # acc := H(acc || chunk)   (linear hash chain)
# ...repeat for all 256 bits...

<lamport_pubkey_root> OP_EQUAL # final acc must equal the committed PQ root
```

`OP_CAT` is what turns "256 independent equality checks" into "one rolling hash commitment" — without it, the verifier cannot compress the public key on-stack and the construction is impractical.

### 5.2 Output construction — the part that is NOT one opcode

```python
# ---- HYPOTHETICAL construction flow (Python-ish pseudocode) ----
from os import urandom
import hashlib
def H(b): return hashlib.sha256(b).digest()

# 1. Lamport keypair (quantum-resistant: security reduces to hash preimage)
sk = [(urandom(32), urandom(32)) for _ in range(256)]          # 256 secret pairs
pk = [(H(a), H(b)) for (a, b) in sk]                           # 256 public pairs
pq_root = lamport_commit(pk)                                   # linear/Merkle root

# 2. Build the tapscript leaf that verifies a Lamport sig against pq_root
leaf_script = build_lamport_verifier(pq_root)                  # uses OP_CAT + OP_SHA256
leaf = TapLeaf(version=0xc0, script=leaf_script)

# 3. THE UNSOLVED PART: neutralize the Taproot key-path.
#    Today the internal key P is ECDSA/Schnorr -> Shor-breakable.
#    A NUMS point does NOT help: NUMS security == discrete-log hardness.
internal_key = NUMS_POINT          # <-- comment: insufficient vs. a quantum adversary
#    A genuinely safe output requires a *hypothetical* consensus change:
#    e.g. a new output type / tapleaf flag that asserts "key-path disabled,
#    script-path only" and is enforced by nodes. This needs its own soft fork
#    to Taproot and does not exist as of writing.

output = taproot_output(internal_key, tree=[leaf])             # script-path PQ-safe;
                                                               # key-path still a hole
```

### 5.3 The migration template, summarized

```
SAFE_PQ_SPEND  =  RE_ENABLED(OP_CAT)            # BIP-347 soft fork  (done / Complete)
              +   LAMPORT_LEAF(pq_root)         # expressible once OP_CAT exists
              +   KEYPATH_DISABLE(taproot)      # HYPOTHETICAL second soft fork — missing
              +   PQ_OUTPUT_TYPE(...)           # likely a purpose-built address format
```

Only the first line ships today. The third and fourth are the reason "one opcode quantum-proofs Bitcoin" is a slogan, not an architecture: `OP_CAT` makes the post-quantum *signature* sayable in Script, but a post-quantum *output* still needs Bitcoin to grow a way to shut the elliptic-curve key-path — a separate consensus change that, unlike OP_CAT, no one has yet reduced to thirteen lines.
