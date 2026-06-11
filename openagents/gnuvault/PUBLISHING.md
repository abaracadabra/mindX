# Publishing GNUVAULT to PyPI — Trusted Publisher template

GNUVAULT publishes to PyPI with **Trusted Publishing** (OpenID Connect): no API
token is ever created, stored, or pasted. PyPI verifies the GitHub Actions
workflow's identity directly. The pipeline is [`.github/workflows/publish.yml`](.github/workflows/publish.yml),
which builds + `twine check`s + uploads on each GitHub Release.

## One-time setup (the template)

### 1. Create the PyPI "pending publisher"

At **<https://pypi.org/manage/account/publishing/>** → *Add a new pending
publisher* (GitHub), enter exactly:

| Field | Value |
|---|---|
| **PyPI Project Name** | `gnuvault` |
| **Owner** | `gnugui` |
| **Repository name** | `GNUVAULT` |
| **Workflow name** | `publish.yml` |
| **Environment name** | `pypi` |

(A *pending* publisher works before the project exists — the first successful run
creates `gnuvault` on PyPI and binds it to this workflow.)

### 2. Create the GitHub environment

In the repo: **Settings → Environments → New environment** named **`pypi`**
(optionally add a required reviewer to gate publishes). This matches
`environment: pypi` in the workflow.

### 3. (optional) TestPyPI dry run

Mirror the above at <https://test.pypi.org/manage/account/publishing/> and add a
`repository-url: https://test.pypi.org/legacy/` step to validate end-to-end
before the real index.

## Publishing a version

1. Tag + cut a GitHub Release (`vX.Y.Z`) — as every GNUVAULT release already does.
2. `publish.yml` fires on `release: published`, builds the sdist + wheel, runs
   `twine check`, and uploads to PyPI via OIDC. No secret involved.
3. `pipx install gnuvault` / `pip install gnuvault` now works.

You can also trigger it manually once the publisher is configured:

```bash
gh workflow run publish.yml --repo gnugui/GNUVAULT
```

## Why no token

Tokens leak. Trusted Publishing is the cypherpunk2048-consistent choice: the
authority is the *public, auditable workflow*, not a stored secret — and there is
no key for anyone, including us, to lose. *take it, own it, use it, share it.*
