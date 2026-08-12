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
    state: dict[str, object] = {
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
                        "awaiting_test": "test",
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
    state: dict[str, object] = {
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
    state: dict[str, object] = {
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
    state: dict[str, object] = {
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


def test_default_next_role_strips_state_name() -> None:
    assert DEFAULT_TOPOLOGY.default_next_role(" passed ") == "planner"


def test_routes_for_role_returns_copy_not_internal_reference() -> None:
    first = DEFAULT_TOPOLOGY.routes_for_role("auditor")
    second = DEFAULT_TOPOLOGY.routes_for_role("auditor")
    assert first is not second
    assert first == second


def _full_roles_block() -> dict[str, object]:
    return {
        "orchestrator": {"allowed_current_states": ["intake"]},
        "planner": {"allowed_current_states": ["intake"]},
        "developer": {"allowed_current_states": ["intake"]},
        "test": {"allowed_current_states": ["intake"]},
        "auditor": {
            "allowed_current_states": ["awaiting_audit", "audit_in_progress"]
        },
    }


def test_from_state_rejects_unknown_role_key_in_roles() -> None:
    roles = _full_roles_block()
    roles["auditr"] = {"allowed_current_states": ["awaiting_audit"]}
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": roles,
                    "routes": {},
                    "default_next_role": {"intake": "planner"},
                }
            }
        }
    }
    with pytest.raises(TopologyError, match="auditr"):
        Topology.from_state(state)


def test_from_state_rejects_unknown_role_key_in_routes() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": _full_roles_block(),
                    "routes": {"auditr": {"passed": ["planner"]}},
                    "default_next_role": {"intake": "planner"},
                }
            }
        }
    }
    with pytest.raises(TopologyError, match="auditr"):
        Topology.from_state(state)


def test_from_state_accepts_routes_state_with_matching_default_next_role() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": _full_roles_block(),
                    "routes": {"auditor": {"second_opinion": ["auditor"]}},
                    "default_next_role": {
                        "intake": "planner",
                        "audit_in_progress": "auditor",
                        "second_opinion": "auditor",
                    },
                }
            }
        }
    }
    topology = Topology.from_state(state)
    assert topology.routes_for_role("auditor") == {
        "second_opinion": frozenset({"auditor"})
    }


def test_from_state_rejects_routes_state_missing_default_next_role() -> None:
    # Reproduces the reviewer's finding: a routes entry for "second_opinion"
    # with no matching default_next_role entry lets apply_role_return_signal
    # write current_round.state = "second_opinion" while
    # build_role_session_plan can never route from it, wedging the round.
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "topology": {
                    "roles": _full_roles_block(),
                    "routes": {"auditor": {"second_opinion": ["auditor"]}},
                    "default_next_role": {
                        "intake": "planner",
                        "audit_in_progress": "auditor",
                    },
                }
            }
        }
    }
    with pytest.raises(TopologyError, match="second_opinion"):
        Topology.from_state(state)
