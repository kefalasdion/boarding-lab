"""Canonical JSON helpers for reproducible public results."""

from __future__ import annotations

import dataclasses
import enum
import json
from typing import Any


def to_primitive(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: to_primitive(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_primitive(item) for item in value]
    if isinstance(value, set):
        return sorted(to_primitive(item) for item in value)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        to_primitive(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json_text(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")
