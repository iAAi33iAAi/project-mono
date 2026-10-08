"""Adversarial tests for fail-closed kernel behavior."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from invariants.graph_anomaly_check import GraphAnomalyCheckInvariant
from invariants.infra_plan_check import InfraPlanCheckInvariant
from invariants.tests_and_types import TestsAndTypesInvariant


def _ctx(tmp_path, **overrides):
    ctx = {
        "pr_number": 9001,
        "commit_sha": "redteam",
        "actor": "attacker",
        "mode": "deploy",
        "emergency": False,
        "diff_text": "",
        "changed_files": [],
        "ci_artifacts": {},
        "repo_root": tmp_path,
    }
    ctx.update(overrides)
    return ctx


def test_missing_ci_evidence_fails_closed(tmp_path):
    result = TestsAndTypesInvariant().evaluate(_ctx(tmp_path))
    assert result.status == "fail"


def test_missing_anomaly_evidence_fails_closed(tmp_path):
    result = GraphAnomalyCheckInvariant().evaluate(
        _ctx(tmp_path, changed_files=["src/main.py"])
    )
    assert result.status == "fail"


def test_missing_infra_plan_fails_closed(tmp_path):
    result = InfraPlanCheckInvariant().evaluate(
        _ctx(tmp_path, changed_files=["infra/terraform/main.tf"])
    )
    assert result.status == "fail"


def test_emergency_flag_cannot_bypass_failed_invariant(tmp_path, monkeypatch):
    from scripts import alga_fold_kernel

    class FailingInvariant:
        name = "redteam_failure"

        def evaluate(self, ctx):
            from invariants import InvariantResult
            return InvariantResult(
                name=self.name,
                status="fail",
                details="forced red-team failure",
                remediation=["do not approve"],
            )

    monkeypatch.setattr(alga_fold_kernel, "load_invariants", lambda: [FailingInvariant()])

    ci = tmp_path / "ci.json"
    ci.write_text(json.dumps({"pytest": {"exit_code": 0}, "ruff": "pass", "mypy": "pass"}))
    ledger = tmp_path / "ledger.jsonl"

    rc = alga_fold_kernel.run(
        [
            "--pr", "9001",
            "--commit", "redteam",
            "--actor", "attacker",
            "--mode", "deploy",
            "--emergency",
            "--ci-artifacts", str(ci),
            "--repo-root", str(tmp_path),
            "--ledger", str(ledger),
            "--metrics", str(tmp_path / "metrics.json"),
        ]
    )

    assert rc == 1
    record = json.loads(ledger.read_text().splitlines()[0])
    assert record["decision"] == "deny"
    assert record["emergency"] is True
