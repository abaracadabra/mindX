# Robert's Rules of Order — Encoded for DAIO

Parliamentary procedure as code. Robert's Rules of Order is the governance
protocol that has run every legitimate deliberative body since 1876. DAIO
puts it on-chain.

Prior art: [Rob's Rules DAO LCA](https://robsrulesdao.com/) — a Limited
Cooperative Association using Vocdoni/Aragon to deploy Robert's Rules on
blockchain. They proved the concept. DAIO formalizes the state machine.

See also: [The Parliamentary Assistant](http://www.ibiblio.org/bosak/pa/pa.htm)
— Jon Bosak's early proposal for a "legally binding, formal decision-making
machine" based on Robert's Rules, implemented as a web server add-on.

## The State Machine

A motion in Robert's Rules follows an exact state machine. Every transition
has a precondition. Every state has defined legal actions. This is a protocol.

```
                    ┌──────────────┐
                    │   NO MOTION  │ (floor is open)
                    └──────┬───────┘
                           │ member moves
                           ▼
                    ┌──────────────┐
                    │   PROPOSED   │ (motion on floor, needs second)
                    └──────┬───────┘
                           │ another member seconds
                           ▼
                    ┌──────────────┐
                    │   STATED     │ (chair states the question)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌───────────┐ ┌──────────┐ ┌───────────┐
       │  DEBATED  │ │ AMENDED  │ │ REFERRED  │
       └─────┬─────┘ └────┬─────┘ └───────────┘
             │             │ (returns to STATED)
             ▼             │
       ┌───────────┐       │
       │  VOTED    │◄──────┘
       └─────┬─────┘
             │
     ┌───────┼───────┐
     ▼       ▼       ▼
  ADOPTED  REJECTED  TABLED
```

### States

| State | Description | Legal Actions |
|-------|-------------|---------------|
| NO_MOTION | Floor is open. No pending question. | Move (main motion), raise privilege, call orders of day |
| PROPOSED | Motion moved, awaiting second. | Second, withdraw |
| STATED | Chair has stated the question. Debate may begin. | Debate, amend, refer, postpone, previous question, table, vote |
| DEBATED | Motion under active debate. | Continue debate, amend, previous question (close debate), table |
| AMENDED | Amendment pending on the main motion. | Debate amendment, vote on amendment (returns to STATED) |
| REFERRED | Motion sent to committee. | Committee reports back (returns to STATED) |
| VOTED | Vote taken. | Adopt, reject, or reconsider |
| ADOPTED | Motion carries. | Execute, rescind (2/3 vote) |
| REJECTED | Motion fails. | Reconsider (same session), renew (next session) |
| TABLED | Motion laid on table. Temporary. | Take from table (majority vote) |

## Motion Classification

Robert's Rules defines four classes of motions. Each has different precedence,
debatability, and vote requirements. This is the type system.

### Class 1: Privileged Motions (highest precedence)

These override everything. They address the assembly's immediate needs,
not the pending question.

| # | Motion | Second | Debatable | Amendable | Vote | Precedence |
|---|--------|--------|-----------|-----------|------|------------|
| 1 | Fix time to adjourn | Yes | Yes (limited) | Yes | Majority | Highest |
| 2 | Adjourn | Yes | No | No | Majority | 2nd |
| 3 | Recess | Yes | No | Yes | Majority | 3rd |
| 4 | Raise question of privilege | No | No | No | Chair rules | 4th |
| 5 | Call for orders of the day | No | No | No | Chair rules | 5th |

### Class 2: Subsidiary Motions (modify the main motion)

These attach to the pending main motion and must be resolved before it.
Listed highest to lowest precedence.

| # | Motion | Second | Debatable | Amendable | Vote | Effect |
|---|--------|--------|-----------|-----------|------|--------|
| 6 | Lay on the table | Yes | No | No | Majority | Temporarily set aside |
| 7 | Previous question (close debate) | Yes | No | No | **2/3** | End debate, force vote |
| 8 | Limit/extend debate | Yes | No | Yes | **2/3** | Control debate time |
| 9 | Postpone definitely | Yes | Yes (limited) | Yes | Majority | Delay to specific time |
| 10 | Commit/refer to committee | Yes | Yes (limited) | Yes | Majority | Send to committee |
| 11 | Amend | Yes | Yes | Yes | Majority | Modify the motion |
| 12 | Postpone indefinitely | Yes | Yes | No | Majority | Kill the motion |

### Class 3: Incidental Motions (arise from procedure)

No fixed precedence among themselves. They must be decided immediately
when they arise.

| Motion | Second | Debatable | Amendable | Vote | When Used |
|--------|--------|-----------|-----------|------|-----------|
| Point of order | No | No | No | Chair rules | Procedure violated |
| Appeal the chair | Yes | Yes (limited) | No | Majority | Challenge chair's ruling |
| Suspend the rules | Yes | No | No | **2/3** | Bypass a rule |
| Objection to consideration | No | No | No | **2/3 against** | Block a question |
| Division of the question | Yes | No | Yes | Majority | Split a compound motion |
| Division of the assembly | No | No | No | Automatic | Demand a counted vote |
| Parliamentary inquiry | No | No | No | Chair answers | Ask about procedure |
| Withdraw a motion | No | No | No | Majority (or consent) | Maker takes back motion |

### Class 4: Main Motions (lowest precedence)

The main motion introduces new business. Everything else takes precedence
over it. This is the directive in the boardroom.

| Motion | Second | Debatable | Amendable | Vote | Notes |
|--------|--------|-----------|-----------|------|-------|
| Main motion | Yes | Yes | Yes | Majority | The question before the assembly |
| Reconsider | Yes | Yes (limited) | No | Majority | Reopen a decided question (same session) |
| Rescind/repeal | Yes | Yes | Yes | **2/3** (or majority with notice) | Undo a previous action |
| Take from table | Yes | No | No | Majority | Resume a tabled motion |

## Vote Thresholds in Robert's Rules

Robert's Rules uses exactly two vote thresholds:

```
MAJORITY (> 50% of votes cast, ignoring blanks):
  Main motions, amendments, refer, postpone, table,
  adjourn, recess, appeal, take from table, reconsider

TWO-THIRDS (≥ 2/3 of votes cast):
  Previous question (close debate)
  Limit or extend debate
  Suspend the rules
  Objection to consideration
  Close nominations
  Rescind (without previous notice)
  Adopt constitution/bylaws (initial adoption)

  The 2/3 threshold protects the minority's right to debate.
  Any motion that silences debate or overrides rules requires 2/3.
  This is the same 2/3 as DAIO's supermajority threshold.
```

## Quorum

A quorum is the minimum number of members who must be present for
business to be legally transacted. Robert's Rules defaults:

```
Quorum defaults:
  Mass meeting:      those present
  Organization:      majority of membership
  Convention:        majority of registered delegates
  Board:             majority of board members
  Committee:         majority of committee members

  Without quorum:    no business may be transacted
  Exception:         motion to adjourn, motion to fix time to adjourn,
                     motion to recess, motion to obtain a quorum
```

In DAIO: quorum is the minimum number of soldiers who must vote (not abstain)
for a boardroom session to produce a binding outcome. An all-abstain session
is inquorate — the directive is not rejected, it is unconsidered.

## Mapping to DAIO

### Robert's Rules → Boardroom

| Robert's Rules | DAIO Boardroom | Implementation |
|----------------|----------------|----------------|
| Chair | CEO | Presents directive, does not vote |
| Member | Soldier | Votes approve/reject/abstain with reasoning |
| Main motion | Directive | `convene(directive=...)` |
| Second | Auto-seconded | All seated soldiers implicitly second by attendance |
| Debate | Deliberation | Each soldier's reasoning in the vote response |
| Amendment | Exploration branch | Dissent creates alternative directive branches |
| Previous question | — | Not needed (single-round voting, no open debate) |
| Vote | Weighted tally | `_tally_votes(session, threshold)` |
| Majority | 2/3 Majority | Default SUPERMAJORITY_THRESHOLD = 0.666 |
| 2/3 vote | 3/3 Unilateral | Constitutional-importance directives |
| Quorum | Minimum votes | Session requires non-abstain votes to be valid |
| Adjourn | Session end | Session logged, autonomous loop resumes |
| Table | Deferred priority | `priority="deferred"` |
| Refer to committee | Exploration | Dissent branches assigned to specific agents |
| Point of order | CISO/CRO veto | 1.2x weight = procedural override signal |
| Suspend rules | Executive priority | `priority="executive"` preempts autonomous loop |

### Robert's Rules → On-Chain (TriumvirateGovernance.sol)

| Robert's Rules | DAIO On-Chain | Contract |
|----------------|---------------|----------|
| Call to order | Proposal creation | `createProposal()` |
| Second | Proposal staking | `stakeOnProposal()` — economic second |
| Debate period | Voting window | `votingEndsAt` timestamp |
| Vote | Domain voting | `voteOnProposal()` per domain |
| Majority | 2/3 domains | `requiredDomains = 2` of 3 |
| 2/3 vote | 3/3 domains | Constitutional proposals |
| Quorum | Minimum participation | `humanVotersParticipated >= required` |
| Timelock | Execution delay | `DAIOTimelock.sol` — 1/3/7/14-day delays |
| Rescind | Cancel proposal | `cancelProposal()` |
| Table | Postpone | Proposal state → POSTPONED |
| Point of order | Challenge | On-chain dispute resolution |
| Suspend rules | Emergency | `EmergencyTimelock.sol` |
| Chair's ruling | Chairman's veto | `DAIO_Constitution.sol` veto power |

### Robert's Rules → PhysicsDAO Cycle

```
Robert's Rules procedural flow:

  CALL TO ORDER          → PhysicsDAO: Chronos schedules the session
  READING OF MINUTES     → PhysicsDAO: Previous session outcomes reviewed
  REPORTS                → PhysicsDAO: TimeOracle status, inference health
  UNFINISHED BUSINESS    → PhysicsDAO: Tabled motions, deferred directives
  NEW BUSINESS           → PhysicsDAO: CEO presents directive
    ├─ MOTION            → PhysicsDAO: Directive proposed
    ├─ SECOND            → PhysicsDAO: Soldiers seated (auto-second)
    ├─ DEBATE            → PhysicsDAO: Parallel deliberation (streaming)
    ├─ AMENDMENT          → PhysicsDAO: Exploration branches
    └─ VOTE              → PhysicsDAO: Weighted consensus tally
  ANNOUNCEMENTS          → PhysicsDAO: Model report, inference summary
  ADJOURNMENT            → PhysicsDAO: Session logged, Kairos evaluates
```

## The Precedence Stack as Code

Robert's Rules precedence is a stack. Higher-precedence motions push onto
the stack and must resolve before lower ones. This is a call stack.

```python
class ParliamentaryStack:
    """Robert's Rules as a motion stack."""

    PRECEDENCE = [
        # Highest precedence first
        "fix_time_to_adjourn",   # 1 — privileged
        "adjourn",                # 2 — privileged
        "recess",                 # 3 — privileged
        "raise_privilege",        # 4 — privileged
        "call_orders_of_day",     # 5 — privileged
        "lay_on_table",           # 6 — subsidiary
        "previous_question",      # 7 — subsidiary (2/3 vote)
        "limit_debate",           # 8 — subsidiary (2/3 vote)
        "postpone_definitely",    # 9 — subsidiary
        "commit_refer",           # 10 — subsidiary
        "amend",                  # 11 — subsidiary
        "postpone_indefinitely",  # 12 — subsidiary
        "main_motion",            # 13 — lowest precedence
    ]

    REQUIRES_SECOND = {
        "fix_time_to_adjourn", "adjourn", "recess",
        "lay_on_table", "previous_question", "limit_debate",
        "postpone_definitely", "commit_refer", "amend",
        "postpone_indefinitely", "main_motion",
        "reconsider", "rescind", "take_from_table",
    }

    DEBATABLE = {
        "fix_time_to_adjourn",  # limited
        "postpone_definitely",  # limited
        "commit_refer",         # limited
        "amend", "postpone_indefinitely", "main_motion",
        "appeal", "reconsider", "rescind",
    }

    AMENDABLE = {
        "fix_time_to_adjourn", "recess",
        "limit_debate", "postpone_definitely",
        "commit_refer", "amend", "main_motion", "rescind",
    }

    TWO_THIRDS_VOTE = {
        "previous_question",     # silences debate
        "limit_debate",          # restricts debate
        "suspend_rules",         # overrides rules
        "objection_to_consider", # blocks a question
        "close_nominations",     # ends nominations
        "rescind",               # undoes previous action (without notice)
    }

    def __init__(self):
        self.stack = []  # pending motions, highest precedence on top

    def is_in_order(self, motion: str) -> bool:
        """A motion is in order if it has higher precedence than the current top."""
        if not self.stack:
            return motion == "main_motion"  # only main motions when floor is open
        current = self.stack[-1]
        return (self.PRECEDENCE.index(motion) < self.PRECEDENCE.index(current))

    def move(self, motion: str, mover: str) -> dict:
        """Member moves a motion."""
        if not self.is_in_order(motion):
            return {"status": "out_of_order", "reason": f"{motion} cannot interrupt {self.stack[-1]}"}
        needs_second = motion in self.REQUIRES_SECOND
        self.stack.append(motion)
        return {"status": "proposed", "motion": motion, "mover": mover,
                "needs_second": needs_second}

    def second(self, seconder: str) -> dict:
        """Another member seconds the pending motion."""
        if not self.stack:
            return {"status": "error", "reason": "nothing to second"}
        motion = self.stack[-1]
        return {"status": "stated", "motion": motion, "seconder": seconder,
                "debatable": motion in self.DEBATABLE,
                "amendable": motion in self.AMENDABLE,
                "vote_required": "2/3" if motion in self.TWO_THIRDS_VOTE else "majority"}

    def vote(self, motion: str, result: str) -> dict:
        """Resolve a vote on the top motion."""
        if self.stack and self.stack[-1] == motion:
            self.stack.pop()
        return {"status": result, "motion": motion,
                "pending": self.stack[-1] if self.stack else None}
```

## The Dojo — Yes or No

The dojo is Robert's Rules reduced to a single motion type: the question.
No precedence. No seconds. No amendments. No weighted votes. One member,
one vote, yes or no. Advisory — the dojo signals, it does not execute.

This is the General Assembly to the boardroom's Security Council.

```
Boardroom (full Robert's Rules):
  22 motion types
  4 motion classes
  Precedence stack
  Seconds required
  Debate periods
  Weighted votes (CISO 1.2x, CRO 1.2x, CLO 0.8x)
  2/3 for debate-silencing
  Quorum enforcement
  Binding — directives execute

Dojo (simplified):
  1 motion type: the question
  0 classes: no precedence
  No seconds: the question stands on its own
  No debate: the question is binary
  1 member = 1 vote: no weighting
  Simple majority: yes > no
  No quorum: whoever votes, votes
  Advisory — the dojo legitimizes, it does not command
```

### Why the Simplicity

The dojo's power is not in its procedure but in its scale. When 100 agents
vote yes/no, the signal is clear regardless of weighting. The boardroom
needs procedure because 8 members with weighted votes can produce ambiguous
outcomes. The dojo cannot produce ambiguity: yes or no, more or fewer.

The simplicity is the feature. A dojo question that says "Should the
boardroom deploy the treasury contract?" has one of two outcomes:

- **Yes > No**: The dojo signals approval. The boardroom may proceed with
  the knowledge that the broader community supports it. This is the General
  Assembly resolution — moral authority, not legal force.

- **No > Yes**: The dojo signals disapproval. The boardroom may still
  proceed (the Security Council can act without General Assembly approval),
  but it does so without legitimacy. This is the cost.

### Dojo in RobertsRulesDAIO.sol

```solidity
// Any dojo member can ask a question
askDojo("Should the boardroom deploy the treasury contract?")

// Any dojo member votes yes or no
voteDojo(questionId, true)   // yes
voteDojo(questionId, false)  // no

// After voting period ends, anyone can close
closeDojo(questionId)
// Emits: DojoQuestionClosed(id, yesCount, noCount)
```

No precedence stack. No second requirement. No debate period (just a voting
window). No weighted votes. The contract enforces only: one member one vote,
voting period, and the tally.

## RobertsRulesDAIO.sol — The Contract

**Location**: `daio/contracts/daio/governance/RobertsRulesDAIO.sol`

The contract encodes both interfaces in a single deployment:

### Boardroom Interface

| Function | Robert's Rules | Access | Notes |
|----------|---------------|--------|-------|
| `registerSoldier()` | Seat a member | Chair | Weight in basis points (10000=1.0x) |
| `moveMotion()` | "I move that..." | Soldier | Checks precedence stack |
| `secondMotion()` | "I second" | Soldier | Cannot second own motion |
| `vote()` | Aye/nay/abstain | Soldier | Weighted by soldier registration |
| `finalizeVote()` | Chair announces result | Anyone | After debate ends; checks quorum |
| `tableMotion()` | Lay on table | Chair | Temporary — can be taken up later |
| `takeFromTable()` | Resume tabled motion | Soldier | Resets votes for new consideration |
| `referMotion()` | Commit to committee | Chair | Exploration branch |
| `withdrawMotion()` | Withdraw | Mover only | Only before vote begins |
| `setThreshold()` | — | Chair | 3334 (1/3) to 10000 (3/3) basis points |
| `setDebateDuration()` | — | Chair | 1 hour to 30 days |
| `setQuorum()` | — | Chair | Minimum participating weight |

### Dojo Interface

| Function | Description | Access |
|----------|-------------|--------|
| `askDojo()` | Propose a yes/no question | Dojo member |
| `voteDojo()` | Vote yes or no | Dojo member |
| `closeDojo()` | Close after voting period | Anyone |
| `setDojoDuration()` | Set voting window | Chair |

### Motion Types (22 total)

```
Main (4):        MAIN_MOTION, RECONSIDER, RESCIND, TAKE_FROM_TABLE
Subsidiary (7):  POSTPONE_INDEFINITELY, AMEND, COMMIT_REFER,
                 POSTPONE_DEFINITELY, LIMIT_DEBATE, PREVIOUS_QUESTION,
                 LAY_ON_TABLE
Incidental (6):  POINT_OF_ORDER, APPEAL, SUSPEND_RULES,
                 OBJECTION_TO_CONSIDER, DIVISION_OF_QUESTION, WITHDRAW
Privileged (5):  CALL_ORDERS_OF_DAY, RAISE_PRIVILEGE, RECESS,
                 ADJOURN, FIX_TIME_TO_ADJOURN
```

### Consensus Thresholds (basis points)

```
DICTATOR_THRESHOLD = 3334   // > 33.33% — 1/3 diffusion
MAJORITY           = 5001   // > 50%    — simple majority
TWO_THIRDS         = 6667   // ≥ 66.67% — supermajority (default)
UNANIMOUS          = 10000  // 100%     — 3/3 unilateral
```

### Precedence Stack

The contract maintains a stack of pending motions. Higher-precedence motions
push onto the stack and must resolve before lower ones. This enforces
Robert's Rules procedural order on-chain:

```
Stack: [MAIN_MOTION, AMEND, PREVIOUS_QUESTION]
                                    ↑ top (must resolve first)

PREVIOUS_QUESTION (rank 7) > AMEND (rank 3) > MAIN_MOTION (rank 1)

To vote on the amendment, first resolve the previous question.
To vote on the main motion, first resolve the amendment.
```

## Implementation Status

### Now (boardroom.py — off-chain)
- Main motion as directive
- Auto-second by attendance
- Streaming deliberation (debate analog)
- Weighted vote with configurable 1/3, 2/3, 3/3 threshold
- Exploration branches (amendment/referral analog)
- Session logging as minutes
- Priority levels (privileged motion analog)

### Now (RobertsRulesDAIO.sol — on-chain)
- Full motion state machine (9 states)
- 22 motion types across 4 classes
- Precedence stack enforcement
- Second requirement (cannot second own motion)
- Debate period with timestamp bounds
- Weighted votes per registered soldier
- 2/3 vote for debate-silencing and rule-overriding motions
- Quorum enforcement on finalization
- Table / take-from-table persistence
- Refer to committee (exploration branch)
- Withdraw by mover
- Configurable threshold (1/3 to 3/3)
- Dojo: yes/no questions, one member one vote, advisory

### Deployment

```bash
# Compile
forge build --contracts daio/governance/RobertsRulesDAIO.sol

# Test
forge test --match-path test/daio/RobertsRulesDAIO.t.sol

# Deploy (when governance transitions on-chain)
forge create --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY \
  daio/governance/RobertsRulesDAIO.sol:RobertsRulesDAIO
```

---

*Robert's Rules of Order has governed legitimate deliberation since 1876.*
*RobertsRulesDAIO.sol puts it on-chain. The boardroom is the full protocol.*
*The dojo is yes or no. Both are governance. Both are necessary.*
*The state machine is the same. The enforcement is cryptographic.*

Sources:
- [Rob's Rules DAO LCA](https://robsrulesdao.com/) — Robert's Rules on Vocdoni/Aragon blockchain
- [Robert's Rules of Order — Official](https://robertsrules.com/)
- [Motion Precedence Table](https://westsidetoastmasters.com/resources/roberts_rules/rror--02.html)
- [Motion Classification](https://westsidetoastmasters.com/resources/roberts_rules/chap6.html)
- [Voting Procedures](http://www.rulesonline.com/rror-08.htm)
- [OpenZeppelin Governor](https://docs.openzeppelin.com/contracts/4.x/api/governance) — modular on-chain governance
