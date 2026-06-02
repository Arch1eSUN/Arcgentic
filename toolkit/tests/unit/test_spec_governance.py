from __future__ import annotations

from pathlib import Path

from arcgentic.spec_governance import SpecGovernanceError, load_artifact_graph

FIXTURES = Path(__file__).parents[1] / "fixtures" / "v1" / "openspec"


def test_detects_required_artifacts_and_task_counts() -> None:
    graph = load_artifact_graph(FIXTURES / "changes" / "add-session-mode")

    assert graph.proposal.exists()
    assert graph.design.exists()
    assert graph.tasks.exists()
    assert graph.completed_tasks == 2
    assert graph.incomplete_tasks == 1
    assert graph.delta_specs == ("specs/session-mode/spec.md",)


def test_archive_not_ready_when_tasks_are_incomplete() -> None:
    graph = load_artifact_graph(FIXTURES / "changes" / "add-session-mode")

    assert graph.archive_ready is False
    assert "incomplete tasks" in graph.errors[0]


def test_missing_required_artifact_fails(tmp_path: Path) -> None:
    change = tmp_path / "changes" / "missing-design"
    change.mkdir(parents=True)
    (change / "proposal.md").write_text("# Proposal\n", encoding="utf-8")
    (change / "tasks.md").write_text("- [x] Done\n", encoding="utf-8")

    try:
        load_artifact_graph(change)
    except SpecGovernanceError as exc:
        assert "missing required artifact" in str(exc)
    else:
        raise AssertionError("expected SpecGovernanceError")
