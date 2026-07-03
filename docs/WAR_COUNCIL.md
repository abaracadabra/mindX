# The War Council — live-message → decision → blueprint bridge

## The gap this closes (investigation)

A blueprint run was not being generated for live messages. The investigation:

- **"Blueprint run"** = `BlueprintAgent.generate_next_evolution_blueprint()`. It is
  invoked **only** inside `agents/core/mindXagent.py`'s autonomous improvement loop
  (the scheduled self-improvement path). Nothing invokes it in response to an
  incoming/live proposal.
- **Live messages** surface outbound — `GET /insight/thinking/live` (SSE), the
  `/insight/agentic/activity` feed, the dockable activity panel — and inbound
  questions hit `/chat/docs` (RAG). **No component takes a live *proposal* and
  routes it through a decision that can trigger a blueprint.**
- A **War Council** already existed only as prose (`scripts/publish_war_council_articles.py`,
  the ephermaleth `votingbooth` records `council="warcouncil"`) — no decision engine.

The War Council is that missing bridge: **live proposal → vote → guaranteed verdict
→ (on approval) a blueprint run.** mindX keeps two rooms — the **Boardroom**
(7 soldiers + CEO, deliberative, CISO/CRO veto, governance) and the **War Council**
(13 seats, fast and decisive) for live calls.

## Design — 13 prime-weighted seats, accelerating prime majority

`mindx/war_council.py` · `GET /insight/war_council`

- **13 seats.** 13 is prime and odd, so a binary vote among the non-abstaining
  seats can never tie on raw count.
- **Distinct prime weights** — the first 13 primes `[2,3,5,7,11,13,17,19,23,29,31,37,41]`
  (total weight 238). Seats are individually identifiable and weighted tallies are
  highly tie-resistant; the prime weights are what actually decide.
- **Accelerating majority.** The approval bar climbs a **prime-ratio ladder** with
  the proposal's stakes: `7/13` (≈0.538) → `11/13` (≈0.846) → `13/13` (1.0). A
  persistent high-stakes proposal must consolidate an ever-stronger majority or be
  decisively turned down — the "acceleration" that forces termination.

### How a verdict is guaranteed (no deadlock)

`tally(votes, stakes)` resolves, in order:

1. weighted approval ratio ≥ the accelerating bar → **approved**;
2. weighted opposition ratio ≥ the bar → **rejected**;
3. otherwise the **weighted (prime) majority** decides (`w_app` vs `w_rej`);
4. exact weighted tie → broken by the **odd raw-seat majority**;
5. total deadlock → safe decisive default (**rejected**).

Because distinct primes make weighted ties vanishingly rare and 13 odd seats break
any raw tie, the council **always returns a decisive verdict** (`guaranteed: true`)
for any non-empty vote set. That is the "guarantee outcome from proposal and vote."

## The bridge

```python
from mindx.war_council import WarCouncil
wc = WarCouncil(
    vote_fn=collect_votes,        # inject: boardroom soldiers / LLM personas / deterministic
    blueprint_fn=run_blueprint,   # called with the proposal on an approved verdict
)
result = await wc.decide({"id": "p1", "title": "...", "source": "live"}, stakes=1)
# result.verdict ∈ {approved, rejected}; on approved, blueprint_fn fires → a blueprint run
```

`vote_fn(proposal, stakes)` returns up to 13 seat votes
(`{"seat": 0..12, "vote": "approve"|"reject"|"abstain"}`) — wire it to the existing
Boardroom soldiers, LLM personas, or a deterministic policy. `blueprint_fn(proposal)`
is the **blueprint run** that was previously unreachable from live messages; on an
approved verdict the War Council fires it, closing the gap.

## Seats

`vanguard · logistics · intelligence · security · risk · doctrine · economy ·
diplomacy · engineering · ethics · morale · reserve · warlord` — 13 distinct lenses,
each carrying its prime weight. A war council, not a rubber stamp.

## Endpoints

- `GET /insight/war_council` — council config (seats, primes, ladder, thresholds) +
  recent verdicts. `?h=true` for plain text.

## Wiring (live)

`mindx/war_council_bridge.py` wires both ends, installed on read at `/insight/war_council`:

- **`vote_fn` → the in-process Boardroom.** `boardroom_vote_fn` calls
  `Boardroom.get_instance().convene(...)`, which queries the 7 soldiers via local
  inference (Ollama) — **no separate service required** (the `:8771` Node service is
  an optional `MINDX_BOARDROOM_SERVICE_ENABLED=1` cutover, not deployed here). Each
  soldier maps onto its seat by domain; `/insight/war_council` shows
  `vote_source: "boardroom (in-process soldiers)"`.
- **`blueprint_fn` → BlueprintAgent.** On an approved verdict, `blueprint_fn` calls
  `(await MindXAgent.get_instance()).blueprint_agent.generate_next_evolution_blueprint(...)`
  — the blueprint run that was previously unreachable from a live message. The loop is closed.

## Roadmap

- Subscribe the council to a live-proposal stream (the activity/thinking feed) so
  flagged proposals auto-route to a vote.
- Record each verdict + blueprint id in the ephermaleth voting booth.
