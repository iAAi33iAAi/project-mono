#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# init-repo.sh — Run once after extracting the project files.
# Creates the Git repo on branch "main" with a single initial commit.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Initialising Git repository on branch main"
git init -b main

echo "==> Staging all files"
git add -A

echo "==> Creating initial commit"
git commit -m "feat: initial commit — unified monorepo scaffold

Consolidates code, docs, infra, experiments, and data into a single
clean code tree.

Includes:
- Python backend (FastAPI) with API routes and Pydantic models
- Optional React/Vite frontend shell
- GitHub Actions CI (lint → test → typecheck)
- Docker and docker-compose configuration
- Terraform skeleton with VPC module placeholder
- Kubernetes deployment manifest
- Experiment notebook directory with conventions
- Sample seed data (JSON + SQL)
- Helper scripts (setup, build, test, deploy)
- Pre-commit hooks (ruff, trailing-whitespace, YAML check)
- CONTRIBUTING guide, CODE_OF_CONDUCT, MIT LICENSE
- Comprehensive .gitignore"

echo ""
echo "✓ Repository initialised with 1 commit on branch main."
echo "  Run 'git log --oneline' to verify."
echo "  Add a remote:  git remote add origin <url>"
echo "  Push:          git push -u origin main"
