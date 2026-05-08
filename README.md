# Minerva Core

Minerva Core is a backend-only FastAPI + SQLAlchemy + Postgres inventory and traceability service. The codebase is intentionally stripped back to a small relational core:

`items -> typed item details -> lots -> stock_movements -> derived balances -> order_material traceability`

There is no legacy template-driven item creation flow, no frontend runtime, and no mutable stock balance table.

## Core Model

- `items` holds shared item identity and unit/manufacturer links.
- `item_blanks` and `item_ivobase_cartridges` hold typed relational item facts.
- `lots` snapshot item/manufacturer/material/shade values at receipt time.
- `stock_movements` is append-only and is the only stock source of truth.
- `order_materials` snapshots consumption traceability and links to the consuming stock movement.

## API

- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `GET /api/health`
- Auth:
  - `POST /api/auth/login`
  - `GET /api/auth/me`
- Lookups:
  - `GET/POST /api/lookups/manufacturers`
  - `GET/POST /api/lookups/shade-systems`
  - `GET/POST /api/lookups/shades`
  - `GET/POST /api/lookups/material-classes`
  - `GET/POST /api/lookups/units`
  - `GET/POST /api/lookups/stock-locations`
  - `GET/POST /api/lookups/movement-reasons`
- Items:
  - `GET /api/items`
  - `POST /api/items`
  - `GET /api/items/{item_id}`
  - `POST /api/items/blanks`
  - `POST /api/items/ivobase-cartridges`
- Lots:
  - `GET /api/lots`
  - `GET /api/lots/{lot_id}`
- Stock:
  - `POST /api/stock/receive`
  - `POST /api/stock/adjust`
  - `POST /api/stock/consume`
  - `GET /api/stock/movements`
  - `GET /api/stock/balances/lots`
  - `GET /api/stock/balances/items`
- Orders:
  - `GET /api/orders`
  - `POST /api/orders`
  - `GET /api/orders/{order_id}`
  - `GET /api/order-materials`

## Dev Workflow

The schema source of truth is Alembic.

1. Start Postgres:
   - `docker compose -f docker-compose.dev.yml up -d db`
2. Apply schema:
   - `docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head`
3. Run tests:
   - `docker compose -f docker-compose.dev.yml run --rm api pytest -q`
4. Start API:
   - `docker compose -f docker-compose.dev.yml up -d api`

`AUTO_CREATE_DB=false` by default. If you turn it on for throwaway experiments, that is explicitly a non-standard dev shortcut and not the supported schema path.

## Clean DB Reset

This refactor replaces the old migration chain with one clean initial migration. Existing dev databases must be reset:

- `docker compose -f docker-compose.dev.yml down -v`
- `docker compose -f docker-compose.dev.yml up -d db`
- `docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head`

No compatibility migration path is provided for old template or attribute schemas.

## Default Admin

- Username: `admin`
- Password: `admin123`

The startup bootstrap also seeds a minimal lookup set including `disc`, `ZIRCONIA`, `A2`, and movement reasons such as `RECEIPT`, `CONSUME`, and `ADJUST`.
