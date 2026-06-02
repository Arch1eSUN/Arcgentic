from __future__ import annotations

from pathlib import Path

from arcgentic.source_intake import SourceIntakeError, load_source_records

FIXTURES = Path(__file__).parents[1] / "fixtures" / "v1"


def test_loads_repo_marketplace_and_openspec_source_records() -> None:
    records = load_source_records([FIXTURES / "source-records.yaml"])

    assert [record.id for record in records] == ["superpowers-marketplace", "awesome-openspec"]
    assert records[0].kind == "marketplace"
    assert records[1].rt_tier == "RT0"


def test_rejects_duplicate_source_record_ids(tmp_path: Path) -> None:
    duplicate = tmp_path / "sources.yaml"
    duplicate.write_text(
        """
- id: same
  kind: repo
  origin: https://example.com/a
  retrieved_at: "2026-06-02T00:00:00Z"
  revision: abc
  license: MIT
  used_parts: [README]
  excluded_parts: []
  rt_tier: RT0
- id: same
  kind: doc
  origin: docs/local.md
  retrieved_at: "2026-06-02T00:00:00Z"
  revision: local
  license: project-owned
  used_parts: [all]
  excluded_parts: []
  rt_tier: RT3
""",
        encoding="utf-8",
    )

    try:
        load_source_records([duplicate])
    except SourceIntakeError as exc:
        assert "duplicate source id" in str(exc)
    else:
        raise AssertionError("expected SourceIntakeError")
