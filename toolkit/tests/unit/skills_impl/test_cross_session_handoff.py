from __future__ import annotations

import time
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from arcgentic.skills_impl.cross_session_handoff import (
    acquire_lock,
    read_state,
    release_lock,
    snapshot_state,
    write_state,
)


def test_read_returns_state_without_lock(tmp_path: Path) -> None:
    state_path = tmp_path / ".arcgentic" / "state.yaml"
    state_path.parent.mkdir()
    state_path.write_text("current_round: R1\n", encoding="utf-8")

    result = read_state(state_path)

    assert result.ok
    assert result.state == {"current_round": "R1"}
    assert not state_path.with_suffix(".yaml.lock").exists()


def test_write_acquires_lock_updates_and_releases(tmp_path: Path) -> None:
    state_path = tmp_path / ".arcgentic" / "state.yaml"

    result = write_state(
        state_path,
        session_id="dev-session",
        updates={"current_round": "R2", "current_phase": "dev"},
    )

    assert result.ok
    assert not state_path.with_suffix(".yaml.lock").exists()
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    assert state["current_round"] == "R2"
    assert state["last_session_id"] == "dev-session"


def test_lock_ttl_expiry_allows_new_session(tmp_path: Path) -> None:
    state_path = tmp_path / ".arcgentic" / "state.yaml"
    first = acquire_lock(state_path, "old-session", ttl=1)
    assert first.ok
    time.sleep(1.1)

    second = acquire_lock(state_path, "new-session", ttl=60)

    assert second.ok
    release_lock(state_path, "new-session")


def test_snapshot_writes_history_file(tmp_path: Path) -> None:
    state_path = tmp_path / ".arcgentic" / "state.yaml"
    state_path.parent.mkdir()
    state_path.write_text("current_round: R3\n", encoding="utf-8")

    result = snapshot_state(state_path, session_id="audit-session")

    assert result.ok
    assert result.path is not None
    assert result.path.exists()
    assert "current_round: R3" in result.path.read_text(encoding="utf-8")
