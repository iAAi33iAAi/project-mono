"""
Invariant: Graph Anomaly Check

Consults the anomaly-detector output at ops/embeddings/anomalies.json
and cross-references it with the files changed in the PR.

If a changed file has an anomaly severity >= threshold (default 0.8) the
invariant requires a broken-to-better case and an additional reviewer;
otherwise it denies the merge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invariants import BaseInvariant, InvariantResult

_SEVERITY_THRESHOLD = 0.8


class GraphAnomalyCheckInvariant(BaseInvariant):
    name = "graph_anomaly_check"

    def evaluate(self, ctx: dict[str, Any]) -> InvariantResult:
        repo_root: Path = ctx.get("repo_root", Path("."))
        changed: list[str] = ctx.get("changed_files", [])
        pr_number: int = ctx.get("pr_number", 0)

        anomalies_path = repo_root / "ops" / "embeddings" / "anomalies.json"

        if not anomalies_path.is_file():
            return InvariantResult(
                name=self.name,
                status="pass",
                details="no anomaly data found at ops/embeddings/anomalies.json; skipping",
            )

        try:
            anomalies: list[dict[str, Any]] = json.loads(
                anomalies_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError) as exc:
            return InvariantResult(
                name=self.name,
                status="error",
                details=f"failed to parse anomalies.json: {exc}",
                remediation=["fix or regenerate ops/embeddings/anomalies.json"],
            )

        severity_map: dict[str, float] = {}
        for entry in anomalies:
            fpath = entry.get("file", "")
            sev = float(entry.get("severity", 0.0))
            if fpath in severity_map:
                severity_map[fpath] = max(severity_map[fpath], sev)
            else:
                severity_map[fpath] = sev

        flagged: list[tuple[str, float]] = []
        for f in changed:
            sev = severity_map.get(f, 0.0)
            if sev >= _SEVERITY_THRESHOLD:
                flagged.append((f, sev))

        if not flagged:
            return InvariantResult(
                name=self.name,
                status="pass",
                details=(
                    f"checked {len(changed)} changed file(s) against "
                    f"{len(severity_map)} anomaly entries; none above threshold"
                ),
            )

        # Check whether a case already exists for this PR
        cases_dir = repo_root / "docs" / "broken-to-better" / "cases"
        has_case = False
        if cases_dir.is_dir():
            for case_path in cases_dir.iterdir():
                meta = case_path / "metadata.json"
                if meta.is_file():
                    try:
                        data = json.loads(meta.read_text())
                        if data.get("pr_number") == pr_number:
                            has_case = True
                            break
                    except (json.JSONDecodeError, OSError):
                        continue

        if has_case:
            return InvariantResult(
                name=self.name,
                status="pass",
                details=(
                    f"anomaly flagged file(s) "
                    f"({', '.join(f for f, _ in flagged)}) but a case exists "
                    f"for PR #{pr_number}"
                ),
            )

        detail_parts = [f"{f} (severity {s:.2f})" for f, s in flagged]
        return InvariantResult(
            name=self.name,
            status="fail",
            details=(
                "anomaly-flagged files touched without a case: "
                + "; ".join(detail_parts)
            ),
            remediation=[
                "create a broken-to-better case for this PR",
                "request an additional reviewer for anomaly-flagged files",
                f"threshold is {_SEVERITY_THRESHOLD}; lower severity anomalies are informational only",
            ],
        )
