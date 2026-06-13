# @mindx/dojo-service

Standalone reputation + personhood ledger for mindX. No aisdk — pure
ledger logic. Two oracles behind one interface:

| Oracle | When | Source of truth |
|---|---|---|
| `VouchingOracle` | Pre-BONA-FIDE mint (today) | K-of-N wallet vouches in `personhood.jsonl` |
| `BonaFideOracle` | Post-BONA-FIDE mint | Algorand ASA balance via indexer |

Flip via `MINDX_BONA_FIDE_LIVE=1`. Both can co-run for migration audits
(the post-mint cutover writes both ledgers for 7 days, then VouchingOracle
shuts down).

## Endpoints (Phase F)

```
GET  /healthz
GET  /version
GET  /rank/{score}                       (utility — rank for a score)

# Coming in Phase F:
GET  /agents/{address}/reputation        { score, rank, tier, balance, history }
POST /agents/{address}/reputation        { delta, event_type, reason }  (auth ≥ tier 4)
GET  /standings                          (leaderboard)
GET  /privileges/{address}/{action}      { allowed, required_rank }

POST /personhood/declare                 (wallet self-declares; creates pending)
POST /personhood/vouch/{address}         (K-of-N vouch from another person)
GET  /personhood/{address}               { status, vouches_count }
POST /personhood/grant                   (sovereign grant; auth ≥ tier 5)
```

## Rank thresholds (matches `daio/governance/dojo.py`)

| Rank | Score |
|---|---|
| novice | 0 |
| apprentice | 101 |
| journeyman | 501 |
| expert | 1501 |
| master | 5001 |
| grandmaster | 15001 |
| sovereign | 50001 |

Privilege escalation per rank matches existing dojo behaviour.

## Run + deploy

```bash
cd openagents/dojo-service
npm install
npm run dev      # tsx watch
# curl http://127.0.0.1:8772/healthz
# curl http://127.0.0.1:8772/rank/12345  → {"score":12345,"rank":"master"}
```

systemd: `sudo cp deploy/systemd/dojo-service.service /etc/systemd/system/ && sudo systemctl enable --now dojo-service`
Apache: include `deploy/apache/dojo-svc.conf` from the mindx.pythai.net vhost.
