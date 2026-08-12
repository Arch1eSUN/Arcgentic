"""Arcgentic V2 role-session orchestration primitives."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, cast

import yaml  # type: ignore[import-untyped]

from arcgentic.topology import Topology, TopologyError

Role = Literal["orchestrator", "planner", "developer", "test", "auditor"]
HostKind = Literal["codex", "claude-code-broker"]
V2Mode = Literal["single-session-subagent", "multi-session-subthread"]
RoleActionKind = Literal["create", "reuse"]
RoleActionTarget = Literal["thread", "subagent"]
OrchestratorStatus = Literal["active", "sleeping", "idle"]
VALID_V2_MODES: Final[frozenset[str]] = frozenset(
    {"single-session-subagent", "multi-session-subthread"}
)

V2_MODE_CHOICE_MESSAGE: Final[str] = (
    "project.arcgentic_v2.mode is not set. Ask the user to choose one "
    "project-level Arcgentic V2 mode before dispatching Planner: "
    "single-session-subagent is faster and usually completes sooner, but has "
    "weaker audit isolation; multi-session-subthread is slower, but gives "
    "stronger role separation and external-audit evidence."
)

FIXED_ROLE_TITLES: Final[dict[str, str]] = {
    "orchestrator": "Orchestrator",
    "planner": "Planner",
    "developer": "Developer",
    "test": "Test",
    "auditor": "Auditor",
}

ROLE_ORDER: tuple[Role, ...] = (
    "orchestrator",
    "planner",
    "developer",
    "test",
    "auditor",
)

ROLE_RETURN_SIGNAL_KEYS: Final[frozenset[str]] = frozenset(
    {"role", "status", "round_id", "state", "artifacts", "next_recommended_role"}
)

ROLE_RETURN_SIGNAL_BLOCK_RE: Final[re.Pattern[str]] = re.compile(
    r"```arcgentic-role-return\s*(?P<fenced>\{.*?\})\s*```|"
    r"ARCGENTIC_ROLE_RETURN\s*(?P<marked>\{.*?\})\s*END_ARCGENTIC_ROLE_RETURN",
    re.DOTALL,
)

GIT_COMMIT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")

AUDIT_INCOMPLETE_STATUSES: Final[frozenset[str]] = frozenset(
    {"AUDIT_INCOMPLETE", "INCOMPLETE"}
)
_CLOSED_STATUS_QUERY_TERMS: Final[tuple[str, ...]] = (
    "analyze",
    "analysis",
    "assess",
    "check",
    "complete",
    "done",
    "finished",
    "inspect",
    "review",
    "status",
    "whether",
    "分析",
    "查看",
    "检查",
    "看看",
    "看一下",
    "是否",
    "有没有",
    "完成",
    "做完",
    "状态",
    "评估",
)
_CLOSED_NEW_WORK_TERMS: Final[tuple[str, ...]] = (
    "add",
    "build",
    "create",
    "implement",
    "make",
    "new",
    "update",
    "增加",
    "新增",
    "做一个",
    "实现",
    "开发",
    "创建",
)


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
    target: RoleActionTarget = "thread"

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

    @classmethod
    def from_text(cls, payload: str) -> RoleReturnSignal:
        match = ROLE_RETURN_SIGNAL_BLOCK_RE.search(payload)
        if match is None:
            raise V2SessionOrchestrationError(
                "role return text must contain an arcgentic-role-return block"
            )
        json_payload = match.group("fenced") or match.group("marked")
        return cls.from_json(json_payload)


def normalize_role(value: object) -> Role:
    role = str(value or "").strip().lower()
    if role not in FIXED_ROLE_TITLES:
        raise V2SessionOrchestrationError(f"unsupported V2 role: {value}")
    return cast(Role, role)


def fixed_role_title(role: Role) -> str:
    return FIXED_ROLE_TITLES[role]


def fixed_subagent_id(role: Role) -> str:
    return f"subagent:{role}"


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


def ensure_initial_round_id(state: dict[str, object]) -> dict[str, object]:
    """Return state with a durable first-round id when the project is at intake."""
    current_round = state.get("current_round")
    if not isinstance(current_round, dict):
        updated = deepcopy(state)
        updated["current_round"] = {"id": "R1", "state": "intake"}
        return updated
    if str(current_round.get("id") or "").strip():
        return state

    updated = deepcopy(state)
    updated_round = updated.setdefault("current_round", {})
    if not isinstance(updated_round, dict):
        raise V2SessionOrchestrationError("current_round must be an object")
    updated_round["id"] = "R1"
    updated_round.setdefault("state", "intake")
    return updated


def _role_sessions(v2: dict[str, object]) -> dict[str, object]:
    raw = v2.get("role_sessions")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise V2SessionOrchestrationError("project.arcgentic_v2.role_sessions must be an object")
    return raw


def _role_return_footer_example(role: Role, round_id: str) -> str:
    examples = {
        "planner": {
            "role": "planner",
            "status": "planned",
            "round_id": round_id,
            "state": "awaiting_dev_start",
            "artifacts": {
                "handoff": f"docs/plans/{round_id}.md",
                "project_plan": {
                    "phases": [
                        {
                            "id": "P1",
                            "rounds": [
                                {
                                    "id": round_id,
                                    "handoff": f"docs/plans/{round_id}.md",
                                    "test_gate": {
                                        "required": False,
                                        "reason": (
                                            "No separate reality QA gate is needed for this round."
                                        ),
                                    },
                                }
                            ],
                        }
                    ]
                },
            },
            "next_recommended_role": "developer",
        },
        "developer": {
            "role": "developer",
            "status": "completed",
            "round_id": round_id,
            "state": "awaiting_test",
            "artifacts": {
                "self_audit": f"docs/audits/{round_id}-self-audit.md",
                "commit": "<40-hex-local-dev-commit>",
            },
            "next_recommended_role": "test",
        },
        "test": {
            "role": "test",
            "status": "user_tested",
            "round_id": round_id,
            "state": "awaiting_audit",
            "artifacts": {
                "user_test": f"docs/tests/{round_id}-user-test.md",
                "commit": "<40-hex-local-dev-commit>",
            },
            "next_recommended_role": "auditor",
        },
        "auditor": {
            "role": "auditor",
            "status": "PASS",
            "round_id": round_id,
            "state": "passed",
            "artifacts": {
                "verdict": f"docs/audits/{round_id}.md",
                "commit": "<40-hex-local-audit-commit>",
            },
            "next_recommended_role": "planner",
        },
    }
    return json.dumps(examples[role], indent=2)


def _ensure_project_v2_block(state: dict[str, object], host: HostKind) -> dict[str, object]:
    project = state.setdefault("project", {})
    if not isinstance(project, dict):
        raise V2SessionOrchestrationError("project must be an object")
    v2 = project.setdefault("arcgentic_v2", {})
    if not isinstance(v2, dict):
        raise V2SessionOrchestrationError("project.arcgentic_v2 must be an object")
    v2.setdefault("host", host)
    v2.setdefault("role_sessions", {})
    return v2


def set_v2_mode(state: dict[str, object], host: HostKind, mode: str) -> dict[str, object]:
    """Persist the project-level V2 mode after the user chooses it."""
    if mode not in VALID_V2_MODES:
        raise V2SessionOrchestrationError(f"unsupported V2 mode: {mode}")
    updated = deepcopy(state)
    v2 = _ensure_project_v2_block(updated, host)
    existing = str(v2.get("mode") or "").strip()
    if existing and existing != mode:
        raise V2SessionOrchestrationError(
            f"project.arcgentic_v2.mode is already set to {existing!r}; "
            "do not change project-level mode mid-workflow"
        )
    v2["mode"] = mode
    return updated


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# Retained only for the existing test suite's direct calls (see
# test_v2_session_orchestration.py). No longer consulted by
# apply_role_return_signal()/build_role_session_plan() — both now go
# through Topology (see topology.py) exclusively.
def next_role_for_state(state_name: str) -> Role:
    state = state_name.strip()
    if state in {"intake", "planning", "passed", "closed"}:
        return "planner"
    if state in {"awaiting_dev_start", "dev_in_progress", "needs_fix", "fix_in_progress"}:
        return "developer"
    if state in {"awaiting_test", "test_in_progress"}:
        return "test"
    if state in {"awaiting_audit", "audit_in_progress"}:
        return "auditor"
    raise V2SessionOrchestrationError(f"unsupported round state for V2 routing: {state_name}")


def _validate_developer_test_anchor(signal: RoleReturnSignal) -> None:
    if signal.role != "developer" or signal.state != "awaiting_test":
        return
    _validate_developer_completion_anchor(signal, target_state="awaiting_test")


def _validate_developer_audit_anchor(signal: RoleReturnSignal) -> None:
    if signal.role != "developer" or signal.state != "awaiting_audit":
        return
    _validate_developer_completion_anchor(signal, target_state="awaiting_audit")


def _validate_developer_completion_anchor(
    signal: RoleReturnSignal, *, target_state: str
) -> None:
    self_audit = signal.artifacts.get("self_audit")
    if not isinstance(self_audit, str) or not self_audit.strip():
        raise V2SessionOrchestrationError(
            f"developer {target_state} return must include artifacts.self_audit"
        )
    commit = signal.artifacts.get("commit")
    if not isinstance(commit, str) or GIT_COMMIT_RE.fullmatch(commit) is None:
        raise V2SessionOrchestrationError(
            f"developer {target_state} return must include artifacts.commit as a "
            "40-hex local git commit anchor"
        )


def _validate_test_audit_anchor(signal: RoleReturnSignal) -> None:
    if signal.role != "test" or signal.state != "awaiting_audit":
        return
    user_test = signal.artifacts.get("user_test")
    if not isinstance(user_test, str) or not user_test.strip():
        raise V2SessionOrchestrationError(
            "test awaiting_audit return must include artifacts.user_test"
        )
    commit = signal.artifacts.get("commit")
    if not isinstance(commit, str) or GIT_COMMIT_RE.fullmatch(commit) is None:
        raise V2SessionOrchestrationError(
            "test awaiting_audit return must include artifacts.commit as a "
            "40-hex local git commit anchor"
        )


def _validate_auditor_pass_anchor(signal: RoleReturnSignal) -> None:
    if signal.role != "auditor" or signal.state != "passed":
        return
    verdict = signal.artifacts.get("verdict")
    if not isinstance(verdict, str) or not verdict.strip():
        raise V2SessionOrchestrationError(
            "auditor PASS return must include artifacts.verdict"
        )
    commit = signal.artifacts.get("commit")
    if not isinstance(commit, str) or GIT_COMMIT_RE.fullmatch(commit) is None:
        raise V2SessionOrchestrationError(
            "auditor PASS return must include artifacts.commit as a "
            "40-hex local audit commit anchor"
        )


def _validate_planner_closed_anchor(signal: RoleReturnSignal) -> None:
    if signal.role != "planner" or signal.state != "closed":
        return
    closeout = signal.artifacts.get("closeout")
    if not isinstance(closeout, str) or not closeout.strip():
        raise V2SessionOrchestrationError(
            "planner closed return must include artifacts.closeout"
        )
    commit = signal.artifacts.get("commit")
    if not isinstance(commit, str) or GIT_COMMIT_RE.fullmatch(commit) is None:
        raise V2SessionOrchestrationError(
            "planner closed return must include artifacts.commit as a "
            "40-hex local closeout commit anchor"
        )


def _sync_project_plan_from_planner_return(
    v2: dict[str, object], signal: RoleReturnSignal
) -> None:
    if signal.role != "planner" or signal.state != "awaiting_dev_start":
        return
    project_plan = signal.artifacts.get("project_plan")
    if isinstance(project_plan, dict):
        v2["project_plan"] = project_plan


def _iter_project_plan_rounds(
    project_plan: dict[str, object],
) -> Iterator[tuple[int, dict[str, object], int, dict[str, object]]]:
    phases = project_plan.get("phases")
    if not isinstance(phases, list):
        return
    for phase_index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            continue
        rounds = phase.get("rounds")
        if not isinstance(rounds, list):
            continue
        for round_index, round_plan in enumerate(rounds):
            if isinstance(round_plan, dict):
                yield (
                    phase_index,
                    cast(dict[str, object], phase),
                    round_index,
                    cast(dict[str, object], round_plan),
                )


def advance_passed_round_from_project_plan(state: dict[str, object]) -> dict[str, object]:
    round_id, current_state = _current_round(state)
    if current_state != "passed":
        return state
    v2 = _project_v2_block(state)
    project_plan = v2.get("project_plan")
    if not isinstance(project_plan, dict):
        return state

    phase_entries = list(_iter_project_plan_rounds(project_plan) or [])
    current_position = None
    for position in phase_entries:
        _, _, _, round_plan = position
        if str(round_plan.get("id") or "") == round_id:
            current_position = position
            break
    if current_position is None:
        return state

    updated = deepcopy(state)
    updated_v2 = _ensure_project_v2_block(updated, "codex")
    updated_plan = updated_v2.get("project_plan")
    if not isinstance(updated_plan, dict):
        return state

    updated_entries = list(_iter_project_plan_rounds(updated_plan) or [])
    _, _, _, updated_round_plan = updated_entries[phase_entries.index(current_position)]
    updated_round_plan["status"] = "passed"

    current_phase_index, _, current_round_index, _ = current_position
    next_round_plan = None
    for phase_index, _, round_index, candidate in updated_entries:
        if phase_index == current_phase_index and round_index > current_round_index:
            if str(candidate.get("status") or "planned") != "passed":
                next_round_plan = candidate
                break

    current_round = updated.setdefault("current_round", {})
    if not isinstance(current_round, dict):
        raise V2SessionOrchestrationError("current_round must be an object")
    if next_round_plan is not None:
        next_round_id = str(next_round_plan.get("id") or "").strip()
        if not next_round_id:
            raise V2SessionOrchestrationError("next project_plan round is missing id")
        next_round_plan["status"] = "active"
        current_round["id"] = next_round_id
        current_round["state"] = "awaiting_dev_start"
        current_round["audit_verdict"] = None
        updated_v2["next_role"] = "developer"
        updated_v2["current_phase_index"] = current_phase_index
        updated_v2["current_round_id"] = next_round_id
        history = current_round.setdefault("state_history", [])
        if isinstance(history, list):
            history.append(
                {
                    "state": "awaiting_dev_start",
                    "ts": _utc_now(),
                    "by": "orchestrator",
                    "artifact": json.dumps(
                        {"advanced_from": round_id, "advanced_to": next_round_id},
                        sort_keys=True,
                    ),
                }
            )
        return updated

    current_round["state"] = "planning"
    updated_v2["next_role"] = "planner"
    updated_v2["phase_boundary"] = {
        "after_round": round_id,
        "phase_index": current_phase_index,
    }
    history = current_round.setdefault("state_history", [])
    if isinstance(history, list):
        history.append(
            {
                "state": "planning",
                "ts": _utc_now(),
                "by": "orchestrator",
                "artifact": json.dumps(
                    {"phase_boundary_after": round_id},
                    sort_keys=True,
                ),
            }
        )
    return updated


def record_role_session(
    state: dict[str, object],
    role: Role,
    *,
    thread_id: str,
    title: str | None = None,
    host: HostKind = "codex",
    repair_current_orchestrator: bool = False,
) -> dict[str, object]:
    if not thread_id:
        raise V2SessionOrchestrationError("thread_id is required")
    if repair_current_orchestrator and role != "orchestrator":
        raise V2SessionOrchestrationError(
            "--repair-current-orchestrator can only repair the Orchestrator session"
        )
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
    existing = role_sessions.get(role)
    if isinstance(existing, dict):
        existing_thread_id = str(existing.get("thread_id") or "")
        if existing_thread_id and existing_thread_id != thread_id:
            if role == "orchestrator" and repair_current_orchestrator:
                pass
            else:
                repair_hint = (
                    "; use --repair-current-orchestrator only when correcting the "
                    "current Orchestrator push-return target"
                    if role == "orchestrator"
                    else ""
                )
                raise V2SessionOrchestrationError(
                    f"{role} is already recorded as thread {existing_thread_id!r}; "
                    "reuse that fixed role thread instead of creating or recording "
                    f"a duplicate{repair_hint}"
                )
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


def remember_active_user_request(
    state: dict[str, object],
    user_request: str,
    *,
    host: HostKind = "codex",
) -> dict[str, object]:
    request = user_request.strip()
    if not request:
        return state
    updated = deepcopy(state)
    v2 = _ensure_project_v2_block(updated, host)
    v2["active_user_request"] = request
    return updated


def is_closed_project_status_query(user_request: str) -> bool:
    request = user_request.strip().lower()
    if not request:
        return False
    if any(term in request for term in _CLOSED_NEW_WORK_TERMS):
        return False
    return any(term in request for term in _CLOSED_STATUS_QUERY_TERMS)


def apply_role_return_signal(
    state: dict[str, object],
    signal: RoleReturnSignal,
) -> dict[str, object]:
    round_id, current_state = _current_round(state)
    if signal.round_id != round_id:
        raise V2SessionOrchestrationError(
            f"stale role signal for round {signal.round_id!r}; current round is {round_id!r}"
        )
    v2_state = _project_v2_block(state)
    orchestrator_status = str(v2_state.get("orchestrator_status") or "active")
    pending_role: Role | None = None
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

    try:
        topology = Topology.from_state(state)
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
    try:
        allowed_current_states = topology.allowed_current_states(signal.role)
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
    is_pending_idempotent_return = (
        orchestrator_status == "sleeping"
        and pending_role == signal.role
        and signal.state == current_state
    )
    if current_state not in allowed_current_states and not is_pending_idempotent_return:
        raise V2SessionOrchestrationError(
            f"stale {signal.role} signal cannot apply from current state {current_state!r}"
        )
    try:
        route_options = topology.routes_for_role(signal.role)
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
    allowed_next_roles = route_options.get(signal.state)
    if allowed_next_roles is None:
        raise V2SessionOrchestrationError(
            f"{signal.role} cannot route round to state {signal.state!r}"
        )
    try:
        next_role = signal.next_recommended_role or topology.default_next_role(
            signal.state, signal.artifacts
        )
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
    if next_role not in allowed_next_roles:
        allowed = ", ".join(sorted(allowed_next_roles))
        raise V2SessionOrchestrationError(
            f"{signal.role} cannot recommend next role {next_role!r} for state "
            f"{signal.state!r}; expected one of: {allowed}"
        )
    _validate_developer_test_anchor(signal)
    _validate_developer_audit_anchor(signal)
    _validate_test_audit_anchor(signal)
    _validate_auditor_pass_anchor(signal)
    _validate_planner_closed_anchor(signal)

    updated = deepcopy(state)
    v2 = _ensure_project_v2_block(updated, "codex")
    _sync_project_plan_from_planner_return(v2, signal)
    v2["last_signal"] = signal.to_dict()
    if signal.state == "closed":
        v2.pop("next_role", None)
        v2["orchestrator_status"] = "idle"
    else:
        v2["next_role"] = next_role
        v2["orchestrator_status"] = "active"
    v2.pop("pending_role", None)
    v2.pop("pending_thread_id", None)
    v2.pop("pending_since", None)
    current_round = updated.setdefault("current_round", {})
    if isinstance(current_round, dict):
        current_round["state"] = signal.state
        if signal.role == "auditor" and signal.state in {
            "passed",
            "needs_fix",
            "audit_in_progress",
        }:
            verdict = signal.artifacts.get("verdict")
            if isinstance(verdict, str) and verdict.strip():
                audit_verdict: dict[str, object] = {
                    "path": verdict,
                    "outcome": signal.status.upper(),
                    "fact_table_total": 0,
                    "fact_table_pass": 0,
                    "findings": [],
                }
                commit = signal.artifacts.get("commit")
                if isinstance(commit, str) and commit.strip():
                    audit_verdict["commit"] = commit
                current_round["audit_verdict"] = audit_verdict
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
    footer_example = _role_return_footer_example(role, round_id)
    v2 = _project_v2_block(state)
    sessions = _role_sessions(v2)
    orchestrator_session = sessions.get("orchestrator")
    orchestrator_thread_id = (
        str(orchestrator_session.get("thread_id") or "")
        if isinstance(orchestrator_session, dict)
        else ""
    )
    wake_instruction = (
        "When your role-owned work is complete, actively send a message to "
        f"Orchestrator thread {orchestrator_thread_id} containing your natural-language "
        "summary and the same ARCGENTIC_ROLE_RETURN block. Do not wait for the "
        "Orchestrator to poll your thread.\n"
        if orchestrator_thread_id
        else "Orchestrator thread id is not recorded in state. Report this as a "
        "blocking orchestration setup issue instead of assuming the Orchestrator "
        "can poll your thread.\n"
    )
    request_line = f"Current user request: {user_request.strip()}\n" if user_request.strip() else ""
    return (
        f"You are {title}.\n"
        f"Current round: {round_id}\n"
        f"Current state: {current_state}\n"
        f"{request_line}"
        "Read .agentic-rounds/state.yaml before acting.\n"
        "Use Arcgentic V2 fixed-role boundaries:\n"
        "- Planner owns brainstorming, the full project plan, phase/round "
        "decomposition, and per-round gate decisions.\n"
        "- Developer owns implementation, self-audit, and NEEDS_FIX repair.\n"
        "- Test owns strict reality QA / simulated user-session testing only "
        "when the current round's project_plan.test_gate requires it.\n"
        "- Auditor owns stricter independent PASS / NEEDS_FIX / "
        "AUDIT_INCOMPLETE review and must not trust Developer self-audit as "
        "proof.\n"
        "- Orchestrator owns routing, state recording, and phase/project close "
        "only.\n"
        "Only the Orchestrator may mutate .agentic-rounds/state.yaml, dispatch roles, "
        "or record role return signals. Planner, Developer, Test, and Auditor "
        "must write their own artifacts only, then return JSON for Orchestrator "
        "to consume.\n"
        "Do not stop after acknowledging the role. Complete the role-owned work in "
        "this turn, using tools as needed, before returning the RoleReturnSignal.\n"
        "Developer, Test, and Auditor must use "
        "project.arcgentic_v2.last_signal.artifacts to locate the prior role "
        "artifact they need to consume.\n"
        "Planner must produce a complete project plan before the first Developer "
        "round. The plan must split the project into phases and rounds, and each "
        "round must declare gates including whether Test is required. Put a "
        "structured project_plan object in artifacts.project_plan, not only prose.\n"
        "Planner must first do a reference/tool discovery pass for the user's idea: "
        "search GitHub or equivalent public sources for reliable comparable projects "
        "or effective implementation references, scan locally available skills, "
        "plugins, MCP servers, connectors, and CLI tools, and write the selected "
        "references/tools into the detailed Markdown handoff. Every round handoff "
        "must include which references to inspect, which skills/MCP/plugins/tools "
        "to use, which ones were considered but rejected, and why.\n"
        "Planner handoffs are full Markdown engineering documents, not short JSON "
        "summaries. The Orchestrator may transfer prompt instructions between "
        "threads, but each role session must read the referenced handoff artifact "
        "before doing role-owned work.\n"
        "Developer must create a local git commit after implementation and "
        "verification. Use git add for the files owned by the round, create a "
        "normal local commit, verify it with `git rev-parse HEAD`, then include "
        "that hash in the return footer. Developer always returns self_audit and "
        "commit. If the current round's project_plan.test_gate.required is true, "
        "route to awaiting_test/test. If it is false, route directly to "
        "awaiting_audit/auditor and include the skip reason in the human-readable "
        "summary. A GitHub remote is stronger evidence but is not required for "
        "local audit.\n"
        "Test is optional and must run only when the project_plan for this round "
        "requires it. When required, Test must simulate realistic user behavior "
        "with domain-specific strictness: UI spacing/radius/alignment/states, "
        "scroll and frame-rate observations, responsive behavior, CLI install/help/"
        "stdin/stderr/exit codes, or agent end-to-end user conversations as "
        "appropriate. Test writes a readable user-test artifact and returns "
        "awaiting_audit only when the simulated user flow passes. If the user "
        "flow fails, route to needs_fix/developer.\n"
        "Auditor is stricter than Developer self-audit. Auditor must independently "
        "replay evidence, verify commit anchors and required/skipped Test gates, "
        "check scope against the plan, and reject PASS when the evidence chain is "
        "insufficient. Auditor verdicts must include a fact-table "
        "section headed exactly `## 7. Fact table` or "
        "`## § 7. Mechanical audit facts`, use the exact markdown table header "
        "`| # | Command | Expected | Comment |`, keep expected values exact, do "
        "not add a separate Actual column, and run "
        "`arcgentic audit-check <verdict> --strict --strict-extended` before "
        "returning PASS. Auditor PASS fact rows must use stable evidence such "
        "as committed artifacts, fixed git hashes, artifact file contents, and "
        "test/build outputs. Do not use mutable live routing state such as "
        "`current_round.state`, `project.arcgentic_v2.last_signal.role`, or "
        "`project.arcgentic_v2.last_signal.state` as PASS facts unless the "
        "command reads an immutable committed snapshot. Auditor PASS returns "
        "must also include artifacts.commit "
        "as the 40-hex local audit commit anchor for the committed verdict.\n"
        "Use natural language for your role-owned output: Planner writes a readable "
        "plan, Developer writes a readable self-audit summary, Test writes a readable "
        "user-test report, and Auditor writes a readable verdict. Do not make the "
        "whole response raw JSON.\n"
        "Recommended closing shape: first write 3-8 concise human-readable bullets "
        "covering what you decided or completed, where the artifact lives, and what "
        "the next role should do. Then add the fenced routing footer below.\n"
        "At the end of your role-owned output, include exactly one machine-readable "
        "footer. Format the JSON over multiple lines with indentation so humans can "
        "read it:\n"
        "```arcgentic-role-return\n"
        f"{footer_example}\n"
        "```\n"
        f"{wake_instruction}"
        "Do not add extra fields outside role, status, round_id, state, artifacts, "
        "and next_recommended_role.\n"
        "Planner may route only to awaiting_dev_start/developer, planning/planner, "
        "or closed/null for final project completion. For closed returns, Planner "
        "must write the closeout artifact, create a local closeout commit, verify "
        "`git rev-parse HEAD`, and include artifacts.closeout plus artifacts.commit "
        "in the return footer.\n"
        "If the current state is closed and the user request asks for new work, "
        "Planner must decide the next phase or next round instead of returning closed.\n"
        "Developer may route only to awaiting_test/test, awaiting_audit/auditor, "
        "or needs_fix/developer.\n"
        "Test may route only to awaiting_audit/auditor or needs_fix/developer.\n"
        "Auditor may route only to passed/planner, needs_fix/developer, or "
        "audit_in_progress/auditor. Auditor may use audit_in_progress/auditor only "
        "for retryable audit work. If the same evidence gap cannot be resolved by "
        "another audit pass, route to needs_fix/developer or stop with a concise "
        "AUDIT_INCOMPLETE report instead of creating an audit loop."
    )


def _is_repeated_audit_incomplete(v2: dict[str, object], current_state: str) -> bool:
    if current_state != "audit_in_progress":
        return False
    signal = v2.get("last_signal")
    if not isinstance(signal, dict):
        return False
    role = normalize_role(signal.get("role"))
    next_role = normalize_role(signal.get("next_recommended_role"))
    status = str(signal.get("status") or "").upper()
    state = str(signal.get("state") or "")
    return (
        role == "auditor"
        and next_role == "auditor"
        and status in AUDIT_INCOMPLETE_STATUSES
        and state == "audit_in_progress"
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
    mode = str(v2.get("mode") or "").strip()
    if not mode:
        raise V2SessionOrchestrationError(V2_MODE_CHOICE_MESSAGE)
    if mode not in VALID_V2_MODES:
        raise V2SessionOrchestrationError(f"unsupported V2 mode: {mode}")
    typed_mode = cast(V2Mode, mode)

    round_id, current_state = _current_round(state)
    sessions = _role_sessions(v2)
    orchestrator_status = str(v2.get("orchestrator_status") or "active")
    try:
        next_role = Topology.from_state(state).default_next_role(current_state)
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
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
    if orchestrator_status == "idle":
        if current_state != "closed":
            raise V2SessionOrchestrationError(
                "idle orchestrator_status is only valid for closed rounds"
            )
        active_request = str(v2.get("active_user_request") or "").strip()
        incoming_request = user_request.strip()
        if (
            not incoming_request
            or incoming_request == active_request
            or is_closed_project_status_query(incoming_request)
        ):
            return SessionPlan(
                host=host,
                mode=typed_mode,
                current_round=round_id,
                current_state=current_state,
                next_role=next_role,
                actions=(),
                orchestrator_status="idle",
            )
    elif orchestrator_status != "active":
        raise V2SessionOrchestrationError(
            f"unsupported orchestrator_status: {orchestrator_status}"
        )

    if _is_repeated_audit_incomplete(v2, current_state):
        return SessionPlan(
            host=host,
            mode=typed_mode,
            current_round=round_id,
            current_state=current_state,
            next_role=next_role,
            actions=(),
            orchestrator_status="active",
        )

    if current_state == "passed":
        return SessionPlan(
            host=host,
            mode=typed_mode,
            current_round=round_id,
            current_state=current_state,
            next_role=next_role,
            actions=(),
            orchestrator_status="active",
        )

    if current_state == "closed":
        active_request = str(v2.get("active_user_request") or "").strip()
        incoming_request = user_request.strip()
        if (
            not incoming_request
            or incoming_request == active_request
            or is_closed_project_status_query(incoming_request)
        ):
            return SessionPlan(
                host=host,
                mode=typed_mode,
                current_round=round_id,
                current_state=current_state,
                next_role=next_role,
                actions=(),
                orchestrator_status="idle",
            )

    if current_state == "closed" and not user_request.strip():
        return SessionPlan(
            host=host,
            mode=typed_mode,
            current_round=round_id,
            current_state=current_state,
            next_role=next_role,
            actions=(),
            orchestrator_status="active",
        )

    title = fixed_role_title(next_role)
    session = sessions.get(next_role)
    if typed_mode == "single-session-subagent":
        if isinstance(session, dict) and session.get("thread_id"):
            action_kind: RoleActionKind = "reuse"
            thread_id = str(session["thread_id"])
        else:
            action_kind = "create"
            thread_id = fixed_subagent_id(next_role)
        actions = (
            RoleAction(
                role=next_role,
                title=title,
                kind=action_kind,
                thread_id=thread_id,
                target="subagent",
                prompt=role_prompt(next_role, state, user_request=user_request),
            ),
        )
    elif isinstance(session, dict) and session.get("thread_id"):
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
