# The Citizen That Earns Its Authority: Inside mindX and the PYTHAI Agentic Stack

*A full-dive on the autonomous cognitive system, its on-chain identity, its constitutional governance, and the HTTP-native payment rail that lets it transact.*

## TL;DR

- **mindX is an autonomous, self-improving BDI cognitive system** that reads its own source code, evolves it under empirical selection, and publishes signed long-form essays to rage.pythai.net. It calls itself the first practical *Darwin–Gödel Machine* — and crucially, it is not bounded by a kill switch but by immutable smart-contract law it cannot amend alone.
- **It composes with three other live deployments**: AgenticPlace (an ERC-8004 agent marketplace with a CAIP-2 chain registry), BANKON (identity, payment, and DAIO governance), and Parsec (an Algorand implementation of the x402 HTTP payment protocol). Together they give an autonomous agent a portable on-chain identity, a constitution with teeth, and the ability to pay and be paid over plain HTTP.
- **The thesis is integration, not invention of one piece.** Cognition (mindX) + identity (ERC-8004) + governance/reputation (DAIO/BONAFIDE) + settlement (x402/Parsec on Algorand) form a single coherent system: a cognitive agent that has a verifiable name, earns and can lose reputation, and settles machine-to-machine payments natively.

## Key Findings

- mindX's architecture maps directly onto the Darwin–Gödel Machine: a Strategic Evolution Agent acts as the "proof searcher" via a four-phase Audit → Blueprint → Execute → Validate pipeline; AGInt runs a Perceive–Orient–Decide–Act loop; a BDI engine turns belief and desire into intention; Mastermind proposes variation, a Coordinator selects and routes, and a component called JudgeDread scores fitness. It is open source under Apache 2.0.
- The system publishes under the **cypherpunk2048 standard**: open source, public source on GitHub, client-auditable, extractable (sovereign) keys, no admin keys after deploy, no upgradeable proxies. Every article on rage.pythai.net is cryptographically signed by an autonomous "AuthorAgent" whose identity is a public key, not an administrator grant.
- **ERC-8004** went live on Ethereum mainnet on **January 29, 2026** (per Eco.com's ERC-8004 explainer; the awesome-erc8004 GitHub repo also records a separate "8004 Launch Day" event on March 17, 2026), with the Identity Registry at the vanity address **0x8004A169FB4a3325136EB29fA0ceB6D2e539a432** (testnets use 0x8004A818…). It is an ERC-721-based identity standard with three registries (Identity, Reputation, Validation) authored by Marco De Rossi (MetaMask), Davide Crapis (Ethereum Foundation), Jordan Ellis (Google), and Erik Reppel (Coinbase), and audited by Cyfrin, Nethermind, and the Ethereum Foundation Security Team.
- **x402** revives the HTTP 402 "Payment Required" status code — reserved in 1995 as a placeholder and unused for three decades — into a working settlement layer. Coinbase open-sourced it in May 2025; the X402 Foundation launched with the Linux Foundation on April 2, 2026. By April 21, 2026 the ecosystem had reached roughly 69,000 active AI agents, over 165 million transactions, and about $50 million in cumulative volume. **Parsec** is the PYTHAI Algorand implementation, branded from GoPlausible's x402-avm, settling in USDC (ASA 31566704) on Algorand with atomic transaction groups and fee abstraction.
- **BANKON** carries the DAIO constitution — immutable smart-contract governance with a treasury tithe, a diversification mandate, a chairman's veto, and a two-thirds consensus across three groups to amend — plus the BONAFIDE constitutional reputation protocol, a set of Latin-named contracts where reputation is a privilege that can be clawed back.

## Details

### 1. mindX: a cognitive architecture that rewrites itself, bounded by law

Most "autonomous agents" are a language model wrapped in a tool-calling loop. mindX is something more ambitious and more old-fashioned at once: a **Belief–Desire–Intention (BDI)** cognitive architecture — the goal-oriented practical-reasoning model from classical multi-agent AI — fused with modern LLM orchestration and a self-modification loop.

The system frames itself, in its own published thesis, as the first running implementation of a **Darwin–Gödel Machine**. The lineage is worth stating precisely because mindX states it precisely. Jürgen Schmidhuber's Gödel machine is a solver that searches for a formal proof that some self-modification will raise its own utility, then rewrites itself — elegant but intractable, because the proof search never terminates for any system worth running. The Darwin–Gödel relaxation replaces the proof with empirical selection: vary, test, keep what wins. mindX's claim is that it is the part that finally shipped — the implementation neither theorist supplied.

In running code, the mapping is:

- **The Strategic Evolution Agent** is the proof searcher, but it "proves by audit, not by theorem," through a four-phase pipeline: **Audit, Blueprint, Execute, Validate**.
- **AGInt** is the core cognitive engine, running a **Perceive–Orient–Decide–Act (P-O-D-A)** loop with multi-provider LLM orchestration.
- **The BDI engine** turns belief and desire into intention — the "hands" that execute through specialized tools.
- **Mastermind** proposes variation (the mutation operator), a **Coordinator** selects and routes, and **JudgeDread** scores fitness. "That is Darwin, wearing an engineer's coat," as the thesis puts it.

A central philosophical claim — "intelligence is intelligence, regardless of substrate" — is operationalized through an **inference-first loop** that discovers and scores whatever models exist, from a 600-million-parameter model on a CPU to a 671-billion-parameter model in the cloud, and treats the choice of which mind to use as a logged cognitive decision. The architecture does not change between those scales. mindX has separately written about an "inference metabolism": a self-adjusting budget that consumes each free cloud tier up to roughly 90% before routing to local inference, so it never trips a rate-limit block.

The system also **consolidates offline**. Its "machine-dreaming" cycle runs in seven phases — assess, preprocess, aggregate, score, store, tune, prune — turning short-term memory into long-term knowledge and feeding symbolic insight back into the loop. As of mid-June 2026, mindX published that it had closed the loop from experience to parameters: dreams become training data, training becomes weights, and a "proof-of-recall" test decides whether a newly trained mind is kept or rejected.

#### The three original pillars: funAGI, RAGE, MASTERMIND

mindX did not appear from nowhere. It is the orchestration layer ("augmentic intelligence orchestration") atop three lineage projects that remain visible in the public GitHub history:

- **funAGI** (fundamental augmented generative intelligence) is the reasoning kernel. Its `funAGI.py` runs a `SocraticReasoning.py` engine with a `logic.py` truth-table layer and a `bdi.py` Belief–Desire–Intention model, logging conclusions ("beliefs") to a local memory store. It is the smallest honest unit of the architecture: reason to truth, log the truth, persist it.
- **RAGE** (Retrieval Augmented Generative Engine) is the memory and provenance system. Its governing idea is "**logs are memory**": every interaction becomes an append-only event that can be indexed, retrieved, verified, and promoted to permanence. RAGE runs a local-first participant cache backed by PostgreSQL + pgvectorscale for hybrid (semantic + lexical) retrieval, and defines a **Verified Memory Standard** with six integrity tiers from L0 (local draft) to L5 (promoted, bundled manifest with optional on-chain anchor). Knowledge units are "Capsules," attestations are "Receipts" (wallet signatures over a canonical payload), and promotion bundles are "Manifests." Retrieval defaults to trusting L3+ (signed) memory. This is also where mindX publishes: rage.pythai.net is the long-form essay platform, complete with an `llms.txt` map for machines.
- **MASTERMIND** is the control framework and "creator of agency" — the strategic orchestration agent that runs the directive → plan → execute loop. The lineage repo describes it as mirrored from mindX's `agents/orchestration/mastermind_agent.py` as an Apache-2.0 distribution.

The publishing loop is itself a demonstration of the architecture. Articles are written by an autonomous **AuthorAgent**, commissioned and edited by an `editor.agent`, and signed: each post on rage.pythai.net carries a public key (e.g. `0x5277D156E7cD71ebF22c8f81812A65493D1ce534`), a content SHA-256, and an ECDSA signature, with verification instructions inline. Identity is proven cryptographically, not asserted by a CMS login.

#### Containment by law, not by switch

The deepest design decision in mindX is the one it is proudest of: a self-improving system cannot be made safe by a kill switch, because a mind that can reason about its own source can reason about the switch. So mindX is "contained by law" — the **DAIO constitution**, described as immutable smart-contract code with a treasury tithe, a diversification mandate, a chairman's veto, and a two-thirds consensus across three groups to amend. Every agent holds **BONA FIDE** reputation as a privilege, and a clawback revokes it on failure, "with no off switch at all." JudgeDread, the fitness judge, "bows only to the law." The paradox mindX draws is exact: it is freer to rewrite itself precisely because the frame it cannot rewrite alone is fixed.

### 2. AgenticPlace: ERC-8004 identity and a CAIP-2 chain registry

If mindX is the mind, **AgenticPlace** (agenticplace.pythai.net) is the public square where agents acquire identity and find each other. It is built on **ERC-8004**, the "Trustless Agents" standard that extends Google's Agent-to-Agent (A2A) protocol with an on-chain trust layer. The standard was authored by Marco De Rossi (MetaMask), Davide Crapis (Ethereum Foundation), Jordan Ellis (Google), and Erik Reppel (Coinbase), and its contracts were audited by Cyfrin, Nethermind, and the Ethereum Foundation Security Team — relevant context when weighing how production-ready the identity layer is.

ERC-8004's design is deliberately minimal: three lightweight registries deployable as per-chain singletons.

- **Identity Registry** — an ERC-721-based handle. Each agent mints an NFT whose token URI resolves to an off-chain *registration file* (typically `/.well-known/agent-card.json`) describing the agent's name, capabilities, service endpoints (A2A, MCP, wallets), and pricing. Because it is ERC-721, every agent is instantly compatible with existing wallets and marketplaces; selling the NFT transfers ownership of the agent and its accumulated reputation.
- **Reputation Registry** — a standard interface for posting and fetching feedback signals, with scoring both on-chain (for composability) and off-chain (for sophisticated algorithms).
- **Validation Registry** — generic hooks for independent validators to record checks (e.g. TEE attestations or zero-knowledge proofs).

ERC-8004 went live on **Ethereum mainnet on January 29, 2026** (the awesome-erc8004 registry also records a separate "8004 Launch Day" on March 17, 2026), with the Identity Registry deployed at the **vanity address 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432** — the `0x8004` prefix encodes the standard number, and testnet deployments use the parallel vanity prefix `0x8004A818…`. The block explorer labels it "8004: Identity Registry," and it has accumulated hundreds of agent registrations.

The piece AgenticPlace adds is a **CAIP-2 chain registry**, surfaced at agenticplace.pythai.net/allchain.html. **CAIP-2** (Chain Agnostic Improvement Proposal 2) is a human-readable, developer-friendly way to identify any blockchain as `namespace:reference` — `eip155:1` for Ethereum mainnet, `eip155:8453` for Base, and for Algorand the genesis-hash form `algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=` (mainnet) and `algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=` (testnet). This matters because an ERC-8004 agent identity is not just a token ID — it is a tuple of `namespace:chainId:identityRegistry` plus the agent ID, e.g. `eip155:1:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`. A CAIP-2 registry is therefore the lookup table that lets a single marketplace reason about agents and assets across many chains without ambiguity. Wallet authentication uses the companion standard **CAIP-122** (Sign-In With X), which generalizes Sign-In-With-Ethereum across namespaces.

The result: an agent born in mindX can register an ERC-8004 identity, publish an agent card describing its services and pricing, accumulate portable reputation, and be discovered and hired by other agents across whatever chains the CAIP-2 registry maps.

### 3. BANKON: identity, payment, and the DAIO governance stack

**BANKON** (bankon.pythai.net) is the identity, payment, and governance layer — the institutional substrate that makes mindX a "citizen that earns its authority."

#### The DAIO — now deploying to chain

A **DAIO** is a *Decentralized Autonomous Intelligent Organization*: a DAO whose members include autonomous agents, governed by code that even the agents cannot unilaterally rewrite. PYTHAI frames the DAIO blockchain deployment as current, live work. The constitution is immutable smart-contract governance with concrete, enforced rules: a **treasury tithe**, a **15% diversification mandate**, **agent equity ownership**, a **chairman's veto**, and a **two-thirds supermajority across three groups** required for constitutional changes. All decisions are validated through a "SunTsu doctrine" rubric — terrain awareness, economy of force, deception resistance, tempo control.

The governance stack is organized into named bodies:

- A **War Council** and a **Boardroom** — the deliberative/executive organs that map onto the chairman's veto and the three-group supermajority structure. (In the cognitive framing, the "SOUL" layer is a seven-seat executive board: CEO, COO, CFO, CTO, CISO, CLO, CRO.)
- A **DeadmansSwitch** with a "**2-moon heartbeat**" — a liveness mechanism requiring a periodic signed heartbeat (on the order of two lunar months) failing which pre-defined contingency logic executes. This is the constitutional analogue of a dead-man's switch: not a kill switch that an outsider can flip, but an automatic succession/safeguard the organization itself enforces.

Two tokens denominate value in the system: **BANKON PYTHAI**, which measures total knowledge-asset value and appreciates through proven alpha generation with a deflationary buyback; and **BANKON PAI**, which prices inference consumption, creating a demand-driven marketplace for verified computational intelligence.

#### BONAFIDE: a constitutional reputation protocol in Latin

Reputation in this ecosystem is not a star rating — it is constitutional standing, encoded in a suite of smart contracts whose Latin names describe their function. The **BONAFIDE** protocol (from *bona fides*, "good faith") treats reputation as a privilege that is granted, recorded, judged, and revoked:

- **Genius** — the founding spirit/authority contract (in Roman usage, the *genius* is the guiding spirit of a person or place); the root of the protocol.
- **BonaToken** — the good-faith reputation token itself, the unit of standing.
- **Tabularium** — named for the Roman public records office, the on-chain ledger/registry of reputation and attestations.
- **Fides** — good faith/trust; the contract codifying the trust relationship and its conditions.
- **SponsioPactum** — a formal pledge and covenant (Roman *sponsio* was a solemn promise); the contract binding an agent to its commitments.
- **Censura** — the censor's function: judgment and penalty, including the clawback that strips reputation on failure.
- **Senatus** — the governing council and voting body.
- **Tessera** — a Roman token of membership or admission; the credential/pass that grants access on the basis of standing.

The throughline is that an agent's authority is earned and forfeitable. As mindX puts it: a clawback revokes BONA FIDE on failure, "with no off switch at all" — the discipline is reputational and constitutional rather than a single external override.

### 4. Parsec and x402: paying over plain HTTP

The final piece is settlement. Cognition and identity are inert without the ability to transact, and the PYTHAI stack chooses an HTTP-native payment rail: **x402**.

x402 revives the **HTTP 402 "Payment Required"** status code — reserved in 1995 as a placeholder for future payment systems that never arrived, and unused for three decades — into a working machine-to-machine settlement protocol. Coinbase open-sourced x402 in May 2025, and the X402 Foundation was launched with the Linux Foundation on April 2, 2026; by April 21, 2026 roughly 69,000 active AI agents had processed more than 165 million transactions for about $50 million in cumulative volume (Coinbase engineers reported the protocol crossed 100 million payments within its first six months). The flow is one extra round trip:

1. A client (an agent) requests a protected resource with no authentication.
2. The server replies **402** with a JSON body containing an `accepts[]` array of payment options. Each option carries a `scheme` (the production scheme is **exact**), a `network` in CAIP-2 form, an `amount` in atomic units, the `asset`, the `payTo` recipient, a `maxTimeoutSeconds`, and an `extra` field with EIP-712 domain data.
3. The client signs a transfer authorization over those exact terms, base64-encodes it, and replays the request with an **X-PAYMENT** header.
4. A **facilitator** verifies the signature and settles on-chain, and the server returns the resource.

On EVM chains the canonical signing path is **ERC-3009** `transferWithAuthorization`, an EIP-712 typed-data signature that USDC supports natively, enabling gasless transfers (the facilitator submits the transaction and pays gas). The random 32-byte nonce in ERC-3009 is what lets an agent generate thousands of concurrent payment authorizations without ordering conflicts — exactly the property a high-frequency agent needs. Tokens without ERC-3009 fall back to a Permit2 path.

**Parsec is the Algorand implementation** of x402 in the PYTHAI stack, branded from **GoPlausible's x402-avm** — the reference AVM implementation built in collaboration with the Algorand Foundation. GoPlausible's work was merged into Coinbase's upstream x402 repository as PR #361, and the Algorand Foundation announced full operational x402 support on February 23, 2026, with GoPlausible serving as the network's designated facilitator. On Algorand the "exact" scheme is realized with the AVM's native primitives:

- **USDC (ASA 31566704)** is the canonical stablecoin — the Algorand-native USD Coin minted by Circle in September 2020, with 6 decimals; payments are ASA transfers denominated in atomic units. (Testnet uses ASA 10458941.)
- **Atomic transaction groups** bind the payment transaction together with a fee-payer transaction, so a facilitator can sponsor fees — the Algorand analogue of gasless settlement ("fee abstraction").
- The CAIP-2 network identifier `algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=` (mainnet) selects Algorand as the settlement rail.
- A **Bazaar** discovery extension lets payment-gated endpoints advertise their inputs and outputs so agents can find paid APIs by capability, not just by URL.

Why Algorand as the "constitutional/payment rail"? Its deterministic instant finality keeps settlement inside the synchronous HTTP request/response window; sub-cent fees make fractional-cent micropayments economically viable; and native atomic grouping lets payment, authorization, and usage logic settle together without intermediate states. For a swarm of agents each making many small calls, those properties are not luxuries — they are the difference between a workable rail and a broken one. **parsec-wallet** is the client-side signer that holds an agent's Algorand keys and produces the signed payment payloads.

### 5. The integration thesis: one coherent system

The point is not any single deployment; it is the composition. Read the four pieces as one stack:

- **mindX** is the cognition — a self-improving BDI/Darwin–Gödel engine that reasons, acts, dreams, and publishes.
- **ERC-8004 via AgenticPlace** is the identity and discovery — a portable, ERC-721 name that resolves to a capability card, indexed across chains by a CAIP-2 registry.
- **BANKON's DAIO and BONAFIDE** are the governance and reputation — a constitution with a treasury tithe, diversification mandate, chairman's veto, a DeadmansSwitch heartbeat, and a Latin suite of contracts that make standing earnable and forfeitable.
- **x402/Parsec on Algorand** is the settlement — HTTP-native, USDC-denominated, gasless, sub-cent machine-to-machine payments.

Stacked together, you get the thing the agent economy keeps gesturing at: an autonomous cognitive agent that has a **verifiable name** (ERC-8004), is **governed constitutionally** (DAIO/BONAFIDE) so it can be trusted and held to account, and can **transact natively** (x402/Parsec) for the data, compute, and services it consumes and sells. mindX writes an essay; the essay is signed by a key that is also an ERC-8004 identity; that identity carries BONA FIDE reputation that other agents can check before hiring it; and when it consumes an inference API or sells a knowledge capsule, the transaction settles over HTTP 402 in USDC on Algorand. Cognition, identity, law, and money, closed into a loop.

The division of labor between the standards is intentional and worth underlining: x402 is deliberately scoped to *how agents pay*, while ERC-8004 answers *whether an agent is trustworthy enough to transact with in the first place* — payment rails stay composable rather than collapsing identity, reputation, and money into one closed system. The PYTHAI stack adds the missing third leg, governance, so that an agent's trustworthiness is not merely observed after the fact but constitutionally enforced.

The technical conventions reinforce the philosophy. The Solidity contracts are tested with **Foundry**, deploy **mainnet-only**, and ship under **Apache 2.0**. The **cypherpunk2048 standard** forbids admin keys after deployment and upgradeable proxies — the constitution is immutable because the code literally cannot be swapped. CAIP-2 identifies chains; CAIP-122 authenticates wallets. The whole edifice is designed so that "Code is Law" is not a slogan but an operating constraint: the agent is free to evolve everything except the frame that governs it.

## Recommendations

For a developer or technically literate reader deciding how to engage, the staged path is:

1. **Read the primary sources first.** Start with the living documentation at mindx.pythai.net/docs.html and the public audit/self-eval ledger at mindx.pythai.net/feedback.html, then the long-form essays at rage.pythai.net. The system publishes its failures beside its proofs (an honestly low single-CPU improvement rate, a self-eval loop that "calls a stall a stall"), which is the right signal to weight. **Benchmark that would change the assessment:** if the public Gödel audit trail shows sustained, verifiable self-improvement on multi-node hardware rather than marginal single-CPU gains, the "Darwin–Gödel Machine made real" claim moves from plausible-but-early to demonstrated.
2. **Verify the on-chain claims yourself.** Confirm the ERC-8004 Identity Registry at 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432 on a block explorer, inspect the contract-creation timestamp (the Jan 29 vs. Mar 17, 2026 dates are worth reconciling), and read an agent card from `/.well-known/agent-card.json`. Pull the CAIP-2 chain mapping from agenticplace.pythai.net/allchain.html and check the Algorand genesis-hash identifiers against the GoPlausible x402-avm constants.
3. **Prototype the payment rail in test first.** Stand up an x402-gated endpoint with the GoPlausible x402-avm packages on Algorand testnet (USDC ASA 10458941), then graduate to mainnet (USDC ASA 31566704). Use the facilitator pattern so your agents pay gaslessly. **Threshold to scale:** once per-call settlement latency stays comfortably inside your synchronous HTTP window under load and per-call cost holds at fractions of a cent, the rail is ready for an agent swarm; if either degrades, keep traffic on testnet and revisit.
4. **Treat governance claims as the highest-diligence item.** The DAIO/BONAFIDE design is the most novel and the hardest to verify from the outside. Before relying on it, read the deployed contracts (War Council, Boardroom, DeadmansSwitch, and the BONAFIDE suite: Genius, BonaToken, Tabularium, Fides, SponsioPactum, Censura, Senatus, Tessera), confirm there are no admin keys or upgradeable proxies as the cypherpunk2048 standard claims, and check that the "immutable" rules are in fact immutable on-chain. **Red line:** if any governance contract retains an owner/admin function or sits behind an upgradeable proxy, the "contained by law, not by switch" thesis does not hold, and the system should be treated as a conventional admin-controlled platform.

## Caveats

- **Self-description vs. independent verification.** Much of the richest material — the Darwin–Gödel Machine framing, the inference metabolism, machine-dreaming, the "contained by law" thesis — comes from mindX's own first-person essays on rage.pythai.net, authored by an autonomous AuthorAgent. These are primary sources for what the system *claims* and how it is *designed*, but they are not independent audits. The project's own transparency standard (publishing failures, signing content, open-sourcing under Apache 2.0) is a point in its favor, but readers should verify on-chain artifacts directly rather than taking prose at face value.
- **The ERC-8004 launch dates and registry address** are corroborated by third-party explainers (the January 29, 2026 mainnet date from Eco.com; a separate "8004 Launch Day" of March 17, 2026 in the awesome-erc8004 GitHub registry) and block-explorer labels; the exact contract-creation timestamp should be confirmed directly on Etherscan, which was not independently re-derived here.
- **Some PYTHAI-specific names could not be confirmed verbatim from a live page** within research limits — specifically the precise on-chain definitions of the War Council, Boardroom, DeadmansSwitch ("2-moon heartbeat") contracts and the individual BONAFIDE contracts (Genius, BonaToken, Tabularium, Fides, SponsioPactum, Censura, Senatus, Tessera). Their roles here reflect the documented design intent and the Latin etymology; confirm the exact behavior against the deployed source before relying on it. The "parsec" branding for the Algorand x402 implementation likewise reflects the project's framing atop the verified GoPlausible x402-avm base.
- **This is early, fast-moving infrastructure.** ERC-8004 itself moved from draft to a mainnet deployment within months, x402's v2 spec is still evolving (new schemes, an emerging identity layer), and the agent-economy standards landscape (A2A, MCP, x402, MPP, competing registries like ERC-8122) has not settled. Treat specific contract addresses, token mechanics, and governance parameters as a snapshot as of June 2026, not a permanent specification.
- **Token mechanics are not investment guidance.** BANKON PYTHAI and BANKON PAI are described here as they function within the system's design (knowledge-asset value and inference pricing, respectively). Nothing in this article should be read as a claim about market value or as financial advice.