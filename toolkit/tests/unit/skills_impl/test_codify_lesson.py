from __future__ import annotations

from pathlib import Path

from arcgentic.skills_impl.codify_lesson import run


def test_codify_lesson_promotes_three_occurrences(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    lessons_dir = tmp_path / "lessons"
    amendments_dir = tmp_path / "mandates" / "amendments"
    audit_dir.mkdir()
    for i in range(3):
        (audit_dir / f"R{i + 1}-audit.md").write_text(
            "| F | P2 | reference table missing use mode gate |\n",
            encoding="utf-8",
        )

    result = run(audit_dir=audit_dir, lessons_dir=lessons_dir, amendments_dir=amendments_dir)

    assert result.exit_code == 0
    assert len(result.lessons) == 1
    assert "PROVISIONAL" in result.lessons[0].read_text(encoding="utf-8")


def test_codify_lesson_writes_amendment_at_five_occurrences(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for i in range(5):
        (audit_dir / f"R{i + 1}-audit.md").write_text(
            "| F | P3 | audit evidence missing fixed commit range |\n",
            encoding="utf-8",
        )

    result = run(
        audit_dir=audit_dir,
        lessons_dir=tmp_path / "lessons",
        amendments_dir=tmp_path / "mandates" / "amendments",
    )

    assert len(result.lessons) == 1
    assert len(result.amendments) == 1
    assert "FORMAL" in result.lessons[0].read_text(encoding="utf-8")
