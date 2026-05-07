from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.db.models import AttributeType, ItemTemplate


class AttributeValidationError(ValueError):
    pass


class TemplateSpecError(ValueError):
    pass


@dataclass(frozen=True)
class RangeSpec:
    min: Decimal | None
    max: Decimal | None
    step: Decimal | None


@dataclass(frozen=True)
class PadSpec:
    width: int
    char: str


@dataclass(frozen=True)
class AttributeSpecConfig:
    key: str
    type: AttributeType
    required: bool
    allowed_values: list[Any] | None
    allowed_range: RangeSpec | None
    unit: str | None
    normalize: dict[str, Any]
    sku_pad: PadSpec | None
    sku_map: dict[str, str] | None
    include_in_identity: bool
    include_in_sku: bool


def _normalize_flags(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, (list, tuple, set)):
        return {str(item).strip().lower(): True for item in raw}
    if isinstance(raw, str):
        return {part.strip().lower(): True for part in raw.split(",") if part.strip()}
    raise TemplateSpecError("Invalid normalize config; expected dict, list, or string.")


def _coerce_attr_type(raw: Any) -> AttributeType:
    if isinstance(raw, AttributeType):
        return raw
    if isinstance(raw, str):
        try:
            return AttributeType(raw.lower())
        except ValueError as exc:
            raise TemplateSpecError(f"Unknown attribute type '{raw}'.") from exc
    raise TemplateSpecError("Attribute type must be a string or AttributeType.")


def _parse_pad_spec(raw: Any, key: str) -> PadSpec | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        if raw <= 0:
            raise TemplateSpecError(f"sku_pad width must be > 0 for '{key}'.")
        return PadSpec(width=raw, char="0")
    if isinstance(raw, dict):
        width = raw.get("width")
        char = raw.get("char", "0")
        if not isinstance(width, int) or width <= 0:
            raise TemplateSpecError(f"sku_pad width must be > 0 for '{key}'.")
        if not isinstance(char, str) or len(char) != 1:
            raise TemplateSpecError(f"sku_pad char must be a single character for '{key}'.")
        return PadSpec(width=width, char=char)
    raise TemplateSpecError(f"Invalid sku_pad for '{key}'.")


def _parse_decimal_spec(value: Any, field_key: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TemplateSpecError(f"Invalid numeric spec for '{field_key}'.") from exc


def _parse_range(raw: Any, field_key: str) -> RangeSpec | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TemplateSpecError(f"allowed_range must be an object for '{field_key}'.")
    min_val = raw.get("min")
    max_val = raw.get("max")
    step_val = raw.get("step")

    min_dec = _parse_decimal_spec(min_val, field_key) if min_val is not None else None
    max_dec = _parse_decimal_spec(max_val, field_key) if max_val is not None else None
    step_dec = _parse_decimal_spec(step_val, field_key) if step_val is not None else None

    if min_dec is not None and max_dec is not None and min_dec > max_dec:
        raise TemplateSpecError(f"allowed_range min > max for '{field_key}'.")
    if step_dec is not None and step_dec <= 0:
        raise TemplateSpecError(f"allowed_range step must be > 0 for '{field_key}'.")

    return RangeSpec(min=min_dec, max=max_dec, step=step_dec)


def parse_attribute_specs(template: ItemTemplate) -> dict[str, AttributeSpecConfig]:
    specs_raw = template.attribute_specs or []
    if not isinstance(specs_raw, list):
        raise TemplateSpecError("attribute_specs must be a list.")

    specs: dict[str, AttributeSpecConfig] = {}
    for spec in specs_raw:
        if not isinstance(spec, dict):
            raise TemplateSpecError("Each attribute spec must be an object.")
        key = spec.get("key")
        if not key or not isinstance(key, str):
            raise TemplateSpecError("Each attribute spec requires a string 'key'.")
        if key in specs:
            raise TemplateSpecError(f"Duplicate attribute spec key '{key}'.")

        attr_type = _coerce_attr_type(spec.get("type"))
        required = bool(spec.get("required", False))
        allowed_values = spec.get("allowed_values")
        if allowed_values is not None and not isinstance(allowed_values, list):
            raise TemplateSpecError(f"allowed_values must be a list for '{key}'.")
        allowed_range = spec.get("allowed_range")
        if allowed_values is not None and allowed_range is not None:
            raise TemplateSpecError(f"Provide only allowed_values or allowed_range for '{key}'.")
        if attr_type == AttributeType.ENUM and not allowed_values:
            raise TemplateSpecError(f"Enum attribute '{key}' requires allowed_values.")

        range_spec = _parse_range(allowed_range, key)
        if range_spec and attr_type not in (AttributeType.INT, AttributeType.DECIMAL):
            raise TemplateSpecError(f"allowed_range only applies to numeric types for '{key}'.")

        unit = spec.get("unit")
        normalize = _normalize_flags(spec.get("normalize"))
        sku_pad = _parse_pad_spec(spec.get("sku_pad"), key)
        sku_map = spec.get("sku_map")
        if sku_map is not None and not isinstance(sku_map, dict):
            raise TemplateSpecError(f"sku_map must be an object for '{key}'.")
        include_in_identity = bool(spec.get("include_in_identity", True))
        include_in_sku = bool(spec.get("include_in_sku", True))

        specs[key] = AttributeSpecConfig(
            key=key,
            type=attr_type,
            required=required,
            allowed_values=allowed_values,
            allowed_range=range_spec,
            unit=unit,
            normalize=normalize,
            sku_pad=sku_pad,
            sku_map=sku_map,
            include_in_identity=include_in_identity,
            include_in_sku=include_in_sku,
        )
    return specs


def _strip_unit(text: str, unit: str) -> str:
    pattern = rf"\s*{re.escape(unit)}\s*$"
    return re.sub(pattern, "", text, flags=re.IGNORECASE)


def _parse_decimal_value(value: Any, field_key: str, unit: str | None) -> Decimal:
    if isinstance(value, bool):
        raise AttributeValidationError(f"Invalid numeric value for '{field_key}'.")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip()
        if unit:
            text = _strip_unit(text, unit)
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise AttributeValidationError(f"Invalid numeric value for '{field_key}'.") from exc
    raise AttributeValidationError(f"Invalid numeric value for '{field_key}'.")


def _decimal_to_str(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _coerce_bool(value: Any, field_key: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise AttributeValidationError(f"Invalid boolean value for '{field_key}'.")
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in {"true", "1", "yes", "y"}:
            return True
        if candidate in {"false", "0", "no", "n"}:
            return False
    raise AttributeValidationError(f"Invalid boolean value for '{field_key}'.")


def _apply_string_normalization(text: str, normalize: dict[str, Any]) -> str:
    value = text
    if normalize.get("strip"):
        value = value.strip()
    if normalize.get("lower"):
        value = value.lower()
    return value


def _validate_range(value: Decimal, spec: RangeSpec, field_key: str) -> None:
    if spec.min is not None and value < spec.min:
        raise AttributeValidationError(f"Value for '{field_key}' is below minimum.")
    if spec.max is not None and value > spec.max:
        raise AttributeValidationError(f"Value for '{field_key}' is above maximum.")
    if spec.step is not None:
        base = spec.min or Decimal(0)
        remainder = (value - base) % spec.step
        if remainder != 0:
            raise AttributeValidationError(f"Value for '{field_key}' does not match step.")


def _validate_allowed_values(spec: AttributeSpecConfig, value: Any) -> None:
    if spec.allowed_values is None:
        return
    if spec.type in (AttributeType.STRING, AttributeType.ENUM):
        allowed = {str(item) for item in spec.allowed_values}
        if value not in allowed:
            raise AttributeValidationError(f"Value '{value}' not allowed for '{spec.key}'.")
        return
    if spec.type == AttributeType.BOOL:
        allowed = {_coerce_bool(item, spec.key) for item in spec.allowed_values}
        if value not in allowed:
            raise AttributeValidationError(f"Value '{value}' not allowed for '{spec.key}'.")
        return
    if spec.type == AttributeType.INT:
        allowed = {_parse_decimal_value(item, spec.key, spec.unit) for item in spec.allowed_values}
        allowed_ints = {int(val) for val in allowed if val == val.to_integral_value()}
        if value not in allowed_ints:
            raise AttributeValidationError(f"Value '{value}' not allowed for '{spec.key}'.")
        return
    if spec.type == AttributeType.DECIMAL:
        allowed = {_decimal_to_str(_parse_decimal_value(item, spec.key, spec.unit)) for item in spec.allowed_values}
        if value not in allowed:
            raise AttributeValidationError(f"Value '{value}' not allowed for '{spec.key}'.")


def validate_and_normalize_attributes(template: ItemTemplate, attrs_in: dict[str, Any]) -> dict[str, Any]:
    specs = parse_attribute_specs(template)
    input_keys = set(attrs_in.keys())
    unknown = input_keys - set(specs.keys())
    if unknown:
        raise AttributeValidationError(f"Unknown attributes: {', '.join(sorted(unknown))}.")

    normalized: dict[str, Any] = {}
    for key, spec in specs.items():
        if spec.required and key not in attrs_in:
            raise AttributeValidationError(f"Missing required attribute: {key}.")
        if key not in attrs_in:
            continue
        raw = attrs_in[key]
        if raw is None:
            if spec.required:
                raise AttributeValidationError(f"Missing required attribute: {key}.")
            continue

        if spec.type == AttributeType.STRING:
            value = _apply_string_normalization(str(raw), spec.normalize)
            _validate_allowed_values(spec, value)
            normalized[key] = value
            continue
        if spec.type == AttributeType.ENUM:
            value = _apply_string_normalization(str(raw), spec.normalize)
            enum_map = spec.normalize.get("enum_map") or spec.normalize.get("map")
            if isinstance(enum_map, dict):
                mapped = enum_map.get(value)
                if mapped is None:
                    mapped = enum_map.get(str(value))
                if mapped is not None:
                    value = str(mapped)
            _validate_allowed_values(spec, value)
            normalized[key] = value
            continue
        if spec.type == AttributeType.INT:
            dec_value = _parse_decimal_value(raw, key, spec.unit)
            if dec_value != dec_value.to_integral_value():
                raise AttributeValidationError(f"Value for '{key}' must be an integer.")
            if spec.allowed_range:
                _validate_range(dec_value, spec.allowed_range, key)
            value = int(dec_value)
            _validate_allowed_values(spec, value)
            normalized[key] = value
            continue
        if spec.type == AttributeType.DECIMAL:
            dec_value = _parse_decimal_value(raw, key, spec.unit)
            if spec.allowed_range:
                _validate_range(dec_value, spec.allowed_range, key)
            value = _decimal_to_str(dec_value)
            _validate_allowed_values(spec, value)
            normalized[key] = value
            continue
        if spec.type == AttributeType.BOOL:
            value = _coerce_bool(raw, key)
            _validate_allowed_values(spec, value)
            normalized[key] = value
            continue

        raise AttributeValidationError(f"Unsupported attribute type for '{key}'.")

    return dict(sorted(normalized.items()))


def compute_attribute_hash(template: ItemTemplate, canonical_attrs: dict[str, Any]) -> str:
    specs = parse_attribute_specs(template)
    identity = {
        key: canonical_attrs[key]
        for key, spec in specs.items()
        if spec.include_in_identity and key in canonical_attrs
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
