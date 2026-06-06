"""Close a passed arcgentic round after external audit PASS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .audit_check import run as run_audit_check
from .skills_impl.codify_lesson import run as run_codify_lesson
from .verdict_completeness import validate_verdict_completeness


class CloseRoundError(ValueError):
    """Raised when close-round preconditions fail."""


@dataclass(frozen=True)
class CloseRoundResult:
    closed: bool
    round_id: str
    message: str
    lessons: int
    amendments: int


def close_round(*, state_path: Path, verdict_path: Path, audit_commit: str) -> CloseRoundResult:
    """Close a passed round and record last_passed_round without touching git history."""

    if not audit_commit:
        raise CloseRoundError("audit commit is required")
    if not verdict_path.exists():
        raise CloseRoundError(f"verdict file not found: {verdict_path}")
    state = _load_state(state_path)
    current = state.get("current_round")
    if not isinstance(current, dict):
        raise CloseRoundError("current_round block missing")
    if current.get("state") != "passed":
        raise CloseRoundError("state must be passed before close-round")

    verdict = current.get("audit_verdict")
    if not isinstance(verdict, dict) or verdict.get("outcome") != "PASS":
        raise CloseRoundError("close-round requires PASS audit_verdict in state")
    if not verdict.get("commit"):
        raise CloseRoundError("audit commit is required in state audit_verdict")

    completeness = validate_verdict_completeness(verdict_path.read_text(encoding="utf-8"))
    if not completeness.ok:
        raise CloseRoundError("verdict completeness failed: " + "; ".join(completeness.issues))

    repo_root = _repo_root(state=state, state_path=state_path)
    audit_check = run_audit_check(
        audit_path=verdict_path,
        strict=True,
        strict_extended=True,
        repo_root=repo_root,
    )
    if audit_check.exit_code != 0:
        raise CloseRoundError(f"audit-check failed: {audit_check.summary_text}")

    lesson_scan = run_codify_lesson(
        audit_dir=repo_root / "docs" / "audits",
        lessons_dir=repo_root / "lessons",
        amendments_dir=repo_root / "mandates" / "amendments",
    )

    round_id = str(current.get("id") or "")
    current["state"] = "closed"
    history = current.setdefault("state_history", [])
    if isinstance(history, list):
        history.append(
            {
                "state": "closed",
                "ts": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "by": "close-round",
                "artifact": f"{verdict_path}@{audit_commit[:7]}",
            }
        )
    state["last_passed_round"] = {
        "id": round_id,
        "commit": audit_commit,
        "verdict_doc": str(verdict_path),
        "closed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    _clear_v2_pending_dispatch(state)
    _write_state(state_path, state)
    return CloseRoundResult(
        closed=True,
        round_id=round_id,
        lessons=len(lesson_scan.lessons),
        amendments=len(lesson_scan.amendments),
        message=(
            f"closed {round_id}; lesson scan: {len(lesson_scan.lessons)} lessons, "
            f"{len(lesson_scan.amendments)} amendments; next step: orchestrator may "
            "recommend next round"
        ),
    )


def _load_state(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise CloseRoundError("state file must contain a mapping")
    return loaded


def _write_state(path: Path, state: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _clear_v2_pending_dispatch(state: dict[str, object]) -> None:
    project = state.get("project")
    if not isinstance(project, dict):
        return
    v2 = project.get("arcgentic_v2")
    if not isinstance(v2, dict):
        return
    v2["orchestrator_status"] = "active"
    v2["round_status"] = "closed"
    v2["project_status"] = "closed"
    v2.pop("next_role", None)
    v2.pop("pending_role", None)
    v2.pop("pending_thread_id", None)
    v2.pop("pending_since", None)


def _repo_root(*, state: dict[str, object], state_path: Path) -> Path:
    project = state.get("project")
    if isinstance(project, dict):
        root = project.get("root")
        if isinstance(root, str) and root:
            return Path(root)
    return state_path.parent
