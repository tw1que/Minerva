from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Item, ItemTemplate, SKUCounter
from app.services.attributes import AttributeSpecConfig, TemplateSpecError, parse_attribute_specs


class SKUGenerationError(ValueError):
    pass


INSTANCE_SEQ_SEPARATOR = "-"
INSTANCE_SEQ_WIDTH = 4


def _lookup_mapping(mapping: dict[str, Any], value: Any) -> str | None:
    if value in mapping:
        return mapping[value]
    value_text = str(value)
    if value_text in mapping:
        return mapping[value_text]
    return None


def _apply_pad(text: str, pad_spec: dict[str, Any] | None, fallback: AttributeSpecConfig | None) -> str:
    width = None
    char = "0"
    if pad_spec:
        if isinstance(pad_spec, int):
            width = pad_spec
        elif isinstance(pad_spec, dict):
            width = pad_spec.get("width")
            char = pad_spec.get("char", "0")
        else:
            raise SKUGenerationError("SKU pad format must be an object or integer.")
    if width is None and fallback and fallback.sku_pad:
        width = fallback.sku_pad.width
        char = fallback.sku_pad.char
    if width is None:
        return text
    if not isinstance(width, int) or width <= 0:
        raise SKUGenerationError("SKU pad width must be a positive integer.")
    if not isinstance(char, str) or len(char) != 1:
        raise SKUGenerationError("SKU pad char must be a single character.")
    return text.rjust(width, char)


def _format_token(
    value: Any,
    spec: AttributeSpecConfig | None,
    token_format: dict[str, Any] | None,
) -> str:
    mapping = None
    if token_format:
        mapping = token_format.get("map") or token_format.get("mapping")
    if not mapping and spec and spec.sku_map:
        mapping = spec.sku_map
    if isinstance(mapping, dict):
        mapped = _lookup_mapping(mapping, value)
        if mapped is not None:
            value = mapped

    text = str(value)
    strip_unit = True
    if token_format and "strip_unit" in token_format:
        strip_unit = bool(token_format.get("strip_unit"))
    if strip_unit and spec and spec.unit and isinstance(value, str):
        text = value.strip()
        if text.lower().endswith(spec.unit.lower()):
            text = text[: -len(spec.unit)].strip()

    pad_spec = token_format.get("pad") if token_format else None
    return _apply_pad(text, pad_spec, spec)


def _validate_template_field_order(template: ItemTemplate) -> None:
    fields = getattr(template, "fields", None)
    if not fields:
        return
    missing_order = [
        field.field_key
        for field in fields
        if field.include_in_sku and field.sku_order is None
    ]
    if missing_order:
        missing_text = ", ".join(sorted(set(missing_order)))
        raise SKUGenerationError(
            "SKU fields missing sku_order: "
            f"{missing_text}."
        )


def _validate_sku_tokens(
    specs: dict[str, AttributeSpecConfig],
    tokens: list[str],
) -> None:
    if not tokens:
        missing_order = [key for key, spec in specs.items() if spec.include_in_sku]
        if missing_order:
            raise SKUGenerationError(
                "SKU rule tokens required to order include_in_sku attributes."
            )
        return

    missing = [key for key, spec in specs.items() if spec.include_in_sku and key not in tokens]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise SKUGenerationError(
            "SKU rule tokens missing include_in_sku attributes: "
            f"{missing_text}."
        )


def build_product_code(template: ItemTemplate, canonical_attrs: dict[str, Any]) -> str:
    """Build a deterministic product code without touching counters."""
    _validate_template_field_order(template)
    sku_rule = template.sku_rule or {}
    if not isinstance(sku_rule, dict):
        raise SKUGenerationError("Invalid sku_rule format.")
    prefix = sku_rule.get("prefix")
    if not prefix:
        raise SKUGenerationError("SKU rule missing prefix.")
    separator = sku_rule.get("separator", "-")
    if not isinstance(separator, str):
        raise SKUGenerationError("SKU rule separator must be a string.")
    tokens = sku_rule.get("tokens") or []
    if not isinstance(tokens, list):
        raise SKUGenerationError("SKU rule tokens must be a list.")

    token_format = sku_rule.get("token_format") or {}
    if token_format and not isinstance(token_format, dict):
        raise SKUGenerationError("SKU rule token_format must be an object.")

    try:
        specs = parse_attribute_specs(template)
    except TemplateSpecError as exc:
        raise SKUGenerationError(str(exc)) from exc

    _validate_sku_tokens(specs, tokens)

    seen_tokens: set[str] = set()
    token_values: list[str] = []
    for token in tokens:
        if not isinstance(token, str):
            raise SKUGenerationError("SKU rule tokens must be strings.")
        if token in seen_tokens:
            raise SKUGenerationError(f"Duplicate SKU token '{token}'.")
        seen_tokens.add(token)
        if token not in specs:
            raise SKUGenerationError(f"Unknown SKU token '{token}'.")
        spec = specs[token]
        if not spec.include_in_sku:
            raise SKUGenerationError(f"SKU token '{token}' is excluded by spec.")
        if token not in canonical_attrs:
            if spec.required:
                raise SKUGenerationError(f"Missing SKU attribute: {token}.")
            continue
        token_format_entry = token_format.get(token) if token_format else None
        if token_format_entry is not None and not isinstance(token_format_entry, dict):
            raise SKUGenerationError(f"Invalid token_format for '{token}'.")
        token_values.append(
            _format_token(canonical_attrs[token], spec, token_format_entry)
        )

    if token_values:
        return separator.join([prefix] + token_values)
    return prefix


def build_instance_sku(product_code: str, seq: int) -> str:
    """Build an instance SKU using a deterministic product code and a seq."""
    if seq <= 0:
        raise SKUGenerationError("Instance seq must be positive.")
    padded = str(seq).rjust(INSTANCE_SEQ_WIDTH, "0")
    return f"{product_code}{INSTANCE_SEQ_SEPARATOR}{padded}"


def assign_instance_seq(db: Session, item: Item) -> int:
    """Assign a sequence only when creating a physical instance to avoid burned numbers."""
    if not db.in_transaction():
        raise SKUGenerationError("assign_instance_seq requires an active transaction.")

    scope_key = f"variant:{item.id}"
    counter_stmt = (
        select(SKUCounter)
        .where(
            SKUCounter.template_id == item.template_id,
            SKUCounter.scope_key == scope_key,
        )
        .with_for_update()
    )

    counter = db.execute(counter_stmt).scalar_one_or_none()
    if counter is None:
        try:
            with db.begin_nested():
                db.add(
                    SKUCounter(
                        template_id=item.template_id,
                        scope_key=scope_key,
                        next_seq=1,
                    )
                )
                db.flush()
        except IntegrityError:
            pass
        counter = db.execute(counter_stmt).scalar_one()

    seq = counter.next_seq
    counter.next_seq = counter.next_seq + 1
    return seq


def generate_sku(template: ItemTemplate, canonical_attrs: dict[str, Any]) -> str:
    """Deprecated: use build_product_code instead."""
    return build_product_code(template, canonical_attrs)
