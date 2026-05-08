from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("MINERVA_API_URL", "http://localhost:8000").rstrip("/")
USERNAME = os.environ.get("MINERVA_ADMIN_USERNAME", "admin")
PASSWORD = os.environ.get("MINERVA_ADMIN_PASSWORD", "admin123")

ITEM_SKU = "BLK-98-20-A2"
ORDER_NUMBER = "SANITY-ORDER-001"
LOT_CODE = "TESTLOT001"


class SanityFailure(RuntimeError):
    pass


@dataclass
class ApiError(RuntimeError):
    status: int
    body: str

    def __str__(self) -> str:
        return f"HTTP {self.status}: {self.body}"


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.token: str | None = None

    def login(self, username: str, password: str) -> None:
        body = urlencode({"username": username, "password": password}).encode()
        payload = self._request(
            "POST",
            "/api/auth/login",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=False,
        )
        self.token = require_field(payload, "access_token")

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, data=json.dumps(payload).encode())

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        auth: bool = True,
    ) -> Any:
        request_headers = {"Accept": "application/json"}
        if data is not None and "Content-Type" not in (headers or {}):
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        if auth:
            if not self.token:
                raise SanityFailure("API token is missing.")
            request_headers["Authorization"] = f"Bearer {self.token}"

        request = Request(f"{self.base_url}{path}", data=data, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=10) as response:
                response_body = response.read()
        except HTTPError as exc:
            raise ApiError(exc.code, exc.read().decode("utf-8", errors="replace")) from exc
        except URLError as exc:
            raise SanityFailure(f"Could not reach API at {self.base_url}: {exc.reason}") from exc
        except OSError as exc:
            raise SanityFailure(f"Could not reach API at {self.base_url}: {exc}") from exc

        if not response_body:
            return None
        return json.loads(response_body)


def main() -> int:
    client = ApiClient(BASE_URL)
    try:
        run_flow(client)
    except Exception as exc:
        print(f"FAIL {exc}")
        return 1

    print("PASS manual API sanity flow completed")
    return 0


def run_flow(client: ApiClient) -> None:
    step("login", lambda: client.login(USERNAME, PASSWORD))

    unit = step("fetch unit disc", lambda: get_by_code(client, "/api/lookups/units", "disc"))
    material_class = step(
        "fetch material class ZIRCONIA",
        lambda: get_by_code(client, "/api/lookups/material-classes", "ZIRCONIA"),
    )
    shade = step("fetch shade A2", lambda: get_by_code(client, "/api/lookups/shades", "A2"))
    receipt_reason = step(
        "fetch movement reason RECEIPT",
        lambda: get_by_code(client, "/api/lookups/movement-reasons", "RECEIPT"),
    )
    consume_reason = step(
        "fetch movement reason CONSUME",
        lambda: get_by_code(client, "/api/lookups/movement-reasons", "CONSUME"),
    )

    item = step(
        "create blank item BLK-98-20-A2",
        lambda: create_or_get_by_field(
            client,
            create_path="/api/items/blanks",
            list_path="/api/items",
            field="sku",
            value=ITEM_SKU,
            payload={
                "sku": ITEM_SKU,
                "name": "Zirconia blank 98x20 A2",
                "item_type": "blank",
                "unit_id": unit["id"],
                "material_class_id": material_class["id"],
                "shade_id": shade["id"],
                "diameter_mm": "98",
                "thickness_mm": "20",
                "is_multilayer": False,
                "metadata_json": {},
            },
        ),
    )
    require_equal(item["item_type"], "blank", "sanity item type")

    order = step(
        "create order SANITY-ORDER-001",
        lambda: create_or_get_by_field(
            client,
            create_path="/api/orders",
            list_path="/api/orders",
            field="order_number",
            value=ORDER_NUMBER,
            payload={
                "order_number": ORDER_NUMBER,
                "status": "OPEN",
                "notes": "Manual backend sanity flow",
            },
        ),
    )

    lot = find_lot(client, item["id"], LOT_CODE)
    should_consume = True
    if lot is None:
        step(
            "receive stock quantity 10",
            lambda: client.post(
                "/api/stock/receive",
                {
                    "item_id": item["id"],
                    "quantity": "10",
                    "movement_reason_id": receipt_reason["id"],
                    "manufacturer_lot_code": LOT_CODE,
                    "lot_code": LOT_CODE,
                },
            ),
        )
        lot = step("verify lot exists", lambda: require_lot(client, item["id"], LOT_CODE))
        step("verify lot balance = 10", lambda: require_equal(get_lot_balance(client, lot["id"]), Decimal("10"), "lot balance after receipt"))
    else:
        print("PASS receive stock quantity 10 (existing sanity lot found)")
        existing_balance = get_lot_balance(client, lot["id"])
        if existing_balance == Decimal("10"):
            print("PASS verify lot balance = 10")
        elif existing_balance == Decimal("8"):
            print("PASS verify final lot balance = 8 (existing completed sanity flow found)")
            should_consume = False
        else:
            raise SanityFailure(f"expected existing lot balance 10 or 8, got {existing_balance}")

    if should_consume:
        consume_movement = step(
            "consume quantity 2 into the order",
            lambda: client.post(
                "/api/stock/consume",
                {
                    "order_id": order["id"],
                    "item_id": item["id"],
                    "lot_id": lot["id"],
                    "quantity": "2",
                    "movement_reason_id": consume_reason["id"],
                    "used_by": "manual-sanity",
                },
            ),
        )
        require_equal(decimal_value(consume_movement["qty_delta"]), Decimal("-2"), "consume movement qty_delta")
    else:
        print("PASS consume quantity 2 into the order (already completed)")

    order_material = step(
        "verify order_material exists with snapshots",
        lambda: require_order_material(client, order["id"], item["id"], lot["id"]),
    )
    verify_snapshots(order_material)

    final_balance = step("verify final lot balance = 8", lambda: get_lot_balance(client, lot["id"]))
    require_equal(final_balance, Decimal("8"), "final lot balance")


def step(label: str, action):
    try:
        result = action()
    except Exception as exc:
        print(f"FAIL {label}: {exc}")
        raise
    print(f"PASS {label}")
    return result


def get_by_code(client: ApiClient, path: str, code: str) -> dict[str, Any]:
    for row in client.get(path):
        if row.get("code") == code:
            return row
    raise SanityFailure(f"{path} did not contain code {code!r}")


def create_or_get_by_field(
    client: ApiClient,
    create_path: str,
    list_path: str,
    field: str,
    value: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing = find_by_field(client, list_path, field, value)
    if existing is not None:
        return existing

    try:
        return client.post(create_path, payload)
    except ApiError as exc:
        if exc.status != 400:
            raise

    existing = find_by_field(client, list_path, field, value)
    if existing is None:
        raise SanityFailure(f"{create_path} returned duplicate-style error, but {value!r} was not found")
    return existing


def find_by_field(client: ApiClient, path: str, field: str, value: str) -> dict[str, Any] | None:
    for row in client.get(path):
        if row.get(field) == value:
            return row
    return None


def find_lot(client: ApiClient, item_id: int, lot_code: str) -> dict[str, Any] | None:
    for lot in client.get("/api/lots"):
        if lot.get("item_id") == item_id and lot.get("lot_code") == lot_code:
            return lot
    return None


def require_lot(client: ApiClient, item_id: int, lot_code: str) -> dict[str, Any]:
    lot = find_lot(client, item_id, lot_code)
    if lot is None:
        raise SanityFailure(f"lot {lot_code!r} was not found for item id {item_id}")
    return lot


def get_lot_balance(client: ApiClient, lot_id: int) -> Decimal:
    for row in client.get("/api/stock/balances/lots"):
        if row.get("key_id") == lot_id:
            return decimal_value(row["qty_on_hand"])
    raise SanityFailure(f"lot balance was not found for lot id {lot_id}")


def require_order_material(client: ApiClient, order_id: int, item_id: int, lot_id: int) -> dict[str, Any]:
    matches = [
        row
        for row in client.get("/api/order-materials")
        if row.get("order_id") == order_id and row.get("item_id") == item_id and row.get("lot_id") == lot_id
    ]
    if not matches:
        raise SanityFailure("order material row was not found")
    return matches[-1]


def verify_snapshots(order_material: dict[str, Any]) -> None:
    expected = {
        "unit_code_snapshot": "disc",
        "item_sku_snapshot": ITEM_SKU,
        "item_name_snapshot": "Zirconia blank 98x20 A2",
        "lot_code_snapshot": LOT_CODE,
        "material_class_code_snapshot": "ZIRCONIA",
        "shade_code_snapshot": "A2",
    }
    for field, value in expected.items():
        require_equal(order_material.get(field), value, field)


def require_field(payload: dict[str, Any], field: str) -> Any:
    value = payload.get(field)
    if value is None:
        raise SanityFailure(f"response did not include {field!r}")
    return value


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise SanityFailure(f"{label}: expected {expected!r}, got {actual!r}")


def decimal_value(value: Any) -> Decimal:
    return Decimal(str(value))


if __name__ == "__main__":
    sys.exit(main())
