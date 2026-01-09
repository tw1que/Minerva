# Minerva Inventory Forge

FastAPI + Postgres inventory core with template-driven SKUs, lots, stock movements, and order allocations.
Includes a minimal brutalist UI and Docker dev/prod setups.

## Quick start (dev)

```bash
docker compose -f docker-compose.dev.yml up --build
```

- UI: http://localhost:8000
- API docs: http://localhost:8000/docs

Dev mode auto-creates tables on startup (AUTO_CREATE_DB=true).

## Default login (dev)

- Username: admin
- Password: admin123

Change these via `INITIAL_ADMIN_USERNAME` and `INITIAL_ADMIN_PASSWORD`.

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
- `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`
- `CORS_ORIGINS` as JSON list string

## Notes

### Template specs + SKU rules

Templates now define JSON-driven attribute specs and SKU rules.

Example payload for `POST /templates`:

```json
{
  "name": "Blanks voor freesmachine",
  "attribute_specs": [
    {"key": "diameter", "type": "int", "required": true, "allowed_values": [95, 98]},
    {"key": "thickness", "type": "int", "required": true, "allowed_range": {"min": 10, "max": 30, "step": 1}},
    {"key": "color", "type": "enum", "required": true, "allowed_values": ["A1", "A2", "A3", "B1", "BL"]},
    {
      "key": "type",
      "type": "enum",
      "required": true,
      "allowed_values": ["mono", "multilayer"],
      "normalize": {"lower": true},
      "sku_map": {"mono": "MO", "multilayer": "ML"}
    }
  ],
  "sku_rule": {
    "prefix": "BLK",
    "separator": "-",
    "tokens": ["diameter", "thickness", "color", "type"],
    "version": 1,
    "freeze_existing_skus": true
  }
}
```

Key points:
- `attribute_specs` validates and normalizes attributes (required, enum/range, normalize, sku_map).
- `sku_rule` builds SKU from ordered tokens with the template prefix and separator.
- No property prefixes are added; SKU becomes `BLK-98-20-A2-ML` (or `BLK-98-20-A2` if optional tokens are missing).
