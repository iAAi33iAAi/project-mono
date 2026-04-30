# API Reference

Base URL: `http://localhost:8000`

## Endpoints

### `GET /`

Returns a welcome message.

**Response** `200 OK`
```json
{ "message": "Welcome to project-mono" }
```

### `GET /health`

Liveness probe for orchestrators and load balancers.

**Response** `200 OK`
```json
{ "status": "ok" }
```

---

_Add new endpoint docs here as you build them._
