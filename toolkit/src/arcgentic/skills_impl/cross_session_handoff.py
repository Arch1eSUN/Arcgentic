"""cross-session-handoff skill implementation."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


@dataclass(frozen=True)
class CrossSessionResult:
    action: str
    ok: bool
    message: str
    state: dict[str, Any] | None = None
    path: Path | None = None

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1


def read_state(state_path: Path) -> CrossSessionResult:
    """Read state without acquiring a lock."""

    if not state_path.exists():
        return CrossSessionResult("read", True, "state file not found", state={}, path=state_path)
    state = _read_yaml(state_path)
    return CrossSessionResult("read", True, "state read", state=state, path=state_path)


def acquire_lock(state_path: Path, session_id: str, ttl: int = 1800) -> CrossSessionResult:
    lock_path = _lock_path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    now = int(time.time())
    try:
        with lock_path.open("x", encoding="utf-8") as handle:
            handle.write(f"{session_id}\n{now}\n{ttl}\n")
        return CrossSessionResult("acquire-lock", True, "lock acquired", path=lock_path)
    except FileExistsError:
        existing = _read_lock(lock_path)
        if existing and now - existing[1] >= existing[2]:
            lock_path.unlink()
            return acquire_lock(state_path, session_id, ttl)
        owner = existing[0] if existing else "unknown"
        return CrossSessionResult(
            "acquire-lock",
            False,
            f"lock held by {owner}",
            path=lock_path,
        )


def release_lock(state_path: Path, session_id: str) -> CrossSessionResult:
    lock_path = _lock_path(state_path)
    if not lock_path.exists():
        return CrossSessionResult("release-lock", True, "no lock present", path=lock_path)
    existing = _read_lock(lock_path)
    if existing and existing[0] != session_id:
        return CrossSessionResult(
            "release-lock",
            False,
            f"lock held by {existing[0]}, not {session_id}",
            path=lock_path,
        )
    lock_path.unlink()
    return CrossSessionResult("release-lock", True, "lock released", path=lock_path)


def write_state(
    state_path: Path,
    *,
    session_id: str,
    updates: dict[str, Any],
    ttl: int = 600,
) -> CrossSessionResult:
    lock = acquire_lock(state_path, session_id, ttl)
    if not lock.ok:
        return CrossSessionResult("write", False, lock.message, path=state_path)
    try:
        current = _read_yaml(state_path) if state_path.exists() else {}
        current.update(updates)
        current["last_session_id"] = session_id
        _atomic_write_yaml(state_path, current)
        return CrossSessionResult("write", True, "state written", state=current, path=state_path)
    finally:
        release_lock(state_path, session_id)


def snapshot_state(
    state_path: Path,
    *,
    session_id: str,
    history_dir: Path | None = None,
    ttl: int = 1800,
) -> CrossSessionResult:
    lock = acquire_lock(state_path, session_id, ttl)
    if not lock.ok:
        return CrossSessionResult("snapshot", False, lock.message, path=state_path)
    try:
        state = _read_yaml(state_path) if state_path.exists() else {}
        target_dir = history_dir if history_dir is not None else state_path.parent / "state-history"
        target_dir.mkdir(parents=True, exist_ok=True)
        round_name = str(state.get("current_round", "unknown-round"))
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        snapshot_path = target_dir / f"{stamp}-{round_name}.yaml"
        _atomic_write_yaml(snapshot_path, state)
        return CrossSessionResult(
            "snapshot",
            True,
            f"snapshot written: {snapshot_path}",
            state=state,
            path=snapshot_path,
        )
    finally:
        release_lock(state_path, session_id)


def parse_updates_json(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("updates must be a JSON object")
    return parsed


def _lock_path(state_path: Path) -> Path:
    return state_path.with_suffix(state_path.suffix + ".lock")


def _read_lock(lock_path: Path) -> tuple[str, int, int] | None:
    try:
        lines = lock_path.read_text(encoding="utf-8").splitlines()
        return lines[0], int(lines[1]), int(lines[2])
    except (IndexError, OSError, ValueError):
        return None


def _read_yaml(path: Path) -> dict[str, Any]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError(f"state file must be a YAML mapping: {path}")
    return dict(parsed)


def _atomic_write_yaml(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
    tmp_path.replace(path)
