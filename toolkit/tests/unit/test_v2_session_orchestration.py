from __future__ import annotations

from arcgentic.v2_session_orchestration import (
    FIXED_ROLE_TITLES,
    RoleReturnSignal,
    build_codex_role_session_plan,
    next_role_for_state,
    role_prompt,
)


def test_fixed_role_titles_do_not_include_round_ids() -> None:
    assert FIXED_ROLE_TITLES == {
        "orchestrator": "Orchestrator",
        "planner": "Planner",
        "developer": "Developer",
        "auditor": "Auditor",
    }


def test_codex_plan_reuses_existing_threads_and_creates_missing_roles() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "role_sessions": {
                    "orchestrator": {"thread_id": "orch-1", "title": "Orchestrator"},
                    "developer": {"thread_id": "dev-1", "title": "Developer"},
                },
            }
        },
        "current_round": {"id": "R2", "state": "awaiting_dev_start"},
    }

    plan = build_codex_role_session_plan(state)

    assert [action.role for action in plan.actions] == [
        "orchestrator",
        "planner",
        "developer",
        "auditor",
    ]
    assert plan.actions[0].kind == "reuse"
    assert plan.actions[0].thread_id == "orch-1"
    assert plan.actions[1].kind == "create"
    assert plan.actions[1].title == "Planner"
    assert plan.actions[2].kind == "reuse"
    assert plan.actions[2].thread_id == "dev-1"
    assert plan.actions[3].kind == "create"


def test_needs_fix_routes_back_to_developer() -> None:
    assert next_role_for_state("needs_fix") == "developer"
    assert next_role_for_state("fix_in_progress") == "developer"


def test_passed_routes_to_planner_for_phase_decision_not_closeout() -> None:
    assert next_role_for_state("passed") == "planner"


def test_role_return_signal_round_trips_json() -> None:
    signal = RoleReturnSignal(
        role="developer",
        status="completed",
        round_id="R1",
        state="awaiting_audit",
        artifacts={"self_audit": "docs/audits/R1-self-audit.md"},
        next_recommended_role="auditor",
    )

    parsed = RoleReturnSignal.from_json(signal.to_json())

    assert parsed == signal


def test_role_prompt_mentions_fixed_role_and_current_round() -> None:
    state: dict[str, object] = {"current_round": {"id": "R3", "state": "awaiting_audit"}}

    prompt = role_prompt("auditor", state)

    assert "You are Auditor." in prompt
    assert "Current round: R3" in prompt
    assert "Return a RoleReturnSignal JSON object" in prompt
