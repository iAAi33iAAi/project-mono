# ALGA_FOLD_KERNEL — Design & Extension Guide

> **AETHEL_MOONUNDER_UNDERSUN** — the immutable hinge between human intent
> and system state.

---

## 1. Purpose

The kernel is the **final gate** for every critical change — merges, infra
applies, and deploys. It evaluates a battery of pluggable invariants against
PR metadata, diffs, and CI artifacts, then records an append-only decision to
the Knowledge Ledger.

### Guarantees

| Property | How it's enforced |
|---|---|
| **Mediation** | CI job `alga-fold-kernel` blocks merge on nonzero exit |
| **Minimal trust surface** | < 2 000 LOC, stdlib + zero runtime deps, pure functions |
| **Auditability** | Every decision → signed JSONL record in `ops/ledger/` |
| **Linkage** | Records reference commit SHA, PR number, actor |
| **Extensibility** | Drop a new `BaseInvariant` subclass in `invariants/` |
| **Fail-safe** | Any invariant failure → deny + remediation plan |

---

## 2. Architecture

```
┌──────────────────────────────────────────────────┐
│  CI  (GitHub Actions)                            │
│   lint → test → typecheck → alga-fold-kernel     │
└──────────────┬───────────────────────────────────┘
               │ exit 0 = approve
               │ exit 1 = deny
               ▼
┌──────────────────────────────────────────────────┐
│  scripts/alga_fold_kernel.py   (kernel runner)   │
│   1. Build evaluation context from CLI args      │
│   2. Load invariants (auto-discovery)            │
│   3. Evaluate each invariant (pure function)     │
│   4. Decide: approve / deny / emergency bypass   │
│   5. Append record → ops/ledger/ (atomic)        │
│   6. Update metrics → ops/monitoring/            │
└──────────────┬───────────────────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ledger_ │ │tests_  │ │no_     │  ... (6 modules)
│presence│ │& types │ │secrets │
└────────┘ └────────┘ └────────┘
```

---

## 3. Invariant modules

Each invariant is a Python class inheriting from `BaseInvariant` with a
single `evaluate(ctx) -> InvariantResult` method.

| Module | File | Enforces |
|---|---|---|
| `ledger_presence` | `invariants/ledger_presence.py` | Critical-path PRs must have a ledger entry or case |
| `tests_and_types` | `invariants/tests_and_types.py` | pytest, ruff, mypy all pass; flakiness below 5 % |
| `no_secrets` | `invariants/no_secrets.py` | No secret patterns or high-entropy strings in diff |
| `infra_plan_check` | `invariants/infra_plan_check.py` | No protected resource deletions or IAM changes without sign-off |
| `graph_anomaly_check` | `invariants/graph_anomaly_check.py` | Anomaly-flagged files require a broken-to-better case |
| `gpg_signature_check` | `invariants/gpg_signature_check.py` | GPG signature required when CODEX mandates it |

### Evaluation context (`ctx`)

The kernel runner builds a `dict` with these keys:

```python
{
    "pr_number": int,
    "commit_sha": str,
    "actor": str,
    "mode": "merge" | "deploy" | "apply",
    "emergency": bool,
    "diff_text": str,
    "changed_files": list[str],
    "ci_artifacts": dict,
    "repo_root": Path,
}
```

### InvariantResult

```python
@dataclass(frozen=True)
class InvariantResult:
    name: str
    status: str          # "pass" | "fail" | "warn" | "error"
    details: str
    remediation: list[str]
```

---

## 4. Decision record schema

Each decision is a single JSON line in `ops/ledger/kernel-decisions.jsonl`:

```json
{
  "decision_id": "uuid4",
  "timestamp": "ISO-8601",
  "actor": "github-username",
  "pr_number": 123,
  "commit_sha": "full-sha",
  "mode": "merge|deploy|apply",
  "emergency": false,
  "invariant_results": {
    "ledger_presence": {"status": "pass", "details": "..."},
    "no_secrets": {"status": "fail", "details": "..."}
  },
  "decision": "deny|approve",
  "reason": "human-readable reason",
  "remediation": ["step 1", "step 2"],
  "elapsed_ms": 42,
  "kernel_version": "alga-fold-kernel v0.1.0",
  "signature": null
}
```

---

## 5. CLI reference

```bash
python scripts/alga_fold_kernel.py \
  --pr 123 \
  --commit abc123 \
  --actor alice \
  --mode merge \
  --diff-file /tmp/pr.diff \
  --ci-artifacts /tmp/ci.json \
  --repo-root . \
  --emergency          # optional: bypass with retrospective mandate
```

| Exit code | Meaning |
|---|---|
| `0` | Approved |
| `1` | Denied (invariant failure) |
| `2` | Internal error |

---

## 6. Emergency bypass

When `--emergency` is set and invariants fail:
- Decision is **approve** (exit 0) but the record is tagged.
- A mandatory retrospective is required within 48 hours.
- The remediation list includes `"file retrospective within 48 hours"`.
- The `emergency_bypasses` counter increments in metrics.

This path exists for genuine production emergencies only. Abuse is
detectable via the ledger and metrics.

---

## 7. Adding a new invariant

1. Create `invariants/my_check.py`:

```python
from invariants import BaseInvariant, InvariantResult

class MyCheckInvariant(BaseInvariant):
    name = "my_check"

    def evaluate(self, ctx):
        # Pure function of ctx — no side effects
        if something_wrong(ctx):
            return InvariantResult(
                name=self.name,
                status="fail",
                details="what went wrong",
                remediation=["how to fix it"],
            )
        return InvariantResult(name=self.name, status="pass", details="ok")
```

2. The loader discovers it automatically — no registration needed.
3. Add tests in `tests/test_kernel.py`.
4. Add simulation scenarios in `ops/simulations/kernel-scenarios/`.

### Safe-coding checklist for invariants

- [ ] Pure function — no I/O beyond reading `ctx` and repo files
- [ ] Deterministic — same inputs always produce same result
- [ ] Handles missing data gracefully (return `warn` or `pass`, not crash)
- [ ] Has unit tests covering pass, fail, and edge cases
- [ ] Remediation list is actionable and specific
- [ ] No external network calls

---

## 8. Simulation harness

```bash
python scripts/simulate_lifecycle.py \
  --scenarios-dir ops/simulations/kernel-scenarios/ \
  --runs 10
```

Each scenario is a JSON file describing a synthetic PR context and the
expected kernel decision. The harness runs each scenario N times and
reports pass/fail.

### Scenario format

```json
{
  "name": "descriptive-name",
  "description": "what this tests",
  "pr_number": 500,
  "commit_sha": "abc123",
  "actor": "dev-alice",
  "mode": "merge",
  "emergency": false,
  "diff_text": "unified diff string",
  "ci_artifacts": { ... },
  "anomalies": [ ... ],
  "role_mapping": { ... },
  "cases": [{"id": "case-1", "meta": {"pr_number": 500}}],
  "expected_decision": "approve|deny"
}
```

---

## 9. CODEX governance integration

The kernel consults `docs/codex/role-mapping.json` to enforce:
- Role-based GPG requirements
- Minimum approver counts for infra and src changes
- Emergency retrospective deadlines

Edit the role-mapping file to onboard new actors and teams.

---

## 10. Observability

| File | Purpose |
|---|---|
| `ops/ledger/kernel-decisions.jsonl` | Append-only decision audit trail |
| `ops/monitoring/kernel-metrics.json` | Counters: decisions, approvals, denials, emergency bypasses, failures by invariant |

### Monitoring recommendations

- Alert on `emergency_bypasses > 0` — ensure retrospective is filed.
- Track `failures_by_invariant` — persistent failures indicate systemic issues.
- Dashboard `total_elapsed_ms / total_decisions` for average kernel latency.

---

## 11. Staged rollout

1. **Phase 1 — Observe**: run kernel in CI but don't block merges
   (change exit code to always 0, still log decisions).
2. **Phase 2 — Staging**: enable blocking on `staging` branch only.
3. **Phase 3 — Production**: enable blocking on `main`.
4. Monitor `kernel-metrics.json` at each phase for false-positive rate.

---

## 12. File inventory

```
invariants/
├── __init__.py              # BaseInvariant, InvariantResult, loader
├── ledger_presence.py       # Ledger/case requirement
├── tests_and_types.py       # CI quality gate
├── no_secrets.py            # Secret scanner
├── infra_plan_check.py      # Terraform safety
├── graph_anomaly_check.py   # Anomaly cross-reference
└── gpg_signature_check.py   # Optional GPG enforcement

scripts/
├── alga_fold_kernel.py      # Kernel runner + CLI
├── ledger_append.py         # Atomic JSONL writer
└── simulate_lifecycle.py    # Monte-Carlo simulation harness

ops/
├── ledger/
│   └── kernel-decisions.jsonl
├── monitoring/
│   └── kernel-metrics.json
├── embeddings/
│   └── anomalies.json
└── simulations/
    └── kernel-scenarios/
        ├── 01-clean-merge.json
        ├── 02-secret-leak.json
        ├── 03-infra-destroy.json
        ├── 04-emergency-bypass.json
        └── 05-anomaly-flagged.json

docs/
├── codex/
│   └── role-mapping.json
└── sk-kernel.md             # This document

tests/
└── test_kernel.py           # 32 tests across 10 classes

.github/workflows/
└── ci.yml                   # Includes alga-fold-kernel job
```
