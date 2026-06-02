"""Capability registry parser for marketplace-style catalogs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


class CapabilityRegistryError(ValueError):
    """Raised when marketplace capability parsing fails."""


@dataclass(frozen=True)
class Capability:
    name: str
    version: str
    source: str
    strict: bool
    category: str
    description: str
    tags: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityRegistry:
    capabilities: tuple[Capability, ...]

    def to_json(self) -> str:
        return json.dumps(
            {"capabilities": [capability.to_dict() for capability in self.capabilities]},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


def build_registry(catalog_paths: list[Path]) -> CapabilityRegistry:
    """Parse one or more marketplace catalogs and reject duplicate names."""

    capabilities: list[Capability] = []
    seen: set[str] = set()
    for catalog_path in catalog_paths:
        for entry in _load_entries(catalog_path):
            capability = _capability_from_entry(entry, catalog_path)
            if capability.name in seen:
                raise CapabilityRegistryError(f"duplicate capability: {capability.name}")
            seen.add(capability.name)
            capabilities.append(capability)
    return CapabilityRegistry(tuple(capabilities))


def _load_entries(path: Path) -> list[dict[str, object]]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CapabilityRegistryError(f"invalid marketplace JSON: {path}") from exc
    entries = loaded.get("plugins") if isinstance(loaded, dict) else None
    if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
        raise CapabilityRegistryError(f"marketplace catalog must contain plugins list: {path}")
    return entries


def _capability_from_entry(entry: dict[str, object], path: Path) -> Capability:
    name = str(entry.get("name") or "")
    if not name:
        raise CapabilityRegistryError(f"missing plugin name in {path}")
    version = str(entry.get("version") or "")
    source = _normalize_source(entry.get("source"))
    category = str(entry.get("category") or "")
    description = str(entry.get("description") or "")
    tags = _tags(entry, name=name, description=description, category=category)
    return Capability(
        name=name,
        version=version,
        source=source,
        strict=bool(entry.get("strict", False)),
        category=category,
        description=description,
        tags=tags,
    )


def _normalize_source(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        source_type = str(value.get("source") or "unknown")
        if "path" in value:
            return f"{source_type}:{value['path']}"
        if "url" in value:
            return f"{source_type}:{value['url']}"
    return ""


def _tags(
    entry: dict[str, object],
    *,
    name: str,
    description: str,
    category: str,
) -> tuple[str, ...]:
    explicit = entry.get("keywords")
    tags: list[str] = []
    if isinstance(explicit, list):
        tags.extend(str(item).lower() for item in explicit if str(item))
    if category:
        tags.append(category.lower())
    text = f"{name} {description}".lower()
    for token in ("workflow", "memory", "audit", "planning", "skill", "round"):
        if token in text:
            tags.append(token)
    return tuple(dict.fromkeys(tags))
