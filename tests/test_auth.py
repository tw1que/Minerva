from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import User, UserRole
from app.main import app
from app.services.bootstrap import ensure_admin_user


async def _post_form(path: str, data: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    status_code = 500
    headers: dict[str, str] = {}
    body_chunks: list[bytes] = []
    body = urlencode(data).encode("utf-8")

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

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
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
            (b"content-length", str(len(body)).encode("latin-1")),
        ],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "state": {},
    }

    await app(scope, receive, send)
    return status_code, headers, b"".join(body_chunks)


def test_admin_bootstrap_creates_admin_user(db_session: Session) -> None:
    ensure_admin_user()
    db_session.expire_all()

    user = db_session.execute(select(User).where(User.username == "admin")).scalar_one()

    assert user.role == UserRole.ADMIN
    assert user.active is True
    assert user.password_hash.startswith("$2b$")


def test_login_succeeds_with_bootstrapped_admin(db_session: Session) -> None:
    ensure_admin_user()

    with _override_db(db_session):
        status_code, _, body = asyncio.run(
            _post_form("/api/auth/login", {"username": "admin", "password": "admin123"})
        )

    payload = json.loads(body)
    assert status_code == 200
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_fails_with_wrong_password(db_session: Session) -> None:
    ensure_admin_user()

    with _override_db(db_session):
        status_code, _, body = asyncio.run(
            _post_form("/api/auth/login", {"username": "admin", "password": "wrong-password"})
        )

    assert status_code == 401
    assert json.loads(body) == {"detail": "Invalid credentials."}


class _override_db:
    def __init__(self, db: Session) -> None:
        self.db = db

    def __enter__(self) -> None:
        def override() -> Iterator[Session]:
            yield self.db

        app.dependency_overrides[get_db] = override

    def __exit__(self, *exc_info: object) -> None:
        app.dependency_overrides.clear()
