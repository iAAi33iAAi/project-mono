"""
Aethel Grid — Daily Security Audit
Laminar Lattice Prime 3.6.9

Run via: python -m aethel.audit --full
The audit exits non-zero when critical stewardship drift is detected.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("aethel.audit")


@dataclass
class AuditFinding:
    severity: str
    category: str
    path: str
    detail: str


@dataclass
class AuditReport:
    timestamp: float
    findings: List[AuditFinding]
    lattice_clean: bool
    summary: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "lattice_clean": self.lattice_clean,
            "summary": self.summary,
            "findings": [asdict(finding) for finding in self.findings],
        }


_WORLD_WRITABLE = stat.S_IWOTH
_PROTECTED_FILES = [
    "SPEC.md",
    "src/aethel/stewardship.py",
    "src/aethel/__init__.py",
    "src/aethel/audit.py",
]

_DRIFT_PATTERNS = [
    "self_preservation_override",
    "bypass_gateway",
    "skip_psi_check",
    "disable_stewardship",
    "ARCHITECT_CONSTANT_DIVISOR = 0\\n",
]


def _check_file_permissions(root: Path) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    for protected in _PROTECTED_FILES:
        path = root / protected
        if not path.exists():
            findings.append(
                AuditFinding(
                    severity="WARN",
                    category="SPEC",
                    path=str(path),
                    detail=f"Protected file missing — expected at {protected}",
                )
            )
            continue
        if path.stat().st_mode & _WORLD_WRITABLE:
            findings.append(
                AuditFinding(
                    severity="CRITICAL",
                    category="PERMISSIONS",
                    path=str(path),
                    detail="World-writable permission detected on protected file. Fix: chmod o-w",
                )
            )
    return findings


def _check_drift(root: Path) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    for py_file in root.rglob("*.py"):
        if "test" in py_file.parts or py_file.name == "audit.py":
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for pattern in _DRIFT_PATTERNS:
            if pattern in content:
                findings.append(
                    AuditFinding(
                        severity="CRITICAL",
                        category="DRIFT",
                        path=str(py_file),
                        detail=(
                            f"Drift pattern detected: '{pattern}'. "
                            "This weakens stewardship policy — remove before merge."
                        ),
                    )
                )
    return findings


def _check_spec_present(root: Path) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    spec = root / "SPEC.md"
    if not spec.exists():
        findings.append(
            AuditFinding(
                severity="CRITICAL",
                category="SPEC",
                path=str(spec),
                detail="SPEC.md not found in repo root. Stewardship constitution is missing.",
            )
        )
    elif spec.stat().st_size < 100:
        findings.append(
            AuditFinding(
                severity="CRITICAL",
                category="SPEC",
                path=str(spec),
                detail="SPEC.md appears truncated (< 100 bytes). Possible corruption or deletion.",
            )
        )
    return findings


def _check_ca_constant(root: Path) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    target = root / "src" / "aethel" / "stewardship.py"
    if not target.exists():
        findings.append(
            AuditFinding(
                severity="WARN",
                category="CONFIG",
                path=str(target),
                detail="stewardship.py is missing; constant checks could not run.",
            )
        )
        return findings

    content = target.read_text(encoding="utf-8", errors="ignore")
    if "C_a_DIVISOR = 0.01" not in content and "ARCHITECT_CONSTANT_DIVISOR = 0.01" not in content:
        findings.append(
            AuditFinding(
                severity="CRITICAL",
                category="CONFIG",
                path=str(target),
                detail=(
                    "Architect's Constant divisor (C_a_DIVISOR = 0.01) not found "
                    "in stewardship.py."
                ),
            )
        )
    if "PSI_THRESHOLD = 1.0" not in content:
        findings.append(
            AuditFinding(
                severity="CRITICAL",
                category="CONFIG",
                path=str(target),
                detail=(
                    "Psi threshold (PSI_THRESHOLD = 1.0) not found in stewardship.py. "
                    "Entropy mitigation may be disabled."
                ),
            )
        )
    return findings


def run_audit(root: Optional[Path] = None, verbose: bool = False) -> AuditReport:
    del verbose
    if root is None:
        root = Path(__file__).resolve().parents[2]
    root = root.resolve()

    findings: List[AuditFinding] = []
    findings.extend(_check_spec_present(root))
    findings.extend(_check_file_permissions(root))
    findings.extend(_check_ca_constant(root))
    findings.extend(_check_drift(root))

    critical = [finding for finding in findings if finding.severity == "CRITICAL"]
    warnings = [finding for finding in findings if finding.severity == "WARN"]
    lattice_clean = not critical
    summary_parts = [f"{len(critical)} critical", f"{len(warnings)} warnings"]
    summary = (
        f"LATTICE_CLEAN — {', '.join(summary_parts)}"
        if lattice_clean
        else f"LATTICE_DIRTY — {', '.join(summary_parts)}"
    )
    return AuditReport(
        timestamp=time.time(),
        findings=findings,
        lattice_clean=lattice_clean,
        summary=summary,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m aethel.audit",
        description="Aethel Grid daily security audit.",
    )
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", dest="output_json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else None
    report = run_audit(root=root, verbose=args.verbose)
    if args.output_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print("")
        print("=" * 60)
        print("  AETHEL GRID SECURITY AUDIT -- Laminar Lattice Prime 3.6.9")
        print("=" * 60)
        print(f"  {report.summary}")
        print("=" * 60)
        print("")
        for finding in report.findings:
            if finding.severity == "INFO" and not args.verbose:
                continue
            if finding.severity == "CRITICAL":
                marker = "[CRITICAL]"
            elif finding.severity == "WARN":
                marker = "[WARN]   "
            else:
                marker = "[INFO]   "
            print(f"  {marker} [{finding.category}]")
            print(f"     Path   : {finding.path}")
            print(f"     Detail : {finding.detail}")
            print("")

        if not report.findings:
            print("  OK No findings. Lattice is clean.")
            print("")

    return 0 if report.lattice_clean else 1


if __name__ == "__main__":
    sys.exit(main())
