# Arcgentic V2 Topology Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three hardcoded role/state tables in `toolkit/src/arcgentic/v2_session_orchestration.py` (`ROLE_ALLOWED_CURRENT_STATES`, `ROLE_ALLOWED_SIGNAL_ROUTES`, `next_role_for_state`) with a project-configurable `Topology` object that defaults to byte-for-byte the same data, so zero-config projects see zero behavior change.

**Architecture:** One new module, `toolkit/src/arcgentic/topology.py`, owns the graph data (`Topology` dataclass). Its four call sites across two functions in `v2_session_orchestration.py` — three inside `apply_role_return_signal()` (Task 2), one inside `build_role_session_plan()` (Task 3) — are swapped from module-level dict lookups to `Topology.from_state(state)` method calls. `topology.py` has zero imports from `v2_session_orchestration.py` to avoid a circular import (see Task 1). No new runtime dependency, no change to `claude_code_broker.py` / `orchestrator_dispatch.py` (they only consume `apply_role_return_signal()`'s return value).

**Tech Stack:** Python 3.13, stdlib `dataclasses` + `typing`, pytest. No new third-party dependency.

## Global Constraints

- Zero-config (no `project.arcgentic_v2.topology` in state.yaml) dispatch decisions must be identical to pre-change behavior — verified by running the full existing `toolkit/tests/unit/test_v2_session_orchestration.py` suite unmodified.
- No `eval`/generic expression engine for `condition` — attribute-path + equality only.
- `mypy` and `ruff` must pass (per this repo's existing `toolkit/pyproject.toml` quality gates) — match existing type-annotation style (`from __future__ import annotations`, `Final`, `Literal`, frozen dataclasses).
- Design source of truth: [`docs/plans/2026-08-12-arcgentic-v2-topology-graph-engine-design.md`](./2026-08-12-arcgentic-v2-topology-graph-engine-design.md).

---

### Task 1: `Topology` module with default table + condition evaluation

**Files:**
- Create: `toolkit/src/arcgentic/topology.py`
- Test: `toolkit/tests/unit/test_topology.py`

**Interfaces:**
- Produces: `Topology` (frozen dataclass), `DEFAULT_TOPOLOGY: Final[Topology]`, `NextRoleCandidate` (frozen dataclass: `role: Role`, `condition: Condition | None = None`), `Condition` (frozen dataclass: `path: str`, `equals: object`), `TopologyError(ValueError)`, `Role` (type alias), `KNOWN_ROLES: Final[tuple[Role, ...]]`.
  - `Topology.allowed_current_states(role: Role) -> frozenset[str]`
  - `Topology.routes_for_role(role: Role) -> dict[str, frozenset[Role]]`
  - `Topology.default_next_role(state_name: str, artifacts: dict[str, object] | None = None) -> Role`
  - `Topology.from_state(state: dict[str, object]) -> Topology` (returns `DEFAULT_TOPOLOGY` when `project.arcgentic_v2.topology` is absent)
- Consumes: nothing from `v2_session_orchestration.py`. **`topology.py` must have zero imports from `v2_session_orchestration.py`** — Task 2/3 make `v2_session_orchestration.py` import `Topology` from `topology.py`, so the reverse import would be circular. `topology.py` defines its own `Role = Literal["orchestrator", "planner", "developer", "test", "auditor"]` and its own role-name validation (`_normalize_role`), independent of the structurally-identical `Role`/`normalize_role` in `v2_session_orchestration.py`. mypy checks `Literal` types structurally, so this duplication cannot silently drift without a type error at the Task 2/3 call sites.

- [ ] **Step 1: Write the failing tests for the default topology**

```python
# toolkit/tests/unit/test_topology.py
from __future__ import annotations

import pytest

from arcgentic.topology import DEFAULT_TOPOLOGY, Topology, TopologyError


def test_default_topology_allowed_current_states_match_legacy_table() -> None:
    assert DEFAULT_TOPOLOGY.allowed_current_states("orchestrator") == frozenset(
        {"intake", "planning", "passed", "closed"}
    )
    assert DEFAULT_TOPOLOGY.allowed_current_states("planner") == frozenset(
        {"intake", "planning", "passed", "closed"}
    )
    assert DEFAULT_TOPOLOGY.allowed_current_states("developer") == frozenset(
        {"awaiting_dev_start", "dev_in_progress", "needs_fix", "fix_in_progress"}
    )
    assert DEFAULT_TOPOLOGY.allowed_current_states("test") == frozenset(
        {"awaiting_test", "test_in_progress"}
    )
    assert DEFAULT_TOPOLOGY.allowed_current_states("auditor") == frozenset(
        {"awaiting_audit", "audit_in_progress"}
    )


def test_default_topology_routes_match_legacy_table() -> None:
    assert DEFAULT_TOPOLOGY.routes_for_role("auditor") == {
        "passed": frozenset({"planner"}),
        "needs_fix": frozenset({"developer"}),
        "audit_in_progress": frozenset({"auditor"}),
    }


def test_default_topology_default_next_role_matches_legacy_function() -> None:
    assert DEFAULT_TOPOLOGY.default_next_role("needs_fix") == "developer"
    assert DEFAULT_TOPOLOGY.default_next_role("awaiting_test") == "test"
    assert DEFAULT_TOPOLOGY.default_next_role("passed") == "planner"


def test_default_topology_rejects_unknown_state() -> None:
    with pytest.raises(TopologyError, match="unsupported round state for V2 routing: bogus"):
        DEFAULT_TOPOLOGY.default_next_role("bogus")


def test_from_state_returns_default_when_topology_absent() -> None:
    assert Topology.from_state({}) is DEFAULT_TOPOLOGY
    assert Topology.from_state({"project": {"arcgentic_v2": {}}}) is DEFAULT_TOPOLOGY


def test_from_state_parses_custom_routes_and_allowed_states() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": {
                        "orchestrator": {"allowed_current_states": ["intake"]},
                        "planner": {"allowed_current_states": ["intake", "planning"]},
                        "developer": {"allowed_current_states": ["dev_in_progress"]},
                        "test": {"allowed_current_states": ["awaiting_test"]},
                        "auditor": {"allowed_current_states": ["awaiting_audit"]},
                    },
                    "routes": {
                        "developer": {"awaiting_test": ["test"]},
                    },
                    "default_next_role": {
                        "dev_in_progress": "developer",
                    },
                }
            }
        }
    }
    topology = Topology.from_state(state)
    assert topology.allowed_current_states("orchestrator") == frozenset({"intake"})
    assert topology.routes_for_role("developer") == {"awaiting_test": frozenset({"test"})}
    assert topology.default_next_role("dev_in_progress") == "developer"


def test_from_state_requires_all_five_roles() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": {"orchestrator": {"allowed_current_states": ["intake"]}},
                    "routes": {},
                    "default_next_role": {},
                }
            }
        }
    }
    with pytest.raises(TopologyError, match="topology.roles is missing role"):
        Topology.from_state(state)


def test_default_next_role_evaluates_condition_candidates_in_order() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": {
                        "orchestrator": {"allowed_current_states": ["intake"]},
                        "planner": {"allowed_current_states": ["intake"]},
                        "developer": {"allowed_current_states": ["intake"]},
                        "test": {"allowed_current_states": ["intake"]},
                        "auditor": {"allowed_current_states": ["intake"]},
                    },
                    "routes": {},
                    "default_next_role": {
                        "audit_in_progress": [
                            {
                                "role": "planner",
                                "condition": {"path": "audit_verdict.outcome", "equals": "PASS"},
                            },
                            {"role": "developer"},
                        ]
                    },
                }
            }
        }
    }
    topology = Topology.from_state(state)
    assert (
        topology.default_next_role(
            "audit_in_progress", {"audit_verdict": {"outcome": "PASS"}}
        )
        == "planner"
    )
    assert (
        topology.default_next_role(
            "audit_in_progress", {"audit_verdict": {"outcome": "NEEDS_FIX"}}
        )
        == "developer"
    )
    assert topology.default_next_role("audit_in_progress", None) == "developer"


def test_default_next_role_candidate_list_requires_unconditioned_fallback_last() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": {
                        "orchestrator": {"allowed_current_states": ["intake"]},
                        "planner": {"allowed_current_states": ["intake"]},
                        "developer": {"allowed_current_states": ["intake"]},
                        "test": {"allowed_current_states": ["intake"]},
                        "auditor": {"allowed_current_states": ["intake"]},
                    },
                    "routes": {},
                    "default_next_role": {
                        "audit_in_progress": [
                            {
                                "role": "planner",
                                "condition": {"path": "audit_verdict.outcome", "equals": "PASS"},
                            }
                        ]
                    },
                }
            }
        }
    }
    with pytest.raises(
        TopologyError,
        match="default_next_role\\[audit_in_progress\\] must end with an unconditioned candidate",
    ):
        Topology.from_state(state)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd toolkit && python -m pytest tests/unit/test_topology.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcgentic.topology'`

- [ ] **Step 3: Implement `toolkit/src/arcgentic/topology.py`**

```python
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
        return self.routes[role]

    def default_next_role(
        self, state_name: str, artifacts: dict[str, object] | None = None
    ) -> Role:
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
```

Note: `Topology.from_state` uses `dict.get` chains without the `isinstance` guards that `_project_v2_block` in `v2_session_orchestration.py` already has — this is intentional duplication of a *narrower* check (only reading, never raising on non-object `project`/`arcgentic_v2`, since an absent/malformed block just means "use defaults", which `apply_role_return_signal` already validates elsewhere before topology is ever consulted).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd toolkit && python -m pytest tests/unit/test_topology.py -v`
Expected: PASS (all 9 tests)

- [ ] **Step 5: Run mypy and ruff**

Run: `cd toolkit && python -m mypy src/arcgentic/topology.py && python -m ruff check src/arcgentic/topology.py tests/unit/test_topology.py`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/src/arcgentic/topology.py toolkit/tests/unit/test_topology.py
git commit -m "feat(v2): add data-driven Topology replacing hardcoded role/state tables

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Wire `apply_role_return_signal()` to `Topology`

**Files:**
- Modify: `toolkit/src/arcgentic/v2_session_orchestration.py:761,771,777`
- Test: `toolkit/tests/unit/test_v2_session_orchestration.py` (existing suite — no edits expected; this task's pass criterion IS the existing suite passing unmodified)

**Interfaces:**
- Consumes: `Topology.from_state`, `Topology.allowed_current_states`, `Topology.routes_for_role`, `Topology.default_next_role`, `TopologyError` (from Task 1).

**Exception translation note:** `TopologyError` (Task 1) does NOT subclass `V2SessionOrchestrationError` — `topology.py` has zero imports from this module (see Task 1's circular-import note), so it cannot reference `V2SessionOrchestrationError` to subclass it. `claude_code_broker.py:123,150` and `cli.py:771,821,898` catch `V2SessionOrchestrationError` specifically around calls that reach `apply_role_return_signal`. To keep that contract, wrap the topology lookups in a `try`/`except TopologyError` that re-raises as `V2SessionOrchestrationError` with the same message, at the point they're first called in this function — not scattered per-lookup.

- [ ] **Step 1: Read the exact current lines to confirm no drift**

Run: `sed -n '738,790p' toolkit/src/arcgentic/v2_session_orchestration.py`

Confirm lines 761, 771, and 777 still read exactly:
```python
    allowed_current_states = ROLE_ALLOWED_CURRENT_STATES[signal.role]
```
```python
    route_options = ROLE_ALLOWED_SIGNAL_ROUTES[signal.role]
```
```python
    next_role = signal.next_recommended_role or next_role_for_state(signal.state)
```

If line numbers have drifted (e.g. Task 1's import changed nothing in this file, so they should not have), locate by searching for these exact strings instead of trusting line numbers.

- [ ] **Step 2: Replace the three lookups**

In `apply_role_return_signal()`, change:

```python
    allowed_current_states = ROLE_ALLOWED_CURRENT_STATES[signal.role]
```
to:
```python
    topology = Topology.from_state(state)
    try:
        allowed_current_states = topology.allowed_current_states(signal.role)
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
```

Change:
```python
    route_options = ROLE_ALLOWED_SIGNAL_ROUTES[signal.role]
```
to:
```python
    try:
        route_options = topology.routes_for_role(signal.role)
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
```

Change:
```python
    next_role = signal.next_recommended_role or next_role_for_state(signal.state)
```
to:
```python
    try:
        next_role = signal.next_recommended_role or topology.default_next_role(
            signal.state, signal.artifacts
        )
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
```

Add the import at the top of the file (alongside the existing local imports):
```python
from arcgentic.topology import Topology, TopologyError
```

`allowed_current_states` and `route_options` are computed once, near the top of the function, before both are used later in the function body — do not move the `topology = Topology.from_state(state)` line past their first use. Each `try`/`except` block is intentionally narrow (wraps one lookup, not the whole function) so a `TopologyError` from an unrelated later line (e.g. a validator further down) is never accidentally swallowed here.

- [ ] **Step 3: Run the full existing V2 orchestration test suite**

Run: `cd toolkit && python -m pytest tests/unit/test_v2_session_orchestration.py -v`
Expected: PASS, same test count as before this task (no test file changes in this task) — this is the equivalence proof for `apply_role_return_signal`.

- [ ] **Step 4: Run mypy and ruff**

Run: `cd toolkit && python -m mypy src/arcgentic/v2_session_orchestration.py && python -m ruff check src/arcgentic/v2_session_orchestration.py`
Expected: no errors. If `ruff` flags `ROLE_ALLOWED_CURRENT_STATES` / `ROLE_ALLOWED_SIGNAL_ROUTES` / `next_role_for_state` as now-unused module-level names, do NOT delete them yet — Task 3 still uses `next_role_for_state` at a second call site, and `toolkit/tests/unit/test_v2_session_orchestration.py:11` imports `next_role_for_state` directly (see Task 3's note on why this stays a public function, just no longer called internally by `apply_role_return_signal`).

- [ ] **Step 5: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/src/arcgentic/v2_session_orchestration.py
git commit -m "refactor(v2): route apply_role_return_signal through Topology

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Wire `build_role_session_plan()` to `Topology`

**Files:**
- Modify: `toolkit/src/arcgentic/v2_session_orchestration.py:1009`

**Interfaces:**
- Consumes: `Topology.from_state`, `Topology.default_next_role`, `TopologyError` (from Task 1).

**Why this is a separate task from Task 2:** `next_role_for_state(current_state)` is called at two independent sites in this file (`:777` inside `apply_role_return_signal`, already handled in Task 2; `:1009` inside `build_role_session_plan`, handled here). `build_role_session_plan` runs on cold start / resume — there is no `RoleReturnSignal` in scope yet, so there are no `artifacts` to evaluate a `condition` against; `Topology.default_next_role` already handles `artifacts=None` by skipping conditioned candidates and falling through to the mandatory unconditioned last candidate (verified by Task 1's `test_default_next_role_evaluates_condition_candidates_in_order`, last assertion).

- [ ] **Step 1: Replace the lookup**

`build_role_session_plan()` raises `V2SessionOrchestrationError` elsewhere in its body (e.g. `V2_MODE_CHOICE_MESSAGE`, `:1001`), so callers expect that exception type from this function too — apply the same `TopologyError` → `V2SessionOrchestrationError` translation as Task 2.

In `build_role_session_plan()`, change:
```python
    next_role = next_role_for_state(current_state)
```
to:
```python
    try:
        next_role = Topology.from_state(state).default_next_role(current_state)
    except TopologyError as exc:
        raise V2SessionOrchestrationError(str(exc)) from exc
```

(`Topology` and `TopologyError` are already imported at the top of this file from Task 2 — no new import needed here.)

- [ ] **Step 2: Run the full existing V2 orchestration test suite**

Run: `cd toolkit && python -m pytest tests/unit/test_v2_session_orchestration.py -v`
Expected: PASS, same test count as before this task.

- [ ] **Step 3: Confirm `next_role_for_state` is still exported for the existing test file's direct import**

Run: `grep -n "^def next_role_for_state" toolkit/src/arcgentic/v2_session_orchestration.py`
Expected: the function definition (lines 426-436) is untouched — it is no longer called from within this module, but stays as a public function because `toolkit/tests/unit/test_v2_session_orchestration.py:11` imports and calls it directly (lines 259-269). Do not delete or rename it.

- [ ] **Step 4: Run mypy and ruff**

Run: `cd toolkit && python -m mypy src/arcgentic/v2_session_orchestration.py && python -m ruff check src/arcgentic/v2_session_orchestration.py`
Expected: no errors, no unused-name warnings (the function is still used by the test suite, which ruff's default config does not scan for cross-file usage of a `def`, so this should already be clean; if `ruff` still flags it, add `# noqa: keeping for test-suite direct import compatibility` on the def line rather than suppressing project-wide).

- [ ] **Step 5: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/src/arcgentic/v2_session_orchestration.py
git commit -m "refactor(v2): route build_role_session_plan through Topology

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Schema — loosen `current_round.state` enum, declare `topology`

**Files:**
- Modify: `schema/state.schema.json`

**Interfaces:** none (schema-only change; nothing in the V2 Python path currently validates state.yaml against this file — see design doc §3.3 — so this task cannot break V2 runtime behavior; it only keeps the schema truthful for anything that does read it, e.g. IDE tooling or the V1 bash `validate-schema.sh`).

- [ ] **Step 1: Loosen the `current_round.state` enum**

In `schema/state.schema.json`, find:
```json
        "state": {
          "type": "string",
          "enum": ["intake", "planning", "awaiting_dev_start", "dev_in_progress", "awaiting_test", "test_in_progress", "awaiting_audit", "audit_in_progress", "passed", "needs_fix", "fix_in_progress", "closed"]
        },
```
Replace with:
```json
        "state": {
          "type": "string",
          "minLength": 1,
          "description": "Round state. Validated against the project's active topology at runtime (project.arcgentic_v2.topology if set, else the built-in default 12-state graph) — not by this schema, which cannot express that cross-field constraint."
        },
```

- [ ] **Step 2: Add `topology` to the `arcgentic_v2` object**

In `schema/state.schema.json`, inside `properties.project.properties.arcgentic_v2.properties` (the object that already has `host`, `mode`, `next_role`, etc.), add a new property:
```json
            "topology": {
              "type": "object",
              "additionalProperties": false,
              "description": "Optional project-defined role/state routing graph. Omit to use the built-in default (today's fixed 5-role sequence). See toolkit/src/arcgentic/topology.py.",
              "properties": {
                "roles": { "type": "object" },
                "routes": { "type": "object" },
                "default_next_role": { "type": "object" }
              }
            },
```

Place it alphabetically-adjacent to the existing `role_sessions` property for readability (exact position does not affect validation).

- [ ] **Step 3: Validate the schema file itself is well-formed JSON**

Run: `python3 -c "import json; json.load(open('schema/state.schema.json')); print('ok')"`
Expected: `ok`

- [ ] **Step 4: Run the existing bash schema test (V1 path — confirm no regression)**

Run: `bash scripts/state/validate-schema.test.sh`
Expected: PASS (same as before this task)

- [ ] **Step 5: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add schema/state.schema.json
git commit -m "schema: loosen current_round.state enum, declare arcgentic_v2.topology

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: End-to-end custom-topology test through the public API

**Files:**
- Modify: `toolkit/tests/unit/test_v2_session_orchestration.py` (add new tests; do not edit existing ones)

**Interfaces:**
- Consumes: `apply_role_return_signal`, `RoleReturnSignal` (existing), a custom `topology` block in the `state` dict fixture (Task 1/4 shapes).

This task proves the whole stack (Task 1 + Task 2 wired together) with a custom topology exercised through the real public entry point, not just `Topology` in isolation.

- [ ] **Step 1: Write the failing test**

Add to `toolkit/tests/unit/test_v2_session_orchestration.py`:

```python
def test_apply_role_return_signal_uses_custom_topology_condition() -> None:
    custom_topology = {
        "roles": {
            "orchestrator": {"allowed_current_states": ["intake", "planning", "passed", "closed"]},
            "planner": {"allowed_current_states": ["intake", "planning", "passed", "closed"]},
            "developer": {
                "allowed_current_states": [
                    "awaiting_dev_start",
                    "dev_in_progress",
                    "needs_fix",
                    "fix_in_progress",
                ]
            },
            "test": {"allowed_current_states": ["awaiting_test", "test_in_progress"]},
            "auditor": {"allowed_current_states": ["awaiting_audit", "audit_in_progress"]},
        },
        "routes": {
            "auditor": {
                "passed": ["planner"],
                "needs_fix": ["developer"],
                "audit_in_progress": ["auditor"],
            },
        },
        "default_next_role": {
            "passed": [
                {
                    "role": "developer",
                    "condition": {"path": "audit_verdict.rush_release", "equals": True},
                },
                {"role": "planner"},
            ],
        },
    }
    state = {
        "project": {"arcgentic_v2": {"host": "codex", "topology": custom_topology}},
        "current_round": {"id": "R1", "state": "audit_in_progress"},
    }
    signal = RoleReturnSignal(
        role="auditor",
        status="PASS",
        round_id="R1",
        state="passed",
        artifacts={
            "verdict": "docs/audits/R1.md",
            "commit": "a" * 40,
            "audit_verdict": {"rush_release": True},
        },
    )

    updated = apply_role_return_signal(state, signal)

    assert updated["project"]["arcgentic_v2"]["next_role"] == "developer"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd toolkit && python -m pytest tests/unit/test_v2_session_orchestration.py::test_apply_role_return_signal_uses_custom_topology_condition -v`
Expected: FAIL before Task 1-2 land, or PASS immediately if this task runs after Task 1-2 are already committed (in which case this step confirms Task 1-2 actually did their job — treat an unexpected FAIL here as a signal to re-check Task 2's wiring, not as "test is broken").

- [ ] **Step 3: Run it to verify it passes**

Run: `cd toolkit && python -m pytest tests/unit/test_v2_session_orchestration.py -v`
Expected: PASS, full suite including the new test.

- [ ] **Step 4: Run mypy and ruff on the test file**

Run: `cd toolkit && python -m mypy tests/unit/test_v2_session_orchestration.py && python -m ruff check tests/unit/test_v2_session_orchestration.py`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/tests/unit/test_v2_session_orchestration.py
git commit -m "test(v2): cover apply_role_return_signal with a custom conditioned topology

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Full-suite regression + flag out-of-scope V1 cleanup

**Files:** none created/modified — verification-only task, plus one `spawn_task` flag.

- [ ] **Step 1: Run the entire toolkit test suite**

Run: `cd toolkit && python -m pytest -q`
Expected: all tests pass, including `tests/unit/test_v2_session_orchestration.py`, `tests/unit/test_topology.py`, `tests/unit/test_claude_code_broker.py`, `tests/integration/test_end_to_end_round.py`.

- [ ] **Step 2: Run mypy and ruff across the whole toolkit**

Run: `cd toolkit && python -m mypy src/ && python -m ruff check src/ tests/`
Expected: no errors.

- [ ] **Step 3: Run the bash test suite (V1 path — must be untouched)**

Run: `for f in scripts/**/*.test.sh tests/integration/*.test.sh; do bash "$f" || echo "FAILED: $f"; done`
Expected: no `FAILED:` lines.

- [ ] **Step 4: Flag the V1 bash state machine as dead code for separate cleanup**

This plan explicitly does not touch `scripts/state/*.sh` or the schema's now-unused-by-V2 `states` field (per the design doc §4). Use the `mcp__ccd_session__spawn_task` tool to flag it as a follow-up, title "Retire or clearly mark scripts/state/*.sh as V1-only", so it does not get silently forgotten now that V2 has its own topology mechanism.

- [ ] **Step 5: Update `toolkit/README.md` changelog/status note if one exists**

Run: `grep -n "topology\|## Changelog\|## Status" toolkit/README.md`

If a changelog or status section exists, add a one-line entry noting `project.arcgentic_v2.topology` is now available for custom role/state routing, defaulting to the existing 5-role sequence. If no such section exists, skip this step — do not invent a new doc section as part of this task.

- [ ] **Step 6: Final commit (only if Step 5 produced a change)**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/README.md
git commit -m "docs(toolkit): note arcgentic_v2.topology availability

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
