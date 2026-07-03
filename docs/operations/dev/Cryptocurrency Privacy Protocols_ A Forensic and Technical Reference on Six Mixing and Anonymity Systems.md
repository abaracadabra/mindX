# Six Cryptocurrency Privacy & Anonymity Protocols: A Forensic & Technical Reference

**A standalone educational reference document on Bitcoin Fog, Tornado Cash, Dash, Monero, Komodo, and Bitcoin Cash.**

---

## Table of Contents

1. [Bitcoin Fog](#1-bitcoin-fog)
2. [Tornado Cash](#2-tornado-cash)
3. [Dash](#3-dash)
4. [Monero](#4-monero)
5. [Komodo](#5-komodo)
6. [Bitcoin Cash](#6-bitcoin-cash)
7. [Further Reading](#further-reading)
8. [Technical Glossary](#technical-glossary)

---

## 1. Bitcoin Fog

### Origin and Operators

Bitcoin Fog was the longest-running custodial Bitcoin tumbler in the history of cryptocurrency, operating continuously from October 2011 until April 2021. It was announced on the [BitcoinTalk forum](https://bitcointalk.org/) by a user posting under the handle **Akemashite Omedetou** ("Happy New Year" in Japanese), who promised total anonymity by pooling deposits and disbursing them in randomized amounts at randomized intervals. The U.S. Department of Justice ultimately alleged that this pseudonym was operated by **Roman Sterlingov**, a dual Russian-Swedish national who was [22 years old at the time of the launch](https://protos.com/bitcoin-fog-history-roman-sterlingov-bitcointalk/). At its peak in February 2012, Sterlingov reported that Bitcoin Fog was already processing 150–200 BTC per day. Over its decade of operation, the DOJ's [November 8, 2024 sentencing press release](https://justice.gov/opa/pr/bitcoin-fog-operator-sentenced-money-laundering-conspiracy) states that Bitcoin Fog "processed transactions involving over 1.2 million bitcoin, valued at approximately $400 million at the time the transactions occurred," and that Principal Deputy Assistant Attorney General Nicole M. Argentieri concluded "Roman Sterlingov laundered over $400 million in criminal proceeds through Bitcoin Fog."

Sterlingov was [arrested on April 27, 2021 at Los Angeles International Airport](https://justice.gov/opa/pr/individual-arrested-and-charged-operating-notorious-darknet-cryptocurrency-mixer) by IRS-Criminal Investigation agents from the District of Columbia Cyber Crime Unit and the FBI Washington Field Office. He was held in pre-trial detention continuously for nearly three years until trial. Bitcoin Fog ceased operations effectively on the date of his arrest, though the website (`bitcoinfog.pw`) and certain custodial wallets persisted afterward — including a [1,354 BTC wallet that the court ultimately ordered forfeited](https://www.upi.com/Top_News/US/2024/11/09/longest-bitcoin-laundering-service-man-sentenced/8411731178404/), valued at more than $103 million at sentencing.

### Protocol Mechanics

Bitcoin Fog was a **centralized custodial mixer**. Unlike modern non-custodial mixers (which rely on cryptographic obfuscation), Bitcoin Fog required users to deposit BTC into a wallet controlled by the operator. The service then waited (typically 40 to 120 minutes for small amounts, days for large amounts), broke deposits into many small fragments, commingled them with deposits from other users in a single internal pool, and finally disbursed funds to user-specified withdrawal addresses in amounts that were deliberately not equal to the original deposit amounts. The official [bitcoinfog.pw](https://bitcoinfog.pw/) help text explicitly advised users to make multiple non-matching deposits and withdrawals so that "there is no way to analyze or correlate your deposits with your withdrawals on the block chain."

The architecture was therefore not a cryptographic privacy protocol at all in the modern sense — it was a **trust-based statistical obfuscator**. The operator necessarily held the entire mapping between deposit and withdrawal addresses and could de-anonymize users at will (or be compelled to do so by law enforcement). The minimum withdrawal was 0.001 BTC; fees fluctuated but typically ranged between 1% and 3%.

### Source Code

Bitcoin Fog never released its server-side source code; it was a closed, custodial web service hosted as a Tor hidden service. No public repository walkthrough is possible. What is publicly accessible is the [archived web interface](https://bitcoinfog.pw/) and the BitcoinTalk announcement threads under the `Akemashite Omedetou` handle.

### Legal Case

The criminal case is captioned **United States v. Sterlingov**, Case No. **1:21-cr-00399-RDM** (D.D.C.), assigned to U.S. District Judge **Randolph D. Moss**. Trial Attorneys Jeff Pearlman and C. Alden Pelker of the DOJ Criminal Division's Computer Crime and Intellectual Property Section (CCIPS) and Assistant U.S. Attorney Christopher B. Brown for the District of Columbia prosecuted. Defense was led by Tor Ekeland. Key dates:

- **April 27, 2021** — Arrest at LAX.
- **June 23 / August 22 / September 13–15, 2023** — Daubert hearings on the admissibility of Chainalysis Reactor evidence.
- **February 29, 2024** — Judge Moss issued a [Memorandum Opinion and Order](https://www.moneylaunderingnews.com/wp-content/uploads/sites/12/2024/03/District_of_Columbia_USA_v._STERLINGOV_Memo_Opinion_and_Order.pdf) holding that Chainalysis Reactor's testimony was admissible under Federal Rule of Evidence 702 and the *Daubert* standard.
- **March 12, 2024** — Jury verdict: guilty on all four counts (money laundering conspiracy, money laundering, operating an unlicensed money transmitting business, and money transmission without a license in DC).
- **November 8, 2024** — Sentencing: **12 years 6 months (150 months)** in prison, $395,563,025.39 in restitution, $1.76 million in forfeited assets, and forfeiture of the 1,354 BTC Bitcoin Fog wallet (then worth ~$103M). Prosecutors had sought 30 years; the defense had asked for no more than 7. Sterlingov is appealing.

The trial also featured testimony from cooperating witnesses **Larry Harmon** (former operator of the Helix mixer, who pleaded guilty in 2021 and forfeited 4,400 BTC plus a $60 million fine) and **Ilya Lichtenstein** (the Bitfinex hack launderer who pleaded guilty in August 2023).

### How the Mixing Was Broken

Bitcoin Fog was de-anonymized through a combination of (a) **blockchain forensics** using Chainalysis Reactor's clustering heuristics, (b) **off-chain OSINT** linking the `Akemashite Omedetou` handle and Sterlingov's known accounts on the now-defunct **Mt. Gox** and **BTC-e** exchanges, and (c) **IP correlation** showing the same IP addresses logging into Bitcoin Fog administrator accounts and Sterlingov's personal accounts during overlapping intervals. The government's prosecution memorandum and Judge Moss's Daubert ruling describe a layered case in which:

> *"This is not a case in which the government's theory that Sterlingov was the operator of Bitcoin Fog turns exclusively, or even primarily, on Scholl and Bisbee's use of the Reactor software... the government relies in substantial part on materials found in Sterlingov's possession when he was arrested, various posts on an online forum called Bitcoin Talk, internet protocol ('IP') analyses showing an individual accessing accounts directly linked to the Bitcoin Fog administrator and accounts directly linked to Sterlingov in close temporal proximity."* — Memorandum Opinion, Dkt. 259 (Feb. 29, 2024)

Chainalysis Reactor used multi-input clustering ("Heuristic 1"), change-address heuristics, and behavioral patterns to attribute over **900,000 Bitcoin addresses to the Bitcoin Fog cluster**. The system traced 43 transactions from 144 unique Bitcoin Fog cluster addresses to Sterlingov's personal accounts on Kraken and Mt. Gox.

### The Forensic Methodology Controversy

The case generated **the first sustained judicial scrutiny of proprietary blockchain analytics software in a U.S. criminal trial**, and it remains one of the most contested forensic-science questions in cryptocurrency enforcement. Sterlingov's defense — supported by experts including forensic accountant J. W. Verret — argued that Chainalysis Reactor is a "black-box" system with **no published error rate**, **no peer review**, and **no public access to its source code**. At the June 23, 2023 hearing, Chainalysis Government Solutions' Head of Investigations **Elizabeth Bisbee** testified that she was "unaware" of any scientific publication validating Reactor's accuracy. CipherTrace expert **Jonelle Still** likewise testified that her firm did not use the behavioral heuristics Chainalysis relied upon, and that running the Bitcoin Fog data through CipherTrace's own toolset did not by itself identify Sterlingov as the operator.

The court nonetheless [admitted the evidence](https://caselaw.findlaw.com/court/us-dis-crt-dis-col/115886148.html), finding the methodology corroborated by Sterlingov's own pre-trial testimony (in which he conceded that BTC in his Kraken account had passed through Bitcoin Fog), by manual on-chain tracing, and by cross-validation against TRM Labs and CipherTrace clustering. After conviction, the firm [**ChainArgos** filed an amicus brief on September 22, 2025](https://www.chainargos.com/chainalysis-claims-95-accuracy-why-thats-irrelevant/) in support of Sterlingov's appeal, arguing that the blockchain forensics presented at trial was "fundamentally unscientific" under the standards set out in the 2009 U.S. National Academy of Sciences report *Strengthening Forensic Science in the United States: A Path Forward*. **Elliptic's** Tom Robinson and Chainalysis exchanged public statements during the controversy, with both firms defending their respective methodologies. The Sterlingov *Daubert* ruling has since been cited by prosecutors in **U.S. v. Storm** (Tornado Cash) and **The Netherlands v. Pertsev**.

### Forensic and Historical Significance

Bitcoin Fog's investigation also surfaced its central role in laundering proceeds from the **Welcome to Video** child sexual abuse material site and from a long roster of darknet markets: **Silk Road**, **Silk Road 2.0**, **Agora**, **Evolution**, **AlphaBay**, and **Sheep Marketplace**. Investigators traced the original Bitcoin Fog domain purchase through Liberty Reserve payments tied to Mt. Gox accounts that Sterlingov logged into from his personal IP addresses — a forensic trail that began with KYC data leaks from the **2014 collapse of Mt. Gox** and the **2017 indictment of Alexander Vinnik of BTC-e**, which produced the underlying KYC records used to identify Sterlingov.

---

## 2. Tornado Cash

### Origin and Status

Tornado Cash is a **non-custodial, smart-contract-based Ethereum mixer** built on zero-knowledge proofs. The protocol was deployed beginning in 2019 by three co-founders: **Roman Storm** (a U.S. resident based in Auburn, Washington), **Roman Semenov** (a Russian national), and **Alexey Pertsev** (a Russian national resident in the Netherlands). The protocol's smart contracts were uploaded to the Ethereum mainnet in 2019, with the immutable pool smart contracts irreversibly locked (their admin keys ceremonially destroyed) in May 2020.

As of May 2026, the protocol's smart contracts **remain live and functional** on Ethereum and on several sidechains and L2s including Gnosis Chain (formerly xDai), Binance Smart Chain, Polygon, Avalanche, Arbitrum, and Optimism. Elliptic's published research estimates "nearly $9 billion in total funds sent through the Tornado Cash mixer to date." Pertsev was convicted in the Netherlands in May 2024; Storm was partially convicted in the U.S. in August 2025; Semenov remains at large.

### Cryptographic Mechanics

Tornado Cash Classic operates on **fixed-denomination anonymity pools** (0.1 ETH, 1 ETH, 10 ETH, and 100 ETH on Ethereum, with analogous denominations for DAI, cDAI, USDC, USDT, and WBTC). The cryptographic primitives are:

- **zk-SNARK proving scheme**: **Groth16** over the BN254 (alt_bn128) elliptic curve, allowing efficient on-chain proof verification (~230k gas).
- **Hash function for Merkle tree**: **MiMC Sponge** — chosen because it is "SNARK-friendly," meaning it can be expressed efficiently in arithmetic circuits over the BN254 scalar field. (Note that newer ZK mixers often prefer Poseidon.)
- **Accumulator**: an **incremental Merkle tree of height 20**, allowing 2²⁰ ≈ 1 million deposits per pool. Each leaf is a deposit commitment.
- **Pedersen hash** is used to bind the user's secret and nullifier into a commitment.

The **deposit flow** proceeds as follows: a user generates two random 31-byte values, the `secret` and the `nullifier`. The user computes a commitment `commitment = PedersenHash(secret, nullifier)`. The user then sends a transaction depositing exactly 1 ETH (or 0.1, 10, or 100) to the Tornado Cash pool contract, including the commitment as a public argument. The pool contract inserts the commitment as a leaf in its Merkle tree and emits an event.

The **withdrawal flow** is where the privacy magic happens. To withdraw, the user generates a Groth16 zk-SNARK proof off-chain that demonstrates: (i) knowledge of a `(secret, nullifier)` pair whose commitment is contained somewhere in the current Merkle tree (proven via a Merkle path), and (ii) the corresponding `nullifierHash = Hash(nullifier)`. The proof is submitted to the contract along with the recipient address, an optional relayer address, and a fee. The contract verifies that the proof's Merkle root matches one of the last 30 historical roots (`isKnownRoot`), that the `nullifierHash` has not already been seen, and then disburses the deposited amount to the recipient. Because the proof reveals nothing about which commitment was spent, there is no on-chain link between the depositor and the withdrawer except membership in the same anonymity set.

A **relayer network** addresses the bootstrapping problem: a freshly empty recipient address has no ETH to pay gas. Relayers submit the withdrawal transaction on behalf of the user in exchange for a small fee deducted from the withdrawal. This preserves anonymity by decoupling the withdrawal from the user's funded address. The original [Tornado Cash whitepaper v1.4](https://berkeley-defi.github.io/assets/material/Tornado%20Cash%20Whitepaper.pdf) describes the construction formally.

### Trusted Setup

Groth16 requires a circuit-specific trusted setup. Tornado Cash used the [**Perpetual Powers of Tau** (PPOT) ceremony](https://blog.ethereum.org/2020/12/09/ef-supported-teams-research-and-development-update-2020-pt-2), a community-driven multi-party computation launched in September 2019 that produced a reusable Phase 1 string for BN254-based circuits. Tornado Cash then layered its own circuit-specific Phase 2 contribution on top. The PPOT ceremony supports circuits up to 2²⁸ constraints; as long as **at least one** of the 60+ participants destroyed their toxic waste, the resulting setup is secure.

### Source Code Architecture

The original Tornado Cash GitHub organization at [github.com/tornadocash](https://github.com/tornadocash) was taken offline by GitHub on August 8, 2022 (the day OFAC sanctioned the protocol), though community mirrors and the original IPFS deployments persist. The major repositories and their roles are:

- [**`tornado-core`**](https://github.com/tornadocash/tornado-core) — Solidity contracts implementing the deposit/withdraw pool, the MiMC hasher, the Merkle tree, and the Groth16 verifier; Circom circuits (`withdraw.circom`) defining the SNARK constraint system. This is the on-chain heart of the protocol.
- [**`tornado-classic-ui`**](https://github.com/tornadocash/tornado-classic-ui) — The Nuxt.js web frontend for the classic fixed-denomination pools, deployed via IPFS.
- [**`tornado-nova`**](https://github.com/tornadocash/tornado-nova) — The Nova variant that supports **arbitrary amounts and shielded transfers** on Gnosis Chain (the former xDai), bridging from Ethereum mainnet via the AMB Omnibridge. Nova introduces a UTXO-style model and was launched in December 2021. Withdrawals to L1 must exceed 0.05 ETH to prevent bridge-spam attacks. The Nova circuits were audited by Igor Gulamov of Zeropool.
- [**`tornado-anonymity-mining`**](https://github.com/tornadocash/tornado-anonymity-mining) — Implementation of the anonymity-mining incentive (active until December 2021), which rewarded depositors who kept funds in pools longer with the governance token TORN.
- [**`tornado-relayer`**](https://github.com/tornadocash/tornado-relayer) — Node.js relayer reference implementation.
- [**`tornado-cli`**](https://github.com/tornadocash/tornado-cli) — Command-line interface for depositing, withdrawing, and reconstructing notes offline.
- [**`circomlib`**](https://github.com/iden3/circomlib) (maintained by iden3) — Provides MiMC, Pedersen hash, EdDSA, and other zk-friendly primitives consumed by `tornado-core`.

**Governance** is managed by the **TORN token**, which controls a community-governed DAO. TORN was distributed in December 2020 via an airdrop and anonymity-mining program. The governance contract can deploy new pools and adjust parameters on **mutable** wrapper contracts, but it **cannot** modify the core immutable pool contracts that anchor the system.

### Legal and Regulatory Timeline

- **August 8, 2022** — The U.S. Treasury Department's Office of Foreign Assets Control (OFAC) [sanctioned Tornado Cash](https://home.treasury.gov/news/press-releases/jy0916), placing the protocol and 44 associated Ethereum addresses on the Specially Designated Nationals and Blocked Persons (SDN) List. Treasury's August 8, 2022 designation notice stated that "The Lazarus Group...used Tornado Cash to obfuscate the movement of over $455 million stolen in the March 2022 attack on Axie Infinity's Ronin network bridge, the largest known virtual currency heist to date," with total Tornado Cash volumes alleged at "more than $7 billion."
- **August 10, 2022** — Alexey Pertsev was arrested in the Netherlands.
- **September / October 2022** — Coin Center filed suit in Florida (later moved to the 11th Circuit), and six Tornado Cash users (lead plaintiff Joseph Van Loon) filed suit in the Western District of Texas, both arguing OFAC exceeded its IEEPA authority.
- **June 24, 2022** — The Lazarus Group exploited Harmony's Horizon Bridge for ~$100 million; ~$96 million was laundered through Tornado Cash. The August 2, 2022 Nomad bridge hack added at least $7.8 million in laundered proceeds.
- **November 15, 2022** — OFAC re-designated Tornado Cash citing Executive Order 13694.
- **August 23, 2023** — A grand jury in the Southern District of New York returned an [indictment](https://www.justice.gov/usao-sdny/pr/tornado-cash-co-founders-charged-money-laundering-and-sanctions-violations) of Roman Storm and Roman Semenov in case **1:23-cr-00430** (S.D.N.Y., Judge Katherine Polk Failla) on three counts: (1) conspiracy to commit money laundering, (2) conspiracy to commit sanctions violations (IEEPA), and (3) conspiracy to operate an unlicensed money transmitting business. Storm was arrested in Washington State on the same day. Semenov is at large.
- **May 14, 2024** — **The Netherlands v. Alexey Pertsev**, East Brabant District Court, Case No. 82/198261-22: a three-judge panel found Pertsev guilty of laundering $1.2 billion (some reports: $2.2 billion) through Tornado Cash, sentencing him to **64 months (5 years 4 months)** in prison and ordering forfeiture of a Porsche and €1.9 million in seized crypto. Judge Henrieke Slaar stated from the bench: *"Tornado Cash in its nature and functioning is a tool intended for criminals. The criminal user is fully facilitated."* Pertsev was sent directly from the courtroom to a Dutch penitentiary; his appeal remains pending.
- **November 26, 2024** — [**Van Loon v. Department of the Treasury**, No. 23-50669 (5th Cir. 2024)](https://www.ca5.uscourts.gov/opinions/pub/23/23-50669-CV0.pdf), a unanimous three-judge panel of the U.S. Court of Appeals for the Fifth Circuit, reversed the district court and held that **OFAC exceeded its statutory authority** under IEEPA by sanctioning Tornado Cash's immutable smart contracts, because *"immutable smart contracts ... are not the 'property' of a foreign national or entity"* in the plain meaning of IEEPA — they are not "capable of being owned." This was one of the first appellate sanctions decisions applying the new *Loper Bright* framework that ended Chevron deference.
- **March 21, 2025** — The Treasury Department [delisted Tornado Cash](https://www.steptoe.com/en/news-publications/international-compliance-blog/treasury-department-delists-tornado-cash-following-the-fifth-circuits-decision.html) from the SDN list following the *Van Loon* mandate, but explicitly framed the decision as an exercise of "discretion" rather than a concession that the Fifth Circuit was correct. Semenov individually remains designated.
- **August 6, 2025** — **United States v. Storm** (S.D.N.Y.): after a four-week trial before Judge Failla and nearly a week of jury deliberations, the jury returned a [partial verdict](https://www.coindesk.com/policy/2025/08/06/roman-storm-guilty-of-unlicensed-money-transmitting-conspiracy-in-partial-verdict). Storm was convicted on **Count 3 — conspiracy to operate an unlicensed money transmitting business** (max 5 years), but the jury hung on Counts 1 and 2 (money-laundering conspiracy and IEEPA conspiracy, each carrying up to 20 years). The result was widely described as a **partial mistrial**. Storm remained free on bail pending sentencing and indicated he would appeal. The Department of Justice retains the option to retry on the deadlocked counts.

### How Tornado Cash Privacy Was Eroded

Despite the strong cryptographic foundation, Tornado Cash withdrawals have been systematically **de-mixed** by chain-analytics firms in many cases. The dominant attacks are:

1. **Anonymity-set collapse**: Pools with low usage in a given epoch reveal too much. If only a handful of deposits exist in a denomination, withdrawals can be matched probabilistically by timing.
2. **Address-reuse and clustering on the recipient side**: Many users withdraw to addresses that have other on-chain history, which an analyst can immediately link to KYCed exchange accounts.
3. **Common-relayer fingerprinting**: A withdrawer who consistently uses the same relayer, or who uses an unusual relayer-fee pattern, becomes statistically separable.
4. **Deposit/withdraw timing correlation**: Especially for large structured laundering (e.g., Lazarus Group hacks), the systematic pattern of dozens or hundreds of equal-size deposits followed by equal-size withdrawals to fresh addresses produces a clear footprint, as documented by [Elliptic's analysis of the Harmony Horizon laundering](https://www.elliptic.co/hubfs/Harmony%20Horizon%20Bridge%20Hack%20P1%20briefing%20note%20final.pdf).
5. **Cross-protocol leakage via Railgun and other downstream mixers**: when Lazarus moved Harmony funds from Tornado Cash through Railgun in January 2023, the unusual concentration of Harmony-tainted ETH in a small Railgun pool made the mixing effectively reversible.

Elliptic concluded that the Lazarus Group sent more than **$555 million** through Tornado Cash from the Ronin and Harmony hacks alone — about **5.8%** of the nearly $9 billion in total funds ever sent through the mixer.

### Cryptographic Vulnerabilities

The Groth16 proving system has a known **proof-malleability** property: an attacker who has a valid proof can construct a different but equally valid proof for the same public inputs. The Tornado Cash contracts defend against this only by tracking nullifier hashes (not entire proofs); as documented by [Beosin](https://beosin.com/resources/exploring-tornado-cash-in-depth-to-reveal-malleability-attac), naive Groth16 wrappers that only record proof bytes would be vulnerable to replay attacks. The Tornado Cash design avoids this by keying double-spend prevention on the nullifier rather than the proof.

### Key Academic Papers and Specifications

- [**Tornado Cash Privacy Solution v1.4 Whitepaper**](https://berkeley-defi.github.io/assets/material/Tornado%20Cash%20Whitepaper.pdf) — the canonical protocol specification.
- **Groth16** — Jens Groth, "On the Size of Pairing-based Non-interactive Arguments" (EUROCRYPT 2016), [eprint 2016/260](https://eprint.iacr.org/2016/260).
- **MiMC** — Albrecht, Grassi, Rechberger, Roy, Tiessen, "MiMC: Efficient Encryption and Cryptographic Hashing with Minimal Multiplicative Complexity" (ASIACRYPT 2016), [eprint 2016/492](https://eprint.iacr.org/2016/492).
- [**Snarky Ceremonies**](https://eprint.iacr.org/2021/219) — Kohlweiss et al., analysing the security of multi-party trusted setups including Tornado Cash, Plumo, and Hermez.

---

## 3. Dash

### Origin and Status

Dash launched on **January 18, 2014** under the name **XCoin**, the work of programmer **Evan Duffield**. The codebase was originally forked from Litecoin (itself a fork of Bitcoin). It was renamed **Darkcoin** within days — an explicit branding nod to the privacy-focused Dark Wallet bitcoin project — and was rebranded again to **Dash** ("digital cash") in March 2015 as the project moved its public positioning away from anonymity toward payments. The reference implementation is [github.com/dashpay/dash](https://github.com/dashpay/dash), a direct descendant of Bitcoin Core.

Dash is **not a privacy-by-default protocol** in the way Monero is. It is a Bitcoin-derived UTXO chain with the same fully transparent ledger as Bitcoin, augmented with an **optional opt-in mixing feature** called PrivateSend (originally DarkSend). The vast majority of Dash transactions are not mixed.

Dash remains active as of May 2026, trading on most major exchanges (with notable exceptions for the privacy-coin delistings discussed below). It is widely used as a payments rail in parts of Latin America, notably Venezuela.

### Two-Tier Network Architecture

Dash's defining structural innovation is its **two-tier network**. The first tier consists of conventional miners running the **X11 hashing algorithm** — a chained hash that pipelines eleven cryptographic primitives (BLAKE, BMW, Groestl, JH, Keccak, Skein, Luffa, CubeHash, SHAvite, SIMD, ECHO). The second tier consists of **masternodes**: server nodes that post a collateral of exactly **1,000 DASH** to a special escrow-style transaction, locking the collateral while continuing to control the spending keys. Masternodes provide network services (PrivateSend coordination, InstantSend, ChainLocks, governance voting) and receive **45% of every block reward** in return; miners receive another 45%; and the remaining 10% funds the on-chain treasury, allocated by masternode vote.

Sybil attacks on the masternode tier are economically expensive because the 1,000-DASH collateral is at-stake (it isn't slashed, but it can be moved at any time — doing so simply removes masternode status). At ~4,100 masternodes the total locked collateral is on the order of 4.1 million DASH.

**InstantSend** uses a Long-Living Masternode Quorum (LLMQ) to pre-commit transactions in seconds rather than waiting for block confirmations. **ChainLocks** uses similar LLMQ-signed messages to finalize blocks within seconds, defending against 51% reorganization attacks on the comparatively low-hashrate X11 chain.

### PrivateSend Mechanics

**PrivateSend** (formerly DarkSend) is fundamentally a **CoinJoin** scheme with masternode-coordinated session management. The protocol breaks user funds into **standard denominations** — 0.001, 0.01, 0.1, 1, and 10 DASH — and mixes equal-amount inputs from multiple users in a single transaction so that on-chain analysis cannot distinguish which output corresponds to which input within the same denomination tier. A masternode is randomly contacted by each participating client; the masternode acts as a coordinator, collecting signed inputs and outputs and constructing the joint CoinJoin transaction. Importantly, **the masternode never holds custody of funds** — only the users sign the final transaction.

Users typically configure between 2 and 16 **rounds** of mixing, with each round chaining a fresh CoinJoin on top of the previous output. The default is 4 rounds. Higher round counts increase the anonymity set but linearly increase fees (approximately 0.0001 DASH per ten rounds on average due to anti-spam fees). The maximum amount that can be processed per PrivateSend transaction was historically capped at 1,000 DASH.

Compared to Tornado Cash's zero-knowledge architecture, PrivateSend has two well-known weaknesses: (i) the coordinating masternode learns the input-to-output mapping during the session and could leak it (deliberately, by subpoena, or by compromise), and (ii) the requirement to mix in pre-defined denominations leaves a visible "mixing footprint" on the chain. Repeated rounds across many different masternodes mitigate (i) somewhat, but the masternode tier is also somewhat centralized: estimates from the 2014–2018 period suggested that a small number of operators controlled a meaningful fraction of masternodes.

The PrivateSend specification is maintained in the [Dash documentation](https://docs.dash.org/en/stable/wallets/dashcore/privatesend-instantsend.html), and the on-chain CoinJoin transactions carry a special network code (`DSTX`) identifying them.

### Source Code

[**`github.com/dashpay/dash`**](https://github.com/dashpay/dash) is the reference implementation, forked from Bitcoin Core. Key components:

- `src/coinjoin/` — the CoinJoin / PrivateSend logic, including client, server (masternode), and shared coordination code.
- `src/llmq/` — Long-Living Masternode Quorums, the substrate of InstantSend and ChainLocks.
- `src/masternode/` — masternode list management, payment scheduling, and governance proposal handling.
- `src/governance/` — on-chain voting and treasury management.

Wallet support also exists via [Dash Electrum](https://github.com/dashpay/electrum-dash) and the [Dash Core mobile and desktop wallets](https://github.com/dashpay).

### The Instamine Controversy

Within the first **48 hours** of the network's January 2014 launch, approximately **1.9 million DASH** were mined — roughly **10%** of the projected eventual total supply of ~18.9 million coins. Duffield and the Dash project [characterized this as an accidental mining-difficulty miscalculation](https://bitcoinmagazine.com/culture/battle-privacycoins-why-dash-not-really-private) inherited from the Litecoin code. A community proposal to relaunch the chain or perform an airdrop to flatten the early distribution was rejected; the team opted to continue with the existing chain. Critics have variously characterized the event as an accidental bug, opportunistic premining, or simple negligence; the historical record (early BitcoinTalk posts) is consistent with both readings. Investigative pieces in [Bitcoin Magazine](https://bitcoinmagazine.com/business/op-ed-closer-look-origins-dash-part-2) note that approximately one to five operators controlling ~106 Amazon AWS and Microsoft Azure cloud instances may have captured the bulk of the early supply, raising lasting concerns about Dash's wealth concentration.

### Privacy Coin Delistings

Beginning in late 2020, regulatory pressure on privacy-enhanced cryptocurrencies led several major exchanges to delist coins with mixing features:

- **November 2020** — ShapeShift delisted Monero (XMR), Dash (DASH), and Zcash (ZEC) "for the same reason — to further derisk the company from a regulatory standpoint" per Chief Legal Officer Veronica McGregor in [CoinDesk](https://www.coindesk.com/business/2020/11/10/shapeshift-delists-privacy-coin-zcash-over-regulatory-concerns).
- **January 1, 2021 (announcement) / January 15, 2021 (effective)** — Bittrex announced the [delisting of XMR, ZEC, DASH, and GRIN markets](https://decrypt.co/53012/bittrex-to-delist-privacy-coins-monero-zcash-and-dash-in-two-weeks), with all relevant pairs (BTC, ETH, USDT, USD) removed at 23:00 UTC on January 15.

In response, Dash has progressively de-emphasized its "privacy coin" framing. Official documentation now refers to PrivateSend explicitly as a "form of CoinJoin" rather than a unique anonymizing protocol, and the project's public positioning emphasizes payments speed and merchant adoption.

---

## 4. Monero

### Origin and Lineage

Monero descends directly from the **CryptoNote 2.0** protocol described in a [whitepaper published October 17, 2013](https://bytecoin.org/old/whitepaper.pdf) by the pseudonymous author **Nicolas van Saberhagen**. CryptoNote was first implemented as **Bytecoin**, which launched in March 2014 with a notorious **~80% premine**. A BitcoinTalk user under the handle `thankful_for_today` forked Bytecoin to launch **BitMonero** — the announcement was posted on April 9, 2014, with mainnet launch on **April 18, 2014**. Within weeks the community had become dissatisfied with `thankful_for_today`'s direction and forked the codebase again to **Monero** (Esperanto for "coin"), led by a core team that publicly included Riccardo "Fluffypony" Spagni and grew over time to include Francisco "ArticMine" Cabañas, Surae Noether, Sarang Noether, and many others. There was **no premine** in the Monero fork.

Monero is **active and continues hard-forking on a roughly biannual cadence**. The reference implementation is [github.com/monero-project/monero](https://github.com/monero-project/monero). Research is conducted by the [**Monero Research Lab (MRL)**](https://www.getmonero.org/resources/research-lab/), whose publications (MRL-0001 through MRL-0010 and beyond) provide the theoretical foundation for nearly every protocol upgrade.

### Cryptographic Architecture

Monero is the most aggressively private of all major cryptocurrencies in routine use, because **every transaction enforces three orthogonal privacy guarantees by default**:

**(1) Sender privacy via Ring Signatures.** When a Monero output is spent, the actual signer's public key is hidden among a "ring" of other plausible signers (decoys drawn from the chain's existing UTXO set). The original CryptoNote ring signature was a variant of the Fujisaki-Suzuki Traceable Ring Signature. Monero migrated to **MLSAG** (Multilayered Linkable Spontaneous Anonymous Group signatures) with the introduction of RingCT, and then to **CLSAG** (Compact Linkable Spontaneous Anonymous Group signatures, [Goodell, Noether, RandomRun, 2019](https://eprint.iacr.org/2019/654)) at the **October 17, 2020** hard fork. CLSAG reduced ring-signature size by ~25% and verification time substantially. Since the **August 13, 2022** hard fork at block 2,688,888, the **ring size is fixed at 16** (one real signer plus 15 decoys).

Double-spending is prevented even though the actual signer is hidden, because each spent output produces a unique deterministic **key image** derived from its private key. The network rejects any transaction whose ring signature carries a previously-seen key image.

**(2) Recipient privacy via Stealth Addresses.** Every transaction output is sent to a one-time public key derived from the recipient's long-term view and spend keys via an Elliptic-Curve Diffie-Hellman exchange. The recipient scans every block with their view key to detect which outputs are theirs; outside observers cannot link any output to a known address.

**(3) Amount privacy via Ring Confidential Transactions (RingCT).** Output values are hidden inside **Pedersen commitments** (`C = bG + aJ`, where `a` is the amount and `b` is a blinding factor). A **range proof** demonstrates that the committed amount is non-negative without revealing it. RingCT was first deployed (as an optional feature) at the [**January 10, 2017** hard fork (v4, block 1,220,516)](https://www.getmonero.org/2017/09/13/september-15-2017-protocol-upgrade-hard-fork.html), and made **mandatory** at the **September 16, 2017** hard fork (v6, block 1,400,000). The construction was specified by Shen Noether in [**MRL-0005, "Ring Confidential Transactions"**](https://www.getmonero.org/resources/research-lab/pubs/MRL-0005.pdf), 2015.

The original RingCT range proofs (Borromean ring signatures) were extremely large. At the **October 18, 2018** hard fork (v8, block 1,685,555), Monero replaced them with [**Bulletproofs**](https://eprint.iacr.org/2017/1066) (Bünz, Bootle, Boneh, Poelstra, Maxwell, Wuille, 2018), which reduced typical transaction size by approximately 80%. At the **August 13, 2022** hard fork, Bulletproofs were upgraded to **Bulletproofs+**, yielding a further 5–7% size reduction.

**(4) Network-layer privacy via Dandelion++.** A 2017 protocol due to Fanti et al. (USENIX Security 2018) routes a transaction through a randomized "stem" phase before broadcast, making it statistically difficult to link a transaction to the originating IP address.

**(5) ASIC-resistant mining via RandomX.** At the **November 30, 2019** hard fork (block 1,978,433), Monero replaced CryptoNight-R with [**RandomX**](https://github.com/tevador/RandomX), a memory-hard, CPU-friendly proof-of-work algorithm by `tevador` (with significant contributions from SChernykh and hyc). RandomX executes randomly-generated bytecode per nonce in a virtual machine, deliberately defeating dedicated-silicon optimization.

**(6) Tail Emission.** Monero's main emission concluded in mid-2022. From [**block 2,641,623 mined at 2022-06-09 00:28:57 UTC**](https://monero.observer/monero-enters-tail-emission-era/) (the U.S. evening of June 8, 2022 in eastern time, hence often dated June 8), Monero entered a perpetual tail emission of **0.6 XMR per block** (approximately 0.3 XMR per minute given the 2-minute block target), producing a permanent miner subsidy that asymptotes to below 1% annual inflation and then trends toward zero percent. The economic rationale, articulated by ArticMine, is that a non-zero perpetual subsidy ensures long-term security without relying solely on transaction fees.

**(7) Dynamic block size.** Monero has no hard block-size limit; instead, blocks above the trailing 100-block median incur a quadratic penalty on the miner's reward, allowing organic scaling while disincentivizing spam.

### Source Code Walkthrough

The [**`monero-project/monero`**](https://github.com/monero-project/monero) repository organizes its C++ implementation into:

- [**`src/cryptonote_basic/`**](https://github.com/monero-project/monero/tree/master/src/cryptonote_basic) — Core data structures (transactions, blocks, account keys, stealth address derivation, miner-transaction construction). The fundamental on-the-wire types.
- [**`src/cryptonote_core/`**](https://github.com/monero-project/monero/tree/master/src/cryptonote_core) — Consensus logic, transaction-pool management, blockchain validation, key-image tracking. This is where hard-fork rules are gated by block height.
- [**`src/ringct/`**](https://github.com/monero-project/monero/tree/master/src/ringct) — All RingCT cryptography: MLSAG/CLSAG signatures, Pedersen commitments, range proofs, Bulletproofs and Bulletproofs+. The core privacy machinery lives here.
- [**`src/crypto/`**](https://github.com/monero-project/monero/tree/master/src/crypto) — Low-level Ed25519/curve25519 primitives, hash functions, and RandomX bindings.
- **`src/wallet/wallet2.cpp`** — the canonical wallet implementation used by `monero-wallet-cli` and the GUI; handles output scanning, ring construction (decoy selection), transaction signing, and recovery from view keys.

The Monero Research Lab repository is [github.com/monero-project/research-lab](https://github.com/monero-project/research-lab) and contains all MRL bulletins and works-in-progress.

### How Monero Privacy Has Been Attacked

Despite Monero's robust cryptographic design, several real-world weaknesses have been documented:

**(a) The 0-decoy era (pre-2016).** The original CryptoNote protocol permitted a "mixin" of zero (a true ring of size 1). The seminal academic paper on this is **[Miller, Möser, Lee, Narayanan, "An Empirical Analysis of Linkability in the Monero Blockchain"](https://arxiv.org/abs/1704.04299)** (2017) and **[Kumar, Fischer, Tople, Saxena, "A Traceability Analysis of Monero's Blockchain"](https://eprint.iacr.org/2017/338.pdf)** (ESORICS 2017), which found that **65.9% of all pre-RingCT inputs had zero mix-ins** and were trivially traceable, and that these zero-mixin inputs caused a **cascade effect** that degraded the untraceability of subsequently mixed inputs. Mandatory minimum ring sizes were progressively raised — to 3 in March 2016, to 5 in September 2017 with mandatory RingCT, to 11 in 2019, and to 16 in August 2022 — closing this attack.

**(b) EAE (Eve-Alice-Eve) attacks.** If the same adversarial entity (e.g., an exchange) controls both the deposit and withdrawal sides of a user's flow, ring signatures provide no protection: the adversary knows which output it sent, so it knows which decoy in any subsequent ring containing that output is the real one. This is a fundamental limitation common to all mix-style systems.

**(c) Statistical decoy-selection biases.** Multiple papers have shown that early Monero wallets did not sample decoys from the realistic distribution of "spend ages," making the true input statistically distinguishable. The decoy-selection algorithm has been hardened repeatedly. The most recent MRL work targets [**FCMP++** (Full-Chain Membership Proofs)](https://www.getmonero.org/resources/research-lab/), which would replace bounded-ring signatures with a proof of membership over the *entire* unspent-output set, eliminating the statistical attack surface.

**(d) The 2014 Merkle-tree exploit ([MRL-0002](https://www.getmonero.org/resources/research-lab/pubs/MRL-0002.pdf), September 4, 2014).** A novel counterfeiting attack was executed against Monero exploiting a Merkle-tree implementation bug. The flaw was patched and is the subject of MRL-0002.

**(e) Government-sponsored tracing efforts.** In **September 2020**, the IRS Criminal Investigation Division [announced a $625,000 contract](https://decrypt.co/43451/irs-1-million-contracts-data-firms-crack-monero) to each of **Chainalysis** and **Integra FEC** — totaling $1.25 million — to develop tools "for investigators that would allow them to trace transaction inputs and outputs to a specific user and differentiate them from mixins/multisig actors for Monero and/or Lightning Layer 2 cryptocurrency transactions." This effort, sometimes referenced as part of "Operation Hidden Treasure," produced public deliverables on the Lightning Network side but **no public claim of successful end-to-end Monero tracing has emerged** from either contractor as of May 2026. **CipherTrace** announced its own (private-sector) Monero forensic tool in 2020, but the Monero community pointed out that its capabilities were limited to heuristic enrichment of pre-RingCT-era data and EAE-style flows.

### Key Monero Research Lab Papers

- [**MRL-0001**](https://www.getmonero.org/resources/research-lab/pubs/MRL-0001.pdf) — Adam Mackenzie, "A note on chain reactions in traceability in CryptoNote 2.0" (September 2014).
- [**MRL-0002**](https://www.getmonero.org/resources/research-lab/pubs/MRL-0002.pdf) — Surae Noether, "Counterfeiting via Merkle Tree Exploits within Virtual Currencies Employing the CryptoNote Protocol" (September 2014).
- **MRL-0003** — Shen Noether, "Review of CryptoNote White Paper."
- [**MRL-0004**](https://www.getmonero.org/resources/research-lab/pubs/MRL-0004.pdf) — Mackenzie, S. Noether, "Improving Obfuscation in the CryptoNote Protocol" (January 2015).
- [**MRL-0005**](https://www.getmonero.org/resources/research-lab/pubs/MRL-0005.pdf) — S. Noether, "Ring Confidential Transactions" (2015).
- **MRL-0008 / CLSAG** — Goodell, Noether, RandomRun, "Concise Linkable Ring Signatures and Forgery Against Adversarial Keys" ([eprint 2019/654](https://eprint.iacr.org/2019/654)).
- **Triptych & Arcturus** — MRL preprints on more advanced linkable ring signatures for larger anonymity sets.

---

## 5. Komodo

### Origin and Status

The Komodo Platform was launched in 2016 by **James "jl777" Lee**, originally as a fork of the **Zcash** codebase (which itself descends from Bitcoin via the Zerocash protocol). Lee emerged from the **NXT / SuperNET** ecosystem, where he had developed an interblockchain framework and the BarterDEX atomic-swap engine. The relationship with NXT became strained, and Komodo became the new substrate for his vision.

Komodo's KMD coin retains the **Equihash** mining algorithm and the **zk-SNARK shielded transaction** machinery inherited from Zcash. Its native maximum supply is 200 million KMD, with a block time of approximately 60 seconds. The reference implementation is [github.com/KomodoPlatform/komodo](https://github.com/KomodoPlatform/komodo).

As of May 2026, Komodo remains active, though significantly diminished in market profile from its 2017–2018 peak. The JUMBLR mixer has been **deprecated and removed** from the modern Komodo Wallet / AtomicDEX product line.

### Delayed Proof of Work (dPoW)

Komodo's defining innovation is **delayed Proof of Work (dPoW)**. A network of **64 notary nodes**, elected annually by KMD holders, periodically writes hashes of Komodo blocks onto the **Bitcoin blockchain**. Once a Komodo block has been notarized to Bitcoin, an attacker wishing to reorganize the Komodo chain past the notarization point would have to also reorganize Bitcoin — an economically infeasible task. This anchoring lets Komodo (and any "asset chain" launched via Komodo's infrastructure) inherit a derivative form of Bitcoin's security without competing for the same hashrate.

The 64 notary nodes are elected by KMD holders in annual elections and split into two regional groups. They are paid through a combination of an extra block reward when they mine and a share of fees from notarization transactions.

### Source Code

- [**`KomodoPlatform/komodo`**](https://github.com/KomodoPlatform/komodo) — The core daemon `komodod`, a fork of Zcash's `zcashd`. Includes the standard Zcash-era shielded-transaction codebase plus Komodo-specific extensions for dPoW notarization, **asset chains** (independent blockchains parameterized at launch time via the `-ac_name` and related flags), **CryptoConditions** ("smart-contract" logic), and JUMBLR (in older versions).
- [**`KomodoPlatform/atomicDEX-API`**](https://github.com/KomodoPlatform/atomicDEX-API) — The successor to BarterDEX; a Rust implementation of cross-chain atomic swaps using Hash Time Locked Contracts (HTLCs). This is the engine behind the Komodo Wallet (formerly AtomicDEX), supporting atomic swaps between BTC, ETH, ERC-20s, and KMD asset-chain coins.
- **`SuperNET/iguana`** — The legacy multi-blockchain wallet and DEX framework from which AtomicDEX was derived.

### JUMBLR

**JUMBLR** was Komodo's native mixer, layering a custom anti-correlation scheme on top of Zcash's zk-SNARK shielded pool. The [JUMBLR whitepaper](https://github.com/KomodoPlatform/komodo/wiki/JUMBLR-Whitepaper) describes a three-stage flow: a transparent address ("T") deposits funds to a shielded ("Z") address; a Z → Z transaction obscures the funds further inside the shielded pool; and finally a Z → T transaction disburses to a user-chosen secret address. To defeat **timing attacks** (when only one user is JUMBLR'ing) and **knapsack attacks** (when distinctive amounts are JUMBLR'd), JUMBLR restricted denominations to three orders of magnitude (100, 1,000, and 10,000 KMD lots) and synchronized network-wide mixing rounds across active JUMBLR nodes. Fees were 0.3% of mixed value.

The user-facing API was minimal — essentially `jumblr_deposit <address>` and `jumblr_secret <address>` — designed to be invokable from the `komodo-cli` command line. The privacy hardening relied substantially on running JUMBLR on a separate physical node with a separate IP address to defeat network-layer correlation.

**JUMBLR has been deprecated.** The modern Komodo Wallet (formerly AtomicDEX) does not include JUMBLR, and the JUMBLR codepaths in the daemon are unmaintained. Komodo's privacy story has effectively been retired; users seeking shielded transactions on a KMD-style codebase are typically directed to **Pirate Chain (ARRR)**, a Komodo-ecosystem privacy-only chain that uses Sapling shielded transactions exclusively and is itself secured by Komodo's dPoW.

### The June 2019 Agama Wallet "White Hat" Hack

In **June 2019**, Komodo discovered that an attacker had spent **months** [making seemingly legitimate contributions](https://komodoplatform.com/update-agama-vulnerability/) to the open-source **`electron-native-notify`** npm package — a logging library used by Komodo's Agama desktop wallet. Once the package had been incorporated into a released version of Agama, the attacker pushed a malicious update that exfiltrated users' wallet seed phrases to a public server, effectively staging a future bulk theft.

Komodo's Cyber Security Team, working with npm Inc.'s security team, [discovered the backdoor before the attacker could exploit it at scale](https://thehackernews.com/2019/06/komodo-agama-wallet-hacking.html), and made the controversial decision to **exploit the vulnerability themselves first**, sweeping vulnerable users' funds into Komodo-controlled "safe wallets." Komodo's official blog post stated: "We were able to sweep around 8 million KMD and 96 BTC from these vulnerable wallets." CoinDesk reported the combined value as **nearly $13 million** ($12.5 million KMD and $765,000 BTC per Komodo's own attribution at the time). Affected users were able to reclaim their funds from the Komodo-controlled safe addresses (KMD: `RSgD2cmm3niFRu2kwwtrEHoHMywJdkbkeF`; BTC: `1GsdquSqABxP2i7ghUjAXdtdujHjVYLgqk`). The Verus fork of Agama, which did not include the compromised library, was unaffected. The incident is one of the most well-known examples of a **supply-chain attack** in cryptocurrency wallet software, and one of the earliest deployments of "white-hat" exploitation as an emergency-response tactic by a chain's core team.

In the aftermath, Komodo deprecated Agama and shifted user funds onto AtomicDEX, which uses a more modern non-custodial architecture and HD wallets with hardware-wallet support.

### SuperNET Heritage

Komodo's pre-history runs through **SuperNET**, jl777's earlier project on the NXT chain. SuperNET aimed to provide a meta-layer connecting independent blockchains via atomic swaps. Many SuperNET technologies (BarterDEX, iguana) were brought into Komodo when the NXT relationship soured. The notary-node system was a SuperNET design carried over to provide dPoW security to Komodo and its asset chains.

---

## 6. Bitcoin Cash

### Origin and Status

Bitcoin Cash (BCH) is **not a privacy coin**. It is a hard fork of Bitcoin that prioritizes large-block on-chain scaling for payments. It is included here because it hosts a meaningful **opt-in mixing protocol** — CashFusion — which is technically interesting and has been the subject of academic privacy research.

Bitcoin Cash was created on **August 1, 2017**, when activists, developers, and miners opposed to the Segregated Witness (SegWit) soft fork (activated July 21, 2017 at block 477,120 via BIP 91) executed a user-activated hard fork to enable an 8 MB block size. The chain split occurred at **block 478,558** — the last common block — with the first divergent block (478,559) mined at approximately 12:37 UTC on August 1, 2017 (the divergence began six blocks after the originally announced 12:20 UTC marker). Anyone holding BTC at the moment of the fork received 1:1 BCH. Initial development was led by **Bitcoin ABC** (Amaury Séchet, aka "Deadal Nix"), with significant early backing from **Bitmain** (Jihan Wu) and **Roger Ver**. The block size has since been raised, currently to 32 MB.

Bitcoin Cash then itself underwent a contested split on **November 15, 2018** at block **556,766**, dividing into **Bitcoin Cash (BCH)**, following the Bitcoin ABC roadmap, and **Bitcoin SV (BSV)**, led by Craig Wright and Calvin Ayre's CoinGeek/nChain. A further split on **November 15, 2020** (block 661,648) produced **eCash (XEC)** when the Bitcoin ABC team's controversial "infrastructure funding plan" was rejected by the broader BCH community.

### Schnorr Signatures (May 2019)

On **May 15, 2019**, Bitcoin Cash [activated Schnorr signatures](https://github.com/bitcoincashorg/bitcoincash.org/blob/master/spec/2019-05-15-schnorr.md) — pre-dating Bitcoin's Taproot/Schnorr activation by more than two years. The specification was authored by **Mark B. Lundeberg**. Activation was scheduled via Median-Time-Past, with Unix timestamp 1557921600 (12:00 UTC). The activation was confirmed at block 582,680. Schnorr signatures provide cryptographic foundations for compact multisignatures and more efficient threshold schemes; in Bitcoin Cash they also enable more efficient CashFusion-style aggregations.

### CashTokens (May 2023)

The **[CashTokens specification](https://cashtokens.org/docs/spec/chip/)** (CHIP-2022-02-CashTokens, authored by Jason Dreyzehner) was locked in on November 15, 2022 on chipnet and activated on the BCH mainnet on **May 15, 2023** (Unix MTP 1684152000). CashTokens introduce native fungible and non-fungible tokens to the Bitcoin Cash UTXO model — a substantially different design from Ethereum's ERC-20 / ERC-721 contracts.

### CashShuffle (Deprecated)

**CashShuffle** was an implementation of the **CoinShuffle** protocol (Ruffing, Moreno-Sanchez, Kate, "CoinShuffle: Practical Decentralized Coin Mixing for Bitcoin", ESORICS 2014) ported to Bitcoin Cash. It was integrated into the [Electron Cash wallet](https://github.com/Electron-Cash/Electron-Cash) and supported by a network of **CashShuffle servers** maintained by the community. Each CoinShuffle round combined exactly N inputs (one per participant) into a CoinJoin transaction with N equal-value outputs and N change outputs; the protocol used layered encryption (a "DC-net"-like construction) to permit each participant to specify their output address anonymously to the others.

CashShuffle's weakness was the **change output**: because each participant's change equals their input minus the mix denomination minus fees, chain analysis could deterministically link an input to its corresponding change output and thereby gradually reassemble post-mix wallet histories as users consolidated coins. CashShuffle was **effectively superseded by CashFusion starting in 2019**, with defunct CashShuffle servers removed from Electron Cash in the [4.2.3 release](https://github.com/Electron-Cash/Electron-Cash/releases/tag/4.2.3) in 2021. There was no single dated "shutdown" — the protocol gradually fell out of active use.

### CashFusion

[**CashFusion**](https://github.com/cashshuffle/spec/blob/master/CASHFUSION.md), specified by **Jonald Fyookball** and **Mark B. Lundeberg** (with implementation contributions from **Jason B. Cox** and the Electron Cash team), addresses the change-output problem by abandoning the equal-amount requirement entirely. Instead of the rigid 1-input-2-outputs-per-participant structure of CoinShuffle, CashFusion permits **arbitrary numbers of inputs and outputs per participant of non-standard amounts**, all coordinated through a server.

The protocol's central insight is that with sufficiently many inputs and outputs of high-precision values (Bitcoin Cash amounts can carry up to 8 decimal places of satoshi precision), the **combinatorial complexity of matching inputs to outputs becomes intractable**. For example, a CashFusion transaction with 50 inputs and 50 outputs already has 50! ≈ 3 × 10⁶⁴ possible input-to-output mappings; the actual mapping is computationally infeasible to recover from on-chain data alone.

CashFusion uses a **blind verification scheme** — built on cryptographic commitments — that allows each participant's inputs and outputs to be validated by a random other player without revealing the input/output linkage, while still allowing the protocol to detect and ban uncooperative participants who fail to sign. The server learns less than the players (typically zero knowledge of linkages), and players learn less about each other than they would in a pure CoinShuffle setup. By the protocol's one-year anniversary on November 28, 2020, [Bitcoin News reported](https://news.bitcoin.com/) that the `stats.devzero.be` tracker recorded "approximately 19,658 fusions" processed with "close to $200 million worth of bitcoin cash fused to-date," a 328.93% increase over the prior four months. The Kudelski Security audit of CashShuffle's predecessor was positive; CashFusion itself underwent independent review.

Independent analysis confirms the protocol's design intent. In Jonald Fyookball's paper "Analyzing the Combinatoric Math in Cashfusion," analyst James Waugh's verbatim finding was: "it's impossible to determine the true way that inputs and outputs truly relate (since there are multiple possible combinations of ways of getting the inputs and outputs to balance)."

The architecture is documented in the [CashFusion whitepaper](https://github.com/cashshuffle/spec/blob/master/CASHFUSION.md) at `cashshuffle/spec`; reference implementations live in [`Electron-Cash/Electron-Cash`](https://github.com/Electron-Cash/Electron-Cash) and the Go server in [`cashshuffle/cashshuffle`](https://github.com/cashshuffle/cashshuffle).

### Key Papers

- **Ruffing, Moreno-Sanchez, Kate**, "CoinShuffle: Practical Decentralized Coin Mixing for Bitcoin," ESORICS 2014.
- **Maxwell**, "CoinJoin: Bitcoin privacy for the real world," BitcoinTalk forum, August 2013.
- **Fyookball & Lundeberg**, [CashFusion specification](https://github.com/cashshuffle/spec/blob/master/CASHFUSION.md).
- **Fyookball**, "Analyzing the Combinatoric Math in Cashfusion" (referenced in Bitcoin News, October 2020).

---

## Further Reading

### Academic Papers (Cryptography & Privacy)

- **Nicolas van Saberhagen**, [CryptoNote v2.0 Whitepaper](https://bytecoin.org/old/whitepaper.pdf) (October 17, 2013).
- **Shen Noether**, [Ring Confidential Transactions, MRL-0005](https://www.getmonero.org/resources/research-lab/pubs/MRL-0005.pdf) (2015).
- **Surae Noether**, [Counterfeiting via Merkle Tree Exploits, MRL-0002](https://www.getmonero.org/resources/research-lab/pubs/MRL-0002.pdf) (September 2014).
- **Mackenzie, Noether**, [Improving Obfuscation in the CryptoNote Protocol, MRL-0004](https://www.getmonero.org/resources/research-lab/pubs/MRL-0004.pdf) (2015).
- **Bünz, Bootle, Boneh, Poelstra, Maxwell, Wuille**, [Bulletproofs: Short Proofs for Confidential Transactions](https://eprint.iacr.org/2017/1066) (IEEE S&P 2018).
- **Goodell, Noether, RandomRun**, [Concise Linkable Ring Signatures (CLSAG)](https://eprint.iacr.org/2019/654) (eprint 2019/654).
- **Jens Groth**, [On the Size of Pairing-based Non-interactive Arguments](https://eprint.iacr.org/2016/260) (EUROCRYPT 2016) — Groth16.
- **Albrecht, Grassi, Rechberger, Roy, Tiessen**, [MiMC](https://eprint.iacr.org/2016/492) (ASIACRYPT 2016).
- **Miller, Möser, Lee, Narayanan**, [An Empirical Analysis of Linkability in the Monero Blockchain](https://arxiv.org/abs/1704.04299) (PETS 2018).
- **Kumar, Fischer, Tople, Saxena**, [A Traceability Analysis of Monero's Blockchain](https://eprint.iacr.org/2017/338.pdf) (ESORICS 2017).
- **Meiklejohn et al.**, "A Fistful of Bitcoins: Characterizing Payments Among Men with No Names" (IMC 2013).
- **Ruffing, Moreno-Sanchez, Kate**, "CoinShuffle: Practical Decentralized Coin Mixing for Bitcoin" (ESORICS 2014).
- **Fanti et al.**, "Dandelion++: Lightweight Cryptocurrency Networking with Formal Anonymity Guarantees" (USENIX Security 2018).
- **Tornado Cash**, [Privacy Solution v1.4 Whitepaper](https://berkeley-defi.github.io/assets/material/Tornado%20Cash%20Whitepaper.pdf).
- **Kohlweiss et al.**, [Snarky Ceremonies](https://eprint.iacr.org/2021/219) (eprint 2021/219).
- **Fyookball, Lundeberg**, [CashFusion Specification](https://github.com/cashshuffle/spec/blob/master/CASHFUSION.md).

### Court Documents

- **United States v. Sterlingov**, Case No. **1:21-cr-00399-RDM** (D.D.C.), Memorandum Opinion (Feb. 29, 2024) at [moneylaunderingnews.com](https://www.moneylaunderingnews.com/wp-content/uploads/sites/12/2024/03/District_of_Columbia_USA_v._STERLINGOV_Memo_Opinion_and_Order.pdf); sentencing November 8, 2024 ([DOJ press release](https://justice.gov/opa/pr/bitcoin-fog-operator-sentenced-money-laundering-conspiracy)).
- **United States v. Storm**, Case No. **1:23-cr-00430** (S.D.N.Y., Judge Failla); partial verdict August 6, 2025.
- **The Netherlands v. Pertsev**, East Brabant District Court, Case No. **82/198261-22** (May 14, 2024).
- **Van Loon v. Department of the Treasury**, [No. 23-50669 (5th Cir. Nov. 26, 2024)](https://www.ca5.uscourts.gov/opinions/pub/23/23-50669-CV0.pdf), 122 F.4th 549.
- **Coin Center v. Yellen** (S.D. Fla. / 11th Cir.) — companion challenge to Tornado Cash sanctions, held in abeyance following Van Loon.
- **U.S. Treasury OFAC**, "Sanctions Notorious Virtual Currency Mixer Tornado Cash" press release ([JY0916, August 8, 2022](https://home.treasury.gov/news/press-releases/jy0916)); "Treasury Designates Roman Semenov" ([JY1702, August 23, 2023](https://home.treasury.gov/news/press-releases/jy1702)).

### Selected Reporting

- CoinDesk's coverage of the Storm verdict ([Aug. 6, 2025](https://www.coindesk.com/policy/2025/08/06/roman-storm-guilty-of-unlicensed-money-transmitting-conspiracy-in-partial-verdict)).
- CoinDesk on Pertsev ([May 14, 2024](https://www.coindesk.com/policy/2024/05/14/tornado-cash-developer-alexey-pertsev-found-guilty-of-money-laundering)).
- Bloomberg on Sterlingov sentencing ([Nov. 8, 2024](https://www.bloomberg.com/news/articles/2024-11-08/crypto-mixer-gets-150-months-for-bitcoin-fog-money-laundering)).
- Protos on the BitcoinTalk history of Bitcoin Fog ([Sterlingov as Akemashite Omedetou](https://protos.com/bitcoin-fog-history-roman-sterlingov-bitcointalk/)).
- Elliptic on the Harmony Horizon Bridge laundering ([briefing note PDF](https://www.elliptic.co/hubfs/Harmony%20Horizon%20Bridge%20Hack%20P1%20briefing%20note%20final.pdf)).
- Chainalysis on the Bitcoin Fog Daubert ruling ([blog post](https://www.chainalysis.com/blog/bitcoin-fog-daubert-hearing-chainalysis/)).
- ChainArgos on the Sterlingov appeal ([amicus brief commentary](https://www.chainargos.com/chainalysis-claims-95-accuracy-why-thats-irrelevant/)).

---

## Technical Glossary

- **CoinJoin** — A class of Bitcoin-style mixing in which N participants jointly construct a single transaction with N inputs and N+ outputs, such that on-chain observers cannot deterministically link any input to any output within the joint transaction. Proposed by Gregory Maxwell in 2013.
- **CoinShuffle** — A decentralized variant of CoinJoin in which participants coordinate the assignment of output addresses through layered encryption, so that no participant or external party learns the input-to-output mapping. The basis of CashShuffle.
- **zk-SNARK** — Zero-Knowledge Succinct Non-Interactive Argument of Knowledge. A cryptographic proof system permitting one party to prove to another that a statement is true without revealing any information beyond the truth of the statement, with proofs short enough to fit in a single Ethereum transaction. **Groth16** is the most widely deployed variant.
- **Ring signature** — A digital signature that proves the signer is one of an explicit set of public keys (a "ring") without revealing which one. The basis of Monero's sender privacy. **CLSAG** and **MLSAG** are Monero-specific linkable variants.
- **Stealth address** — A scheme in which each on-chain output is sent to a fresh one-time public key derived from the recipient's long-term keys via Diffie-Hellman, so that no two outputs to the same recipient are linkable on-chain.
- **Key image** — A unique, deterministic value derived from a Monero output's private key. Allows the network to detect double-spending of an output without learning which output was spent.
- **RingCT (Ring Confidential Transactions)** — Monero's combination of ring signatures and Pedersen-commitment-based confidential transactions, masking sender, recipient, and amount simultaneously.
- **Bulletproofs / Bulletproofs+** — Compact non-interactive zero-knowledge range proofs that allow proving a committed value lies in a non-negative range, without revealing it. Logarithmic in proof size.
- **Atomic swap** — A trustless cross-chain exchange protocol using Hash Time-Locked Contracts (HTLCs) to ensure that either both parties' transfers complete or neither does.
- **dPoW (Delayed Proof of Work)** — Komodo's security innovation: periodically writing hashes of one blockchain's blocks into another blockchain (typically Bitcoin), so the secondary chain inherits the primary chain's reorganization-resistance.
- **Tumbler / Mixer** — Generic term for any service or protocol that combines coins from multiple sources to break the on-chain link between sender and receiver.
- **Anonymity set** — The set of plausible candidates among whom a true actor is hidden. Larger anonymity sets provide stronger privacy.
- **Trusted setup** — A one-time multi-party computation required by certain zk-SNARK constructions (including Groth16) to generate public proving and verification keys. Security holds as long as at least one participant destroys their "toxic waste."
- **Masternode** — In Dash, a server posting 1,000 DASH collateral that performs second-tier consensus functions (PrivateSend coordination, InstantSend, ChainLocks) and shares in block rewards.
- **Nullifier hash** — In Tornado Cash and similar zk-SNARK mixers, a public value derived from a user's secret that is recorded on-chain upon withdrawal to prevent double-spending of the same deposit.

---

*Last updated: May 2026.*

*License: This document is released under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).*