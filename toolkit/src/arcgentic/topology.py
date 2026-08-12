"""Data-driven graph topology for Arcgentic V2 role/state routing.

Replaces the hardcoded ROLE_ALLOWED_CURRENT_STATES / ROLE_ALLOWED_SIGNAL_ROUTES /
next_role_for_state tables in v2_session_orchestration.py with a structure that
projects can override via project.arcgentic_v2.topology in state.yaml. The
default topology is a literal transcription of those three tables — see
docs/plans/2026-08-12-arcgentic-v2-topology-graph-engine-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, cast

# Deliberately NOT imported from v2_session_orchestration.py — that module
# imports Topology from here, so importing back would be circular. This
# Role/KNOWN_ROLES pair is a structural duplicate of the one in
# v2_session_orchestration.py; mypy compares Literal types structurally, so
# any drift between the two shows up as a type error at the call sites in
# Task 2/3, not as a silent bug.
Role = Literal["orchestrator", "planner", "developer", "test", "auditor"]
KNOWN_ROLES: Final[tuple[Role, ...]] = (
    "orchestrator",
    "planner",
    "developer",
    "test",
    "auditor",
)


class TopologyError(ValueError):
    """Raised when a topology configuration or lookup is invalid."""


def _normalize_role(value: object) -> Role:
    role = str(value or "").strip().lower()
    if role not in KNOWN_ROLES:
        raise TopologyError(f"unsupported V2 role in topology config: {value!r}")
    return cast(Role, role)


@dataclass(frozen=True)
class Condition:
    path: str
    equals: object

    def matches(self, artifacts: dict[str, object]) -> bool:
        node: object = artifacts
        for part in self.path.split("."):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return node == self.equals


@dataclass(frozen=True)
class NextRoleCandidate:
    role: Role
    condition: Condition | None = None


@dataclass(frozen=True)
class Topology:
    allowed_current_states_by_role: dict[Role, frozenset[str]]
    routes: dict[Role, dict[str, frozenset[Role]]]
    default_next_role_table: dict[str, tuple[NextRoleCandidate, ...]]

    def allowed_current_states(self, role: Role) -> frozenset[str]:
        return self.allowed_current_states_by_role[role]

    def routes_for_role(self, role: Role) -> dict[str, frozenset[Role]]:
        # Shallow copy: the inner values are frozensets (already immutable), so
        # copying the outer dict is enough to stop a caller from mutating the
        # module-level DEFAULT_TOPOLOGY singleton's data through this reference.
        return dict(self.routes[role])

    def default_next_role(
        self, state_name: str, artifacts: dict[str, object] | None = None
    ) -> Role:
        state_name = state_name.strip()
        candidates = self.default_next_role_table.get(state_name)
        if not candidates:
            raise TopologyError(f"unsupported round state for V2 routing: {state_name}")
        for candidate in candidates:
            if candidate.condition is None:
                return candidate.role
            if artifacts is not None and candidate.condition.matches(artifacts):
                return candidate.role
        raise TopologyError(
            f"no default_next_role candidate matched for state {state_name!r}"
        )

    @classmethod
    def from_state(cls, state: dict[str, object]) -> Topology:
        project = state.get("project")
        v2 = project.get("arcgentic_v2") if isinstance(project, dict) else None
        raw = v2.get("topology") if isinstance(v2, dict) else None
        if not raw:
            return DEFAULT_TOPOLOGY
        if not isinstance(raw, dict):
            raise TopologyError("project.arcgentic_v2.topology must be an object")
        return _parse_topology(raw)


def _parse_topology(raw: dict[str, object]) -> Topology:
    roles_raw = raw.get("roles")
    if not isinstance(roles_raw, dict):
        raise TopologyError("topology.roles must be an object")
    unknown_role_keys = sorted(set(roles_raw.keys()) - set(KNOWN_ROLES))
    if unknown_role_keys:
        joined = ", ".join(repr(k) for k in unknown_role_keys)
        raise TopologyError(f"topology.roles has unexpected role key(s): {joined}")
    allowed_current_states_by_role: dict[Role, frozenset[str]] = {}
    for role_name in KNOWN_ROLES:
        role = _normalize_role(role_name)
        entry = roles_raw.get(role_name)
        if not isinstance(entry, dict):
            raise TopologyError(f"topology.roles is missing role {role_name!r}")
        states = entry.get("allowed_current_states")
        if not isinstance(states, list) or not all(isinstance(s, str) for s in states):
            raise TopologyError(
                f"topology.roles.{role_name}.allowed_current_states must be a list of strings"
            )
        allowed_current_states_by_role[role] = frozenset(states)

    routes_raw = raw.get("routes")
    if not isinstance(routes_raw, dict):
        raise TopologyError("topology.routes must be an object")
    if routes_raw:
        unknown_route_keys = sorted(set(routes_raw.keys()) - set(KNOWN_ROLES))
        if unknown_route_keys:
            joined = ", ".join(repr(k) for k in unknown_route_keys)
            raise TopologyError(f"topology.routes has unexpected role key(s): {joined}")
    routes: dict[Role, dict[str, frozenset[Role]]] = {}
    for role_name in KNOWN_ROLES:
        role = _normalize_role(role_name)
        role_routes_raw = routes_raw.get(role_name, {})
        if not isinstance(role_routes_raw, dict):
            raise TopologyError(f"topology.routes.{role_name} must be an object")
        role_routes: dict[str, frozenset[Role]] = {}
        for state_name, next_roles_raw in role_routes_raw.items():
            if not isinstance(next_roles_raw, list):
                raise TopologyError(
                    f"topology.routes.{role_name}.{state_name} must be a list"
                )
            role_routes[state_name] = frozenset(
                _normalize_role(r) for r in next_roles_raw
            )
        routes[role] = role_routes

    default_next_role_raw = raw.get("default_next_role")
    if not isinstance(default_next_role_raw, dict):
        raise TopologyError("topology.default_next_role must be an object")
    default_next_role_table: dict[str, tuple[NextRoleCandidate, ...]] = {}
    for state_name, value in default_next_role_raw.items():
        candidates = _parse_default_next_role_value(state_name, value)
        default_next_role_table[state_name] = candidates

    return Topology(
        allowed_current_states_by_role=allowed_current_states_by_role,
        routes=routes,
        default_next_role_table=default_next_role_table,
    )


def _parse_default_next_role_value(
    state_name: str, value: object
) -> tuple[NextRoleCandidate, ...]:
    if isinstance(value, str):
        return (NextRoleCandidate(role=_normalize_role(value)),)
    if not isinstance(value, list) or not value:
        raise TopologyError(
            f"topology.default_next_role.{state_name} must be a role name or a "
            "non-empty list of candidates"
        )
    candidates: list[NextRoleCandidate] = []
    for entry in value:
        if not isinstance(entry, dict) or "role" not in entry:
            raise TopologyError(
                f"topology.default_next_role.{state_name} candidates must be "
                "objects with a 'role' key"
            )
        condition_raw = entry.get("condition")
        condition = None
        if condition_raw is not None:
            if (
                not isinstance(condition_raw, dict)
                or "path" not in condition_raw
                or "equals" not in condition_raw
            ):
                raise TopologyError(
                    f"topology.default_next_role.{state_name} condition must have "
                    "'path' and 'equals'"
                )
            condition = Condition(
                path=str(condition_raw["path"]), equals=condition_raw["equals"]
            )
        candidates.append(
            NextRoleCandidate(role=_normalize_role(entry["role"]), condition=condition)
        )
    if candidates[-1].condition is not None:
        raise TopologyError(
            f"default_next_role[{state_name}] must end with an unconditioned candidate"
        )
    return tuple(candidates)


_LEGACY_ALLOWED_CURRENT_STATES: Final[dict[Role, frozenset[str]]] = {
    "orchestrator": frozenset({"intake", "planning", "passed", "closed"}),
    "planner": frozenset({"intake", "planning", "passed", "closed"}),
    "developer": frozenset(
        {"awaiting_dev_start", "dev_in_progress", "needs_fix", "fix_in_progress"}
    ),
    "test": frozenset({"awaiting_test", "test_in_progress"}),
    "auditor": frozenset({"awaiting_audit", "audit_in_progress"}),
}

_LEGACY_ROUTES: Final[dict[Role, dict[str, frozenset[Role]]]] = {
    "orchestrator": {
        "planning": frozenset({"planner"}),
        "closed": frozenset({"planner"}),
    },
    "planner": {
        "awaiting_dev_start": frozenset({"developer"}),
        "planning": frozenset({"planner"}),
        "closed": frozenset({"planner"}),
    },
    "developer": {
        "awaiting_test": frozenset({"test"}),
        "awaiting_audit": frozenset({"auditor"}),
        "needs_fix": frozenset({"developer"}),
    },
    "test": {
        "awaiting_audit": frozenset({"auditor"}),
        "needs_fix": frozenset({"developer"}),
    },
    "auditor": {
        "passed": frozenset({"planner"}),
        "needs_fix": frozenset({"developer"}),
        "audit_in_progress": frozenset({"auditor"}),
    },
}

_LEGACY_DEFAULT_NEXT_ROLE: Final[dict[str, Role]] = {
    "intake": "planner",
    "planning": "planner",
    "passed": "planner",
    "closed": "planner",
    "awaiting_dev_start": "developer",
    "dev_in_progress": "developer",
    "needs_fix": "developer",
    "fix_in_progress": "developer",
    "awaiting_test": "test",
    "test_in_progress": "test",
    "awaiting_audit": "auditor",
    "audit_in_progress": "auditor",
}

DEFAULT_TOPOLOGY: Final[Topology] = Topology(
    allowed_current_states_by_role=dict(_LEGACY_ALLOWED_CURRENT_STATES),
    routes=dict(_LEGACY_ROUTES),
    default_next_role_table={
        state: (NextRoleCandidate(role=role),)
        for state, role in _LEGACY_DEFAULT_NEXT_ROLE.items()
    },
)
