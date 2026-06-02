"""Close a passed arcgentic round after external audit PASS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .verdict_completeness import validate_verdict_completeness


class CloseRoundError(ValueError):
    """Raised when close-round preconditions fail."""


@dataclass(frozen=True)
class CloseRoundResult:
    closed: bool
    round_id: str
    message: str


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
    _write_state(state_path, state)
    return CloseRoundResult(
        closed=True,
        round_id=round_id,
        message=f"closed {round_id}; next step: orchestrator may recommend next round",
    )


def _load_state(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise CloseRoundError("state file must contain a mapping")
    return loaded


def _write_state(path: Path, state: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8")
