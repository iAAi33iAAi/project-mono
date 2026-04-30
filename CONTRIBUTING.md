# Contributing to project-mono

Thanks for your interest in contributing! This guide will help you get started.

## Getting started

1. **Fork** the repo and clone your fork locally.
2. Create a feature branch: `git checkout -b feat/your-feature`.
3. Install dependencies: `pip install -r requirements.txt -r requirements-dev.txt`.
4. Make your changes — keep commits small and focused.
5. Run the test suite: `pytest tests/ -v`.
6. Push and open a **Pull Request** against `main`.

## Code style

- Python: follow [PEP 8](https://peps.python.org/pep-0008/). We enforce it with `ruff`.
- Frontend (if applicable): Prettier + ESLint defaults.
- Write docstrings for every public function and class.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add user authentication endpoint
fix: correct off-by-one in pagination
docs: update API reference
chore: bump dependency versions
```

## Pull request checklist

- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Linter passes (`ruff check src/`)
- [ ] New code has docstrings and type hints
- [ ] README or docs updated if behaviour changed

## Reporting issues

Open a GitHub Issue with:
- A clear title
- Steps to reproduce
- Expected vs actual behaviour
- Environment details (OS, Python version)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).
