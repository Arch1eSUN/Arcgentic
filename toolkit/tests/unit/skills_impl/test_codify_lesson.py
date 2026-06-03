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
            "\n".join(
                [
                    "## 2. Findings",
                    "",
                    "| Id | Priority | Summary | Evidence |",
                    "|---|---|---|---|",
                    (
                        f"| F-{i} | P2 | reference table missing use mode gate | "
                        "docs/audit.md |"
                    ),
                    "",
                ]
            ),
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
            "\n".join(
                [
                    "## 2. Findings",
                    "",
                    "| Id | Priority | Summary | Evidence |",
                    "|---|---|---|---|",
                    (
                        f"| F-{i} | P3 | audit evidence missing fixed commit range | "
                        "docs/audit.md |"
                    ),
                    "",
                ]
            ),
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


def test_codify_lesson_ignores_r2_style_forward_debt_prose(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    lessons_dir = tmp_path / "lessons"
    amendments_dir = tmp_path / "mandates" / "amendments"
    audit_dir.mkdir()
    for i in range(3):
        (audit_dir / f"R{i + 1}-audit.md").write_text(
            "\n".join(
                [
                    "## 8. Forward-debt observations",
                    "",
                    (
                        "- D-R2-v1-release-hardening-1 (P2): make future self-audit "
                        "state facts stable across audit and closeout transitions by "
                        "checking state_history and fixed dev anchors instead of current "
                        "mutable state/HEAD."
                    ),
                    "",
                    "## 9. Author's note",
                    "",
                    (
                        "The one P2 is about audit fact durability across state and HEAD "
                        "transitions, not product behavior."
                    ),
                    "",
                ]
            ),
            encoding="utf-8",
        )

    result = run(audit_dir=audit_dir, lessons_dir=lessons_dir, amendments_dir=amendments_dir)

    assert result.lessons == []
    assert not list(lessons_dir.glob("*future-fact-audit-state-both*"))
