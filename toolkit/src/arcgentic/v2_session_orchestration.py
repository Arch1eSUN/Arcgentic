"""Arcgentic V2 role-session orchestration primitives."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, cast

import yaml  # type: ignore[import-untyped]

Role = Literal["orchestrator", "planner", "developer", "auditor"]
HostKind = Literal["codex", "claude-code-broker"]
V2Mode = Literal["single-session-subagent", "multi-session-subthread"]
RoleActionKind = Literal["create", "reuse"]
OrchestratorStatus = Literal["active", "sleeping"]

FIXED_ROLE_TITLES: Final[dict[str, str]] = {
    "orchestrator": "Orchestrator",
    "planner": "Planner",
    "developer": "Developer",
    "auditor": "Auditor",
}

ROLE_ORDER: tuple[Role, ...] = ("orchestrator", "planner", "developer", "auditor")

ROLE_RETURN_SIGNAL_KEYS: Final[frozenset[str]] = frozenset(
    {"role", "status", "round_id", "state", "artifacts", "next_recommended_role"}
)

ROLE_ALLOWED_CURRENT_STATES: Final[dict[Role, frozenset[str]]] = {
    "orchestrator": frozenset({"intake", "planning", "passed", "closed"}),
    "planner": frozenset({"intake", "planning", "passed", "closed"}),
    "developer": frozenset(
        {"awaiting_dev_start", "dev_in_progress", "needs_fix", "fix_in_progress"}
    ),
    "auditor": frozenset({"awaiting_audit", "audit_in_progress"}),
}

ROLE_ALLOWED_SIGNAL_ROUTES: Final[dict[Role, dict[str, frozenset[Role]]]] = {
    "orchestrator": {
        "planning": frozenset({"planner"}),
        "closed": frozenset({"planner"}),
    },
    "planner": {
        "awaiting_dev_start": frozenset({"developer"}),
        "planning": frozenset({"planner"}),
    },
    "developer": {
        "awaiting_audit": frozenset({"auditor"}),
        "needs_fix": frozenset({"developer"}),
    },
    "auditor": {
        "passed": frozenset({"planner"}),
        "needs_fix": frozenset({"developer"}),
        "audit_in_progress": frozenset({"auditor"}),
    },
}


class V2SessionOrchestrationError(ValueError):
    """Raised when V2 session orchestration input is malformed."""


@dataclass(frozen=True)
class RoleSession:
    role: Role
    title: str
    thread_id: str
    host: HostKind
    updated_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RoleAction:
    role: Role
    title: str
    kind: RoleActionKind
    prompt: str
    thread_id: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SessionPlan:
    host: HostKind
    mode: V2Mode
    current_round: str
    current_state: str
    next_role: Role
    actions: tuple[RoleAction, ...]
    orchestrator_status: OrchestratorStatus = "active"
    pending_role: Role | None = None
    pending_thread_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "host": self.host,
            "mode": self.mode,
            "current_round": self.current_round,
            "current_state": self.current_state,
            "next_role": self.next_role,
            "orchestrator_status": self.orchestrator_status,
            "pending_role": self.pending_role,
            "pending_thread_id": self.pending_thread_id,
            "actions": [action.to_dict() for action in self.actions],
        }


@dataclass(frozen=True)
class RoleReturnSignal:
    role: Role
    status: str
    round_id: str
    state: str
    artifacts: dict[str, object]
    next_recommended_role: Role | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> RoleReturnSignal:
        raw = json.loads(payload)
        if not isinstance(raw, dict):
            raise V2SessionOrchestrationError("role return signal must be a JSON object")
        extra_keys = sorted(set(raw) - ROLE_RETURN_SIGNAL_KEYS)
        if extra_keys:
            joined = ", ".join(extra_keys)
            raise V2SessionOrchestrationError(
                f"role return signal has unexpected fields: {joined}"
            )
        role = normalize_role(raw.get("role"))
        next_role_raw = raw.get("next_recommended_role")
        next_recommended_role = normalize_role(next_role_raw) if next_role_raw else None
        artifacts = raw.get("artifacts")
        if not isinstance(artifacts, dict):
            raise V2SessionOrchestrationError("role return signal artifacts must be an object")
        return cls(
            role=role,
            status=str(raw.get("status") or ""),
            round_id=str(raw.get("round_id") or ""),
            state=str(raw.get("state") or ""),
            artifacts=artifacts,
            next_recommended_role=next_recommended_role,
        )


def normalize_role(value: object) -> Role:
    role = str(value or "").strip().lower()
    if role not in FIXED_ROLE_TITLES:
        raise V2SessionOrchestrationError(f"unsupported V2 role: {value}")
    return cast(Role, role)


def fixed_role_title(role: Role) -> str:
    return FIXED_ROLE_TITLES[role]


def load_state_file(path: Path) -> dict[str, object]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise V2SessionOrchestrationError(f"state file must be a YAML object: {path}")
    return dict(raw)


def write_state_file(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _project_v2_block(state: dict[str, object]) -> dict[str, object]:
    project = state.get("project")
    if not isinstance(project, dict):
        return {}
    raw = project.get("arcgentic_v2")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise V2SessionOrchestrationError("project.arcgentic_v2 must be an object")
    return raw


def _current_round(state: dict[str, object]) -> tuple[str, str]:
    current_round = state.get("current_round")
    if not isinstance(current_round, dict):
        return ("<round-id>", "intake")
    return (
        str(current_round.get("id") or "<round-id>"),
        str(current_round.get("state") or "intake"),
    )


def _role_sessions(v2: dict[str, object]) -> dict[str, object]:
    raw = v2.get("role_sessions")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise V2SessionOrchestrationError("project.arcgentic_v2.role_sessions must be an object")
    return raw


def _ensure_project_v2_block(state: dict[str, object], host: HostKind) -> dict[str, object]:
    project = state.setdefault("project", {})
    if not isinstance(project, dict):
        raise V2SessionOrchestrationError("project must be an object")
    v2 = project.setdefault("arcgentic_v2", {})
    if not isinstance(v2, dict):
        raise V2SessionOrchestrationError("project.arcgentic_v2 must be an object")
    v2.setdefault("host", host)
    v2.setdefault("mode", "multi-session-subthread")
    v2.setdefault("role_sessions", {})
    return v2


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def next_role_for_state(state_name: str) -> Role:
    state = state_name.strip()
    if state in {"intake", "planning", "passed", "closed"}:
        return "planner"
    if state in {"awaiting_dev_start", "dev_in_progress", "needs_fix", "fix_in_progress"}:
        return "developer"
    if state in {"awaiting_audit", "audit_in_progress"}:
        return "auditor"
    raise V2SessionOrchestrationError(f"unsupported round state for V2 routing: {state_name}")


def record_role_session(
    state: dict[str, object],
    role: Role,
    *,
    thread_id: str,
    title: str | None = None,
    host: HostKind = "codex",
) -> dict[str, object]:
    if not thread_id:
        raise V2SessionOrchestrationError("thread_id is required")
    fixed_title = fixed_role_title(role)
    if title is not None and title != fixed_title:
        raise V2SessionOrchestrationError(
            f"role {role} must use fixed title {fixed_title!r}, got {title!r}"
        )

    updated = deepcopy(state)
    v2 = _ensure_project_v2_block(updated, host)
    role_sessions = v2["role_sessions"]
    if not isinstance(role_sessions, dict):
        raise V2SessionOrchestrationError("project.arcgentic_v2.role_sessions must be an object")
    role_sessions[role] = RoleSession(
        role=role,
        title=fixed_title,
        thread_id=thread_id,
        host=host,
        updated_at=_utc_now(),
    ).to_dict()
    return updated


def record_role_dispatch(
    state: dict[str, object],
    role: Role,
    *,
    thread_id: str,
    host: HostKind = "codex",
) -> dict[str, object]:
    if not thread_id:
        raise V2SessionOrchestrationError("thread_id is required")
    updated = deepcopy(state)
    v2 = _ensure_project_v2_block(updated, host)
    role_sessions = _role_sessions(v2)
    existing = role_sessions.get(role)
    if isinstance(existing, dict) and existing.get("thread_id") != thread_id:
        raise V2SessionOrchestrationError(
            f"dispatch thread {thread_id!r} does not match recorded {role} thread "
            f"{existing.get('thread_id')!r}"
        )
    v2["orchestrator_status"] = "sleeping"
    v2["pending_role"] = role
    v2["pending_thread_id"] = thread_id
    v2["pending_since"] = _utc_now()
    return updated


def apply_role_return_signal(
    state: dict[str, object],
    signal: RoleReturnSignal,
) -> dict[str, object]:
    round_id, current_state = _current_round(state)
    if signal.round_id != round_id:
        raise V2SessionOrchestrationError(
            f"stale role signal for round {signal.round_id!r}; current round is {round_id!r}"
        )
    allowed_current_states = ROLE_ALLOWED_CURRENT_STATES[signal.role]
    if current_state not in allowed_current_states:
        raise V2SessionOrchestrationError(
            f"stale {signal.role} signal cannot apply from current state {current_state!r}"
        )
    v2_state = _project_v2_block(state)
    orchestrator_status = str(v2_state.get("orchestrator_status") or "active")
    if orchestrator_status == "sleeping":
        pending_role = normalize_role(v2_state.get("pending_role"))
        if pending_role != signal.role:
            raise V2SessionOrchestrationError(
                f"sleeping orchestrator is waiting for {pending_role}, got {signal.role}"
            )
    elif orchestrator_status != "active":
        raise V2SessionOrchestrationError(
            f"unsupported orchestrator_status: {orchestrator_status}"
        )
    route_options = ROLE_ALLOWED_SIGNAL_ROUTES[signal.role]
    allowed_next_roles = route_options.get(signal.state)
    if allowed_next_roles is None:
        raise V2SessionOrchestrationError(
            f"{signal.role} cannot route round to state {signal.state!r}"
        )
    next_role = signal.next_recommended_role or next_role_for_state(signal.state)
    if next_role not in allowed_next_roles:
        allowed = ", ".join(sorted(allowed_next_roles))
        raise V2SessionOrchestrationError(
            f"{signal.role} cannot recommend next role {next_role!r} for state "
            f"{signal.state!r}; expected one of: {allowed}"
        )

    updated = deepcopy(state)
    v2 = _ensure_project_v2_block(updated, "codex")
    v2["last_signal"] = signal.to_dict()
    v2["next_role"] = next_role
    v2["orchestrator_status"] = "active"
    v2.pop("pending_role", None)
    v2.pop("pending_thread_id", None)
    v2.pop("pending_since", None)
    current_round = updated.setdefault("current_round", {})
    if isinstance(current_round, dict):
        current_round["state"] = signal.state
        history = current_round.setdefault("state_history", [])
        if isinstance(history, list):
            history.append(
                {
                    "state": signal.state,
                    "ts": _utc_now(),
                    "by": signal.role,
                    "artifact": json.dumps(signal.artifacts, sort_keys=True),
                }
            )
    return updated


def role_prompt(role: Role, state: dict[str, object], *, user_request: str = "") -> str:
    round_id, current_state = _current_round(state)
    title = fixed_role_title(role)
    request_line = f"Current user request: {user_request.strip()}\n" if user_request.strip() else ""
    return (
        f"You are {title}.\n"
        f"Current round: {round_id}\n"
        f"Current state: {current_state}\n"
        f"{request_line}"
        "Read .agentic-rounds/state.yaml before acting.\n"
        "Use Arcgentic V2 fixed-role boundaries:\n"
        "- Planner owns brainstorming, plan completeness, and phase decisions.\n"
        "- Developer owns implementation, self-audit, and NEEDS_FIX repair.\n"
        "- Auditor owns PASS / NEEDS_FIX / AUDIT_INCOMPLETE.\n"
        "- Orchestrator owns routing and mechanical close-round only.\n"
        "Return a RoleReturnSignal JSON object only when this role turn is complete.\n"
        "Do not add extra fields outside role, status, round_id, state, artifacts, "
        "and next_recommended_role.\n"
        "Planner may route only to awaiting_dev_start/developer or planning/planner.\n"
        "If the current state is closed and the user request asks for new work, "
        "Planner must decide the next phase or next round instead of returning closed.\n"
        "Developer may route only to awaiting_audit/auditor or needs_fix/developer.\n"
        "Auditor may route only to passed/planner, needs_fix/developer, or "
        "audit_in_progress/auditor."
    )


def build_role_session_plan(
    state: dict[str, object],
    *,
    host: HostKind = "codex",
    user_request: str = "",
) -> SessionPlan:
    v2 = _project_v2_block(state)
    state_host = str(v2.get("host") or host)
    if state_host != host:
        raise V2SessionOrchestrationError(
            f"state host {state_host!r} does not match requested host {host!r}"
        )
    mode = str(v2.get("mode") or "multi-session-subthread")
    if mode not in {"single-session-subagent", "multi-session-subthread"}:
        raise V2SessionOrchestrationError(f"unsupported V2 mode: {mode}")
    typed_mode = cast(V2Mode, mode)

    round_id, current_state = _current_round(state)
    sessions = _role_sessions(v2)
    orchestrator_status = str(v2.get("orchestrator_status") or "active")
    next_role = next_role_for_state(current_state)
    if orchestrator_status == "sleeping":
        pending_role = normalize_role(v2.get("pending_role"))
        return SessionPlan(
            host=host,
            mode=typed_mode,
            current_round=round_id,
            current_state=current_state,
            next_role=pending_role,
            actions=(),
            orchestrator_status="sleeping",
            pending_role=pending_role,
            pending_thread_id=str(v2.get("pending_thread_id") or ""),
        )
    if orchestrator_status != "active":
        raise V2SessionOrchestrationError(
            f"unsupported orchestrator_status: {orchestrator_status}"
        )

    title = fixed_role_title(next_role)
    session = sessions.get(next_role)
    if isinstance(session, dict) and session.get("thread_id"):
        actions = (
            RoleAction(
                role=next_role,
                title=title,
                kind="reuse",
                thread_id=str(session["thread_id"]),
                prompt=role_prompt(next_role, state, user_request=user_request),
            ),
        )
    else:
        actions = (
            RoleAction(
                role=next_role,
                title=title,
                kind="create",
                prompt=role_prompt(next_role, state, user_request=user_request),
            ),
        )
    return SessionPlan(
        host=host,
        mode=typed_mode,
        current_round=round_id,
        current_state=current_state,
        next_role=next_role,
        actions=actions,
    )


def build_codex_role_session_plan(
    state: dict[str, object], *, user_request: str = ""
) -> SessionPlan:
    return build_role_session_plan(state, host="codex", user_request=user_request)
