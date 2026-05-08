from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import Manufacturer, MovementReason, Shade, StockLocation, UnitOfMeasure, User, UserRole
from app.main import app
from app.services.inventory import ReceiveStockInput, receive_stock
from app.services.items import CreateItemInput, create_item


async def _request(path: str) -> tuple[int, dict[str, str], bytes]:
    status_code = 500
    headers: dict[str, str] = {}
    body_chunks: list[bytes] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        nonlocal status_code, headers
        if message["type"] == "http.response.start":
            status_code = int(message["status"])
            headers = {
                key.decode("latin-1"): value.decode("latin-1")
                for key, value in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            body_chunks.append(bytes(message.get("body", b"")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "state": {},
    }

    await app(scope, receive, send)
    return status_code, headers, b"".join(body_chunks)


@pytest.fixture
def admin_api_overrides(bootstrapped_db: Session) -> Iterator[Session]:
    def override_db() -> Iterator[Session]:
        yield bootstrapped_db

    def override_current_user() -> User:
        return User(username="test-admin", password_hash="x", role=UserRole.ADMIN, active=True)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        yield bootstrapped_db
    finally:
        app.dependency_overrides.clear()


def test_docs_endpoint_is_exposed() -> None:
    status_code, headers, body = asyncio.run(_request("/docs"))

    assert status_code == 200
    assert "text/html" in headers["content-type"]
    assert b"Swagger UI" in body


def test_health_endpoint_returns_ok() -> None:
    status_code, _, body = asyncio.run(_request("/api/health"))

    assert status_code == 200
    assert json.loads(body) == {"status": "ok"}


def test_stock_lot_balances_endpoint_returns_data_for_authenticated_user(admin_api_overrides: Session) -> None:
    unit = admin_api_overrides.query(UnitOfMeasure).filter_by(code="pcs").one()
    manufacturer = admin_api_overrides.query(Manufacturer).filter_by(code="GENERIC").one()
    reason = admin_api_overrides.query(MovementReason).filter_by(code="RECEIPT").one()
    location = admin_api_overrides.query(StockLocation).filter_by(code="MAIN").one()
    shade = admin_api_overrides.query(Shade).filter_by(code="A1").one()
    item = create_item(
        admin_api_overrides,
        CreateItemInput(
            sku="API-BAL-LOT-001",
            name="API Lot Balance Item",
            item_type="generic",
            unit_id=unit.id,
            manufacturer_id=manufacturer.id,
        ),
    )
    lot, _ = receive_stock(
        admin_api_overrides,
        ReceiveStockInput(
            item_id=item.id,
            quantity=Decimal("3.000"),
            movement_reason_id=reason.id,
            manufacturer_lot_code="API-LOT-001",
            manufacturer_id=manufacturer.id,
            shade_id=shade.id,
            to_location_id=location.id,
        ),
    )

    status_code, _, body = asyncio.run(_request("/api/stock/balances/lots"))
    payload = json.loads(body)

    assert status_code == 200
    assert {"key_id": lot.id, "qty_on_hand": "3.000"} in payload


def test_stock_item_balances_endpoint_returns_data_for_authenticated_user(admin_api_overrides: Session) -> None:
    unit = admin_api_overrides.query(UnitOfMeasure).filter_by(code="pcs").one()
    reason = admin_api_overrides.query(MovementReason).filter_by(code="RECEIPT").one()
    item = create_item(
        admin_api_overrides,
        CreateItemInput(
            sku="API-BAL-ITEM-001",
            name="API Item Balance Item",
            item_type="generic",
            unit_id=unit.id,
        ),
    )
    receive_stock(
        admin_api_overrides,
        ReceiveStockInput(
            item_id=item.id,
            quantity=Decimal("4.000"),
            movement_reason_id=reason.id,
            manufacturer_lot_code="API-LOT-ITEM-001",
        ),
    )

    status_code, _, body = asyncio.run(_request("/api/stock/balances/items"))
    payload = json.loads(body)

    assert status_code == 200
    assert {"key_id": item.id, "qty_on_hand": "4.000"} in payload
