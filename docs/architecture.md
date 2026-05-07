# Minerva Architecture

## Core Rules

- Minerva uses relational typed item tables, not EAV, for operational master data.
- JSONB is allowed only for non-critical metadata, import residue, and vendor extras.
- Templates are configuration for SKU/display/forms only; they are not the source of truth for item facts.
- Stock is an append-only ledger in `stock_movements`.
- Stock balance is derived from the ledger and is never the source of truth.
- Lots and stock movements store denormalized snapshots for audit stability.
- Lookup rows should be treated as append-only or immutable-ish: deactivate or add rows instead of changing semantics in place.

## Item Model

- `items` is the central operational master-data table.
- `item_type`, `sku`, `name`, `manufacturer_id`, and `unit_id` live on `items`.
- Legacy `attributes` and `attribute_hash` remain for migration compatibility only.
- Category-specific facts live in typed tables such as:
  - `item_blanks`
  - `item_ivobase_cartridges`

Templates may still define:
- `sku_pattern`
- `display_pattern`
- `form_config`
- defaults, ordering, and label rendering

Templates must not be treated as the authoritative storage layer for item attributes.

## Traceability Model

- `lots` represent received-material snapshots.
- Each lot stores both FK references and code/name snapshots:
  - item SKU/name
  - manufacturer code
  - material class code
  - shade code
- `order_materials` links an order or case to the consumed lot and stores its own snapshots taken at time of use.

## Inventory Model

- `stock_movements` is immutable and append-only.
- Corrections must be represented by new counter-movements, not updates or deletes.
- `movement_reasons` replaces enum-only reasoning as the long-term source of truth.
- `stock_balance` is a derived projection:

```sql
SELECT lot_id, SUM(qty_delta) AS quantity_on_hand
FROM stock_movements
GROUP BY lot_id;
```

## Current Incremental State

- New relational lookups, typed item tables, lot snapshots, movement snapshots, and order-material snapshots are present.
- Legacy `product_code`, `uom`, `attributes`, `attribute_hash`, and enum `StockReason` compatibility paths still exist where needed.
- New service entry points are:
  - `receive_stock(...)`
  - `consume_stock(...)`
  - `adjust_stock(...)`

## Intentionally Deferred

- stock reservations as a separate inventory root
- waste events as a separate root
- typed nullable foreign keys for every stock movement source
- regulatory class cascade and override logic
- allowed-shade matrices
- lookup versioning via `valid_from` / `valid_to`
- heavy database triggers
