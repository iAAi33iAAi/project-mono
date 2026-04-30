#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# push-to-github.sh
# Run once after extracting project-mono.tar.gz to push the
# full code tree (including ALGA_FOLD_KERNEL) to GitHub.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Initialising Git repository on branch main"
git init -b main

echo "==> Staging all files"
git add -A

echo "==> Creating initial commit"
git commit -m "feat: initial commit — unified monorepo with ALGA_FOLD_KERNEL

Consolidates code, docs, infra, experiments, and data into a single
clean code tree.

Includes:
- Python backend (FastAPI) with API routes and Pydantic models
- ALGA_FOLD_KERNEL governance runtime (6 invariant modules)
- Append-only Knowledge Ledger (ops/ledger/)
- GitHub Actions CI with kernel merge gate
- Monte-Carlo simulation harness (5 scenarios)
- CODEX role-mapping and kernel documentation
- Optional React/Vite frontend shell
- Docker, Terraform, and Kubernetes skeletons
- CONTRIBUTING guide, CODE_OF_CONDUCT, MIT LICENSE"

echo "==> Adding GitHub remote"
git remote add origin https://github.com/iAAi33iAAi/project-mono.git

echo "==> Pushing to GitHub"
git push -u origin main

echo ""
echo "✓ All code pushed to https://github.com/iAAi33iAAi/project-mono"
echo "  View it: https://github.com/iAAi33iAAi/project-mono"
