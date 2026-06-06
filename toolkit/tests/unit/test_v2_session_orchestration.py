from __future__ import annotations

from arcgentic.v2_session_orchestration import (
    FIXED_ROLE_TITLES,
    RoleReturnSignal,
    apply_role_return_signal,
    build_codex_role_session_plan,
    next_role_for_state,
    record_role_session,
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


def test_record_role_session_persists_fixed_title_and_thread_id() -> None:
    state: dict[str, object] = {"project": {"name": "demo"}}

    updated = record_role_session(state, "developer", thread_id="thread-dev-1")

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    sessions = v2["role_sessions"]
    assert isinstance(sessions, dict)
    developer = sessions["developer"]
    assert isinstance(developer, dict)
    assert developer["thread_id"] == "thread-dev-1"
    assert developer["title"] == "Developer"
    assert developer["host"] == "codex"
    assert isinstance(developer["updated_at"], str)


def test_record_role_session_rejects_non_fixed_title() -> None:
    state: dict[str, object] = {"project": {}}

    try:
        record_role_session(state, "auditor", thread_id="audit-1", title="R2 Auditor")
    except ValueError as exc:
        assert "fixed title" in str(exc)
    else:
        raise AssertionError("expected non-fixed title to be rejected")


def test_apply_role_return_signal_stores_signal_and_next_role() -> None:
    state: dict[str, object] = {
        "project": {},
        "current_round": {"id": "R4", "state": "awaiting_audit"},
    }
    signal = RoleReturnSignal(
        role="auditor",
        status="NEEDS_FIX",
        round_id="R4",
        state="needs_fix",
        artifacts={"verdict": "docs/audits/R4.md"},
        next_recommended_role="developer",
    )

    updated = apply_role_return_signal(state, signal)

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["last_signal"] == signal.to_dict()
    assert v2["next_role"] == "developer"
    current_round = updated["current_round"]
    assert isinstance(current_round, dict)
    assert current_round["state"] == "needs_fix"
