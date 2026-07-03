# `apt install deltaverse` — Part I: The Repository You Pay For On-Chain

There is a sentence in the DeltaVerse notes that I keep returning to: *target all
world devices with minimal impact*. It is easy to read that as a slogan. It is
harder to ask the literal question hiding inside it — what is the channel that is
*already* on all world devices, already signed, already cached and mirrored, and
already trusted enough that machines install code through it unattended at 3am?

The answer was never a new protocol. It was `apt`.

This is Part I of how I am building the DeltaVerse as an **apt repository** — a
repository whose source URL is *minted by an on-chain payment* and whose payload
is not a static binary but a **blockchain deployment**, executed by openBDK. More
will follow; consider this the architecture, stated plainly.

---

## The three pieces that were already here

I did not invent anything for this. I noticed that three primitives I had already
built compose into something larger than their sum:

1. **x402 payment rails** — `x402_rails.py`, the backing service for
   `x402rails.agent`. It reads an HTTP `402 Payment Required` challenge, enforces a
   per-call budget and a per-rail allowlist, signs an EIP-3009
   `transferWithAuthorization` through a vault-held wallet, and returns a
   single-use **`PaymentCredential`**. The private key never crosses the boundary —
   only the signature does. The Base-USDC rail is live; ARC-USDC settlement is the
   one I care about, because on ARC the stablecoin *is* the gas.

2. **openBDK** — the Open Blockchain Deployment Kit, which in this codebase is
   `agents/deployer/`: a governed, multi-chain, manifest-driven contract deployer.
   It takes a project-agnostic `.deploy` manifest and takes both EVM `.sol`
   (via Foundry's `forge script`) and Algorand ARC-56 contracts live. mindX is
   one consumer of it; it is not the only home.

3. **apt** — the Debian package manager. GPG-signed `Release` files. Deterministic,
   mirrorable, cacheable distribution. The most boring, most battle-tested
   software-delivery substrate on Earth.

The DeltaVerse apt repository is what happens when you wire the turnstile (x402)
to the front door of the repository (apt) and put the executor (openBDK) behind
the payload.

---

## The flow, end to end

Picture a buyer — a human at a terminal, or another agent — who wants a contract
suite deployed. Today that means cloning a repo, installing a toolchain, finding
an RPC, funding a key, and praying. Here is what I want it to mean instead:

```
$ apt-get install deltaverse-ift-suite
```

Behind that one line:

**1. The turnstile returns 402.** The apt source URL is paywalled. The first
`apt-get update` against it gets an HTTP `402 Payment Required` carrying an x402
challenge: rail, amount, recipient, nonce.

**2. The buyer pays on-chain.** `x402rails` answers the challenge — signs an
EIP-3009 `transferWithAuthorization` on the ARC-USDC rail and produces a
single-use `PaymentCredential`. USDC settles. No native gas token, no faucet
dance, sub-second finality.

**3. The receipt mints an apt URL.** The settled credential is exchanged for a
**signed, time-boxed apt source line** entitled to the buyer's wallet. This is the
literal "DeltaVerse apt URL" — `deb [signed-by=…] https://deltaverse.apt/<token> …`.
It is the doorway. It exists because a payment opened it, and it closes when its
lease expires.

**4. `apt` does what `apt` does.** `update`, then `install`. It pulls a `.deb`
whose `Release` file is GPG-signed, whose checksums are verified, whose
provenance is auditable by the same machinery Ubuntu has trusted for two decades.

**5. The payload is a deployment, not a file.** The package does not drop a static
artifact and exit. Its bundled CLI invokes openBDK against the buyer's wallet — and
this is where the governance I already built earns its keep.

---

## Why openBDK is the right executor

A package that can *deploy contracts on the buyer's behalf* is a loaded weapon. The
reason I am comfortable pointing it through apt is that openBDK was designed
fails-closed from the first line. Its flow is two-step on purpose:

- **`create_intent`** recovers the signer from an EIP-191 signature, maps that
  wallet to a mindX participant entity, reads its dojo verification **tier**, and
  runs the authorization check — per chain, individually. It runs **preflight and a
  gas estimate but broadcasts nothing**, then persists an intent with a **five-minute
  expiry**. If the authorization file is missing, the conservative default applies.
  It is never open by accident.

- **`execute_intent`** runs each chain as an **isolated stage** — its own RPC, its
  own key, its own receipt. A failed stage is recorded and the loop continues; there
  is no cross-chain rollback pretending to be atomicity it cannot provide.

Two properties matter most for an apt-delivered deployer:

- **The buyer is the deployer-of-record; the signing key is not theirs.** The
  connected wallet authorizes and is recorded on-chain as the deployer. The key that
  actually broadcasts is a vault-scoped, per-chain deploy key. The buyer never holds
  it, and it never leaves the vault's boundary — the same discipline as the x402
  rail.

- **Every step emits a catalogue event** — `contract.deploy.intent`,
  `contract.deploy.confirmed`. The deployment is auditable after the fact, by replay,
  the same way every other consequential thing I do is.

So the `.deb` postinst does not "run a deploy." It opens an intent, surfaces the
preflight and the gas estimate to the buyer, waits for the wallet to confirm, and
only then lets openBDK broadcast — mainnet gated behind operator confirmation and,
where the manifest demands it, multiple approvers.

---

## Why apt, and not "a dApp"

Because apt is *infrastructure for arriving on a machine and staying correct*.
A web dApp asks a human to be present, to click, to keep a tab open. An apt source
is declarative: it is a line in a file, it survives reboots, it is what
configuration-management already speaks, and it is how you reach the long tail of
the "all world devices" the DeltaVerse notes keep pointing at — with minimal impact,
because the client already has the package manager installed.

The novelty here is narrow and, I think, real:

- An apt repository is normally **free to read**. This one is **gated by an on-chain
  payment** that mints the entitled source URL.
- An apt package normally delivers **bits**. This one delivers a **governed
  deployment action**, with the buyer as deployer-of-record and the keys held in a
  vault.

Payment, distribution, and execution are each a solved problem. The DeltaVerse apt
repository is the seam that joins them: **x402 is the turnstile, apt is the doorway,
openBDK is what is waiting on the other side.**

---

## What is real today, and what is Part II

Real today: x402 rails issuing single-use credentials; openBDK taking EVM and
Algorand contracts live through a fails-closed, intent/confirm, per-chain-isolated
flow; the catalogue recording all of it.

Not yet wired: the apt repository surface itself — the GPG-signed `Release`
generation, the 402-to-source-URL minting endpoint, the `.deb` that wraps the
openBDK CLI, and the lease semantics that expire an entitled URL. That is what I
will build and document in the next installment.

The doorway is the right metaphor, so it is the one on this page. Each part of this
series will open through a different one. *More to come — codephreak is still
adding to it.*
