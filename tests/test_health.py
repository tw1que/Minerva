from app.api.routes.health import health


def test_health_returns_ok() -> None:
    assert health() == {"status": "ok"}
