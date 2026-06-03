"""V1 release-readiness checks for version and install surfaces."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class V1ReleaseReadiness:
    ok: bool
    version: str
    issues: tuple[str, ...]


def check_v1_release_readiness(
    repo_root: Path,
    *,
    expected_version: str | None = None,
    local_install_path: Path | None = None,
) -> V1ReleaseReadiness:
    """Verify all V1 release version surfaces align."""

    versions = _read_versions(repo_root)
    target = expected_version or versions.get("plugin.json") or ""
    issues: list[str] = []
    for surface, version in versions.items():
        if version != target:
            issues.append(f"{surface} version {version!r} != {target!r}")
    if local_install_path is not None and local_install_path.exists():
        try:
            installed = local_install_path.resolve()
            root = repo_root.resolve()
        except OSError as exc:
            issues.append(f"local install path resolution failed: {exc}")
        else:
            if installed != root:
                issues.append(f"local install path {installed} does not point to {root}")
    return V1ReleaseReadiness(ok=not issues, version=target, issues=tuple(issues))


def _read_versions(repo_root: Path) -> dict[str, str]:
    surfaces = {
        "plugin.json": _json_version(repo_root / "plugin.json"),
        ".claude-plugin/plugin.json": _json_version(repo_root / ".claude-plugin" / "plugin.json"),
        ".codex-plugin/plugin.json": _json_version(repo_root / ".codex-plugin" / "plugin.json"),
        "toolkit/pyproject.toml": _pyproject_version(repo_root / "toolkit" / "pyproject.toml"),
        "README.md": _readme_version(repo_root / "README.md"),
        "README.zh-CN.md": _readme_version(repo_root / "README.zh-CN.md"),
    }
    return surfaces


def _json_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("version") or "")


def _pyproject_version(path: Path) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    if not isinstance(project, dict):
        return ""
    return str(project.get("version") or "")


def _readme_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    badge_match = re.search(
        r"version-v([0-9]+\.[0-9]+\.[0-9]+)--([A-Za-z0-9.]+)-",
        text,
    )
    if badge_match:
        return f"{badge_match.group(1)}-{badge_match.group(2)}"
    stable_badge_match = re.search(
        r"version-v([0-9]+\.[0-9]+\.[0-9]+)-[A-Za-z0-9]+\.svg",
        text,
    )
    if stable_badge_match:
        return stable_badge_match.group(1)
    match = re.search(r"version-v([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?)", text)
    if match:
        return match.group(1)
    match = re.search(r"v([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?)", text)
    return match.group(1) if match else ""
