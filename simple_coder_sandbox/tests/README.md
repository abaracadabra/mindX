# Sandbox test templates — external package imports

Reference templates for verifying **any** externally-supplied package dropped
into `simple_coder_sandbox/projects/` before SEA considers it for adoption.
These mirror the pipeline documented in `docs/PACKAGE_ADOPTION.md`:

```
inspect_zip → extract_zip → audit_package → SEA decision
```

## Files

| File | Purpose |
|---|---|
| `test_external_package_template.py` | Per-package verification gauntlet. Parameterized by `MINDX_PACKAGE_ZIP` (sandbox-relative, default `projects/LLMFIT.zip` — the first adopted package, kept as the living reference). Asserts: valid zip, no traversal/zip-bomb flags, clean extraction, audit completes, **zero high-severity findings**, license declared. |
| `test_hostile_fixtures.py` | Helpers that craft hostile archives (traversal members, zip-bombs, oversized member sets) + smoke tests proving the `Sandbox` guard chain rejects them in *this* environment. If these fail, do not trust a green package run. |

## Usage

```bash
# Verify the reference package (LLMFIT)
.mindx_env/bin/python -m pytest simple_coder_sandbox/tests/ --no-cov -q

# Verify a new candidate package
MINDX_PACKAGE_ZIP=projects/NewThing.zip \
  .mindx_env/bin/python -m pytest simple_coder_sandbox/tests/test_external_package_template.py --no-cov -q
```

A green run here is the precondition for handing the package's `audit_summary`
to `SEA.evaluate_external_package_adoption()` (or just run
`scripts/evaluate_package.py projects/NewThing.zip`).

## Template policy for new packages

1. Copy nothing — the template is parameterized; point `MINDX_PACKAGE_ZIP` at the new zip.
2. If the package needs package-specific assertions (expected member names,
   declared license, boundary contract lines), add a small
   `test_<package>_expectations.py` beside this template following the same
   pattern as the LLMFIT expectations test inside the template file.
3. High-severity audit findings (`dynamic_exec`, `deserialization`,
   `native_code`, `process_exec` via `os.system`) are a hard red flag —
   investigate before involving SEA; the decision prompt will see them too.
