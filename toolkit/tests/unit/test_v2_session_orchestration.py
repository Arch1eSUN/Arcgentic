from __future__ import annotations

from arcgentic.v2_session_orchestration import (
    FIXED_ROLE_TITLES,
    RoleReturnSignal,
    V2SessionOrchestrationError,
    apply_role_return_signal,
    build_codex_role_session_plan,
    ensure_initial_round_id,
    next_role_for_state,
    record_role_dispatch,
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


def test_codex_plan_dispatches_only_the_next_role() -> None:
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

    assert plan.orchestrator_status == "active"
    assert plan.next_role == "developer"
    assert len(plan.actions) == 1
    assert plan.actions[0].role == "developer"
    assert plan.actions[0].kind == "reuse"
    assert plan.actions[0].thread_id == "dev-1"


def test_sleeping_codex_plan_does_not_dispatch_more_actions() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "orchestrator_status": "sleeping",
                "pending_role": "planner",
                "pending_thread_id": "planner-1",
                "role_sessions": {
                    "planner": {"thread_id": "planner-1", "title": "Planner"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "planning"},
    }

    plan = build_codex_role_session_plan(state)

    assert plan.orchestrator_status == "sleeping"
    assert plan.next_role == "planner"
    assert plan.pending_role == "planner"
    assert plan.pending_thread_id == "planner-1"
    assert plan.actions == ()


def test_needs_fix_routes_back_to_developer() -> None:
    assert next_role_for_state("needs_fix") == "developer"
    assert next_role_for_state("fix_in_progress") == "developer"


def test_passed_routes_to_planner_for_phase_decision_not_closeout() -> None:
    assert next_role_for_state("passed") == "planner"


def test_closed_round_routes_new_requests_to_planner() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "role_sessions": {
                    "planner": {"thread_id": "planner-1", "title": "Planner"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "closed"},
    }

    plan = build_codex_role_session_plan(state)

    assert plan.orchestrator_status == "active"
    assert plan.next_role == "planner"
    assert len(plan.actions) == 1
    assert plan.actions[0].role == "planner"
    assert plan.actions[0].kind == "reuse"
    assert plan.actions[0].thread_id == "planner-1"


def test_session_plan_injects_user_request_into_role_prompt() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "role_sessions": {},
            }
        },
        "current_round": {"id": "R1", "state": "closed"},
    }

    plan = build_codex_role_session_plan(
        state, user_request="我想做一个极简 todo CLI。请用 Arcgentic 来完成。"
    )

    assert len(plan.actions) == 1
    assert "Current user request: 我想做一个极简 todo CLI" in plan.actions[0].prompt
    assert "must decide the next phase or next round" in plan.actions[0].prompt


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


def test_role_return_signal_rejects_extra_fields() -> None:
    payload = (
        '{"role":"planner","status":"completed","round_id":"R1",'
        '"state":"awaiting_dev_start","artifacts":{"handoff":"docs/plans/R1.md"},'
        '"next_recommended_role":"developer","plan":{"steps":[]}}'
    )

    try:
        RoleReturnSignal.from_json(payload)
    except V2SessionOrchestrationError as exc:
        assert "unexpected fields: plan" in str(exc)
    else:
        raise AssertionError("expected extra RoleReturnSignal fields to be rejected")


def test_role_prompt_mentions_fixed_role_and_current_round() -> None:
    state: dict[str, object] = {"current_round": {"id": "R3", "state": "awaiting_audit"}}

    prompt = role_prompt("auditor", state)

    assert "You are Auditor." in prompt
    assert "Current round: R3" in prompt
    assert "Only the Orchestrator may mutate .agentic-rounds/state.yaml" in prompt
    assert "Do not stop after acknowledging the role" in prompt
    assert "project.arcgentic_v2.last_signal.artifacts" in prompt
    assert "Return a RoleReturnSignal JSON object" in prompt


def test_initial_round_id_defaults_to_r1_before_planning() -> None:
    state: dict[str, object] = {"current_round": {"id": "", "state": "intake"}}

    updated = ensure_initial_round_id(state)

    assert updated["current_round"] == {"id": "R1", "state": "intake"}
    assert state["current_round"] == {"id": "", "state": "intake"}


def test_initial_round_id_is_not_rewritten_when_present() -> None:
    state: dict[str, object] = {"current_round": {"id": "R4", "state": "planning"}}

    updated = ensure_initial_round_id(state)

    assert updated is state


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


def test_record_role_dispatch_puts_orchestrator_to_sleep() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "role_sessions": {
                    "planner": {"thread_id": "planner-1", "title": "Planner"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "planning"},
    }

    updated = record_role_dispatch(state, "planner", thread_id="planner-1")

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["orchestrator_status"] == "sleeping"
    assert v2["pending_role"] == "planner"
    assert v2["pending_thread_id"] == "planner-1"
    assert isinstance(v2["pending_since"], str)


def test_apply_role_return_signal_stores_signal_and_next_role() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "auditor",
                "pending_thread_id": "audit-1",
            }
        },
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
    assert v2["orchestrator_status"] == "active"
    assert "pending_role" not in v2
    assert "pending_thread_id" not in v2
    current_round = updated["current_round"]
    assert isinstance(current_round, dict)
    assert current_round["state"] == "needs_fix"


def test_apply_role_return_signal_rejects_non_pending_role_while_sleeping() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "developer",
                "pending_thread_id": "dev-1",
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_audit"},
    }
    signal = RoleReturnSignal(
        role="auditor",
        status="PASS",
        round_id="R1",
        state="passed",
        artifacts={"verdict": "docs/audits/R1.md"},
        next_recommended_role="planner",
    )

    try:
        apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        assert "waiting for developer, got auditor" in str(exc)
    else:
        raise AssertionError("expected non-pending sleeping role to be rejected")


def test_apply_role_return_signal_rejects_stale_role_state() -> None:
    state: dict[str, object] = {
        "project": {},
        "current_round": {"id": "R1", "state": "awaiting_audit"},
    }
    signal = RoleReturnSignal(
        role="planner",
        status="completed",
        round_id="R1",
        state="awaiting_dev_start",
        artifacts={"handoff": "docs/plans/R1.md"},
        next_recommended_role="developer",
    )

    try:
        apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        assert "stale planner signal" in str(exc)
    else:
        raise AssertionError("expected stale planner signal to be rejected")


def test_apply_role_return_signal_rejects_planner_skipping_developer() -> None:
    state: dict[str, object] = {
        "project": {},
        "current_round": {"id": "R1", "state": "planning"},
    }
    signal = RoleReturnSignal(
        role="planner",
        status="completed",
        round_id="R1",
        state="awaiting_audit",
        artifacts={"handoff": "docs/plans/R1.md"},
        next_recommended_role="auditor",
    )

    try:
        apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        assert "planner cannot route round to state 'awaiting_audit'" in str(exc)
    else:
        raise AssertionError("expected planner audit skip to be rejected")


def test_apply_role_return_signal_rejects_wrong_next_role_for_state() -> None:
    state: dict[str, object] = {
        "project": {},
        "current_round": {"id": "R1", "state": "planning"},
    }
    signal = RoleReturnSignal(
        role="planner",
        status="completed",
        round_id="R1",
        state="awaiting_dev_start",
        artifacts={"handoff": "docs/plans/R1.md"},
        next_recommended_role="auditor",
    )

    try:
        apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        assert "cannot recommend next role 'auditor'" in str(exc)
    else:
        raise AssertionError("expected wrong next role to be rejected")
