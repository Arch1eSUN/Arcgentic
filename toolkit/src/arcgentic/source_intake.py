"""Source-intake records for external workflow references."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]

SourceKind = Literal["repo", "marketplace", "openspec", "doc"]


class SourceIntakeError(ValueError):
    """Raised when source records fail validation."""


@dataclass(frozen=True)
class SourceRecord:
    id: str
    kind: SourceKind
    origin: str
    retrieved_at: str
    revision: str
    license: str
    used_parts: tuple[str, ...]
    excluded_parts: tuple[str, ...]
    rt_tier: str


_KINDS = {"repo", "marketplace", "openspec", "doc"}
_RT_TIERS = {"RT0", "RT1", "RT2", "RT3"}


def load_source_records(paths: list[Path]) -> list[SourceRecord]:
    """Load and validate one or more YAML source-record files."""

    records: list[SourceRecord] = []
    seen: set[str] = set()
    for path in paths:
        for item in _load_yaml_items(path):
            record = _record_from_mapping(item, path)
            if record.id in seen:
                raise SourceIntakeError(f"duplicate source id: {record.id}")
            seen.add(record.id)
            records.append(record)
    return records


def _load_yaml_items(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise SourceIntakeError(f"source record file not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return [loaded]
    if isinstance(loaded, list) and all(isinstance(item, dict) for item in loaded):
        return loaded
    raise SourceIntakeError(f"source record file must contain a mapping or list: {path}")


def _record_from_mapping(data: dict[str, object], path: Path) -> SourceRecord:
    required = (
        "id",
        "kind",
        "origin",
        "retrieved_at",
        "revision",
        "license",
        "used_parts",
        "excluded_parts",
        "rt_tier",
    )
    missing = [key for key in required if key not in data or data[key] in ("", None)]
    if missing:
        raise SourceIntakeError(f"missing required source fields in {path}: {', '.join(missing)}")
    kind = str(data["kind"])
    if kind not in _KINDS:
        raise SourceIntakeError(f"unsupported source kind: {kind}")
    rt_tier = str(data["rt_tier"])
    if rt_tier not in _RT_TIERS:
        raise SourceIntakeError(f"unsupported rt_tier: {rt_tier}")
    used_parts = _list_of_strings(data["used_parts"], "used_parts")
    excluded_parts = _list_of_strings(data["excluded_parts"], "excluded_parts")
    return SourceRecord(
        id=str(data["id"]),
        kind=kind,  # type: ignore[arg-type]
        origin=str(data["origin"]),
        retrieved_at=str(data["retrieved_at"]),
        revision=str(data["revision"]),
        license=str(data["license"]),
        used_parts=used_parts,
        excluded_parts=excluded_parts,
        rt_tier=rt_tier,
    )


def _list_of_strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SourceIntakeError(f"{field} must be a list of strings")
    return tuple(value)
