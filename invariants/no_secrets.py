"""
Invariant: No Secrets

Scans the PR diff for:
  - Known secret patterns (AWS keys, GitHub tokens, private keys, etc.).
  - High-entropy strings that look like leaked credentials.

Any match → deny merge immediately and request secret rotation.
"""

from __future__ import annotations

import math
import re
from typing import Any

from invariants import BaseInvariant, InvariantResult

# ── patterns ─────────────────────────────────────────────────────────
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret Key", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*\S{20,}")),
    ("GitHub Token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub OAuth", re.compile(r"gho_[A-Za-z0-9]{36}")),
    ("Generic API Key", re.compile(r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]?\S{16,}")),
    ("Private Key Block", re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----")),
    ("Generic Secret", re.compile(r"(?i)(secret|password|passwd|token)\s*[=:]\s*['\"]?\S{8,}")),
    ("Slack Token", re.compile(r"xox[bpoas]-[0-9A-Za-z-]{10,}")),
    ("Stripe Key", re.compile(r"sk_live_[0-9a-zA-Z]{24,}")),
    ("Database URL secret", re.compile(r"(?i)(mysql|postgres|mongodb)://\S+:\S+@")),
]

_ENTROPY_THRESHOLD = 4.5  # bits per char — strings above this are suspicious
_MIN_TOKEN_LEN = 20  # only check tokens this long or longer
_ADDED_LINE = re.compile(r"^\+(?!\+\+)", re.MULTILINE)


def _shannon_entropy(s: str) -> float:
    """Return Shannon entropy in bits per character."""
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


class NoSecretsInvariant(BaseInvariant):
    name = "no_secrets"

    def evaluate(self, ctx: dict[str, Any]) -> InvariantResult:
        diff_text: str = ctx.get("diff_text", "")
        if not diff_text:
            return InvariantResult(
                name=self.name,
                status="pass",
                details="no diff provided; nothing to scan",
            )

        # Only inspect added lines
        added_lines = [
            line[1:]  # strip leading '+'
            for line in diff_text.splitlines()
            if _ADDED_LINE.match(line)
        ]
        if not added_lines:
            return InvariantResult(
                name=self.name,
                status="pass",
                details="no added lines in diff",
            )

        added_blob = "\n".join(added_lines)
        findings: list[str] = []

        # ── pattern scan ───────────────────────────────────────────────
        for label, pattern in _SECRET_PATTERNS:
            matches = pattern.findall(added_blob)
            if matches:
                # Redact the actual value
                findings.append(f"{label}: {len(matches)} occurrence(s)")

        # ── entropy scan ───────────────────────────────────────────────
        token_re = re.compile(r"[A-Za-z0-9+/=_-]{%d,}" % _MIN_TOKEN_LEN)  # noqa: UP031
        high_entropy_count = 0
        for token in token_re.findall(added_blob):
            if _shannon_entropy(token) >= _ENTROPY_THRESHOLD:
                high_entropy_count += 1
        if high_entropy_count:
            findings.append(f"high-entropy strings: {high_entropy_count} token(s) above {_ENTROPY_THRESHOLD} bits/char")

        if findings:
            return InvariantResult(
                name=self.name,
                status="fail",
                details="; ".join(findings),
                remediation=[
                    "remove secrets from the diff immediately",
                    "rotate any exposed credentials",
                    "scrub secrets from git history (git filter-repo or BFG)",
                    "add patterns to .gitignore and use environment variables",
                ],
            )

        return InvariantResult(
            name=self.name,
            status="pass",
            details=f"scanned {len(added_lines)} added lines — no secrets detected",
        )
