# Incorporating mindX / DAIO as a Marshall Islands DAO LLC: A Comprehensive Guide

*Prepared for Gregory L. ("codephreak"), architect of the PYTHAI / DELTAVERSE / BANKON ecosystem. This report is informational and is **not legal or tax advice** — engage qualified RMI, U.S./securities, and Canadian tax counsel before acting.*

## TL;DR
- The Republic of the Marshall Islands (RMI) is the strongest available legal home for mindX/DAIO: under the Decentralized Autonomous Organization Act of 2022 (passed November 25, 2022 — a world first — and since amended in 2023 and supplemented by the DAO Regulations of 2024), a DAO can incorporate as a "DAO LLC" that grants full legal personhood and limited liability while statutorily recognizing pure smart-contract ("algorithmic") governance — the operating agreement can simply point to the DAIO contracts (this is precisely how Pyth DAO LLC is structured: "the operating agreement for the Pyth DAO LLC simply points to the Pyth governance smart contracts").
- Realistic budget: roughly US$9,500–$18,500 to incorporate through an authorized agent (MIDAO is the only government-authorized DAO LLC registered agent, at "$9,500 with no hidden fees"), plus a recurring annual fee of ~$2,000–$5,500; choose the **non-profit DAO LLC** (0% RMI tax) for the governance/protocol entity. Only members with ≥25% governance rights must complete KYC; everyone below stays anonymous.
- Governance maps directly onto RMI's class-of-membership rules: the **VOTE DAIO token (13-token fixed mint, 1 token = 1 vote in the War Council)** becomes a distinct voting class, and the **0.666 supermajority resolves to a hard floor of 9 of 13 votes**.
- The biggest risks are NOT in the RMI but extraterritorial: U.S. securities/CFTC exposure if the BANKON PYTHAI token confers economic rights or is sold to U.S. persons, OFAC sanctions screening on a global token, and — critically for codephreak — Canadian tax: as a Canadian resident you will likely owe Canadian tax personally regardless of RMI's tax-neutrality, and a for-profit RMI entity you control could be a "controlled foreign affiliate" subject to FAPI accrual. Engage a qualified crypto/cross-border attorney and a Canadian tax advisor before filing.

## Key Findings

1. **The RMI is purpose-built for exactly this use case.** Unlike Wyoming (a U.S. state, with federal exposure), Cayman/Panama/Liechtenstein (foundations that require human directors as the legally operative layer), or Switzerland (expensive, slow, no member-voting recognition), the RMI DAO LLC statutorily recognizes that "the DAO's on-chain governance *is* the governance." The operating agreement can directly reference governance smart contracts.

2. **Algorithmic management is explicitly legal.** RMI law (DAO Act §107–§108) allows a DAO LLC to be member-managed *or* algorithmically (smart-contract) managed, with no required directors, officers, or local representatives. MIDAO now markets DAO LLCs as "the most advanced legal framework for Web3, DAOs, and AI Agents," describing algorithmic management as "the same statutory primitive: a non-human governance authority recognized as a valid legal mechanism." This directly accommodates the DAIO suite (WarCouncil, Boardroom, DeadmansSwitch, BankonIdentityRegistry, X402AccessGate, ChainRegistry, Daio contracts).

3. **Token holders can be members.** RMI law lets membership interests be defined by governance-token holdings, and the 2023 amendment clarified that **"governance tokens are not considered securities if they do not confer any economic rights"** (Pontinova Law). This means BANKON PYTHAI holders could be admitted as members automatically by token-holding, with membership transferring with the token — but only if the token is structured as pure governance (no profit/dividend rights).

4. **Tax-neutral in RMI, but not elsewhere.** A non-profit DAO LLC pays 0% RMI tax with no revenue reporting; a for-profit DAO LLC pays a 3% Gross Revenue Tax (excluding capital gains and dividends), with an $80/year flat minimum on the first $10,000 of revenue ("If annual income stays within the first $10,000, the DAO pays a flat fee of $80 per year. Any amount above that threshold is taxed at a rate of 3%" — IncFine). RMI tax-neutrality says nothing about members' home-country obligations.

5. **Light but real compliance.** A registered agent in the RMI is mandatory and continuous. Annual Beneficial Owner Information Report (BOIR) filing is due January 1–March 31; only ≥25% governance-rights holders and any managers/officers must KYC; at least one UBO must always be named. On-chain activity is subject to AML/CFT monitoring by the registered agent and law enforcement.

## Details

### 1. Legal Framework

**The Act and its amendments.** The RMI adopted the Decentralized Autonomous Organization Act of 2022 on November 25, 2022, becoming the first sovereign nation to recognize DAOs as a dedicated legal entity. (Initial recognition of DAOs as legal entities came slightly earlier via the Non-Profit Entities (Amendment) Act 2021, announced February 2022; the dedicated DAO Act followed.) It builds on the Marshall Islands Limited Liability Company Act of 1996 (itself modeled on the Delaware LLC Act), applying Title 52 MIRC Chapter 4 to DAOs where consistent. It has since been amended (P.L. 2023-83 / the "2023 Amendment") to add Series DAO LLC capability, a digital-asset classification scheme, and the 3% Gross Revenue Tax mechanism, and supplemented by the Decentralized Autonomous Organization Regulations 2024, which clarified KYC thresholds, the BOIR, FIBL exemption, and on-chain monitoring.

**What it does.** A DAO is defined as a resident domestic LLC whose certificate of formation or LLC agreement contains a statement that the company is a DAO (§104). It must include a publicly available identifier of any smart contract directly used to manage the DAO (§106), and its name must include "DAO LLC" (§104). Incorporation confers legal personhood and limited liability: the entity can own property, contract, sue and be sued, and shields members' personal assets. Without this, a DAO defaults to an unincorporated general partnership, exposing all token-voting participants to joint and several liability (as the CFTC's Ooki DAO action demonstrated in the U.S., where the court treated governance-token voters as members of an unincorporated association).

**Member-managed vs. algorithmically managed.** Management is "vested in its members or a smart contract" (§108). RMI law explicitly contemplates a fully directorless, fully on-chain DAO LLC where smart-contract execution is recognized as valid corporate action and where decisions and records can live entirely on-chain (no separate PDF minute books required). Members are subject only to the implied contractual covenant of good faith and fair dealing — no additional fiduciary duties unless specified. Notably, where the certificate of formation, LLC agreement, and smart contracts conflict, the Act provides ordering rules — and in practice the written legal documents prevail over code. This is the single most important design constraint for the DAIO suite: the smart contracts express governance, but the operating agreement is the controlling legal instrument.

**Non-profit vs. for-profit.** The RMI offers both. A **non-profit DAO LLC** has no economic owners and cannot distribute earnings to members ("beneficial members" rather than "beneficial owners"); it pays no RMI tax and files no revenue reports. This is the dominant choice for open-source, public-benefit, protocol, and grant-making DAOs, and is the recommended structure for the mindX/DAIO governance entity. A **for-profit DAO LLC** may distribute to members but pays the 3% GRT and must report revenue annually.

### 2. Formation Procedure (step by step)

1. **Choose structure and purpose.** Decide non-profit vs. for-profit and define a clear lawful purpose. Select the blockchain network(s) the governance will run on.
2. **Reserve a compliant name.** Must be unique and include "DAO LLC" (e.g., "BANKON PYTHAI DAO LLC" or "mindX DAO LLC").
3. **Engage a registered agent (mandatory and continuous).** This is a legal requirement under §105. **MIDAO (MIDAO Directory Services, Inc. / MIDAO Global, Inc.)** is the exclusive, government-authorized public-private partner for DAO LLC registration — note that International Registries, Inc. (IRI), which handles ordinary RMI corporations, cannot form DAO LLCs. Other firms act as facilitators/resellers or pair with counsel: Offshore Companies International (OCI), DAObox, entity.legal, SBSB, Inteliumlaw, and Pontinova.
4. **Prepare documents.** Core constitutional documents: the **Certificate of Formation**, the **Operating Agreement (LLC Agreement)**, and (for the DAO) a statement that it is a DAO plus the **publicly available smart-contract identifier(s)**. Agents provide editable templates; the operating agreement can be amended later. A Foreign Investment Business License (FIBL) template is provided, though FIBL is not required for a DAO LLC under P.L. 2023-83.
5. **KYC / beneficial ownership.** Founders supply proof of identity and address. Any member with **≥25% governance rights** (and any manager/officer) must complete KYC (name, address, passport); at least one UBO must always be identified. Background screening covers fraud/tax-evasion history (~4 years), PEP status, and sanctions. Everyone below the threshold stays anonymous.
6. **File and receive recognition.** Documents are filed with the Registrar of Resident Domestic and Authorized Foreign Corporations. The BOIR is filed at formation. After review, the Registrar issues the Certificate of Formation.
7. **Post-formation.** Appoint any managing members (or rely on algorithmic management), record smart-contract addresses, and open banking if needed.

**Timeline:** Registration typically completes within ~30 days of filing (commonly quoted as 2–4 weeks; ~3 weeks is typical). MIDAO's premium tier advertises entity creation in under 24 hours.

**Referencing the DAIO code in formation documents.** The §106 requirement to publish a smart-contract identifier is satisfied by listing the deployed governance contract addresses (the Daio core contract and related modules) in the certificate/operating agreement. Unlike Wyoming — which requires the public keys of the managing smart contracts and auto-dissolves an algorithmically-managed DAO whose contracts are immutable or that takes no action for a year — the RMI does not impose those constraints, which is advantageous for an evolving system like DAIO.

### 3. Costs (2025–2026)

The RMI government does not publish a standalone, itemized DAO-LLC government fee schedule; government fees are bundled into agent packages. Confirmed figures:

| Item | Amount | Notes |
|---|---|---|
| **MIDAO all-inclusive package** | **US$9,500** (one-time) | Government-authorized agent; "Starting at $9,500 with no hidden fees"; includes operating-agreement workshops, priority onboarding |
| MIDAO recurring annual fee | **US$2,000–$5,000/yr** | Per MIDAO's published pricing |
| MIDAO premium/TurboDAO tier | +US$10,000 one-time | Entity in <24 hrs, virtual office + phone, extended OA customization |
| entity.legal (Series DAO LLC, API) | **$50/mo for-profit / $30/mo non-profit** | Includes Entity ID, tax number, on-chain registry, banking, automated compliance |
| OCI (Offshore Companies International) | **$6,000 setup + $5,500/yr** | "To set up a Marshall Islands DAO LLC with OCI costs $US6,000"; includes registered agent + office (yr 1), one year legal consulting |
| DAObox | **from $18,500** (single payment) | "begins at $18500… encompasses all formation costs, the first year's government fees, and the registered office cost"; scales with treasury size |
| **For-profit Gross Revenue Tax** | **3% of gross revenue** | Excludes capital gains and dividends; $80/yr flat on first $10,000 |
| Non-profit RMI tax | **$0** | No revenue reporting required |
| Legal counsel (optional, recommended) | Varies | Cross-border securities/tax opinion strongly advised |

**First-year estimate:** ~US$9,500–$18,500 depending on provider. **Ongoing annual:** ~US$2,000–$5,500 (agent/compliance) plus 3% GRT if for-profit. These are dramatically cheaper than Cayman (MIDAO cites "$20,000+ per year") or Switzerland (formation alone historically $75,000+).

*Note: a commonly cited "~$450" RMI government annual franchise fee could not be confirmed from any official source; the government portion is bundled into agent packages and not separately disclosed.*

### 4. Compliance & Ongoing Obligations

- **Annual report / BOIR:** Filed January 1–March 31 each year, containing beneficial-ownership information and details on leadership, community engagement, and financial activities. Beneficial-ownership data is retained ≥5 years after dissolution.
- **Recordkeeping:** Governance records and transaction logs must be retained; on-chain records satisfy "in writing" requirements.
- **AML/CFT & sanctions:** ≥25% holders KYC'd annually; on-chain activity monitored for AML/CFT by the registered agent and law enforcement; sanctions-list screening at onboarding. The RMI does not currently offer VASP licenses, and a DAO LLC may not engage in custody of digital assets for others — relevant if X402AccessGate or BankonIdentityRegistry touch custodial functions.
- **RMI tax treatment:** Tax-neutral (0% non-profit; 3% GRT for-profit). The key caveat: **members owe tax in their home jurisdictions.**

**Canada (codephreak is Canadian-resident).** This is material and should be reviewed with a Canadian tax lawyer:
  - The CRA treats crypto as a commodity (property), not currency. Tokens received as compensation/rewards are income at fair market value on receipt; later disposals are capital gains (50% inclusion) or business income (100%) depending on activity level. Crypto-to-crypto swaps are taxable dispositions.
  - **Foreign property reporting (T1135):** If the cost amount of specified foreign property (which can include certain foreign-held crypto) exceeds CAD $100,000 at any time in the year, Form T1135 is required.
  - **Foreign affiliate / FAPI rules:** A non-resident corporation is a "foreign affiliate" of a Canadian resident who holds ≥10%, and a "controlled foreign affiliate" (CFA) where Canadians control it (generally >50%). If the RMI entity is a *for-profit* CFA earning passive income, that income may be **Foreign Accrual Property Income (FAPI)** taxable to codephreak in Canada *on accrual*, whether or not distributed — eliminating any deferral benefit. (A FAPI de minimis applies where the CFA's FAPI is ≤$5,000.) An RMI *non-profit* member-less governance entity that makes no distributions and earns no passive income is a very different fact pattern, but classification of a foreign DAO LLC under Canadian law is fact-specific and unsettled. Reporting forms T1134 (foreign affiliates) and T1135 may apply.
  - Canada is implementing the OECD Crypto-Asset Reporting Framework (CARF) for 2026–2027, increasing CRA visibility.

**U.S. OFAC / sanctions.** A globally tradable governance token means the DAO could interact with sanctioned addresses. OFAC's 2022 Tornado Cash action showed that even smart-contract "code" and downstream interacting users can be swept in. Wallet/address screening (the kind of function BankonIdentityRegistry/X402AccessGate could enforce on-chain) is a practical mitigant. The RMI wrapper does not shield against OFAC jurisdiction where U.S. persons or U.S.-nexus activity is involved.

### 5. Mapping the DAIO/mindX Tech onto the RMI Structure

**The seven DAIO contracts as recognized "smart-contract governance."** RMI law's recognition of algorithmic management means the DAIO suite can serve as the legally operative governance layer, with the operating agreement referencing the deployed addresses:
- **Daio (core), Boardroom, WarCouncil** → the decision-making bodies. The operating agreement maps the on-chain proposal/voting flow to the LLC's "member voting" provisions.
- **BankonIdentityRegistry + CAIP-122 / login333** → membership identity and the KYC gate (see below).
- **X402AccessGate, ChainRegistry** → access control and multi-chain registry; must avoid functioning as custodial VASP activity.
- **DeadmansSwitch** → continuity/succession mechanism; in legal terms this can be tied to dissolution, manager-replacement, or emergency-control clauses in the operating agreement.

**Mapping the CEO + 7 Counsellors cabinet, Boardroom, War Council, and 0.666 supermajority.** RMI law lets the operating agreement define membership, voting rights, quorum, and supermajority thresholds with near-total freedom — membership interests can be calculated by governance tokens or one-member-one-vote, and quorum/voting rules are whatever the documents specify. This is a decisive advantage over Wyoming, whose statute imposes an impractical 50% quorum. The DAIO 0.666 supermajority threshold (essentially two-thirds, 66.6%) is a standard, widely used supermajority basis and can be written verbatim into the operating agreement as the threshold for binding decisions, with the CEO + 7-Counsellor cabinet defined as managing members or as an on-chain council whose multisig/contract execution the agreement recognizes as valid corporate action. On-chain voting that meets the operating agreement's quorum and supermajority satisfies the LLC's member-voting requirements — there is no separate off-chain approval needed. Real precedents confirm this works: the Pyth DAO LLC operating agreement "simply points to the Pyth governance smart contracts," and the Teia DAO LLC defines TEIA token holders as legally recognized "operating members," with its multisig executing decisions at a 55% on-chain quorum.

**The VOTE DAIO token and the 13-vote War Council.** The DAIO design issues a separate, fixed-mint **VOTE DAIO governance token capped at 13 tokens**, where **1 token = 1 vote in the War Council** (the WarCouncil contract). RMI LLC law accommodates this cleanly through *classes of membership interest*: the operating agreement can define VOTE DAIO holders as a distinct voting class — the War Council — with its own quorum and threshold rules, sitting alongside (and separate from) the broader BANKON PYTHAI membership. Two concrete consequences flow from the 13-token cap and must be written explicitly into the operating agreement:
- **The 0.666 supermajority resolves to a hard floor of 9 of 13 votes.** 0.666 × 13 = 8.66, so a binding War Council decision requires **≥9 affirmative VOTE tokens** (9/13 = 69.2%, which clears two-thirds). State this exact integer in the operating agreement — "nine of thirteen" — rather than only the 0.666 ratio, to eliminate rounding ambiguity in close votes (8 of 13 = 61.5% would *fail*).
- **The ≥25% KYC trigger lands at 4 tokens.** Each VOTE token equals 7.69% of War Council voting power; 3 tokens = 23.1% (below threshold), but **4 tokens = 30.8%, crossing the 25%-governance-rights line that mandates KYC** under RMI rules. Any holder of 4+ VOTE tokens — and any managing-member Counsellor — must complete identity verification with the registered agent, while holders of 1–3 tokens may remain pseudonymous. With at most 13 voters total, the registered agent's KYC burden is trivially small, and the entire War Council can be mapped to named or pseudonymous members in a single page of the operating agreement.

Because VOTE DAIO carries voting power only and **no economic rights**, it stays on the safe side of the 2023 amendment's "governance tokens are not securities" provision — but its extreme scarcity (13 units) concentrates control, so the operating agreement should address transfer restrictions, succession of a lost/destroyed token (tie this to the DeadmansSwitch contract), and what happens to War Council authority if fewer than 9 tokens are ever active.

**BANKON PYTHAI OFT V2 as governance/membership token.** The token (111,111.111 fixed supply, 18 decimals, LayerZero burn-and-mint omnichain OFT) — the broad membership token, distinct from the 13-unit VOTE DAIO War Council class above — can function as the general membership/governance token: RMI law permits the DAO LLC to admit all governance-token holders as members automatically, without KYC for sub-threshold holders, with membership transferring simultaneously with the token. Two critical conditions and caveats:
  - **Keep it a pure governance token.** The 2023 amendment confirms "governance tokens are not considered securities if they do not confer any economic rights." If BANKON PYTHAI confers profit/dividend/revenue rights, it risks being a "digital security," triggering RMI securities provisions (and far more importantly, foreign securities laws).
  - **Securities exposure abroad is the real risk.** Under the U.S. *Howey* test, a token sold with profit expectations from others' efforts is an investment contract/security (per the SEC's 2017 DAO Report). Even with a friendlier 2025 SEC posture, this remains unresolved; the safest path is to (a) structure BANKON PYTHAI as non-economic governance, (b) restrict primary sales to non-U.S. persons, and (c) obtain a securities opinion. The omnichain (LayerZero OFT) nature multiplies jurisdictional touchpoints, and regulators may scrutinize identifiable actors in the stack (DVNs, relayers, the issuer retaining admin control).

**Identity/KYC via BankonIdentityRegistry + CAIP-122 / login333.** CAIP-122 ("Sign-In With X") provides cryptographic proof of wallet/account ownership — excellent for authenticating members and gating governance. However, **proving wallet control is not the same as KYC.** RMI's registered-agent KYC duty for ≥25% holders requires real-world identity verification (legal name, address, passport) and sanctions screening. Self-sovereign identity (SSI) and verifiable credentials *can* streamline and even satisfy this — by binding a verified KYC credential to a wallet via the registry — but only if the underlying verification meets the agent's AML standard. In practice: use BankonIdentityRegistry + CAIP-122/login333 as the on-chain authentication and access layer, and layer a reusable-KYC verifiable credential (issued by a compliant provider) onto it for the small set of beneficial members who cross the 25% threshold (i.e., any holder of 4+ VOTE DAIO tokens). Sub-threshold members can remain pseudonymous via pure wallet auth.

### 6. Jurisdiction Comparison

| Jurisdiction | Entity | Native on-chain/algorithmic governance | Token-holders as members | Tax | Indicative cost | Key drawback for mindX/DAIO |
|---|---|---|---|---|---|---|
| **Marshall Islands** | DAO LLC (non-profit or for-profit) | **Yes — directorless, smart-contract management statutory** | **Yes, automatic by token** | 0% non-profit / 3% GRT | ~$9.5k–$18.5k + ~$2k–$5.5k/yr | New, untested case law; offshore "high-risk" optics with some banks |
| **Wyoming** | DAO LLC / DUNA | Yes, but 50% quorum; immutable contracts barred; auto-dissolves if inactive 1 yr | Yes | U.S. pass-through (DUNA taxed as for-profit) | ~$100 filing + $20k–$60k legal | U.S. jurisdiction = full federal/securities exposure |
| **Cayman** | Foundation Company | No — human directors are the legally operative layer | Beneficiaries, not members | 0% | ~$20k+/yr | Directors required; member-voting only advisory |
| **Switzerland** | Association / Foundation | No dedicated DAO form; no member-voting recognition for foundation | Association members yes | Variable | Foundation historically $75k+; 4–6 mo | Costly, slow, council control |
| **Panama** | Private Interest Foundation | No | Beneficiaries | 0% | Mid-range | Minimal disclosure but no DAO-native governance; optics |

**Verdict:** For a directorless, token-governed, AI-driven, omnichain system whose architect wants the *code* to be the legally recognized governance, the **RMI non-profit DAO LLC is the best fit.** Wyoming's only edge (U.S. domicile) is a liability here, not an asset.

## Recommendations

**Stage 1 — Pre-formation (week 0–2).**
- Decide **non-profit DAO LLC** for the mindX/DAIO governance entity (0% RMI tax, "ownerless," best fit for a protocol/public-benefit system). Reserve the option of a separate for-profit entity or Series DAO LLC for any revenue-generating arm.
- Lock both **BANKON PYTHAI** and **VOTE DAIO** as **pure governance tokens (no economic rights)** in documentation; if economic rights are intended for either, plan a separate token/entity and budget for securities counsel.
- Engage (a) a crypto/cross-border attorney for a securities opinion and (b) a **Canadian tax lawyer** on CFA/FAPI/T1134/T1135 exposure. *Benchmark to change course:* if counsel concludes the token is likely a security in target markets, restructure before any token sale.

**Stage 2 — Engage agent & draft (week 2–4).**
- Retain **MIDAO** (government-authorized, $9,500) or compare OCI ($6,000 + $5,500/yr) / entity.legal ($30–50/mo) / DAObox (from $18,500) on price and service depth. For lowest cost and API-driven Series structure, entity.legal; for full-service, MIDAO; for hands-on governance design, DAObox.
- Draft the operating agreement to: (i) declare DAO status; (ii) list the DAIO contract addresses (Daio core, Boardroom, WarCouncil, etc.); (iii) define general members as BANKON PYTHAI holders; (iv) codify the **CEO + 7-Counsellor cabinet**, define **VOTE DAIO holders (13-token mint, 1 token = 1 vote) as the War Council voting class**, and set the **0.666 supermajority as the exact integer "≥9 of 13"** threshold; (v) tie DeadmansSwitch to succession/dissolution and lost-token clauses; (vi) state that on-chain execution is valid corporate action and the written agreement controls in conflict.

**Stage 3 — File & launch (week 4–8).**
- Complete KYC for any ≥25% governance-rights holder — i.e., any holder of 4+ VOTE DAIO tokens (likely codephreak initially) and any managing Counsellor — and name at least one UBO; file BOIR; receive Certificate of Formation.
- Stand up reusable-KYC verifiable credentials integrated with BankonIdentityRegistry/CAIP-122 for beneficial members; keep sub-threshold members pseudonymous.
- Implement OFAC address-screening at the X402AccessGate/registry layer.

**Stage 4 — Ongoing.**
- Calendar the **Jan 1–Mar 31 BOIR** filing and annual agent fee. If for-profit, track gross revenue for the 3% GRT.
- File Canadian T1134/T1135 as applicable; report personal crypto income/gains to CRA. *Benchmark:* if the entity becomes a for-profit CFA earning passive income, expect FAPI accrual taxation in Canada — revisit structure with your advisor.

## Action Checklist
- [ ] Decide non-profit vs. for-profit (recommended: **non-profit** for governance entity)
- [ ] Confirm **BANKON PYTHAI and VOTE DAIO** are both structured as **non-economic governance tokens**
- [ ] Retain cross-border securities counsel + Canadian tax lawyer
- [ ] Reserve name ending in "DAO LLC"
- [ ] Engage MIDAO (or alternative authorized agent)
- [ ] Draft operating agreement referencing DAIO contract addresses + CEO/7-Counsellor cabinet + **VOTE DAIO War Council class (13 tokens, ≥9-of-13 = 0.666 supermajority)**
- [ ] Complete KYC for ≥25% holders (**≥4 VOTE DAIO tokens**) and managing Counsellors; name ≥1 UBO
- [ ] File Certificate of Formation + BOIR; receive recognition
- [ ] Integrate reusable-KYC VC with BankonIdentityRegistry/CAIP-122
- [ ] Implement OFAC screening at access-gate layer
- [ ] Calendar annual Jan 1–Mar 31 BOIR + agent fee + (if for-profit) GRT
- [ ] File Canadian T1134/T1135 as applicable

## Caveats
- **This is not legal or tax advice.** DAO law in the RMI is new and largely untested in court; cross-border securities and tax treatment of token-governed entities is unsettled. Engage qualified RMI, U.S./securities, and Canadian tax counsel before acting.
- **Figures are 2025–2026 indicative.** The RMI government fee portion is bundled and not separately published; agent prices and the "~$450" franchise figure could not be independently confirmed. Confirm current pricing directly with the chosen agent.
- **Token classification is the pivotal risk.** Whether BANKON PYTHAI or VOTE DAIO is a security depends on facts (economic rights, marketing, purchasers) and varies by jurisdiction. The RMI's "governance tokens aren't securities" provision does not bind the SEC, CRA, or other regulators.
- **Offshore optics & banking.** Some banks/partners auto-flag "Marshall Islands" as high-risk; budget time for banking onboarding.
- **The wrapper limits, not eliminates, liability.** Limited liability and tax-neutrality apply in the RMI; extraterritorial regulators (SEC, CFTC, OFAC, CRA) can still assert jurisdiction over activity touching their markets or residents.
