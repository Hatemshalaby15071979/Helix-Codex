# Helix-Codex Mock Server

A standalone FastAPI mock that mirrors the JSON API surface of the real
`server/` (Helix Codex OS spine) and `helix_codex_app/` (product shell) apps,
so frontend work can proceed **in parallel** with backend development — no
engine, no SQLite stores, no auth pipeline required.

It is generated from the real route definitions (`server/app.py`,
`helix_codex_app/app.py` and their `features/*/router.py` and `modules/*/router.py`
files) and seeded with data shaped exactly like the real Pydantic schemas
(`WorkflowResponse`, `ConversationOut`, `MessageOut`, `NotificationOut`,
`Node.to_dict()`, …).

## Run it standalone

```bash
# from the repo root (pythonpath = ".")
python3 -m mock_server
# -> uvicorn on http://127.0.0.1:8001, scenario=default
```

Environment variables:

| Var               | Default | Meaning                                  |
|-------------------|---------|------------------------------------------|
| `MOCK_PORT`       | `8001`  | Listen port                              |
| `MOCK_SCENARIO`   | `default` | Active scenario at startup             |

Point your frontend's API base URL at `http://127.0.0.1:8001` and you are done.
Auth is **bypassed** — every request is treated as an authenticated demo
account, so no Supabase round-trip or session cookie is needed.

## Scenarios

Switch scenarios without restarting, either via env var at boot or at runtime:

```bash
curl -X POST http://127.0.0.1:8001/__mock/scenario/degraded
curl http://127.0.0.1:8001/__mock/scenario      # current + available
```

| Scenario    | Behaviour                                                                 |
|-------------|---------------------------------------------------------------------------|
| `default`   | Happy path: realistic seeded data, ~20 ms latency, stateful (writes persist). |
| `errors`    | Rate-limits `* ` to 25 req then 429; good for exercising error UI.            |
| `degraded`  | ~1500 ms latency on every response — for loading states / timeout handling.  |
| `readonly`  | Reads work; writes return 202 but are not persisted (deterministic demos).    |

Every response carries `X-Mock-Server: true` and `X-Mock-Scenario: <name>` so
the client can confirm it is hitting the mock.

## Contract endpoints (mirrored)

### Health & control (`server/`)
- `GET  /healthz`            → `{status, profile, version}`
- `GET  /readyz`             → `{ready, checks}`
- `POST /api/workflows`      → 202 (accepted) or 409 (awaiting_approval)
- `GET  /api/workflows`      → list
- `GET  /api/workflows/{id}` → one
- `POST /api/workflows/{id}/execute` / `/result` / `GET .../events`
- `GET  /api/approvals`      → frozen queue
- `POST /api/approvals/{id}` → decide (approved/denied)
- `GET|POST /api/halt/status|engage|release`
- `POST /api/chat/messages`, `GET /api/chat/messages`
- `POST|GET /api/tasks/`, `PUT /api/tasks/{id}/status`
- `POST|GET /api/docs/`, `GET /api/docs/{id}`
- `GET  /api/stream/{correlation_id}` (SSE keep-alive)
- `GET  /metrics`            → Prometheus text

### Product shell (`helix_codex_app/`, all under `/app`)
- `GET  /app/healthz`
- `GET|POST /app/api/tasks`, `GET /app/api/tasks/{id}`,
  `PUT /app/api/tasks/{id}`, `POST /app/api/tasks/{id}/status`,
  `POST /app/api/tasks/{id}/comments`
- `GET|POST /app/api/documents`, `GET /app/api/documents/{id}`,
  `POST /app/api/documents/{id}/blocks`,
  `PUT /app/api/documents/{id}/blocks/{block_id}`
- `GET|POST /app/api/events`, `PUT /app/api/events/{id}`,
  `POST /app/api/events/{id}/respond`, `GET /app/api/oncall`,
  `POST /app/api/oncall/shifts`
- `POST /app/api/attendance/punch`, `GET /app/api/attendance/records|summary`
- `POST /app/api/ops/workflows`, `GET /app/api/ops/workflows/{id}`,
  `POST /app/api/ops/workflows/{id}/approve`, `POST /app/api/ops/demo/wfm`,
  `GET /app/api/ops/audit/{correlation_id}`
- `GET /app/api/cockpit/summary`
- `GET|POST /app/api/conversations`, `GET|POST /app/api/conversations/{id}/messages`,
  `POST /app/api/conversations/{id}/read`, `GET /app/api/conversations/{id}/stream`
- `GET /app/api/notifications`, `POST /app/api/notifications/read-all`,
  `POST /app/api/notifications/{id}/read`, `GET /app/api/notifications/stream`
- `GET /app/api/memory/proposals`, `GET /app/api/memory/proposals/{id}`,
  `POST /app/api/memory/proposals`, `…/evaluate`, `…/approve`,
  `GET /app/api/memory/ledger/verify`, `GET /app/api/memory/promotions`
- `GET /app/api/sections`, `GET /app/api/packs`

> **Not mocked:** HTML/HTMX screen routes (`/app`, `/app/tasks`, `/app/chat`,
> login pages, admin pages, etc.). Those are server-rendered and need the real
> app; the mock only serves the JSON contract the frontend calls.

## Mock control endpoints
- `GET  /__mock/state`      → counts + recent request log
- `POST /__mock/reset`     → re-seed all data
- `GET|POST /__mock/scenario[/<name>]`

## Using from tests

`tests/mock_server/conftest.py` provides `TestClient` fixtures:

```python
def test_tasks_flow(mock_client):
    r = mock_client.post("/app/api/tasks", json={"title": "x"})
    assert r.status_code == 201
    tid = r.json()["task_id"]
    assert mock_client.get(f"/app/api/tasks/{tid}").status_code == 200
```

Available fixtures: `mock_client` (default), `mock_client_errors`,
`mock_client_degraded`. Run the suite with:

```bash
python3 -m pytest tests/mock_server/ -q
```

## Files
- `mock_server/__init__.py` — package export
- `mock_server/server.py`   — FastAPI factory + scenario middleware
- `mock_server/routers.py`  — all mirrored endpoint handlers
- `mock_server/state.py`    — in-memory store, seeded from real schema shapes
- `mock_server/scenarios.py`— scenario definitions
- `mock_server/cli.py`      — `python -m mock_server` entry point
- `tests/mock_server/`      — pytest fixtures + contract tests
