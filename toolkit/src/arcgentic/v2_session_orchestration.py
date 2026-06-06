"""Arcgentic V2 role-session orchestration primitives."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Final, Literal, cast

Role = Literal["orchestrator", "planner", "developer", "auditor"]
HostKind = Literal["codex"]
V2Mode = Literal["single-session-subagent", "multi-session-subthread"]
RoleActionKind = Literal["create", "reuse"]

FIXED_ROLE_TITLES: Final[dict[str, str]] = {
    "orchestrator": "Orchestrator",
    "planner": "Planner",
    "developer": "Developer",
    "auditor": "Auditor",
}

ROLE_ORDER: tuple[Role, ...] = ("orchestrator", "planner", "developer", "auditor")


class V2SessionOrchestrationError(ValueError):
    """Raised when V2 session orchestration input is malformed."""


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

    def to_dict(self) -> dict[str, object]:
        return {
            "host": self.host,
            "mode": self.mode,
            "current_round": self.current_round,
            "current_state": self.current_state,
            "next_role": self.next_role,
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


def next_role_for_state(state_name: str) -> Role:
    state = state_name.strip()
    if state in {"intake", "planning", "passed", "closed"}:
        return "planner"
    if state in {"awaiting_dev_start", "dev_in_progress", "needs_fix", "fix_in_progress"}:
        return "developer"
    if state in {"awaiting_audit", "audit_in_progress"}:
        return "auditor"
    raise V2SessionOrchestrationError(f"unsupported round state for V2 routing: {state_name}")


def role_prompt(role: Role, state: dict[str, object]) -> str:
    round_id, current_state = _current_round(state)
    title = fixed_role_title(role)
    return (
        f"You are {title}.\n"
        f"Current round: {round_id}\n"
        f"Current state: {current_state}\n"
        "Read .agentic-rounds/state.yaml before acting.\n"
        "Use Arcgentic V2 fixed-role boundaries:\n"
        "- Planner owns brainstorming, plan completeness, and phase decisions.\n"
        "- Developer owns implementation, self-audit, and NEEDS_FIX repair.\n"
        "- Auditor owns PASS / NEEDS_FIX / AUDIT_INCOMPLETE.\n"
        "- Orchestrator owns routing and mechanical close-round only.\n"
        "Return a RoleReturnSignal JSON object when this role turn is complete."
    )


def build_codex_role_session_plan(state: dict[str, object]) -> SessionPlan:
    v2 = _project_v2_block(state)
    host = str(v2.get("host") or "codex")
    if host != "codex":
        raise V2SessionOrchestrationError(f"unsupported V2 host for Codex plan: {host}")
    mode = str(v2.get("mode") or "multi-session-subthread")
    if mode not in {"single-session-subagent", "multi-session-subthread"}:
        raise V2SessionOrchestrationError(f"unsupported V2 mode: {mode}")
    typed_mode = cast(V2Mode, mode)

    round_id, current_state = _current_round(state)
    sessions = _role_sessions(v2)
    actions: list[RoleAction] = []
    for role in ROLE_ORDER:
        title = fixed_role_title(role)
        session = sessions.get(role)
        if isinstance(session, dict) and session.get("thread_id"):
            actions.append(
                RoleAction(
                    role=role,
                    title=title,
                    kind="reuse",
                    thread_id=str(session["thread_id"]),
                    prompt=role_prompt(role, state),
                )
            )
        else:
            actions.append(
                RoleAction(
                    role=role,
                    title=title,
                    kind="create",
                    prompt=role_prompt(role, state),
                )
            )
    return SessionPlan(
        host="codex",
        mode=typed_mode,
        current_round=round_id,
        current_state=current_state,
        next_role=next_role_for_state(current_state),
        actions=tuple(actions),
    )
