# Backend

FastAPI backend for the simulated quantitative trading learning platform.

## Modules

- `app/core`: configuration, security, database.
- `app/models`: SQLAlchemy tables.
- `app/routers`: API endpoints.
- `app/services`: user-facing workflows.
- `app/market_data`: quote provider interface and mock provider.
- `app/simulation`: paper order execution engine.
- `app/strategies`: strategy template registry.
- `app/analytics`: daily/monthly summary extension point.

## API Draft

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | health check |
| `POST` | `/api/auth/register` | register |
| `POST` | `/api/auth/login` | login |
| `GET` | `/api/tasks` | list simulation tasks |
| `POST` | `/api/tasks` | create simulation task |
| `GET` | `/api/tasks/{task_id}` | task detail |
| `POST` | `/api/tasks/{task_id}/control` | start, pause, freeze, resume, add/remove cash, end |
| `GET` | `/api/tasks/{task_id}/assets` | list watched assets |
| `POST` | `/api/tasks/{task_id}/assets` | add watched asset |
| `GET` | `/api/tasks/{task_id}/trades` | list paper trade logs |
| `POST` | `/api/tasks/{task_id}/paper-orders` | manually submit a simulated order |
| `GET` | `/api/strategy-templates` | list strategy templates |
| `GET` | `/api/market-board/assets` | list market board assets |
| `POST` | `/api/market-board/assets` | add a market board asset |
| `POST` | `/api/market-board/refresh` | refresh and persist latest quotes |
| `GET` | `/api/market-board/quotes` | latest quote and recent history for the board |
| `GET` | `/api/market-board/assets/{asset_id}/history` | quote history grouped by intraday/day/week/month |

## Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
copy ..\.env.example .env
uvicorn app.main:app --reload --port 8000
```
