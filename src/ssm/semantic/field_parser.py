from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FieldSpec:
    name: str
    raw_type: str
    python_type: str
    required: bool = False
    primary: bool = False
    unique: bool = False
    default: str | None = None
    max_length: int | None = None
    modifiers: tuple[str, ...] = field(default_factory=tuple)


_TYPE_MAP = {
    "string": "str",
    "str": "str",
    "text": "str",
    "int": "int",
    "integer": "int",
    "float": "float",
    "decimal": "float",
    "bool": "bool",
    "boolean": "bool",
    "uuid": "UUID",
    "datetime": "datetime",
    "date": "date",
}


def parse_fields(raw: Any) -> list[FieldSpec]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        items = list(raw.items())
    elif isinstance(raw, list):
        items = []
        for entry in raw:
            if isinstance(entry, str) and ":" in entry:
                k, v = entry.split(":", 1)
                items.append((k.strip(), v.strip()))
            elif isinstance(entry, dict):
                items.extend(entry.items())
            else:
                raise ValueError(f"Invalid field entry: {entry!r}")
    else:
        raise ValueError(f"Invalid fields block: {raw!r}")

    specs: list[FieldSpec] = []
    for name, descriptor in items:
        desc = str(descriptor).strip()
        tokens = desc.split()
        if not tokens:
            raise ValueError(f"Field {name!r} is missing a type")
        raw_type = tokens[0]
        modifiers = tokens[1:]
        lowered_mods = [m.lower() for m in modifiers]
        required = "required" in lowered_mods or "primary" in lowered_mods
        primary = "primary" in lowered_mods
        unique = "unique" in lowered_mods
        default = None
        max_length = None
        for mod in modifiers:
            if mod.startswith("default="):
                default = mod.split("=", 1)[1]
            if mod.startswith("max="):
                max_length = int(mod.split("=", 1)[1])
            if mod.startswith("max_length="):
                max_length = int(mod.split("=", 1)[1])
        specs.append(
            FieldSpec(
                name=str(name),
                raw_type=raw_type,
                python_type=_TYPE_MAP.get(raw_type.lower(), raw_type),
                required=required,
                primary=primary,
                unique=unique,
                default=default,
                max_length=max_length,
                modifiers=tuple(modifiers),
            )
        )
    return specs


def normalize_schema_name(type_name: str) -> str:
    t = str(type_name).strip()
    if t.endswith("[]"):
        t = t[:-2]
    if t.startswith("list[") and t.endswith("]"):
        t = t[5:-1]
    return t


def is_primitive_type(type_name: str) -> bool:
    t = normalize_schema_name(type_name).lower()
    return t in {
        "str",
        "string",
        "text",
        "int",
        "integer",
        "float",
        "decimal",
        "bool",
        "boolean",
        "uuid",
        "datetime",
        "date",
        "dict",
        "object",
        "none",
        "null",
    }


def schema_is_list(type_name: str) -> bool:
    t = str(type_name).strip()
    return t.endswith("[]") or (t.startswith("list[") and t.endswith("]"))
