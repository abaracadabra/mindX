# mindX systemd units

Drop-in `.service` / `.timer` files for the mindX production VPS. The units
assume:

- system user `mindx`
- repo cloned at `/home/mindx/mindX`
- virtualenv at `/home/mindx/mindX/.mindx_env`
- writable state under `/home/mindx/mindX/data` and `/home/mindx/.mindx`

If your layout differs, edit the `User=`, `WorkingDirectory=`,
`ExecStart=`, and `ReadWritePaths=` lines.

---

## `mindx-curator.{service,timer}` — weekly SkillStore audit

Runs `scripts/run_curator.py --apply --quiet` once a week. The Curator is
**archive-only**; it never deletes, and pinned + human-authored skills are
off-limits per the SkillStore contract (`agents/skills/store.py:archive`).
Cadence matches Hermes Agent's 7-day Curator cycle (§8.1 of the integration
doc). Reports land at `data/learnings/curator/<timestamp>.json` and are
surfaced on the dashboard at `/feedback.html` → skills tab.

### Install (one-time, as `root`)

```bash
sudo cp /home/mindx/mindX/scripts/systemd/mindx-curator.service /etc/systemd/system/
sudo cp /home/mindx/mindX/scripts/systemd/mindx-curator.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mindx-curator.timer
```

### Verify

```bash
# Timer present, next fire time visible
systemctl list-timers mindx-curator.timer

# One-shot dry-run right now (does not interfere with the schedule)
sudo systemctl start mindx-curator.service
sudo journalctl -u mindx-curator.service -n 50

# Latest report on disk
ls -lt /home/mindx/mindX/data/learnings/curator/ | head -5

# Last run visible on the public dashboard
curl -s https://mindx.pythai.net/insight/skills | jq '.curator'
```

### Disable / pause

```bash
sudo systemctl disable --now mindx-curator.timer
```

The service unit alone stays installed (harmless when no timer triggers it).

### Notes

- The unit runs with `MemoryDenyWriteExecute=true` and `ProtectSystem=strict`
  — Python interpreters tolerate both. Node units (`mindx-frontend.service`)
  cannot use `MemoryDenyWriteExecute` because V8's JIT needs writable+executable
  pages; that's why that unit's hardening list is one line shorter.
- The Curator imports `SkillStore` and the parsed `SKILL.md` files — neither
  needs network, so we don't open egress. Restricted to `AF_UNIX/INET` only
  in case a future iteration adds an auxiliary-LLM judgment step that wants
  to reach Ollama on the loopback.
- `--apply` is on in this unit because the operator has explicitly enabled
  the timer; `--apply` without the timer (an ad-hoc `systemctl start`) also
  applies. Use `python scripts/run_curator.py` directly for a dry-run.
