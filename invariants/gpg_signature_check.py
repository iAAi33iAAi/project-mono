"""
Invariant: GPG Signature Check (optional)

When the CODEX requires GPG-signed commits for infra or production
changes, this invariant verifies that the commit carries a valid
signature.

Behaviour:
  - If ``docs/codex/role-mapping.json`` sets ``require_gpg`` for the
    actor's role **and** the mode is ``deploy`` or ``apply``, the
    invariant enforces signature presence.
  - For ``merge`` mode or roles that don't require GPG, it passes
    unconditionally.
  - The invariant inspects CI artifacts for a ``gpg_status`` field.
    It does *not* shell out to ``gpg`` itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invariants import BaseInvariant, InvariantResult

_GPG_ENFORCED_MODES = frozenset({"deploy", "apply"})


class GpgSignatureCheckInvariant(BaseInvariant):
    name = "gpg_signature_check"

    def evaluate(self, ctx: dict[str, Any]) -> InvariantResult:
        mode: str = ctx.get("mode", "merge")
        actor: str = ctx.get("actor", "")
        repo_root: Path = ctx.get("repo_root", Path("."))
        ci: dict[str, Any] = ctx.get("ci_artifacts", {})

        # -- load role mapping --
        role_map_path = repo_root / "docs" / "codex" / "role-mapping.json"
        require_gpg = False

        if role_map_path.is_file():
            try:
                role_map: dict[str, Any] = json.loads(
                    role_map_path.read_text(encoding="utf-8")
                )
                actor_role = role_map.get("actors", {}).get(actor, {})
                require_gpg = bool(actor_role.get("require_gpg", False))

                # Also check global setting
                if role_map.get("global", {}).get("require_gpg_for_deploy"):
                    if mode in _GPG_ENFORCED_MODES:
                        require_gpg = True
            except (json.JSONDecodeError, OSError):
                pass  # treat as "not required" if file is malformed

        # -- skip if not enforced --
        if not require_gpg:
            return InvariantResult(
                name=self.name,
                status="pass",
                details=(
                    f"GPG signing not required for actor={actor!r} "
                    f"mode={mode!r}"
                ),
            )

        if mode not in _GPG_ENFORCED_MODES:
            return InvariantResult(
                name=self.name,
                status="pass",
                details=(
                    f"GPG required for deploy/apply but mode is {mode!r}; "
                    "skipping enforcement"
                ),
            )

        # -- check CI artifacts for GPG status --
        gpg_status = ci.get("gpg_status", {})

        if not gpg_status:
            return InvariantResult(
                name=self.name,
                status="fail",
                details=(
                    "GPG signature required for this action but no "
                    "gpg_status found in CI artifacts"
                ),
                remediation=[
                    "sign the commit with GPG: git commit -S",
                    "ensure CI exports gpg_status in the artifacts JSON",
                ],
            )

        signed = gpg_status.get("signed", False)
        valid = gpg_status.get("valid", False)
        signer = gpg_status.get("signer", "unknown")

        if not signed:
            return InvariantResult(
                name=self.name,
                status="fail",
                details="commit is not GPG-signed",
                remediation=[
                    "sign the commit: git commit -S -m 'your message'",
                    "configure git: git config commit.gpgsign true",
                ],
            )

        if not valid:
            return InvariantResult(
                name=self.name,
                status="fail",
                details=f"GPG signature present but invalid (signer: {signer})",
                remediation=[
                    "ensure your GPG key is trusted by the project keyring",
                    "re-sign the commit with a valid key",
                ],
            )

        return InvariantResult(
            name=self.name,
            status="pass",
            details=f"valid GPG signature from {signer}",
        )
