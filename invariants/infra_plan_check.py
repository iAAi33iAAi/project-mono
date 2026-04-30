"""
Invariant: Infrastructure Plan Check

Parses Terraform / Helm plan output (supplied via CI artifacts) and flags:
  - Resource *deletions* in production workspaces.
  - Unexpected security-group or IAM policy changes.
  - Any destroy count > 0 without explicit Approver sign-off.

The invariant is a pure function of the plan JSON — it never runs
``terraform`` itself.
"""

from __future__ import annotations

from typing import Any

from invariants import BaseInvariant, InvariantResult

# Resource types that require extra scrutiny before deletion
_PROTECTED_RESOURCE_TYPES = frozenset({
    "aws_db_instance",
    "aws_rds_cluster",
    "aws_s3_bucket",
    "aws_iam_role",
    "aws_iam_policy",
    "aws_security_group",
    "aws_vpc",
    "aws_subnet",
    "aws_elasticache_cluster",
    "aws_eks_cluster",
    "aws_lambda_function",
    "google_sql_database_instance",
    "google_compute_network",
    "azurerm_resource_group",
    "azurerm_sql_server",
})


class InfraPlanCheckInvariant(BaseInvariant):
    name = "infra_plan_check"

    def evaluate(self, ctx: dict[str, Any]) -> InvariantResult:
        ci: dict[str, Any] = ctx.get("ci_artifacts", {})
        plan: dict[str, Any] = ci.get("terraform_plan", {})

        # If no plan provided and PR doesn't touch infra, skip
        changed: list[str] = ctx.get("changed_files", [])
        touches_infra = any(f.startswith("infra/") for f in changed)

        if not plan and not touches_infra:
            return InvariantResult(
                name=self.name,
                status="pass",
                details="no infra changes and no terraform plan provided",
            )

        if not plan and touches_infra:
            return InvariantResult(
                name=self.name,
                status="warn",
                details=(
                    "PR touches infra/ but no terraform_plan in CI artifacts; "
                    "cannot verify safety of infrastructure changes"
                ),
                remediation=[
                    "add terraform plan JSON output to CI artifacts",
                    "re-run kernel with --ci-artifacts including terraform_plan",
                ],
            )

        # ── analyse plan ───────────────────────────────────────────────
        resource_changes: list[dict[str, Any]] = plan.get(
            "resource_changes", []
        )
        destroy_count = 0
        protected_deletions: list[str] = []
        all_deletions: list[str] = []
        findings: list[str] = []
        remediation: list[str] = []

        for rc in resource_changes:
            actions: list[str] = rc.get("change", {}).get("actions", [])
            r_type: str = rc.get("type", "unknown")
            r_addr: str = rc.get("address", "unknown")

            if "delete" in actions:
                destroy_count += 1
                all_deletions.append(r_addr)
                if r_type in _PROTECTED_RESOURCE_TYPES:
                    protected_deletions.append(r_addr)

        if protected_deletions:
            findings.append(
                f"protected resource deletions: {', '.join(protected_deletions)}"
            )
            remediation.append(
                "obtain explicit Approver sign-off for protected resource deletions"
            )
            remediation.append(
                "verify deletions are intentional and data has been migrated"
            )

        if destroy_count > 0 and not protected_deletions:
            findings.append(
                f"{destroy_count} resource deletion(s): {', '.join(all_deletions[:5])}"
            )
            remediation.append(
                "confirm resource deletions are intentional"
            )

        # Check for security group / IAM changes (even non-delete)
        security_changes: list[str] = []
        for rc in resource_changes:
            r_type = rc.get("type", "")
            r_addr = rc.get("address", "")
            actions = rc.get("change", {}).get("actions", [])
            if any(kw in r_type for kw in ("iam", "security_group", "firewall")):
                if any(a in actions for a in ("create", "update", "delete")):
                    security_changes.append(f"{r_addr} ({', '.join(actions)})")

        if security_changes:
            findings.append(
                f"security-sensitive changes: {'; '.join(security_changes[:5])}"
            )
            remediation.append(
                "review IAM/security-group changes with security team"
            )

        if findings:
            return InvariantResult(
                name=self.name,
                status="fail",
                details="; ".join(findings),
                remediation=remediation,
            )

        add_count = sum(
            1 for rc in resource_changes
            if "create" in rc.get("change", {}).get("actions", [])
        )
        update_count = sum(
            1 for rc in resource_changes
            if "update" in rc.get("change", {}).get("actions", [])
        )

        return InvariantResult(
            name=self.name,
            status="pass",
            details=(
                f"plan: +{add_count} ~{update_count} -{destroy_count} resources; "
                "no protected deletions or security-sensitive changes"
            ),
        )
