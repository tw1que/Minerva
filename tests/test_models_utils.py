import hashlib

from app.db.models import canonical_json, compute_attributes_hash


def test_canonical_json_sorted_and_compact() -> None:
    result = canonical_json({"b": 1, "a": 2})
    assert result == '{"a":2,"b":1}'


def test_compute_attributes_hash_uses_canonical_json() -> None:
    attrs = {"b": 1, "a": 2}
    expected = hashlib.sha256('{"a":2,"b":1}'.encode("utf-8")).hexdigest()
    assert compute_attributes_hash(attrs) == expected
