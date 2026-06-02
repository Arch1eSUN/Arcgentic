from __future__ import annotations

from pathlib import Path

from arcgentic.capability_registry import CapabilityRegistryError, build_registry

FIXTURES = Path(__file__).parents[1] / "fixtures" / "v1" / "marketplace"


def test_parses_superpowers_marketplace_catalog() -> None:
    registry = build_registry([FIXTURES / "superpowers-marketplace.json"])

    assert [capability.name for capability in registry.capabilities] == [
        "superpowers",
        "episodic-memory",
    ]
    assert registry.capabilities[0].strict is True
    assert "workflow" in registry.capabilities[0].tags


def test_parses_codex_marketplace_catalog() -> None:
    registry = build_registry([FIXTURES / "codex-marketplace.json"])

    assert registry.capabilities[0].name == "arcgentic"
    assert registry.capabilities[0].category == "Productivity"
    assert registry.capabilities[0].source == "local:./plugins/arcgentic"


def test_detects_duplicate_capabilities_across_catalogs(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"plugins":[{"name":"superpowers","source":"local","version":"5.0.7"}]}',
        encoding="utf-8",
    )

    try:
        build_registry([FIXTURES / "superpowers-marketplace.json", duplicate])
    except CapabilityRegistryError as exc:
        assert "duplicate capability" in str(exc)
    else:
        raise AssertionError("expected CapabilityRegistryError")
