"""
Invariant: Tests & Types

Verifies that CI artifacts confirm:
  1. pytest passed (exit code 0, or ``tests_passed`` flag in artifacts).
  2. ruff lint passed.
  3. mypy type-check passed.
  4. (optional) flakiness metric is below threshold for sensitive paths.

The invariant is a *pure function* of the CI artifact JSON — it never
executes test runners itself.
"""

from __future__ import annotations

from typing import Any

from invariants import BaseInvariant, InvariantResult

_FLAKINESS_THRESHOLD = 0.05  # 5 % max allowed flakiness rate


class TestsAndTypesInvariant(BaseInvariant):
    name = "tests_and_types"

    def evaluate(self, ctx: dict[str, Any]) -> InvariantResult:
        ci: dict[str, Any] = ctx.get("ci_artifacts", {})

        # If no CI artifacts provided, we cannot verify — warn but don't block
        if not ci:
            return InvariantResult(
                name=self.name,
                status="warn",
                details="no CI artifact JSON provided; cannot verify test results",
                remediation=[
                    "re-run kernel with --ci-artifacts pointing to the CI output JSON"
                ],
            )

        failures: list[str] = []
        remediation: list[str] = []

        # ── pytest ─────────────────────────────────────────────────
        pytest_status = ci.get("pytest", {})
        if isinstance(pytest_status, dict):
            if pytest_status.get("exit_code", 1) != 0:
                failures.append("pytest failed")
                remediation.append("fix failing tests and re-run pytest")
            passed = pytest_status.get("tests_passed", True)
            if not passed:
                failures.append("pytest reported test failures")
                remediation.append("fix failing tests before merge")
        elif pytest_status != "pass":
            failures.append(f"pytest status: {pytest_status}")
            remediation.append("fix failing tests")

        # ── ruff ───────────────────────────────────────────────────
        ruff_status = ci.get("ruff", "unknown")
        if isinstance(ruff_status, dict):
            ruff_status = ruff_status.get("status", "unknown")
        if ruff_status not in ("pass", "ok", "success"):
            failures.append(f"ruff lint status: {ruff_status}")
            remediation.append("run 'ruff check src/ tests/ --fix' and commit")

        # ── mypy ───────────────────────────────────────────────────
        mypy_status = ci.get("mypy", "unknown")
        if isinstance(mypy_status, dict):
            mypy_status = mypy_status.get("status", "unknown")
        if mypy_status not in ("pass", "ok", "success"):
            failures.append(f"mypy status: {mypy_status}")
            remediation.append("resolve type errors reported by mypy")

        # ── flakiness (optional) ───────────────────────────────────────
        flakiness = ci.get("flakiness_rate")
        if flakiness is not None:
            try:
                rate = float(flakiness)
                if rate > _FLAKINESS_THRESHOLD:
                    failures.append(
                        f"flakiness rate {rate:.2%} exceeds "
                        f"threshold {_FLAKINESS_THRESHOLD:.2%}"
                    )
                    remediation.append(
                        "stabilise flaky tests (run pytest --count=10 locally)"
                    )
            except (TypeError, ValueError):
                pass

        if failures:
            return InvariantResult(
                name=self.name,
                status="fail",
                details="; ".join(failures),
                remediation=remediation,
            )

        return InvariantResult(
            name=self.name,
            status="pass",
            details="pytest, ruff, and mypy all passed",
        )
