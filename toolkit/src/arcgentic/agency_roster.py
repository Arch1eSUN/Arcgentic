"""Parse agency-agents-style role catalogs into role-family metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]


class AgencyRosterError(ValueError):
    """Raised when a role catalog cannot be parsed."""


@dataclass(frozen=True)
class RoleEntry:
    department: str
    role_name: str
    source_path: str
    upstream_source: str
    specialty: str
    when_to_use: str
    deliverables: tuple[str, ...]
    workflow_phases: tuple[str, ...]
    language: str


def parse_agency_roster(catalog_path: Path) -> list[RoleEntry]:
    """Parse English directory roles or Chinese CATALOG.md role references."""

    if not catalog_path.exists():
        raise AgencyRosterError(f"catalog path not found: {catalog_path}")
    catalog = catalog_path / "CATALOG.md"
    if catalog.exists():
        return _parse_catalog_md(catalog_path, catalog)
    return sorted(
        (_parse_role_file(catalog_path, path) for path in catalog_path.rglob("*.md")),
        key=lambda role: role.source_path,
    )


def select_role_families(
    keywords: tuple[str, ...],
    *,
    available_roles: list[RoleEntry],
) -> tuple[str, ...]:
    """Select arcgentic role families from round keywords and optional catalog roles."""

    selected = ["minimal-change engineer"]
    joined = " ".join(keywords).lower()
    if any(token in joined for token in ("workflow", "release", "architecture", "spec")):
        selected.append("software architect")
    if any(token in joined for token in ("security", "secret", "trust", "external")):
        selected.append("security engineer")
    if any(role.language == "zh" for role in available_roles):
        selected.append("bilingual implementation reviewer")
    return tuple(dict.fromkeys(selected))


def _parse_catalog_md(root: Path, catalog: Path) -> list[RoleEntry]:
    roles: list[RoleEntry] = []
    for line in catalog.read_text(encoding="utf-8").splitlines():
        match = re.search(r"`([^`]+\.md)`", line)
        if not match:
            continue
        role_path = root / match.group(1)
        roles.append(_parse_role_file(root, role_path))
    return roles


def _parse_role_file(root: Path, path: Path) -> RoleEntry:
    if not path.exists():
        raise AgencyRosterError(f"role file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    metadata = _frontmatter(raw)
    rel = path.relative_to(root).as_posix()
    department = str(metadata.get("department") or path.parent.name)
    role_name = str(metadata.get("role_name") or path.stem.replace("-", " ").title())
    deliverables = _string_tuple(metadata.get("deliverables"))
    workflow_phases = _string_tuple(metadata.get("workflow_phases"))
    if not deliverables:
        raise AgencyRosterError(f"role missing deliverables: {rel}")
    return RoleEntry(
        department=department,
        role_name=role_name,
        source_path=rel,
        upstream_source=str(metadata.get("upstream_source") or ""),
        specialty=str(metadata.get("specialty") or ""),
        when_to_use=str(metadata.get("when_to_use") or ""),
        deliverables=deliverables,
        workflow_phases=workflow_phases,
        language=str(metadata.get("language") or _infer_language(raw)),
    )


def _frontmatter(raw: str) -> dict[str, object]:
    if not raw.startswith("---"):
        return {}
    end = raw.find("\n---", 3)
    if end == -1:
        return {}
    loaded = yaml.safe_load(raw[3:end]) or {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, str) and value:
        return (value,)
    return ()


def _infer_language(raw: str) -> str:
    return "zh" if any("\u4e00" <= char <= "\u9fff" for char in raw) else "en"
