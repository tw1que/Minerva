from __future__ import annotations

import asyncio
import json

from app.db.models import Item, StockMovement
from app.main import app


async def _get(path: str) -> tuple[int, bytes]:
    status_code = 500
    body_chunks: list[bytes] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = int(message["status"])
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
    return status_code, b"".join(body_chunks)


def test_app_imports() -> None:
    assert app.title == "Minerva Core"


def test_health_endpoint_returns_ok() -> None:
    status_code, body = asyncio.run(_get("/api/health"))

    assert status_code == 200
    assert json.loads(body) == {"status": "ok"}


def test_item_model_has_no_legacy_attribute_columns() -> None:
    assert "attributes" not in Item.__table__.c
    assert "attribute_hash" not in Item.__table__.c


def test_stock_movement_model_has_no_legacy_reason_column() -> None:
    assert "reason" not in StockMovement.__table__.c


def test_legacy_routes_are_not_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/templates" not in paths
    assert "/api/catalog/items" not in paths
    assert "/api/inventory/summary" not in paths
