# SPDX-License-Identifier: Apache-2.0
"""External-package verification template.

Run this gauntlet against ANY package zip dropped into
``simple_coder_sandbox/projects/`` before SEA considers it for adoption
(docs/PACKAGE_ADOPTION.md). Parameterized by ``MINDX_PACKAGE_ZIP``
(sandbox-relative path); defaults to ``projects/LLMFIT.zip`` — the first
package adopted through this pipeline, kept as the living reference.

    MINDX_PACKAGE_ZIP=projects/NewThing.zip \
      python -m pytest simple_coder_sandbox/tests/test_external_package_template.py --no-cov -q

Async paths use ``asyncio.run`` directly so no pytest-asyncio is needed
(same convention as tests/test_simple_coder_sandbox.py).
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

# sandbox/tests/ -> sandbox/ -> PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.simple_coder_tools import Sandbox  # noqa: E402

SANDBOX_ROOT = PROJECT_ROOT / "simple_coder_sandbox"
PACKAGE_ZIP = os.environ.get("MINDX_PACKAGE_ZIP", "projects/LLMFIT.zip")

# Findings that must never appear in an adoptable package.
HIGH_SEVERITY_KINDS = {"dynamic_exec", "deserialization", "native_code"}


@pytest.fixture(scope="module")
def sandbox() -> Sandbox:
    return Sandbox(SANDBOX_ROOT)


@pytest.fixture(scope="module")
def inspect_result(sandbox):
    return sandbox.inspect_zip(PACKAGE_ZIP)


@pytest.fixture(scope="module")
def audit_summary():
    """Full audit via the SimpleCoder op — the same artifact SEA consumes."""
    from agents.simple_coder_agent import SimpleCoderAgent
    agent = SimpleCoderAgent()
    stem = Path(PACKAGE_ZIP).stem
    res = asyncio.run(agent.execute(
        "audit_package", archive=PACKAGE_ZIP,
        extract_to=f"temp/{stem}_template_audit",
    ))
    assert res.get("status") == "SUCCESS", f"audit_package failed: {res}"
    yield res["audit_summary"]
    # quarantine hygiene: remove the template's extraction dir
    import shutil
    shutil.rmtree(SANDBOX_ROOT / "temp" / f"{stem}_template_audit", ignore_errors=True)


# ── gate 1: archive safety (non-extracting) ──────────────────────────────────
def test_package_zip_exists():
    assert (SANDBOX_ROOT / PACKAGE_ZIP).is_file(), (
        f"{PACKAGE_ZIP} not found in sandbox — drop the package into "
        f"simple_coder_sandbox/projects/ or set MINDX_PACKAGE_ZIP"
    )


def test_is_valid_zip(inspect_result):
    assert inspect_result["status"] == "SUCCESS"
    assert inspect_result["is_valid"] is True
    assert inspect_result["member_count"] > 0


def test_no_blocking_safety_issues(inspect_result):
    blocking = [
        i for i in inspect_result["potential_issues"]
        if i != "none" and i.split(":")[0] in (
            "path_traversal", "too_many_members",
            "decompressed_too_large", "suspicious_ratio", "corrupt_member",
        )
    ]
    assert not blocking, f"archive rejected by safety checks: {blocking}"


# ── gate 2: contained extraction ─────────────────────────────────────────────
def test_extracts_cleanly(sandbox):
    stem = Path(PACKAGE_ZIP).stem
    res = asyncio.run(sandbox.extract_zip(PACKAGE_ZIP, f"temp/{stem}_template_extract"))
    try:
        assert res["status"] == "SUCCESS", f"extraction failed: {res['messages']}"
        assert res["members_extracted"] > 0
        # every extracted file is inside the extraction root
        dest = Path(res["extracted_to"])
        for name in res["extracted_names"]:
            assert (dest / name).resolve().is_relative_to(dest)
    finally:
        import shutil
        shutil.rmtree(SANDBOX_ROOT / "temp" / f"{stem}_template_extract", ignore_errors=True)


# ── gate 3: static audit (the artifact SEA sees) ─────────────────────────────
def test_audit_completes_with_summary(audit_summary):
    for key in ("package_name", "files", "imports", "risk_findings",
                "aggregate_risk", "declared_license"):
        assert key in audit_summary, f"audit_summary missing {key!r}"


def test_no_high_severity_findings(audit_summary):
    high = [f for f in audit_summary["risk_findings"] if f.get("severity") == "high"]
    assert not high, f"high-severity findings — investigate before SEA: {high}"


def test_no_forbidden_finding_kinds(audit_summary):
    forbidden = [f for f in audit_summary["risk_findings"]
                 if f.get("kind") in HIGH_SEVERITY_KINDS]
    assert not forbidden, f"forbidden finding kinds present: {forbidden}"


def test_license_declared(audit_summary):
    assert audit_summary["declared_license"] != ["undeclared"], (
        "package declares no license — adoption criterion 2 cannot be evaluated"
    )


# ── package-specific expectations (pattern for new packages) ─────────────────
# When importing a new package, add a sibling test_<package>_expectations.py
# following this shape: skip unless the template points at YOUR package, then
# assert the contract you expect (member names, license, boundary lines).
@pytest.mark.skipif(Path(PACKAGE_ZIP).stem.lower() != "llmfit",
                    reason="LLMFIT-specific expectations")
class TestLLMFitExpectations:
    def test_expected_members(self, inspect_result):
        names = {m["name"] for m in inspect_result["members"]}
        assert names == {
            "llmfit_tool.py", "inference_discovery_llmfit_hook.py",
            "llmfit.advisor.agent", "llmfit.container",
        }

    def test_license_boundary(self, audit_summary):
        joined = " ".join(audit_summary["declared_license"])
        assert "Apache-2.0" in joined and "MIT" in joined

    def test_fail_open_contract_present(self, audit_summary):
        notes = " ".join(audit_summary["external_boundary_notes"]).lower()
        assert "fail" in notes and "127.0.0.1" in " ".join(
            audit_summary["external_boundary_notes"])

    def test_only_expected_network_findings(self, audit_summary):
        # llmfit's mediums are loopback urllib — anything else is new and suspect
        kinds = {f["kind"] for f in audit_summary["risk_findings"]}
        assert kinds <= {"network", "process_exec"}, f"unexpected finding kinds: {kinds}"
