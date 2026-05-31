from __future__ import annotations

from pathlib import Path

from arcgentic.hooks.round_boundary_lesson_scan import run


def test_round_boundary_lesson_scan_promotes_repeated_pattern(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for i in range(3):
        (audit_dir / f"R{i + 1}.md").write_text(
            "| F | P2 | handoff required field missing stop condition |\n",
            encoding="utf-8",
        )

    result = run(
        audit_dir=audit_dir,
        lessons_dir=tmp_path / "lessons",
        amendments_dir=tmp_path / "mandates" / "amendments",
    )

    assert result.promotable_clusters == 1
    assert result.lesson_count == 1


def test_round_boundary_lesson_scan_dry_run_does_not_write(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    lessons_dir = tmp_path / "lessons"
    audit_dir.mkdir()
    for i in range(3):
        (audit_dir / f"R{i + 1}.md").write_text(
            "| F | P3 | reference classification missing license evidence |\n",
            encoding="utf-8",
        )

    result = run(
        audit_dir=audit_dir,
        lessons_dir=lessons_dir,
        amendments_dir=tmp_path / "mandates" / "amendments",
        dry_run=True,
    )

    assert result.promotable_clusters == 1
    assert result.lesson_count == 0
    assert not lessons_dir.exists()

