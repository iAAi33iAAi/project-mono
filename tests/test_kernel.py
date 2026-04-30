"""Kernel integration tests for ALGA_FOLD_KERNEL."""

import json, sys, textwrap
from pathlib import Path
from uuid import uuid4
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from invariants import load_invariants, BaseInvariant, KERNEL_VERSION
from invariants.no_secrets import NoSecretsInvariant
from invariants.tests_and_types import TestsAndTypesInvariant
from invariants.infra_plan_check import InfraPlanCheckInvariant
from scripts.ledger_append import append_decision, read_ledger


def _ctx(tmp_path, *, diff="", ci=None, files=None, emergency=False):
    return {"pr_number": 42, "commit_sha": "abc123", "actor": "tester",
            "mode": "merge", "emergency": emergency, "diff_text": diff,
            "changed_files": files or [], "ci_artifacts": ci or {},
            "repo_root": tmp_path}


def _record(**kw):
    base = {"decision_id": str(uuid4()), "timestamp": "2026-04-30T00:00:00Z",
            "actor": "a", "pr_number": 1, "commit_sha": "dead",
            "mode": "merge", "invariant_results": {}, "decision": "approve",
            "reason": "ok", "kernel_version": KERNEL_VERSION}
    base.update(kw)
    return base


class TestLoader:
    def test_loads_all(self):
        names = {i.name for i in load_invariants()}
        assert len(names) >= 6

    def test_subclass(self):
        for i in load_invariants():
            assert isinstance(i, BaseInvariant)


class TestNoSecrets:
    def test_clean(self, tmp_path):
        assert NoSecretsInvariant().evaluate(_ctx(tmp_path, diff="+x=1")).passed()

    def test_aws_key(self, tmp_path):
        d = '+KEY="AKIAIOSFODNN7EXAMPLE"'
        assert NoSecretsInvariant().evaluate(_ctx(tmp_path, diff=d)).status == "fail"


class TestTestsAndTypes:
    def test_green(self, tmp_path):
        ci = {"pytest": {"exit_code": 0}, "ruff": "pass", "mypy": "pass"}
        assert TestsAndTypesInvariant().evaluate(_ctx(tmp_path, ci=ci)).passed()

    def test_red(self, tmp_path):
        ci = {"pytest": {"exit_code": 1}, "ruff": "pass", "mypy": "pass"}
        assert TestsAndTypesInvariant().evaluate(_ctx(tmp_path, ci=ci)).status == "fail"


class TestInfraPlan:
    def test_no_infra(self, tmp_path):
        assert InfraPlanCheckInvariant().evaluate(_ctx(tmp_path)).passed()

    def test_destroy_deny(self, tmp_path):
        plan = {"resource_changes": [{"address": "aws_rds.prod",
                "type": "aws_rds_cluster", "change": {"actions": ["delete"]}}]}
        ctx = _ctx(tmp_path, files=["infra/terraform/main.tf"],
                   ci={"terraform_plan": plan})
        assert InfraPlanCheckInvariant().evaluate(ctx).status == "fail"


class TestLedger:
    def test_append(self, tmp_path):
        f = tmp_path / "ledger.jsonl"
        append_decision(_record(), f)
        assert len(read_ledger(f)) == 1

    def test_multi(self, tmp_path):
        f = tmp_path / "ledger.jsonl"
        append_decision(_record(pr_number=1), f)
        append_decision(_record(pr_number=2), f)
        assert len(read_ledger(f)) == 2

    def test_bad_record(self, tmp_path):
        with pytest.raises(ValueError):
            append_decision({"decision": "approve"}, tmp_path / "l.jsonl")


class TestKernelE2E:
    def test_approve(self, tmp_path):
        from scripts.alga_fold_kernel import run
        ci = tmp_path / "ci.json"
        ci.write_text(json.dumps({"pytest": {"exit_code": 0}, "ruff": "pass", "mypy": "pass"}))
        ledger = tmp_path / "ledger.jsonl"
        rc = run(["--pr", "99", "--commit", "aaa", "--actor", "bob",
                  "--mode", "merge", "--ci-artifacts", str(ci),
                  "--repo-root", str(tmp_path), "--ledger", str(ledger),
                  "--metrics", str(tmp_path / "m.json")])
        assert rc == 0
        assert read_ledger(ledger)[0]["decision"] == "approve"

    def test_deny_secret(self, tmp_path):
        from scripts.alga_fold_kernel import run
        diff = tmp_path / "pr.diff"
        diff.write_text('+SECRET="AKIAIOSFODNN7EXAMPLE"\n')
        ci = tmp_path / "ci.json"
        ci.write_text(json.dumps({"pytest": {"exit_code": 0}, "ruff": "pass", "mypy": "pass"}))
        ledger = tmp_path / "ledger.jsonl"
        rc = run(["--pr", "100", "--commit", "bbb", "--actor", "eve",
                  "--mode", "merge", "--diff-file", str(diff),
                  "--ci-artifacts", str(ci), "--repo-root", str(tmp_path),
                  "--ledger", str(ledger), "--metrics", str(tmp_path / "m.json")])
        assert rc == 1
        assert read_ledger(ledger)[0]["decision"] == "deny"
