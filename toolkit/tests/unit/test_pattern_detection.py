from __future__ import annotations

from pathlib import Path

from arcgentic.utils.pattern_detection import (
    cluster_patterns,
    promote_to_lesson,
    scan_last_n_rounds,
)


def _audit(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_scan_last_n_rounds_extracts_p2_p3_patterns(tmp_path: Path) -> None:
    audit_dir = tmp_path / "docs" / "audits"
    audit_dir.mkdir(parents=True)
    _audit(
        audit_dir / "R1-external-audit.md",
        "| ID | Priority | Finding |\n|---|---|---|\n| F-1 | P2 | Retry loop missing context |\n",
    )

    occurrences = scan_last_n_rounds(audit_dir, n=10)

    assert len(occurrences) == 1
    assert occurrences[0].priority == "P2"
    assert "Retry loop missing context" in occurrences[0].text


def test_cluster_patterns_groups_repeated_shapes(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    for i in range(3):
        _audit(
            audit_dir / f"R{i + 1}-audit.md",
            f"| F-{i} | P3 | audit fact table missing fixed commit evidence |\n",
        )

    clusters = cluster_patterns(scan_last_n_rounds(audit_dir))

    assert clusters[0].occurrence_count == 3
    assert "audit" in clusters[0].signature


def test_promote_to_lesson_writes_lesson_card(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    lessons_dir = tmp_path / "lessons"
    audit_dir.mkdir()
    for i in range(3):
        _audit(audit_dir / f"R{i + 1}.md", "| F | P2 | source rule handoff missing scope |\n")
    cluster = cluster_patterns(scan_last_n_rounds(audit_dir))[0]

    lesson_path = promote_to_lesson(cluster, lessons_dir)

    content = lesson_path.read_text(encoding="utf-8")
    assert "status: PROVISIONAL" in content
    assert "observed_count: 3" in content
