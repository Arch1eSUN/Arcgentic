from __future__ import annotations

from pathlib import Path

import pytest

from arcgentic.skills_impl.track_refs import (
    UnclassifiableReference,
    append_to_index,
    build_reference_entry,
    classify_reference,
    detect_category_tags,
    emit_triplet_table,
    refresh_relevance,
)


def test_classify_reference_implements_rt_tiers() -> None:
    assert classify_reference("repo", "MIT", {"imported_at_runtime": True}) == "RT3"
    assert classify_reference("repo", "MIT", {"binary_vendored": True}) == "RT2"
    assert classify_reference("repo", "MIT", {"code_adapted": True}) == "RT1"
    assert classify_reference("repo", "GPL-3.0", {"code_adapted": True}) == "RT0"
    assert classify_reference("repo", "MIT", {"pattern_only": True}) == "RT0"
    with pytest.raises(UnclassifiableReference):
        classify_reference("repo", "MIT", {})


def test_detect_category_tags_from_repo_files(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "README.md").write_text("# Ref\n", encoding="utf-8")

    tags = detect_category_tags(tmp_path)

    assert {"javascript", "source-layout", "test-patterns", "markdown"} <= set(tags)


def test_append_to_index_and_emit_triplet_table(tmp_path: Path) -> None:
    repo = tmp_path / "references" / "sample"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("# Sample reference\n", encoding="utf-8")
    (repo / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    entry = build_reference_entry(
        repo_path=repo,
        owner_repo="owner/sample",
        round_name="R1",
        usage_evidence={"pattern_only": True},
    )
    index = tmp_path / "references" / "INDEX.md"

    append_to_index(index, entry, "R1")
    table = emit_triplet_table([entry])

    assert "owner/sample" in index.read_text(encoding="utf-8")
    assert "MIT + RT0" in table


def test_refresh_relevance_adds_missing_round_marker(tmp_path: Path) -> None:
    index = tmp_path / "INDEX.md"
    index.write_text(
        "### `owner/repo` (`references/repo/`, MIT)\n"
        "- **CATEGORY**: python\n"
        "- **Key paths**:\n"
        "  - `README.md` — inspect\n",
        encoding="utf-8",
    )

    changes = refresh_relevance(index, "R2", default_relevance="low")

    assert changes == 1
    assert "**R2-relevance**: low" in index.read_text(encoding="utf-8")
