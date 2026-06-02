"""OpenSpec-style artifact graph validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SpecGovernanceError(ValueError):
    """Raised when a spec change directory is malformed."""


@dataclass(frozen=True)
class ArtifactGraph:
    change_dir: Path
    proposal: Path
    design: Path
    tasks: Path
    delta_specs: tuple[str, ...]
    completed_tasks: int
    incomplete_tasks: int
    archive_target: Path
    archive_ready: bool
    errors: tuple[str, ...]


def load_artifact_graph(change_dir: Path, *, archive_root: Path | None = None) -> ArtifactGraph:
    """Load proposal/design/tasks/specs and validate archive readiness."""

    proposal = change_dir / "proposal.md"
    design = change_dir / "design.md"
    tasks = change_dir / "tasks.md"
    missing = [path.name for path in (proposal, design, tasks) if not path.exists()]
    if missing:
        raise SpecGovernanceError(f"missing required artifact: {', '.join(missing)}")

    completed, incomplete = _count_tasks(tasks)
    delta_specs = tuple(
        sorted(
            path.relative_to(change_dir).as_posix()
            for path in (change_dir / "specs").rglob("*.md")
        )
    )
    root = archive_root or change_dir.parent.parent / "archive"
    archive_target = root / change_dir.name
    errors: list[str] = []
    if incomplete:
        errors.append(f"{incomplete} incomplete tasks")
    if archive_target.exists():
        errors.append(f"archive target collision: {archive_target}")
    if not delta_specs:
        errors.append("no delta specs found")

    return ArtifactGraph(
        change_dir=change_dir,
        proposal=proposal,
        design=design,
        tasks=tasks,
        delta_specs=delta_specs,
        completed_tasks=completed,
        incomplete_tasks=incomplete,
        archive_target=archive_target,
        archive_ready=not errors,
        errors=tuple(errors),
    )


def _count_tasks(path: Path) -> tuple[int, int]:
    completed = 0
    incomplete = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("- [x]"):
            completed += 1
        elif stripped.startswith("- [ ]"):
            incomplete += 1
    return completed, incomplete
