# Architecture overview

## High-level diagram

```
┌───────────┐      ┌───────────┐      ┌───────────┐
│  Frontend │─────▶│  API      │─────▶│  Database │
│  (React)  │ HTTP │  (FastAPI)│  SQL │  (Postgres)│
└───────────┘      └─────┬─────┘      └───────────┘
                         │
                   ┌─────▼─────┐
                   │  Workers  │
                   │  (Celery) │
                   └───────────┘
```

## Layers

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| API | `src/api/` | HTTP routing, request validation, auth |
| Models | `src/models/` | Domain entities, Pydantic schemas |
| Utils | `src/utils/` | Cross-cutting helpers (logging, hashing) |
| Frontend | `frontend/` | React SPA served by Vite |
| Infra | `infra/` | Terraform, K8s manifests |

## Design principles

1. **12-Factor App** — config from env vars, stateless processes, disposable containers.
2. **Separation of concerns** — each layer has a single responsibility.
3. **Test-first** — every module ships with unit tests in `tests/`.
