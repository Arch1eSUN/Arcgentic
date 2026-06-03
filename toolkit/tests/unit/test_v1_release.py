from __future__ import annotations

import json
from pathlib import Path

from arcgentic.v1_release import check_v1_release_readiness


def _write_release_surface(root: Path, version: str) -> None:
    (root / ".claude-plugin").mkdir()
    (root / ".codex-plugin").mkdir()
    (root / "toolkit").mkdir()
    for path in [
        root / "plugin.json",
        root / ".claude-plugin/plugin.json",
        root / ".codex-plugin/plugin.json",
    ]:
        path.write_text(json.dumps({"version": version}), encoding="utf-8")
    (root / "toolkit/pyproject.toml").write_text(
        f'[project]\nname = "arcgentic"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text(f"version-v{version}\n", encoding="utf-8")
    (root / "README.zh-CN.md").write_text(f"version-v{version}\n", encoding="utf-8")


def test_v1_release_readiness_passes_when_versions_align(tmp_path: Path) -> None:
    _write_release_surface(tmp_path, "1.0.0-alpha.1")

    result = check_v1_release_readiness(tmp_path, expected_version="1.0.0-alpha.1")

    assert result.ok is True
    assert result.version == "1.0.0-alpha.1"


def test_v1_release_readiness_fails_on_version_drift(tmp_path: Path) -> None:
    _write_release_surface(tmp_path, "1.0.0-alpha.1")
    (tmp_path / ".codex-plugin/plugin.json").write_text(
        json.dumps({"version": "0.2.2-alpha.3"}),
        encoding="utf-8",
    )

    result = check_v1_release_readiness(tmp_path, expected_version="1.0.0-alpha.1")

    assert result.ok is False
    assert any(".codex-plugin/plugin.json" in issue for issue in result.issues)


def test_v1_release_readiness_parses_shields_badge_double_hyphen(tmp_path: Path) -> None:
    _write_release_surface(tmp_path, "0.2.2-alpha.3")
    (tmp_path / "README.md").write_text(
        "[![version](https://img.shields.io/badge/version-v0.2.2--alpha.3-blueviolet.svg)]\n",
        encoding="utf-8",
    )
    (tmp_path / "README.zh-CN.md").write_text(
        "[![version](https://img.shields.io/badge/version-v0.2.2--alpha.3-blueviolet.svg)]\n",
        encoding="utf-8",
    )

    result = check_v1_release_readiness(tmp_path)

    assert result.ok is True
    assert result.version == "0.2.2-alpha.3"


def test_v1_release_readiness_parses_stable_shields_badge(tmp_path: Path) -> None:
    _write_release_surface(tmp_path, "1.0.0")
    (tmp_path / "README.md").write_text(
        "[![version](https://img.shields.io/badge/version-v1.0.0-blueviolet.svg)]\n",
        encoding="utf-8",
    )
    (tmp_path / "README.zh-CN.md").write_text(
        "[![version](https://img.shields.io/badge/version-v1.0.0-blueviolet.svg)]\n",
        encoding="utf-8",
    )

    result = check_v1_release_readiness(tmp_path)

    assert result.ok is True
    assert result.version == "1.0.0"
