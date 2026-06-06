from __future__ import annotations

from arcgentic.v2_session_orchestration import (
    FIXED_ROLE_TITLES,
    RoleReturnSignal,
    V2SessionOrchestrationError,
    advance_passed_round_from_project_plan,
    apply_role_return_signal,
    build_codex_role_session_plan,
    ensure_initial_round_id,
    next_role_for_state,
    record_role_dispatch,
    record_role_session,
    role_prompt,
    set_v2_mode,
)


def test_fixed_role_titles_do_not_include_round_ids() -> None:
    assert FIXED_ROLE_TITLES == {
        "orchestrator": "Orchestrator",
        "planner": "Planner",
        "developer": "Developer",
        "test": "Test",
        "auditor": "Auditor",
    }


def test_record_role_session_rejects_role_thread_overwrite() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "role_sessions": {
                    "auditor": {"thread_id": "auditor-1", "title": "Auditor"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_audit"},
    }

    try:
        record_role_session(state, "auditor", thread_id="auditor-2", title="Auditor")
    except V2SessionOrchestrationError as exc:
        assert "already recorded as thread 'auditor-1'" in str(exc)
    else:
        raise AssertionError("expected duplicate Auditor thread recording to be rejected")


def test_record_role_session_repairs_current_orchestrator_only_when_explicit() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "role_sessions": {
                    "orchestrator": {"thread_id": "source-thread", "title": "Orchestrator"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "intake"},
    }

    updated = record_role_session(
        state,
        "orchestrator",
        thread_id="current-thread",
        title="Orchestrator",
        repair_current_orchestrator=True,
    )

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    sessions = v2["role_sessions"]
    assert isinstance(sessions, dict)
    orchestrator = sessions["orchestrator"]
    assert isinstance(orchestrator, dict)
    assert orchestrator["thread_id"] == "current-thread"


def test_record_role_session_repair_flag_does_not_overwrite_role_threads() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "role_sessions": {
                    "developer": {"thread_id": "dev-1", "title": "Developer"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_dev_start"},
    }

    try:
        record_role_session(
            state,
            "developer",
            thread_id="dev-2",
            title="Developer",
            repair_current_orchestrator=True,
        )
    except V2SessionOrchestrationError as exc:
        assert "--repair-current-orchestrator can only repair" in str(exc)
    else:
        raise AssertionError("expected repair flag to reject non-Orchestrator roles")


def test_record_role_session_allows_idempotent_same_thread_recording() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "role_sessions": {
                    "auditor": {"thread_id": "auditor-1", "title": "Auditor"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_audit"},
    }

    updated = record_role_session(state, "auditor", thread_id="auditor-1", title="Auditor")

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    sessions = v2["role_sessions"]
    assert isinstance(sessions, dict)
    auditor = sessions["auditor"]
    assert isinstance(auditor, dict)
    assert auditor["thread_id"] == "auditor-1"


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


def test_v2_plan_requires_explicit_project_mode_choice() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "role_sessions": {
                    "orchestrator": {"thread_id": "orch-1", "title": "Orchestrator"},
                },
            }
        },
        "current_round": {"id": "R1", "state": "intake"},
    }

    try:
        build_codex_role_session_plan(state)
    except V2SessionOrchestrationError as exc:
        message = str(exc)
        assert "mode is not set" in message
        assert "single-session-subagent is faster" in message
        assert "multi-session-subthread is slower" in message
    else:
        raise AssertionError("expected missing V2 mode to stop before Planner dispatch")


def test_set_v2_mode_persists_user_choice_before_dispatch() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "role_sessions": {
                    "orchestrator": {"thread_id": "orch-1", "title": "Orchestrator"},
                },
            }
        },
        "current_round": {"id": "R1", "state": "intake"},
    }

    updated = set_v2_mode(state, "codex", "single-session-subagent")
    plan = build_codex_role_session_plan(updated)

    assert plan.mode == "single-session-subagent"
    assert plan.next_role == "planner"
    assert len(plan.actions) == 1
    assert plan.actions[0].kind == "create"
    assert plan.actions[0].target == "subagent"
    assert plan.actions[0].thread_id == "subagent:planner"


def test_single_session_reuses_existing_named_subagent_identity() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "single-session-subagent",
                "role_sessions": {
                    "developer": {
                        "thread_id": "subagent:developer",
                        "title": "Developer",
                    }
                },
            }
        },
        "current_round": {"id": "R2", "state": "awaiting_dev_start"},
    }

    plan = build_codex_role_session_plan(state)

    assert plan.mode == "single-session-subagent"
    assert plan.next_role == "developer"
    assert len(plan.actions) == 1
    assert plan.actions[0].kind == "reuse"
    assert plan.actions[0].target == "subagent"
    assert plan.actions[0].title == "Developer"
    assert plan.actions[0].thread_id == "subagent:developer"


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


def test_awaiting_test_routes_to_test_role() -> None:
    assert next_role_for_state("awaiting_test") == "test"
    assert next_role_for_state("test_in_progress") == "test"


def test_passed_routes_to_planner_for_phase_decision_not_closeout() -> None:
    assert next_role_for_state("passed") == "planner"


def test_session_plan_does_not_dispatch_planner_before_close_round() -> None:
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
        "current_round": {"id": "R1", "state": "passed"},
    }

    plan = build_codex_role_session_plan(state)

    assert plan.orchestrator_status == "active"
    assert plan.next_role == "planner"
    assert plan.actions == ()


def test_closed_round_without_new_request_stays_idle() -> None:
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

    assert plan.orchestrator_status == "idle"
    assert plan.next_role == "planner"
    assert plan.actions == ()


def test_closed_round_with_same_active_request_stays_idle() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "orchestrator_status": "idle",
                "active_user_request": "build a wordfreq CLI",
                "role_sessions": {
                    "planner": {"thread_id": "planner-1", "title": "Planner"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "closed"},
    }

    plan = build_codex_role_session_plan(state, user_request="build a wordfreq CLI")

    assert plan.orchestrator_status == "idle"
    assert plan.actions == ()


def test_closed_round_status_query_stays_idle() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "orchestrator_status": "idle",
                "active_user_request": "build a wordfreq CLI",
                "role_sessions": {
                    "planner": {"thread_id": "planner-1", "title": "Planner"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "closed"},
    }

    plan = build_codex_role_session_plan(
        state,
        user_request="Analyze whether Arcgentic V2 is complete after the finished test project.",
    )

    assert plan.orchestrator_status == "idle"
    assert plan.actions == ()


def test_closed_round_routes_new_requests_to_planner() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "orchestrator_status": "idle",
                "active_user_request": "build a wordfreq CLI",
                "role_sessions": {
                    "planner": {"thread_id": "planner-1", "title": "Planner"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "closed"},
    }

    plan = build_codex_role_session_plan(state, user_request="add another mode")

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
    assert "Recommended closing shape" in plan.actions[0].prompt
    assert "search GitHub or equivalent public sources" in plan.actions[0].prompt
    assert "skills, plugins, MCP servers, connectors, and CLI tools" in plan.actions[0].prompt
    assert "full Markdown engineering documents" in plan.actions[0].prompt
    assert '"handoff": "docs/plans/R1.md"' in plan.actions[0].prompt
    assert '"project_plan"' in plan.actions[0].prompt


def test_session_plan_uses_role_specific_return_footer_example() -> None:
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
        "current_round": {"id": "R2", "state": "needs_fix"},
    }

    plan = build_codex_role_session_plan(state, user_request="fix the todo CLI")

    assert len(plan.actions) == 1
    prompt = plan.actions[0].prompt
    assert '"role": "developer"' in prompt
    assert '"state": "awaiting_test"' in prompt
    assert '"self_audit": "docs/audits/R2-self-audit.md"' in prompt
    assert '"commit": "<40-hex-local-dev-commit>"' in prompt
    assert '"next_recommended_role": "test"' in prompt
    assert '"role": "planner"' not in prompt
    assert "{\n  \"role\"" in prompt


def test_role_prompt_requires_auditor_verdict_parser_contract() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "role_sessions": {
                    "orchestrator": {"thread_id": "orch-1", "title": "Orchestrator"},
                    "auditor": {"thread_id": "auditor-1", "title": "Auditor"},
                },
            }
        },
        "current_round": {"id": "R2", "state": "awaiting_audit"},
    }

    plan = build_codex_role_session_plan(state)

    assert len(plan.actions) == 1
    prompt = plan.actions[0].prompt
    assert "Auditor is stricter than Developer self-audit" in prompt
    assert "`## 7. Fact table`" in prompt
    assert "`| # | Command | Expected | Comment |`" in prompt
    assert "do not add a separate Actual column" in prompt
    assert "arcgentic audit-check <verdict> --strict --strict-extended" in prompt
    assert "Do not use mutable live routing state" in prompt
    assert "`current_round.state`" in prompt
    assert "`project.arcgentic_v2.last_signal.role`" in prompt


def test_session_plan_dispatches_test_after_developer_completion() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "role_sessions": {
                    "orchestrator": {"thread_id": "orch-1", "title": "Orchestrator"},
                    "test": {"thread_id": "test-1", "title": "Test"},
                },
            }
        },
        "current_round": {"id": "R2", "state": "awaiting_test"},
    }

    plan = build_codex_role_session_plan(state)

    assert plan.next_role == "test"
    assert len(plan.actions) == 1
    assert plan.actions[0].role == "test"
    assert plan.actions[0].title == "Test"
    assert plan.actions[0].kind == "reuse"
    assert plan.actions[0].thread_id == "test-1"
    assert '"user_test": "docs/tests/R2-user-test.md"' in plan.actions[0].prompt


def test_session_plan_stops_after_audit_incomplete_signal() -> None:
    state = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "orchestrator_status": "active",
                "last_signal": {
                    "role": "auditor",
                    "status": "AUDIT_INCOMPLETE",
                    "round_id": "R1",
                    "state": "audit_in_progress",
                    "artifacts": {"verdict": "docs/audits/R1.md"},
                    "next_recommended_role": "auditor",
                },
                "role_sessions": {
                    "auditor": {"thread_id": "audit-1", "title": "Auditor"}
                },
            }
        },
        "current_round": {"id": "R1", "state": "audit_in_progress"},
    }

    plan = build_codex_role_session_plan(state)

    assert plan.orchestrator_status == "active"
    assert plan.next_role == "auditor"
    assert plan.actions == ()


def test_role_return_signal_round_trips_json() -> None:
    signal = RoleReturnSignal(
        role="developer",
        status="completed",
        round_id="R1",
        state="awaiting_test",
        artifacts={"self_audit": "docs/audits/R1-self-audit.md", "commit": "a" * 40},
        next_recommended_role="test",
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


def test_role_return_signal_extracts_from_natural_language_footer() -> None:
    payload = """
Plan

I will build the smallest useful expense splitter.

```arcgentic-role-return
{"role":"planner","status":"planned","round_id":"R1","state":"awaiting_dev_start","artifacts":{"handoff":"docs/plans/R1.md"},"next_recommended_role":"developer"}
```
"""

    signal = RoleReturnSignal.from_text(payload)

    assert signal.role == "planner"
    assert signal.state == "awaiting_dev_start"
    assert signal.artifacts == {"handoff": "docs/plans/R1.md"}


def test_role_return_signal_extracts_from_push_message_markers() -> None:
    payload = """
Developer finished implementation and self-audit.

ARCGENTIC_ROLE_RETURN
{"role":"developer","status":"completed","round_id":"R1","state":"awaiting_test","artifacts":{"self_audit":"docs/audits/R1-self-audit.md","commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},"next_recommended_role":"test"}
END_ARCGENTIC_ROLE_RETURN
"""

    signal = RoleReturnSignal.from_text(payload)

    assert signal.role == "developer"
    assert signal.next_recommended_role == "test"


def test_role_prompt_mentions_fixed_role_and_current_round() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "role_sessions": {
                    "orchestrator": {"thread_id": "orch-1", "title": "Orchestrator"}
                }
            }
        },
        "current_round": {"id": "R3", "state": "awaiting_test"},
    }

    prompt = role_prompt("test", state)

    assert "You are Test." in prompt
    assert "Current round: R3" in prompt
    assert "Only the Orchestrator may mutate .agentic-rounds/state.yaml" in prompt
    assert "Planner, Developer, Test, and Auditor" in prompt
    assert "Do not stop after acknowledging the role" in prompt
    assert "project.arcgentic_v2.last_signal.artifacts" in prompt
    assert "Developer must create a local git commit" in prompt
    assert "Test must simulate realistic user behavior" in prompt
    assert "A GitHub remote is stronger evidence but is not required" in prompt
    assert "Use natural language for your role-owned output" in prompt
    assert "each role session must read the referenced handoff artifact" in prompt
    assert "```arcgentic-role-return" in prompt
    assert "send a message to Orchestrator thread orch-1" in prompt
    assert "only for retryable audit work" in prompt


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
    assert current_round["audit_verdict"] == {
        "path": "docs/audits/R4.md",
        "outcome": "NEEDS_FIX",
        "fact_table_total": 0,
        "fact_table_pass": 0,
        "findings": [],
    }


def test_apply_role_return_signal_records_auditor_pass_verdict_for_close_round() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "auditor",
                "pending_thread_id": "audit-1",
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_audit"},
    }
    signal = RoleReturnSignal(
        role="auditor",
        status="PASS",
        round_id="R1",
        state="passed",
        artifacts={
            "verdict": "docs/audits/R1.md",
            "commit": "a" * 40,
        },
        next_recommended_role="planner",
    )

    updated = apply_role_return_signal(state, signal)

    current_round = updated["current_round"]
    assert isinstance(current_round, dict)
    assert current_round["state"] == "passed"
    assert current_round["audit_verdict"] == {
        "path": "docs/audits/R1.md",
        "commit": "a" * 40,
        "outcome": "PASS",
        "fact_table_total": 0,
        "fact_table_pass": 0,
        "findings": [],
    }


def test_apply_role_return_signal_rejects_auditor_pass_without_commit_anchor() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "auditor",
                "pending_thread_id": "audit-1",
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
        assert "artifacts.commit" in str(exc)
    else:
        raise AssertionError("expected missing Auditor commit anchor to be rejected")


def test_apply_role_return_signal_rejects_developer_test_without_commit_anchor() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "developer",
                "pending_thread_id": "dev-1",
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_dev_start"},
    }
    signal = RoleReturnSignal(
        role="developer",
        status="completed",
        round_id="R1",
        state="awaiting_test",
        artifacts={"self_audit": "docs/audits/R1-self-audit.md"},
        next_recommended_role="test",
    )

    try:
        apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        assert "artifacts.commit" in str(exc)
    else:
        raise AssertionError("expected missing Developer commit anchor to be rejected")


def test_apply_role_return_signal_accepts_developer_test_with_local_commit_anchor() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "developer",
                "pending_thread_id": "dev-1",
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_dev_start"},
    }
    signal = RoleReturnSignal(
        role="developer",
        status="completed",
        round_id="R1",
        state="awaiting_test",
        artifacts={
            "self_audit": "docs/audits/R1-self-audit.md",
            "commit": "a" * 40,
        },
        next_recommended_role="test",
    )

    updated = apply_role_return_signal(state, signal)

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["next_role"] == "test"
    assert v2["last_signal"] == signal.to_dict()


def test_apply_role_return_signal_accepts_developer_direct_to_auditor_when_test_skipped() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "developer",
                "pending_thread_id": "dev-1",
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_dev_start"},
    }
    signal = RoleReturnSignal(
        role="developer",
        status="completed",
        round_id="R1",
        state="awaiting_audit",
        artifacts={
            "self_audit": "docs/audits/R1-self-audit.md",
            "commit": "a" * 40,
        },
        next_recommended_role="auditor",
    )

    updated = apply_role_return_signal(state, signal)

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["next_role"] == "auditor"
    assert v2["last_signal"] == signal.to_dict()
    assert updated["current_round"]["state"] == "awaiting_audit"  # type: ignore[index]


def test_apply_role_return_signal_stores_planner_project_plan() -> None:
    project_plan = {
        "phases": [
            {
                "id": "P1",
                "rounds": [
                    {
                        "id": "P1.R1",
                        "handoff": "docs/plans/P1.R1.md",
                        "test_gate": {
                            "required": False,
                            "reason": "Pure internal helper.",
                        },
                    }
                ],
            }
        ]
    }
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "planner",
                "pending_thread_id": "planner-1",
            }
        },
        "current_round": {"id": "P1.R1", "state": "planning"},
    }
    signal = RoleReturnSignal(
        role="planner",
        status="planned",
        round_id="P1.R1",
        state="awaiting_dev_start",
        artifacts={
            "handoff": "docs/plans/P1.R1.md",
            "project_plan": project_plan,
        },
        next_recommended_role="developer",
    )

    updated = apply_role_return_signal(state, signal)

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["project_plan"] == project_plan
    assert v2["next_role"] == "developer"


def test_apply_role_return_signal_rejects_planner_closed_without_commit_anchor() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "planner",
                "pending_thread_id": "planner-1",
            }
        },
        "current_round": {"id": "R1", "state": "planning"},
    }
    signal = RoleReturnSignal(
        role="planner",
        status="completed",
        round_id="R1",
        state="closed",
        artifacts={"closeout": "docs/plans/P1-closeout.md"},
        next_recommended_role=None,
    )

    try:
        apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        assert "artifacts.commit" in str(exc)
    else:
        raise AssertionError("expected missing Planner closeout commit anchor to be rejected")


def test_apply_role_return_signal_accepts_planner_closed_as_idle_terminal() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "planner",
                "pending_thread_id": "planner-1",
                "next_role": "planner",
            }
        },
        "current_round": {"id": "R1", "state": "planning"},
    }
    signal = RoleReturnSignal(
        role="planner",
        status="completed",
        round_id="R1",
        state="closed",
        artifacts={
            "closeout": "docs/plans/P1-closeout.md",
            "commit": "b" * 40,
        },
        next_recommended_role=None,
    )

    updated = apply_role_return_signal(state, signal)

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["orchestrator_status"] == "idle"
    assert "next_role" not in v2
    assert "pending_role" not in v2
    assert v2["last_signal"] == signal.to_dict()
    assert updated["current_round"]["state"] == "closed"  # type: ignore[index]


def test_advance_passed_round_from_project_plan_moves_to_next_round_developer() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "project_plan": {
                    "phases": [
                        {
                            "id": "P1",
                            "rounds": [
                                {"id": "P1.R1", "status": "active"},
                                {
                                    "id": "P1.R2",
                                    "status": "planned",
                                    "test_gate": {"required": True},
                                },
                            ],
                        }
                    ]
                },
            }
        },
        "current_round": {"id": "P1.R1", "state": "passed", "state_history": []},
    }

    updated = advance_passed_round_from_project_plan(state)

    current_round = updated["current_round"]
    assert isinstance(current_round, dict)
    assert current_round["id"] == "P1.R2"
    assert current_round["state"] == "awaiting_dev_start"
    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["next_role"] == "developer"
    assert v2["current_round_id"] == "P1.R2"


def test_advance_passed_round_from_project_plan_routes_phase_boundary_to_planner() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "host": "codex",
                "mode": "multi-session-subthread",
                "project_plan": {
                    "phases": [
                        {
                            "id": "P1",
                            "rounds": [
                                {"id": "P1.R1", "status": "active"},
                            ],
                        }
                    ]
                },
            }
        },
        "current_round": {"id": "P1.R1", "state": "passed", "state_history": []},
    }

    updated = advance_passed_round_from_project_plan(state)

    current_round = updated["current_round"]
    assert isinstance(current_round, dict)
    assert current_round["id"] == "P1.R1"
    assert current_round["state"] == "planning"
    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["next_role"] == "planner"
    assert v2["phase_boundary"]["after_round"] == "P1.R1"


def test_apply_role_return_signal_accepts_test_pass_to_auditor() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "test",
                "pending_thread_id": "test-1",
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_test"},
    }
    signal = RoleReturnSignal(
        role="test",
        status="user_tested",
        round_id="R1",
        state="awaiting_audit",
        artifacts={
            "user_test": "docs/tests/R1-user-test.md",
            "commit": "a" * 40,
        },
        next_recommended_role="auditor",
    )

    updated = apply_role_return_signal(state, signal)

    project = updated["project"]
    assert isinstance(project, dict)
    v2 = project["arcgentic_v2"]
    assert isinstance(v2, dict)
    assert v2["next_role"] == "auditor"
    assert v2["last_signal"] == signal.to_dict()


def test_apply_role_return_signal_rejects_test_pass_without_user_test_artifact() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "test",
                "pending_thread_id": "test-1",
            }
        },
        "current_round": {"id": "R1", "state": "awaiting_test"},
    }
    signal = RoleReturnSignal(
        role="test",
        status="user_tested",
        round_id="R1",
        state="awaiting_audit",
        artifacts={"commit": "a" * 40},
        next_recommended_role="auditor",
    )

    try:
        apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        assert "artifacts.user_test" in str(exc)
    else:
        raise AssertionError("expected missing Test user-test artifact to be rejected")


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


def test_apply_role_return_signal_accepts_pending_idempotent_same_state_return() -> None:
    state: dict[str, object] = {
        "project": {
            "arcgentic_v2": {
                "orchestrator_status": "sleeping",
                "pending_role": "auditor",
                "pending_thread_id": "auditor-1",
            }
        },
        "current_round": {"id": "R1", "state": "passed"},
    }
    signal = RoleReturnSignal(
        role="auditor",
        status="PASS",
        round_id="R1",
        state="passed",
        artifacts={
            "verdict": "docs/audits/R1.md",
            "commit": "a" * 40,
        },
        next_recommended_role="planner",
    )

    updated = apply_role_return_signal(state, signal)

    v2 = updated["project"]["arcgentic_v2"]  # type: ignore[index]
    assert v2["orchestrator_status"] == "active"
    assert "pending_role" not in v2
    assert v2["last_signal"]["artifacts"]["verdict"] == "docs/audits/R1.md"
    assert updated["current_round"]["state"] == "passed"  # type: ignore[index]


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
