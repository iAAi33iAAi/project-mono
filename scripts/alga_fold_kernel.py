#!/usr/bin/env python3
"""ALGA_FOLD_KERNEL — Minimal trusted runtime.

Mediates every critical change (merge / deploy / apply) by evaluating
pluggable invariants and recording an append-only decision to the
Knowledge Ledger.

Exit codes: 0 approved, 1 denied, 2 internal error.
"""
from __future__ import annotations
import argparse, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from invariants import KERNEL_VERSION, InvariantResult, load_invariants
from scripts.ledger_append import append_decision


def _build_context(args):
    diff_text = ""
    if args.diff_file and Path(args.diff_file).is_file():
        diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
    changed_files = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 4:
                changed_files.append(parts[3].lstrip("b/"))
    ci_artifacts = {}
    if args.ci_artifacts and Path(args.ci_artifacts).is_file():
        ci_artifacts = json.loads(Path(args.ci_artifacts).read_text(encoding="utf-8"))
    return {
        "pr_number": args.pr, "commit_sha": args.commit,
        "actor": args.actor, "mode": args.mode,
        "emergency": args.emergency, "diff_text": diff_text,
        "changed_files": changed_files, "ci_artifacts": ci_artifacts,
        "repo_root": Path(args.repo_root).resolve(),
    }


def _make_record(ctx, results, decision, reason, remediations, elapsed_ms):
    return {
        "decision_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": ctx["actor"], "pr_number": ctx["pr_number"],
        "commit_sha": ctx["commit_sha"], "mode": ctx["mode"],
        "emergency": ctx["emergency"],
        "invariant_results": {
            r.name: {"status": r.status, "details": r.details} for r in results
        },
        "decision": decision, "reason": reason,
        "remediation": remediations, "elapsed_ms": elapsed_ms,
        "kernel_version": KERNEL_VERSION, "signature": None,
    }


def _update_metrics(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = json.loads(path.read_text()) if path.is_file() else {
        "total_decisions": 0, "approvals": 0, "denials": 0,
        "emergency_bypasses": 0, "failures_by_invariant": {},
        "total_elapsed_ms": 0,
    }
    metrics["total_decisions"] += 1
    metrics["total_elapsed_ms"] += record["elapsed_ms"]
    if record["decision"] == "approve":
        metrics["approvals"] += 1
    else:
        metrics["denials"] += 1
    if record.get("emergency"):
        metrics["emergency_bypasses"] += 1
    for name, res in record["invariant_results"].items():
        if res["status"] in ("fail", "error"):
            metrics["failures_by_invariant"][name] = metrics["failures_by_invariant"].get(name, 0) + 1
    path.write_text(json.dumps(metrics, indent=2) + "\n")


def run(argv=None):
    parser = argparse.ArgumentParser(description="ALGA_FOLD_KERNEL")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--mode", choices=["merge","deploy","apply"], default="merge")
    parser.add_argument("--diff-file", default=None)
    parser.add_argument("--ci-artifacts", default=None)
    parser.add_argument("--emergency", action="store_true")
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT))
    parser.add_argument("--ledger", default=str(PROJECT_ROOT/"ops"/"ledger"/"kernel-decisions.jsonl"))
    parser.add_argument("--metrics", default=str(PROJECT_ROOT/"ops"/"monitoring"/"kernel-metrics.json"))
    args = parser.parse_args(argv)
    try:
        ctx = _build_context(args)
    except Exception as exc:
        print(f"[KERNEL ERROR] context build failed: {exc}", file=sys.stderr)
        return 2
    invariants = load_invariants()
    results = []
    start = time.monotonic_ns()
    for inv in invariants:
        try:
            results.append(inv.evaluate(ctx))
        except Exception as exc:
            results.append(InvariantResult(name=inv.name, status="error", details=f"exception: {exc}", remediation=["investigate invariant crash"]))
    elapsed_ms = (time.monotonic_ns() - start) // 1_000_000
    failures = [r for r in results if r.status in ("fail", "error")]
    all_remediations = []
    for r in failures:
        all_remediations.extend(r.remediation)
    if ctx["emergency"] and failures:
        decision, reason = "approve", "EMERGENCY BYPASS — mandatory retrospective within 48 h."
        all_remediations.insert(0, "file retrospective within 48 hours")
    elif failures:
        decision = "deny"
        reason = f"{len(failures)} invariant(s) failed: " + ", ".join(r.name for r in failures)
    else:
        decision, reason = "approve", "all invariants passed"
    record = _make_record(ctx, results, decision, reason, all_remediations, elapsed_ms)
    try:
        append_decision(record, Path(args.ledger))
    except Exception as exc:
        print(f"[KERNEL ERROR] ledger write failed: {exc}", file=sys.stderr)
        return 2
    try:
        _update_metrics(Path(args.metrics), record)
    except Exception:
        pass
    print(json.dumps(record, indent=2))
    return 0 if decision == "approve" else 1


if __name__ == "__main__":
    sys.exit(run())
