# project-mono

A unified monorepo consolidating **code, documentation, infrastructure, experiments, and data** into a single, navigable code tree.

Includes the **ALGA_FOLD_KERNEL** governance runtime — a minimal trusted kernel that mediates every critical change, evaluates pluggable invariants, and records append-only decisions to the Knowledge Ledger.

---

## Repository layout

```
.
├── src/                 # Application source code (Python)
├── invariants/          # ALGA_FOLD_KERNEL invariant modules
├── frontend/            # Optional Node/React frontend
├── tests/               # Pytest test suite
├── docs/                # Project documentation + kernel design
├── infra/               # Infrastructure-as-code
├── experiments/         # Research notebooks & scripts
├── data/                # Sample / seed data (no secrets)
├── scripts/             # Build, test, deploy, kernel runner
├── config/              # App & environment configs
├── ops/                 # Ledger, monitoring, simulations
├── .github/workflows/   # GitHub Actions CI + kernel gate
├── Dockerfile
├── docker-compose.yml
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE              # MIT
└── .gitignore
```

## Quick start

```bash
git clone https://github.com/iAAi33iAAi/project-mono.git
cd project-mono
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

## Running tests

```bash
pytest tests/ -v
```

## ALGA_FOLD_KERNEL

The kernel is the final gate for merges, deploys, and infra applies.


```bash
python scripts/alga_fold_kernel.py --pr 123 --commit abc123 --actor alice --mode merge
```

See [docs/sk-kernel.md](docs/sk-kernel.md) for the full design and extension guide.

## License

MIT — see [LICENSE](LICENSE) for details.

