# SimpleCoder Sandbox — Audit & Hardening

**Auditor:** Professor Codephreak (operating mindX as a substrate)
**Date:** 2026-06-07
**Scope:** `agents/simple_coder_agent.py` sandbox handling
**Deliverables:** `agents/simple_coder_tools.py` (new boundary), `tests/test_simple_coder_sandbox.py` (proof-suite, 31 tests), agent wiring.

> Linux philosophy: *do one thing and do it well.* The sandbox is now one thing —
> a boundary — implemented once in `simplecoder.tools` and proven by tests, rather
> than re-derived in every file operation.

---

## Findings (pre-hardening)

The original sandbox was a **directory convention, not an enforcement boundary.**

| # | Severity | Finding |
|---|----------|---------|
| 1 | **HIGH** | **Allowlist gates the binary name, not its arguments.** `cat /etc/passwd`, `rm /home/mindx/.ssh/id_rsa`, `cp /etc/shadow .` all worked — the binaries are allowlisted and run with full filesystem access; `cwd=sandbox` does not confine the *arguments* they touch. |
| 2 | **HIGH** | **Interpreters are unrestricted escapes.** `python`/`python3`/`pip` are allowlisted and Turing-complete: `python3 -c "open('/etc/passwd').read()"` / sockets / arbitrary writes. `pip install` runs arbitrary `setup.py`. |
| 3 | **HIGH** | **`find -exec` / `-delete`** are arbitrary-exec / unconfined-delete primitives, allowlisted via `find`. `git -c` injects config → command execution. |
| 4 | **HIGH** | **Full environment leak.** `env = os.environ.copy()` handed every secret (API keys, vault paths, `MINDX_*`) to subprocesses → trivial exfiltration. |
| 5 | **MED** | **No resource limits.** No `setrlimit` — fork bombs, memory bombs, and (via `communicate()`) unbounded output → host memory exhaustion. |
| 6 | **MED** | **Timeout orphans the process.** `asyncio.wait_for` raised but never killed the child; no process group, so children survived. |
| 7 | **MED** | **`max_file_size_mb` declared but never enforced** on read or write. |
| 8 | **LOW** | **Absolute paths silently re-rooted** (`/etc/passwd` → `sandbox/etc/passwd`) — surprising; hid bugs. Symlink-escape via no-follow not considered. |

Net: anything that could run a subprocess could read/write anywhere the process
user could, reach the network, and read every secret in the environment.

---

## Hardening (`simplecoder.tools.Sandbox`)

A single class enforces the boundary. Each guarantee maps to tests in
`tests/test_simple_coder_sandbox.py`.

| Guarantee | Mechanism | Closes |
|-----------|-----------|--------|
| **Path containment** | `resolve()` checks lexical + `realpath`; rejects absolute-outside and `..` escapes | 8 |
| **Symlink-escape rejection** | `_has_symlink_escape()` walks components; a symlink whose real target leaves root is denied (no-follow default) | 8 |
| **Command allowlist** | `check_argv()` — `argv[0]` basename must be allowed | 1 |
| **Argument-path containment** | path-like args (absolute / `~` / `..`) must resolve inside the sandbox | 1 |
| **Escape-flag denial** | `find -exec/-delete`, `git -c`; `python -c` etc. gated by `allow_inline_code` (strict mode + `.strict()` drops interpreters entirely) | 2, 3 |
| **Scrubbed env** | `scrubbed_env()` — only `PATH/LANG/TERM/...`; `HOME`→sandbox; never host secrets | 4 |
| **Resource limits** | `preexec_fn` sets `RLIMIT_CPU/AS/FSIZE/NOFILE/NPROC`; `start_new_session` | 5 |
| **Process-group kill on timeout** | `os.killpg(SIGKILL)` + reap | 6 |
| **Bounded output** | `_communicate_capped()` caps stdout+stderr, kills runaway producers | 5 |
| **File-size limits** | `read_text`/`write_text` enforce `max_file_bytes` | 7 |

### Proof of absolute — the honest part

In-process checks **cannot** make a general-purpose interpreter *absolutely*
contained: an interpreter you are permitted to run can open sockets and read any
file the process user can read. The guarantees that **are** absolute in-process:
path containment, symlink-escape rejection, env scrubbing, resource limits,
output bounding, file-size limits.

For absolute containment of *execution*, the kernel must enforce it. `Sandbox`
auto-detects and **probes** `bwrap` (bubblewrap) / `nsjail`; when a working
backend exists, every command is wrapped so namespaces — not a Python check —
draw the boundary. When the backend is missing or cannot create namespaces
(e.g. already inside a sandbox → `EAGAIN`), `Sandbox` **gracefully falls back**
to in-process defence-in-depth and reports this via `info()["isolation_backend"]`.
The honest operational posture:

- **With `bwrap`/`nsjail` working** → execution boundary is kernel-enforced (absolute).
- **Without** → filesystem/env/resource boundaries hold; interpreters should be
  disabled with `SandboxPolicy.strict()` for untrusted input, or the agent run
  as an unprivileged user in a container.

---

## What changed in the agent

`SimpleCoderAgent` now *routes*; the boundary *enforces*:

- `_resolve_and_check_path()` → delegates to `Sandbox.resolve()` (same `Path|None` contract).
- `_run_shell_command()` → `Sandbox.run()` (allowlist + arg-containment + scrubbed env + rlimits + timeout-kill + output cap + isolation).
- `_read_file()` / `_write_file()` → `Sandbox.read_text()/write_text()` (containment + size limits).
- `_build_sandbox_policy()` maps existing JSON config (`allowed_shell_commands`, `command_timeout_seconds`, `max_file_size_mb`, new `allow_inline_code`, `use_os_isolation`) onto the policy.

No public method signatures changed; existing callers are unaffected.

## Verification

```bash
.mindx_env/bin/python -m pytest tests/test_simple_coder_sandbox.py -q   # 31 passed
```

Covered: relative/absolute/`..` containment, symlink escape (in & out), allowlist,
argument-path escape (absolute/`..`/`~`), `find -exec`/`-delete`, `git -c`,
inline-code default vs strict, env scrubbing, read/write size limits, write-outside,
run success/failure/timeout-kill/output-cap, and `info()` introspection.

## Residual / recommended next steps

1. Ship `bwrap` on the prod VPS and set `use_os_isolation=true` so execution is kernel-enforced there.
2. For untrusted directives, default the agent policy to `.strict()` (no interpreters).
3. Consider a seccomp profile / read-only root bind for the `bwrap` wrap (network already unshared via `--unshare-all`).
