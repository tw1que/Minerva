from app.core.config import Settings


def test_parse_cors_origins_none() -> None:
    assert Settings._parse_cors_origins(None) == []


def test_parse_cors_origins_csv() -> None:
    value = "https://example.com, https://api.example.com"
    assert Settings._parse_cors_origins(value) == [
        "https://example.com",
        "https://api.example.com",
    ]


def test_parse_cors_origins_json() -> None:
    value = '["https://one.example","https://two.example"]'
    assert Settings._parse_cors_origins(value) == [
        "https://one.example",
        "https://two.example",
    ]
