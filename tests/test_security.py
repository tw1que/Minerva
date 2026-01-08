from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = get_password_hash("secret-password")
    assert verify_password("secret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_create_access_token_includes_subject_and_role() -> None:
    token = create_access_token("alice", "ADMIN")
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == "alice"
    assert payload["role"] == "ADMIN"
    assert "exp" in payload
