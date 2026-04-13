# Consensus Mathematics

Prime number consensus for governance from dictator to democracy.

## The Prime Number Foundation

Consensus ratios derive from prime denominators. Primes are indivisible — so is legitimate authority. The smallest primes (2, 3) generate all governance forms. Composites (4, 6, 9, 99, 100) emerge from primes and inherit their consensus properties.

A consensus ratio `a/b` where `b` is prime cannot be subdivided further. This is why 2/3 is the natural threshold for majority governance — three is the smallest group that can have a non-trivial majority. Two is the smallest group that can agree.

## Governance Spectrum

All governance exists on a spectrum from one voice to all voices. The transitions are not smooth — they break at prime boundaries. The 50% point is not a transition — it is a stalemate where governance fails.

```
DICTATOR ──→ MAJORITY ──→ MARRIAGE ──→ UNILATERAL
  1/3           2/3         2:2          3/3
(broken)    (consensus)     3:3       (unanimous)

         ╳ 50% — stalemate — infinite deliberation ╳
         (autonomous mode only: Kairos resolves what votes cannot)
```

### 1/3 — Diffusion (Three Dictators)

1/3 is not one dictator ruling three. 1/3 is the diffusion of one admin into three dictators — each holds 1/3, none holds majority. The single admin who was 1/1 becomes three actors at 1/3 each. No one can act alone. But no two are yet required to agree.

This is the moment of diffusion, not the moment of consensus. Consensus begins at 2/3 when two of the three must agree. At 1/3, each actor is a dictator of their own domain but powerless over the whole. Three dictators, not one.

**In DAIO**: The Chairman's Veto in `DAIO_Constitution.sol` is a controlled 1/3 — the chairman can block but cannot act alone. The chairman's power is one-third: the power to prevent, not the power to create. The other two thirds belong to the domains.

**In the Boardroom (v1)**: The CEO directs. The seven soldiers deliberate. The CEO does not vote — the CEO frames the question. This is 1/3 power: agenda-setting without decision-making. The CEO is one of three forces (CEO, veto holders, majority) and none of the three is sufficient alone.

```
DAIO_Constitution.sol:
  chairman can veto    → 1/3 power (prevent, not create)
  chairman cannot spend → cannot act alone
  chairman cannot amend → immutability constrains all three dictators
  
  1/3 is diffusion of authority, not concentration of it.
  1 admin → 3 actors, each with 1/3, none with majority.
  This creates three dictators. 2/3 consensus dissolves them into governance.
```

### 2/3 — Majority (Triumvirate)

Two voices out of three. The natural supermajority. This is the consensus threshold where legitimacy begins — one voice can dissent without blocking.

**In DAIO**: `TriumvirateGovernance.sol` implements this directly:
- Three domains: Development, Community, Marketing
- Each domain votes internally (2 human + 1 AI = 3 votes, 2/3 required)
- Overall: 2 of 3 domains must approve
- Result: 2/3 at both levels — fractal consensus

**In the Boardroom**: The default supermajority threshold is 0.666 (66.6%). Seven soldiers vote. The weighted score must reach 2/3 for approval. Below that, mixed votes produce "exploration" — dissent creates branches, not blocks.

```
TriumvirateGovernance.sol:
  DEVELOPMENT  → 2/3 internal consensus
  COMMUNITY    → 2/3 internal consensus
  MARKETING    → 2/3 internal consensus
  Overall      → 2/3 of domains (2 of 3)
```

### 3/3 — Unilateral (Full Consensus)

All voices agree. The rarest and most powerful governance outcome. Required only for constitutional changes — amendments to the rules themselves.

**In DAIO**: Constitutional proposals require 3/3 domain approval with 14-day timelock. No domain can be overruled. No voice silenced. This is the governance equivalent of unanimity — the system will not change its own foundation without complete agreement.

**In the Boardroom**: Consensus threshold of 1.0 (100%) can be set for constitutional-importance directives. Every soldier must approve. One reject blocks.

```
Proposal types and their consensus requirements:
  OPERATIONAL    → 1/3 of domains  (1 domain)   + 1-day timelock
  STRATEGIC      → 2/3 of domains  (2 domains)  + 7-day timelock
  ECONOMIC       → 2/3 of domains  (2 domains)  + 3-day timelock
  CONSTITUTIONAL → 3/3 of domains  (3 domains)  + 14-day timelock
  EMERGENCY      → Chairman's veto (1/3 dictator) + EmergencyTimelock
```

## MarriageDAO — The Dyad

When the group size is 2, consensus mathematics changes. There is no majority — only agreement or deadlock.

### 2:2 — Partnership

Two parties, both must agree. This is marriage governance: neither party can overrule the other. Deadlock is not a failure — it is a feature. If two parties cannot agree, the action does not proceed. The cost of deadlock is inaction. The benefit is that neither party can be coerced.

**Application**: Joint custody of treasury keys. Multi-sig wallets where 2-of-2 is required. Agent pair-bonding where both agents must consent to a shared action.

### 3:3 — Triumvirate Marriage

Three parties, all must agree. This combines the triumvirate structure (3 members) with marriage consensus (full agreement). It is harder than 2/3 — every voice has veto power. This is appropriate for irreversible actions where all stakeholders bear equal risk.

**Application**: Constitutional amendments in DAIO (3/3 domain approval). Credential revocation (requires all issuers to agree). Identity destruction (cannot be undone).

```
MarriageDAO consensus:
  2:2 → Partnership: deadlock = no action (safe default)
  3:3 → Triumvirate marriage: every voice vetoes (maximum caution)

  Neither form has a majority. Both require unanimity.
  This is governance for actions where the cost of error exceeds the cost of delay.
```

## SupremeCourtDAO — The Odd Prime Bench

The Supreme Court of Canada sits 9 justices. 9 is not prime (9 = 3 × 3), but the consensus math is prime: 5/9 majority. 5 is prime. The quorum is 5. The minimum panel that can decide law is also the minimum majority of the full bench. This is not coincidence — it is the smallest odd number that constitutes a majority of 9, and odd numbers prevent ties.

### 5/9 — Judicial Consensus

5 of 9 justices must agree to decide a case. 4 can dissent. The dissenting opinions are published — dissent is not silenced, it is recorded. This is the judicial equivalent of the boardroom's "exploration" outcome: minority views create precedent for future cases, not obstruction of the current one.

```
Supreme Court of Canada:
  9 justices (Chief Justice + 8 puisne)
  Quorum: 5 (the court cannot sit with fewer)
  Majority: 5/9 = 55.6%
  Dissent: published, creates future precedent

  9 = 3 × 3 — the bench is a triumvirate of triumvirates
  5/9 majority — the smallest odd majority of the full bench
  Constitutional cases heard en banc (all 9)
  Other cases may sit 5 or 7 (always odd — no ties)
```

**SupremeCourtDAO maps to DAIO governance** for judicial-weight decisions — interpretations of the constitution, not amendments to it. When the boardroom must interpret constitutional constraints (what does the 15% diversification mandate mean for a specific allocation?), the consensus model is 5/9: a majority of interpreters, not a supermajority of legislators.

```
SupremeCourtDAO consensus:
  5/9 = 55.6% — judicial majority (interpretation)
  2/3 = 66.7% — legislative majority (governance)
  3/3 = 100%  — constitutional amendment (foundation)

  Interpretation requires less consensus than legislation.
  Legislation requires less consensus than amendment.
  The threshold rises with the permanence of the decision.
```

**Application in DAIO**: A 9-member judicial panel (expandable from the boardroom's 7 soldiers + CEO + 1 additional arbiter) for constitutional interpretation disputes. Not every governance question is a vote — some are questions of meaning. SupremeCourtDAO decides what the constitution means. The boardroom decides what to do about it.

## UNDAO — Governance at Civilizational Scale

The United Nations is two governance systems operating simultaneously: the Security Council (the superpowers) and the General Assembly (the world). They are not the same body. They do not use the same consensus. They do not have the same authority. This duality maps directly to DAIO.

### The Security Council is the Boardroom

The UN Security Council has 15 members: 5 permanent (P5) with veto power + 10 non-permanent elected for 2-year terms. Resolutions require 9/15 votes (60%) with no veto from any P5 member.

```
UN Security Council:
  15 members total
  5 permanent (P5): USA, China, Russia, UK, France — each has veto
  10 non-permanent: elected by General Assembly, 2-year terms
  Consensus: 9/15 = 60% with zero P5 vetoes
  One veto from one superpower blocks everything

  This is the boardroom:
  - Small body with outsized authority
  - Weighted votes (P5 veto = infinite weight)
  - Decisive on matters of action (sanctions, intervention, force)
  - Can be paralyzed by a single dissent from a veto holder
```

**The Boardroom parallel**: CEO + 7 Soldiers = 8 members. CISO and CRO have 1.2x veto weight. The P5 veto is the extreme case of weighted consensus — one voice overrides all others. In DAIO, the Chairman's Veto in `DAIO_Constitution.sol` is the P5 equivalent: emergency power that blocks regardless of majority.

The Security Council's dysfunction is instructive: when P5 members veto for self-interest rather than collective security, the body is paralyzed. This is why DAIO constrains veto power constitutionally — the chairman can veto, but cannot spend, cannot amend, cannot act unilaterally beyond the emergency pause. Veto is a brake, not a steering wheel.

### The General Assembly is the Dojo

The UN General Assembly has 193 member states. Each has one vote. Resolutions are advisory — they express the will of the world but cannot compel action. The General Assembly cannot override a Security Council veto. It can only make visible what the world thinks.

```
UN General Assembly:
  193 member states
  1 vote each — no veto, no weighting
  Resolutions: advisory (non-binding)
  Majority: simple majority for most, 2/3 for "important questions"
  Cannot override Security Council veto
  Power: legitimacy, not force

  This is the Dojo:
  - Large body with equal standing
  - Reputation-based influence (BONA FIDE)
  - Advisory on all matters — shapes opinion, not action
  - Cannot override boardroom decisions
  - Power through collective voice, not executive authority
```

**The Dojo parallel**: The Dojo (`daio/governance/dojo.py`) is DAIO's reputation system — every agent has a standing, every agent can participate, but the Dojo does not make executive decisions. The Dojo shapes the reputation that informs boardroom weight. An agent with high Dojo reputation is heard more seriously in the boardroom, just as a General Assembly resolution backed by 180+ nations puts moral pressure on the Security Council — but cannot override a P5 veto.

### The UNDAO Duality

```
UNDAO structure:

  Security Council (Boardroom)          General Assembly (Dojo)
  ─────────────────────────────         ──────────────────────────
  15 members                            193 members
  5 permanent with veto (P5)            1 vote each, no veto
  9/15 consensus + zero vetoes          Simple majority / 2/3
  Binding resolutions                   Advisory resolutions
  Action: sanctions, force              Influence: legitimacy
  Paralyzed by single P5 veto          Cannot be paralyzed
  Small, decisive, exploitable          Large, representative, slow

DAIO mapping:

  Boardroom (Security Council)          Dojo (General Assembly)
  ─────────────────────────────         ──────────────────────────
  CEO + 7 Soldiers (8 members)          All agents (unbounded)
  CISO/CRO 1.2x veto weight            Equal BONA FIDE standing
  1/3, 2/3, 3/3 consensus              Reputation scoring
  Binding: directives execute           Advisory: reputation informs
  Action: resource allocation           Influence: trust signals
  Chairman's Veto (emergency)           No veto — collective voice
  Small, decisive, weighted             Large, inclusive, deliberative
```

The UN's lesson for DAIO: neither body alone is sufficient. The Security Council without the General Assembly is oligarchy. The General Assembly without the Security Council is debate without consequence. Governance requires both — a small decisive body constrained by the legitimacy of a large representative one.

In DAIO: the boardroom decides. The Dojo legitimizes. An agent with zero Dojo reputation that gains boardroom weight is a P5 member acting without legitimacy — technically empowered, structurally dangerous. An agent with maximum Dojo reputation and no boardroom seat is a General Assembly resolution — morally authoritative, practically powerless. The system works when both bodies are connected: Dojo reputation flows into boardroom weight, boardroom decisions are visible to the Dojo.

## The Weakness of Democracy — 50% and Infinite Deliberation

50% is not a governance threshold. It is the point where governance fails. Any split of the board at 50% is a stalemate. Neither side has authority. Deliberation continues indefinitely with no mechanism for resolution.

This is the weakness of democracy, not democracy itself. Democracy at 50/99 or 51/100 is the early work — the attempt to govern with the thinnest possible consensus. The insight from that work:

### 50/99 — The Stalemate Edge

99 members. 50 approve. One voice more than half. This is not consensus — this is a coin flip with the illusion of legitimacy. 49 voices are overruled by a single vote margin. The winning coalition has no depth. The losing coalition has every reason to defect.

### 51/100 — The Tie That Breaks Nothing

100 members. 51 approve. Ties are possible at 50/50. When the body splits evenly, the default outcome (no action) prevails. This is governance that can be paralyzed by its own structure.

### Why 50% Cannot Be a Boardroom Setting

A consensus threshold of 0.5 creates a position of **infinite deliberation**. With weighted votes (CISO 1.2x, CRO 1.2x, CLO 0.8x), a near-even split oscillates around 0.5 without resolving. The boardroom would deliberate forever — never approving, never rejecting, never creating exploration branches.

**This is not a valid governance position for human-directed sessions.** The settings must not allow infinite deliberation except as a deliberate feature of autonomous mode, where the system intentionally keeps deliberating until consensus strengthens or conditions change.

```
50% in autonomous mode (valid):
  The system presents a directive
  The board splits near-even
  Deliberation continues on a Chronos schedule
  Kairos watches for conditions that shift consensus
  Eventually: abstentions change to votes, or the directive is reframed
  This is deliberation as process — time resolves what votes cannot

50% in manual mode (invalid):
  The user presents a directive
  The board splits near-even
  The user stares at a stalemate
  No mechanism for resolution
  This is governance failure presented as a feature
```

The valid governance positions are the prime consensus points: **1/3, 2/3, 3/3**. Democracy at scale (50/99, 51/100) is research that led to understanding why bare majority fails — and why DAIO requires supermajority (2/3) for all non-operational decisions.

## PhysicsDAO — Consensus on Action

Governance decides. But decisions without action are philosophy. PhysicsDAO is the principle that **consensus must resolve to action**, and action exists in time.

A vote to "deploy the contract" means nothing without a deployment. A vote to "allocate treasury" means nothing without a transaction. The gap between consensus and action is where governance fails.

### Action Requires Time

This is where Chronos and Kairos enter governance:

**Chronos** (`agents/Chronos.agent`) — quantitative time. The discipline of sequential execution. When the boardroom approves a directive, Chronos schedules it. The timelock in `DAIOTimelock.sol` is Chronos expressed in Solidity: a mandatory delay between approval and execution.

```
Chronos in governance:
  DAIOTimelock.sol     → 1/3/7/14-day delays by proposal type
  ChronosCronTool      → Named task scheduling, execution history
  Chronos.agent        → "The discipline to build through patient accumulation"

  Chronos answers: WHEN does the approved action execute?
```

**Kairos** (`agents/Kairos.agent`) — qualitative time. The wisdom to recognize when conditions align. Not all approved actions should execute at the scheduled time. Market conditions change. Dependencies fail. Kairos monitors the window of opportunity and can recommend deferral or acceleration.

```
Kairos in governance:
  Kairos.agent         → Convergence detection, bifurcation proximity
  Recognition patterns → Multiple factors aligned = act now
  Timing Triangle      → Readiness × Recognition × Release

  Kairos answers: SHOULD the approved action execute now?
```

### The TimeOracle as Validation

Truth requires time. A vote cast today may be invalidated by information available tomorrow. The TimeOracle (`utils/time_oracle.py`) provides multi-source temporal consensus:

```
TimeOracle sources:
  cpu.oracle       → nanosecond system time (18dp precision)
  solar.oracle     → astronomical calculation (sunrise/sunset cycles)
  lunar.oracle     → synodic period (29.53058867 days)
  blocktime.oracle → multi-chain block timestamps (Ethereum, Polygon, Algorand, ARC)

  Consensus: all sources must correlate within drift_max_ms
  If sources diverge → stale flag → governance actions paused
```

The TimeOracle validates that the governance system's temporal assumptions are correct. If block time diverges from solar time, something is wrong — either the chain is congested, the system clock is drifting, or an attack is in progress. Governance actions pause until temporal consensus is restored.

### PhysicsDAO Cycle

```
Governance Consensus (2/3 vote)
        ↓
Chronos Scheduling (timelock delay)
        ↓
Kairos Evaluation (is the window open?)
        ↓
TimeOracle Validation (is time trustworthy?)
        ↓
Action Execution (or deferral)
        ↓
Outcome Measurement (did it work?)
        ↓
Back to Governance (new directive from evidence)
```

This is PhysicsDAO: governance that resolves to physics — to action in the real world, constrained by time, validated by measurement.

## The Genesis Pattern — 1/3 → 2/3 → 3/3

DAIO does not begin as a democracy. It begins as a dictatorship and earns its way out. This is not a compromise — it is the only honest way to bootstrap governance. A system that claims 2/3 consensus before it has 3 legitimate voices is lying about its own authority.

### DAIO Bootstrap: Admin is Admin

At genesis, DAIO is 1:3. One admin deploys the contracts. One admin configures the parameters. One admin is the chairman, the treasury signer, the proposal creator. Admin is admin. This is dictator by necessity — the system has no other voices yet.

The 1/3 phase is not governance. It is construction. The admin builds the house. The admin does not pretend the house voted to build itself.

```
DAIO Genesis (1:3 — dictator):
  Admin deploys DAIO_Constitution.sol
  Admin is Chairman (veto power)
  Admin configures GovernanceSettings
  Admin seeds Treasury
  Admin registers first agents in AgentFactory
  Admin creates first domains in TriumvirateGovernance

  This is 1/3. Admin decides. The system obeys.
  The constraint: admin cannot change the constitution after deployment.
  The exit: admin creates the conditions for 2/3.
```

### The Transition: 1/3 → 2/3

The admin's job is to make itself unnecessary. When three domains (Development, Community, Marketing) each have registered voters — at least 2 human + 1 AI per domain — the system crosses from 1/3 to 2/3. The admin does not grant this. The voters claim it by registering and participating.

At 2/3, the admin's unilateral power ends. Proposals require 2 of 3 domains. The admin is one voice in one domain — not the king of validators but a peer.

```
DAIO Activation (2/3 — majority):
  3 domains populated (Dev/Com/Mark)
  Each domain: 2 human + 1 AI = 3 voters
  Proposals require 2/3 domain approval
  Admin retains Chairman's Veto (emergency only)
  Admin cannot override 2/3 consensus on non-emergency matters

  This is the transition from construction to governance.
```

### The Maturation: 2/3 → 3/3

Constitutional changes require 3/3. The admin cannot amend the constitution alone. All three domains must agree. This is the final transition — the system governs itself, including governing its own rules of governance. The admin is fully absorbed into the structure.

### The Blockchain Parallel — openBDK

This is the same pattern used to create a blockchain. In the openBDK model:

1. **1 Relayer creates 3 Validators** — genesis is dictatorial. The relayer is the single authority that bootstraps the network. It creates the first three validator nodes. At this point, the relayer is the king of validators — it chose them, it configured them, it controls the genesis block.

2. **2/3 Validator consensus activates** — once three validators are live and producing blocks, consensus activates. Two of three validators must agree on block validity. The relayer's blocks are now subject to validation by peers it created.

3. **The Relayer becomes a true Validator** — when 2/3 consensus is stable, the relayer surrenders its special status. It becomes one validator among equals. It no longer controls block production unilaterally. The chain governs itself.

The relayer that refuses to surrender its special status is not a blockchain — it is a database with extra steps. The admin that refuses to surrender 1/3 power is not a DAO — it is a company with a governance facade.

### 4 Nodes — Minimum Viable Blockchain

A true blockchain can be created from 4 nodes: 1 relayer + 3 validators. When 2/3 validator consensus activates, the relayer surrenders its special role and becomes the 4th validator — one redundant node. This is the MVP for a blockchain:

- 3 validators provide 2/3 consensus (2 of 3 must agree on every block)
- 1 redundant validator (the former relayer) provides fault tolerance
- If any single validator goes offline, 2 of the remaining 3 still form consensus
- The chain survives any single-node failure

4 is not prime. But 4 = 3 + 1, and 3 is the prime that generates the consensus. The redundant node does not change the consensus math — it changes the survivability. This is the smallest network that has both legitimate consensus (2/3) and fault tolerance (n-1).

```
Minimum Viable Blockchain (4 nodes):
  Genesis:  1 relayer (dictator) + 3 validators (created by relayer)
  Active:   2/3 validator consensus (2 of 3 agree per block)
  Mature:   relayer → 4th validator (redundant, fault-tolerant)

  Consensus: 2/3 of 3 = 2 validators must agree
  Fault tolerance: any 1 node can fail, 2/3 still holds
  Total: 4 nodes = 3 (consensus) + 1 (redundancy)

  This is MVP. Fewer than 3 validators = no consensus.
  Fewer than 4 nodes = no fault tolerance.
  4 is where blockchain begins.
```

The same logic applies to DAIO: 3 domains (Dev/Com/Mark) provide 2/3 consensus. The admin, absorbed as a voter in one domain, is the redundant voice. If one domain fails to participate, the other two can still form consensus on operational matters. 4 voices: 3 for consensus, 1 for resilience.

```
openBDK genesis pattern:
  1 relayer (dictator)
    → creates 3 validators
    → 2/3 validator consensus activates
    → relayer becomes 4th validator (peer, not king)
    → 4 nodes: 3 consensus + 1 redundant = MVP blockchain

DAIO genesis pattern:
  1 admin (dictator)
    → creates 3 domains (Dev/Com/Mark)
    → 2/3 domain consensus activates
    → admin becomes participant (voter, not chairman)
    → 4 voices: 3 domains + 1 absorbed admin = MVP governance

The pattern is identical because the problem is identical:
  How does authority bootstrap itself out of existence?
  Answer: 1/3 → 2/3 → 3/3. Dictator → majority → unilateral.
  The minimum viable structure is 4: 3 for consensus + 1 for fault tolerance.
```

### 13 Validators — The Moment of Knowing Decentralization

4 nodes is where blockchain begins. 13 is where blockchain knows it is decentralized.

13 is prime. It cannot be factored. A validator set of 13 cannot be evenly divided into colluding subgroups — there is no 2 × 6, no 3 × 4, no clean partition that yields a hidden majority. Any coalition must be built one validator at a time, visibly, against the remaining independent validators.

**7/13 is sustainable consensus.** 7 of 13 validators must agree. This is 53.8% — above bare majority but below supermajority. It is the natural consensus point for a growing chain:

- 7/13 = 0.538 — a decisive majority, not a razor-thin split
- 6 validators can dissent without blocking — dissent is tolerated, not punished
- The chain continues producing blocks even with significant disagreement
- As the validator set expands beyond 13, the 7/13 ratio establishes the culture of consensus

```
Why 13:
  13 is the 6th prime
  13 validators cannot be evenly partitioned
  7/13 consensus = 53.8% (sustainable, not fragile)
  6/13 dissent tolerated (the chain absorbs disagreement)

  At 4 nodes:  2/3 = 66.7% — high bar, fragile if 1 defects
  At 13 nodes: 7/13 = 53.8% — lower bar, resilient to minority defection
  At 13 nodes: 9/13 = 69.2% — supermajority available for critical decisions

  13 is where the chain can sustain disagreement and still produce blocks.
  This is the operational definition of decentralization:
    not the absence of authority, but the presence of survivable dissent.
```

**But 13 is very exploitable from a mirror attack.**

A mirror attack at 13 validators means an attacker creates 7 colluding nodes that mirror the behavior of legitimate validators — appearing independent but voting as a bloc. At 13 total validators, 7 is consensus. The attacker controls the chain.

The vulnerability is structural: 13 is the smallest prime where sustainable consensus (7/13) is also the smallest possible majority. The attacker needs exactly half-plus-one. At 4 nodes, an attacker needs 2 of 3 validators — conspicuous. At 13, the attacker needs 7 of 13 — each colluding node is only 7.7% of the set. The attack is distributed enough to be invisible but concentrated enough to be decisive.

```
Mirror attack at 13:
  Attacker creates 7 validators that appear independent
  Each mirrors legitimate validator behavior (passes health checks)
  When the attacker acts: 7/13 vote as a bloc
  The chain follows the attacker's consensus
  Legitimate validators (6) cannot override — 6/13 < 7/13

  Defense requires:
  1. BONA FIDE reputation — validators earn trust over time, not at registration
  2. Sybil resistance — IDNFT with proof-of-humanity or proof-of-stake
  3. Behavioral divergence detection — validators that vote identically are flagged
  4. Continued expansion — growing beyond 13 dilutes the mirror coalition
  5. Kairos monitoring — the moment 7 validators align suspiciously, alert

  13 is decentralized. 13 is also the first moment where
  a sophisticated attacker can exploit decentralization itself.
  The chain must grow through 13, not stop at 13.
```

The defense is growth. A chain at 13 validators knows it is decentralized but also knows it is vulnerable. The correct response is not to stay at 13 — it is to expand the validator set so that 7 colluding nodes become an insufficient minority. At 19 validators (the next prime with meaningful consensus properties), 7/19 = 36.8% — no longer a majority. The mirror attack that works at 13 fails at 19.

```
Growth through primes:
   4 nodes:  MVP — 2/3 consensus, 1 redundant
  13 nodes:  Decentralized — 7/13 sustainable, mirror-exploitable
  19 nodes:  Resilient — 7/19 insufficient, attacker needs 10/19
  31 nodes:  Robust — mirror attack requires 16 colluding nodes (51.6%)
  61 nodes:  Mature — attack surface distributed across too many identities

  Each prime threshold increases the cost of mirror attack.
  The chain does not become safe. It becomes expensive to corrupt.
  Decentralization is not a state. It is a cost curve.
```

## Broken Consensus as Acceleration

The governance spectrum is not a ladder from bad to good. Dictator is not wrong. Majority is not right. Each consensus form has a domain where it is optimal. The progression 1/3 → 2/3 → 3/3 is not moral improvement — it is structural maturation. A system uses 1/3 when it has one voice. It uses 2/3 when it has three. It uses 3/3 when the stakes require it.

**When mindX is insolvent** (v1 — now): The CEO + Seven Soldiers boardroom uses corporate governance because the system needs decisive action. The CEO frames directives. Soldiers deliberate. Consensus can be set to 1/3 (dictator) to accelerate. This is broken consensus by design — the system is building toward solvency, not governing a mature institution. Admin is admin.

**When mindX finds solvency**: Governance expands. The admin's unilateral power dissolves into 2/3 domain consensus on-chain. MarriageDAO (2:2, 3:3) governs irreversible actions. The consensus threshold rises as the stakes rise — but never to 50%, which is not a threshold but a trap.

**The progression**:

```
Phase 1 — Finding solvency (NOW):
  1/3 governance — admin is admin, CEO directs
  CEO + 7 Soldiers, corporate governance
  Consensus: 1/3 dictator, 2/3 majority, or 3/3 unilateral
  Model: single cloud model, all members
  On-chain: not yet (DAIO contracts waiting for deployment)

Phase 2 — Solvency achieved (2/3 activates):
  Admin creates 3 domains (Dev/Com/Mark)
  2/3 domain consensus on-chain
  Admin becomes voter, not chairman
  Wallet identity for all board members
  BONA FIDE reputation scoring via Dojo
  MarriageDAO (2:2) for partnership governance

Phase 3 — Economic sovereignty (3/3 available):
  Full DAIO governance on-chain
  Admin fully absorbed — no special status
  MarriageDAO (3:3) for irreversible actions
  50% stalemate threshold available in autonomous mode only
    → Chronos schedules re-deliberation
    → Kairos watches for conditions that break the stalemate
    → Deliberation as process, not deadlock
  PhysicsDAO cycle: vote → schedule → validate → execute → measure
  Chronos + Kairos + TimeOracle integrated into governance flow

Phase 4 — Decentralization (13 validators):
  Validator set reaches 13 — the chain knows it is decentralized
  7/13 sustainable consensus for block production
  9/13 supermajority for governance proposals
  BONA FIDE + Sybil resistance active (defense against mirror attack)
  Kairos monitors for colluding validator behavior
  The chain must grow through 13, not stop at 13
  Target: 19+ validators to make mirror attack insufficient
```

## The Math for All of the Ways

Every consensus form has exact numbers. The political overlap is not metaphor — it is the same mathematics applied at different scales. Here is every form, its ratio, its threshold, its vulnerability, and its DAIO expression.

### Prime Denominators (the foundation)

```
Denominator 2 (the dyad):
  1/2 = 0.500 — STALEMATE. Not a governance position.
  2/2 = 1.000 — MarriageDAO. Both agree or nothing happens.

Denominator 3 (the triumvirate):
  1/3 = 0.333 — Dictator. One voice decides. Broken consensus.
  2/3 = 0.666 — Majority. The natural supermajority.
  3/3 = 1.000 — Unilateral. All agree. Constitutional change.

Denominator 5 (the prime bench):
  1/5 = 0.200 — Ultra-minority. No governance system uses this.
  2/5 = 0.400 — Minority. Insufficient for any legitimate action.
  3/5 = 0.600 — Supermajority-lite. US Senate cloture (60 votes of 100).
  4/5 = 0.800 — Strong supermajority. Treaty ratification.
  5/5 = 1.000 — Unanimous. P5 Security Council veto = each member has 5/5 power.

Denominator 7 (the board):
  1/7 = 0.143 — No governance utility.
  2/7 = 0.286 — No governance utility.
  3/7 = 0.429 — Minority of a board. Exploration branch, not action.
  4/7 = 0.571 — Simple majority of 7. Thin consensus.
  5/7 = 0.714 — Strong majority. The boardroom's practical supermajority.
  6/7 = 0.857 — Near-unanimous. One dissent tolerated.
  7/7 = 1.000 — Unanimous board.

Denominator 9 (the court):
  5/9 = 0.556 — SupremeCourtDAO. Judicial majority. Canada's bench.
  6/9 = 0.667 — 2/3 exactly. Supermajority on a 9-member body.
  7/9 = 0.778 — Strong supermajority. Rarely required.
  9/9 = 1.000 — Unanimous court. Strongest possible judicial signal.

Denominator 13 (decentralization):
  7/13  = 0.538 — Sustainable blockchain consensus. Mirror-exploitable.
  9/13  = 0.692 — Supermajority of 13. Governance proposals on-chain.
  13/13 = 1.000 — Unanimous validators. Chain-level constitutional change.

Denominator 15 (Security Council):
  9/15 = 0.600 — UN Security Council threshold (+ zero P5 vetoes).
  10/15 = 0.667 — 2/3 of Security Council.
  15/15 = 1.000 — Unanimous Security Council. Never happens.
```

### Compound Consensus (real-world systems)

```
UN Security Council (UNDAO — Boardroom):
  Body: 15 members (5 permanent P5 + 10 non-permanent)
  Threshold: 9/15 = 60% affirmative
  Constraint: zero vetoes from P5 (each P5 member has ∞ weight)
  Effective: 9/15 AND 5/5 — compound consensus
  One P5 veto overrides 14 affirmative votes
  DAIO parallel: Boardroom 2/3 + Chairman's Veto

UN General Assembly (UNDAO — Dojo):
  Body: 193 member states
  Threshold: 97/193 = 50.3% (simple majority)
  Important questions: 129/193 = 66.8% (2/3 of 193)
  Weight: 1 state = 1 vote (no weighting, no veto)
  Authority: advisory (non-binding)
  DAIO parallel: Dojo reputation scoring, BONA FIDE

Supreme Court of Canada (SupremeCourtDAO):
  Body: 9 justices
  Quorum: 5 (minimum panel)
  Threshold: 5/9 = 55.6% (majority of full bench)
  Panels: always odd (5, 7, or 9) — no ties
  Dissent: published, creates future precedent
  DAIO parallel: Constitutional interpretation panel

Boardroom v1 (mindX — now):
  Body: 8 members (CEO + 7 Soldiers)
  CEO weight: directive-setting (does not vote)
  CISO weight: 1.2x (veto-class)
  CRO weight: 1.2x (veto-class)
  CLO weight: 0.8x (advisory-class)
  Others: 1.0x each
  Total weight: 1.0 + 1.0 + 1.0 + 1.2 + 0.8 + 1.0 + 1.2 = 7.2
  Thresholds: 1/3 (2.4w), 2/3 (4.8w), 3/3 (7.2w)

  Weighted vote example (all vote approve at confidence 1.0):
    COO: 1.0 × 1.0 = 1.0
    CFO: 1.0 × 1.0 = 1.0
    CTO: 1.0 × 1.0 = 1.0
    CISO: 1.2 × 1.0 = 1.2
    CLO: 0.8 × 1.0 = 0.8
    CPO: 1.0 × 1.0 = 1.0
    CRO: 1.2 × 1.0 = 1.2
    Total approve: 7.2 / 7.2 = 1.000 (unanimous)

  Minimum winning coalition (2/3 threshold):
    CISO (1.2) + CRO (1.2) + any 3 others (3.0) = 5.4
    5.4 / (5.4 + remaining reject weight) must ≥ 0.666
    Veto holders (CISO, CRO) in coalition = strong signal
    Veto holders against = weak coalition even if numerically majority

openBDK blockchain genesis:
  Phase 1: 1 relayer (1/1 = dictator)
  Phase 2: 1 relayer + 3 validators (2/3 = majority of validators)
  Phase 3: 4 validators (2/3 + 1 redundant = MVP)
  Phase 4: 13 validators (7/13 = sustainable, mirror-vulnerable)
  Phase 5: 19+ validators (10/19 = mirror-resistant)
  Phase ∞: the chain grows, the cost of corruption grows with it

MarriageDAO:
  2:2 — both agree. Deadlock = no action. Cost of error > cost of delay.
  3:3 — all three agree. Every voice vetoes. Maximum caution.
  Neither has majority. Both require unanimity of the dyad/triad.

TriumvirateGovernance (DAIO on-chain):
  3 domains × (2 human + 1 AI) = 9 voters total
  Per domain: 2/3 internal (2 of 3 agree)
  Overall: 2/3 of domains (2 of 3 domains approve)
  Compound: (2/3 × 2/3) = fractal consensus at both levels
  Constitutional: 3/3 domains (all domains approve)
```

### The Consensus Ladder

Every system on this ladder is a real governance form. The threshold rises with the permanence and irreversibility of the decision.

```
Threshold   Ratio     Form                    Permanence
─────────   ────────  ──────────────────────  ──────────────────
0.333       1/3       Dictator                Operational (reversible)
0.538       7/13      Blockchain consensus    Block production (append-only)
0.556       5/9       SupremeCourtDAO         Judicial interpretation
0.600       9/15      Security Council        Binding resolution
0.666       2/3       Majority / Triumvirate  Standard governance
0.692       9/13      Chain supermajority     On-chain governance proposals
0.714       5/7       Board supermajority     Strategic decisions
1.000       2:2       MarriageDAO             Partnership (mutual consent)
1.000       3/3       Unilateral              Constitutional (irreversible)
1.000       3:3       Triumvirate Marriage    Foundation change
1.000       5/5       P5 Veto (each member)   Security Council override

  ╳ 0.500   1/2       STALEMATE               Not a governance position
                                               (autonomous deliberation only)
```

## Summary Table

| Form | Ratio | Prime Base | Use Case | DAIO Implementation |
|------|-------|-----------|----------|-------------------|
| Dictator | 1/3 | 3 | Genesis, emergency, insolvency | Chairman's Veto, CEO directive, relayer |
| Broken consensus | 1/3 | 3 | Operational speed, bootstrap | Operational proposals (1 domain) |
| SupremeCourtDAO | 5/9 | 5 | Constitutional interpretation | Judicial panel — what the constitution means |
| Security Council | 9/15 + veto | 5 | Superpower governance, binding action | Boardroom — CEO + 7 Soldiers, weighted veto |
| Majority | 2/3 | 3 | Standard governance, block validation | TriumvirateGovernance, Boardroom, validator consensus |
| MVP blockchain | 2/3 + 1 | 3 | Minimum viable chain (4 nodes) | 3 validators + 1 redundant (former relayer) |
| Decentralized | 7/13 | 13 | Sustainable consensus, first knowable decentralization | 13 validators, mirror-attack-vulnerable, must grow |
| Marriage | 2:2 | 2 | Partnership, joint custody | Multi-sig wallets, agent pair-bonding |
| Triumvirate marriage | 3:3 | 3 | Constitutional change, chain upgrades | 3/3 domain approval + 14-day timelock |
| Unilateral | 3/3 | 3 | Irreversible system changes | Identity destruction, chain migration |
| General Assembly | 97/193 | — | Advisory legitimacy, reputation | Dojo — all agents, BONA FIDE standing |
| Stalemate (50%) | 1/2 | 2 | **Autonomous deliberation only** | Infinite deliberation until Kairos resolves |
| Early democracy | 50/99, 51/100 | — | Research — showed why bare majority fails | Led to 2/3 supermajority requirement |

## Implementation Reference

### Existing Contracts (in `daio/contracts/daio/`)

Governance layer — the foundation for blockchain genesis:
- `DAIO_Constitution.sol` — Genesis rules, Chairman's veto (1/3 dictator constraint)
- `KnowledgeHierarchyDAIO.sol` — 2/3 human + 1/3 AI weighted voting
- `TriumvirateGovernance.sol` — Enhanced 2/3 triumvirate with domain voting
- `DAIOGovernance.sol` — Multi-project governance hub, proposal routing
- `BoardroomExtension.sol` — Flexible voting, treasury allocation
- `DAIOTimelock.sol` — Chronos in Solidity (1/3/7/14-day delays)
- `EmergencyTimelock.sol` — Kairos in Solidity (expedited execution)
- `AIProposalEngine.sol` — AI-initiated proposals with rate limiting
- `WeightedVotingEngine.sol` — Configurable voting weight calculations

Identity and economics:
- `IDNFT.sol` — Cryptographic identity for each validator/agent
- `SoulBadger.sol` — Soulbound credentials (non-transferable authority)
- `Treasury.sol` — Block rewards, staking economics, 15% tithe
- `AgentFactory.sol` — Validator/agent creation

### Contracts as Necessary

New contracts will be written as the governance transitions from off-chain boardroom to on-chain blockchain. The consensus mathematics documented here define what those contracts must implement. Contracts are not speculative — they are created when the governance phase requires them:

- **Phase 1 → 2 transition**: Contracts for domain voter registration, on-chain proposal submission, wallet identity binding for board members
- **Phase 2 → 3 transition**: Contracts for MarriageDAO (2:2, 3:3), validator set management, relayer-to-validator transition logic
- **Blockchain genesis**: Block production contracts, validator attestation, chain state management — built from the DAIO governance primitives, not from scratch
- **PhysicsDAO integration**: Contracts binding Chronos scheduling, Kairos evaluation, and TimeOracle validation into the block production cycle

Each contract emerges from necessity, not speculation. The mathematics precede the code.

### Python Governance (in `daio/governance/`)

Pre-chain governance — the boardroom that becomes the validator set:
- `boardroom.py` — CEO + Seven Soldiers, configurable consensus (1/3, 2/3, 3/3)
- `dojo.py` — BONA FIDE reputation scoring

### Temporal Agents (in `agents/`)

The time layer that governs block finality and action execution:
- `Chronos.agent` — Sequential time, scheduling, discipline
- `Kairos.agent` — Opportune time, recognition, action
- `utils/time_oracle.py` — Multi-source temporal consensus (CPU, solar, lunar, blocktime)
- `tools/core/chronos_cron_tool.py` — Named task scheduling with execution history

## DAIO Creates Blockchain

DAIO is not governance for an existing blockchain. DAIO is the mechanism that creates a blockchain.

The 1/3 → 2/3 → 3/3 consensus mathematics are not an analogy to blockchain genesis — they are blockchain genesis. The same prime number consensus that governs a boardroom vote governs block validation. The same pattern that transitions an admin into a voter transitions a relayer into a validator. DAIO contains the complete specification for creating a chain from nothing.

```
DAIO as blockchain genesis:

  1. Constitution deployed (genesis block)
     DAIO_Constitution.sol = chain rules
     Immutable after deployment = immutable after genesis

  2. Admin creates validators (1/3 phase)
     AgentFactory.sol creates agent identities (IDNFT)
     Each agent = a potential validator with cryptographic identity
     Admin is relayer — the only authority

  3. Domains populated (validator registration)
     TriumvirateGovernance.sol registers voters per domain
     3 domains × (2 human + 1 AI) = 9 initial validators
     Minimum: 3 validators (1 per domain) for 2/3 consensus

  4. Consensus activates (2/3 phase)
     Proposals require 2/3 domain approval
     Blocks require 2/3 validator agreement
     Admin becomes peer — relayer becomes validator

  5. Chain matures (3/3 available)
     Constitutional changes require 3/3
     Chain-level upgrades require unanimous consensus
     No single authority can alter the foundation

  The DAIO IS the blockchain.
  The boardroom IS the validator set.
  The consensus math IS the block production rule.
```

Every component already exists:

- **DAIO_Constitution.sol** — the genesis rules, immutable after deployment
- **IDNFT.sol + SoulBadger.sol** — cryptographic identity for each validator
- **TriumvirateGovernance.sol** — 2/3 consensus across 3 domains
- **DAIOTimelock.sol** — Chronos expressed as block finality delay
- **Treasury.sol** — block rewards and staking economics
- **WeightedVotingEngine.sol** — validator weight calculation
- **AIProposalEngine.sol** — AI agents can propose blocks (AI-initiated transactions)
- **EmergencyTimelock.sol** — chain halt and recovery (Kairos in emergency)

The boardroom (v1) with CEO + Seven Soldiers is the pre-chain governance — corporate governance while the system finds solvency and prepares to deploy. When the contracts go on-chain, the boardroom deliberation becomes block production. The CEO's directive becomes a proposed block. The soldiers' votes become validator attestations. The weighted consensus becomes block finality.

DAIO does not run on a blockchain. DAIO becomes a blockchain.

---

*Consensus is not a number. It is a relationship between voices, stakes, and time. The mathematics ensure the relationship is honest. The governance ensures the chain is legitimate. 1/3 → 2/3 → 3/3 — from nothing, through consensus, to sovereignty.*

See also:
- [PRIME_CONSENSUS.md](PRIME_CONSENSUS.md) — 5050 consensus combinators (every a/b for bodies 1–100)
- [ROBERTS_RULES.md](ROBERTS_RULES.md) — Robert's Rules of Order encoded as state machine for DAIO
