"""
Invariant: Ledger Presence

PRs that touch critical paths (src/, infra/, data/, experiments/) must
include either:
  - a case directory under docs/broken-to-better/cases/<entry_id>/
  - OR a ledger draft entry in ops/ledger/ referencing the PR number.

If neither exists the invariant fails and requests the author create one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invariants import BaseInvariant, InvariantResult

_CRITICAL_PREFIXES = ("src/", "infra/", "data/", "experiments/")


class LedgerPresenceInvariant(BaseInvariant):
    name = "ledger_presence"

    def evaluate(self, ctx: dict[str, Any]) -> InvariantResult:
        changed: list[str] = ctx.get("changed_files", [])
        pr_number: int = ctx.get("pr_number", 0)
        repo_root: Path = ctx.get("repo_root", Path("."))

        # Only enforce for critical-path changes
        touches_critical = any(
            f.startswith(prefix) for f in changed for prefix in _CRITICAL_PREFIXES
        )
        if not touches_critical:
            return InvariantResult(
                name=self.name,
                status="pass",
                details="no critical-path files changed; ledger entry not required",
            )

        # Check 1 — broken-to-better case directory
        cases_dir = repo_root / "docs" / "broken-to-better" / "cases"
        if cases_dir.is_dir():
            for case_path in cases_dir.iterdir():
                if case_path.is_dir():
                    # Any case referencing this PR in its metadata is valid
                    meta = case_path / "metadata.json"
                    if meta.is_file():
                        try:
                            data = json.loads(meta.read_text())
                            if data.get("pr_number") == pr_number:
                                return InvariantResult(
                                    name=self.name,
                                    status="pass",
                                    details=f"case {case_path.name} references PR #{pr_number}",
                                )
                        except (json.JSONDecodeError, OSError):
                            continue

        # Check 2 — ledger draft entry in JSONL
        ledger_path = repo_root / "ops" / "ledger" / "kernel-decisions.jsonl"
        if ledger_path.is_file():
            for line in ledger_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("pr_number") == pr_number:
                        return InvariantResult(
                            name=self.name,
                            status="pass",
                            details=f"existing ledger entry found for PR #{pr_number}",
                        )
                except json.JSONDecodeError:
                    continue

        # Neither found — fail
        critical_files = [f for f in changed if any(f.startswith(p) for p in _CRITICAL_PREFIXES)]
        return InvariantResult(
            name=self.name,
            status="fail",
            details=(
                f"PR #{pr_number} touches critical files "
                f"({', '.join(critical_files[:5])}) but has no ledger entry or case"
            ),
            remediation=[
                f"create docs/broken-to-better/cases/<id>/metadata.json with pr_number={pr_number}",
                "or ensure a prior kernel decision record references this PR",
            ],
        )
