# Minerva Inventory Forge

FastAPI + Postgres inventory core with template-driven SKUs, lots, and stock movements.
Includes a minimal brutalist UI and Docker dev/prod setups.

## Quick start (dev)

```bash
docker compose -f docker-compose.dev.yml up --build
```

- UI: http://localhost:8000
- API docs: http://localhost:8000/docs

Dev mode auto-creates tables on startup (AUTO_CREATE_DB=true).

## Production

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Run migrations once:

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## Environment

Copy `.env.example` to `.env` and adjust values if needed.

Key variables:
- `DATABASE_URL`
- `APP_ENV` (dev|prod)
- `AUTO_CREATE_DB` (true in dev)
- `DB_CONNECT_RETRIES` and `DB_CONNECT_DELAY` (startup DB wait)
- `CORS_ORIGINS` as JSON list string

## Notes

- SKU generation uses the template `sku_pattern` plus template field placeholders.
- Use `{prefix}` and `{seq:04d}` in patterns, plus any field keys marked `include_in_sku`.
