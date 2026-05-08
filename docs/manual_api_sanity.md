# Manual API Sanity Flow

This flow is backend-only and assumes the local API is available at `http://localhost:8000`.

To run the same flow as a repeatable script after the API is up:

```powershell
python scripts/manual_sanity.py
```

The script defaults to `http://localhost:8000` and `admin` / `admin123`. Override those with `MINERVA_API_URL`, `MINERVA_ADMIN_USERNAME`, and `MINERVA_ADMIN_PASSWORD`.

## Clean start

Run:

```powershell
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d db
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
docker compose -f docker-compose.dev.yml up -d api
```

## Login

Get a bearer token for the bootstrapped admin user:

```powershell
curl.exe -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=admin&password=admin123"
```

Store the returned `access_token` and send it as:

```text
Authorization: Bearer <token>
```

## Confirm lookup rows

Confirm or create:

- unit `disc`
- material class `ZIRCONIA`
- shade `A2`

Reference endpoints:

- `GET /api/lookups/units`
- `POST /api/lookups/units`
- `GET /api/lookups/material-classes`
- `POST /api/lookups/material-classes`
- `GET /api/lookups/shade-systems`
- `GET /api/lookups/shades`
- `POST /api/lookups/shade-systems`
- `POST /api/lookups/shades`

Expected bootstrap defaults:

- unit `disc` already exists
- material class `ZIRCONIA` already exists
- shade system `VITA_CLASSICAL` already exists
- shade `A2` already exists under `VITA_CLASSICAL`

If `A2` is missing, create it with the `shade_system_id` for `VITA_CLASSICAL`.

## Create the blank item

Use `POST /api/items/blanks` with:

```json
{
  "sku": "BLK-98-20-A2",
  "name": "Zirconia blank 98x20 A2",
  "item_type": "blank",
  "unit_id": "<disc_id>",
  "material_class_id": "<zirconia_id>",
  "shade_id": "<a2_id>",
  "diameter_mm": 98,
  "thickness_mm": 20,
  "is_multilayer": false,
  "metadata_json": {}
}
```

Record the returned `item.id`.

## Create the order

Use `POST /api/orders`:

```json
{
  "order_number": "SANITY-ORDER-001",
  "status": "OPEN",
  "notes": "Manual backend sanity flow"
}
```

Record the returned `order.id`.

## Receive stock

Use `POST /api/stock/receive`:

```json
{
  "item_id": "<item_id>",
  "quantity": 10,
  "movement_reason_id": "<receipt_reason_id>",
  "manufacturer_lot_code": "TESTLOT001",
  "lot_code": "TESTLOT001"
}
```

Verify:

- `GET /api/lots` contains the lot
- `GET /api/stock/movements` contains a positive movement for that lot
- `GET /api/stock/balances/lots` shows `qty_on_hand = 10` for that lot

## Consume stock into the order

Use `POST /api/stock/consume`:

```json
{
  "order_id": "<order_id>",
  "item_id": "<item_id>",
  "lot_id": "<lot_id>",
  "quantity": 2,
  "movement_reason_id": "<consume_reason_id>",
  "used_by": "manual-sanity"
}
```

Verify:

- `GET /api/stock/movements` contains a negative movement for the same lot
- `GET /api/order-materials` contains a row linked to the created stock movement
- that `order_materials` row has snapshot values for:
  - `unit_code_snapshot`
  - `item_sku_snapshot`
  - `item_name_snapshot`
  - `lot_code_snapshot`
  - `material_class_code_snapshot`
  - `shade_code_snapshot`
- `GET /api/stock/balances/lots` shows `qty_on_hand = 8` for that lot

## Scripted verification

The repository includes `scripts/manual_sanity.py` to avoid manual JSON inspection after the stack is up. It performs this flow through the live API:

1. login
2. fetch lookup ids
3. create the blank item
4. create the order
5. receive quantity `10`
6. confirm lot exists and lot balance is `10`
7. consume quantity `2`
8. confirm negative movement exists
9. confirm `order_materials` snapshots exist
10. confirm final lot balance is `8`

This keeps the flow fully backend-only and uses only the live API.
