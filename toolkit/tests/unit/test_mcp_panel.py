from __future__ import annotations

from arcgentic.mcp.panel import (
    render_error_panel_html,
    render_status_panel_html,
    render_status_summary_text,
)


def _state_with_progress() -> dict[str, object]:
    return {
        "current_round": {
            "id": "R7",
            "state": "audit_in_progress",
            "audit_verdict": {
                "outcome": "PASS",
                "fact_table_total": 5,
                "fact_table_pass": 5,
            },
        },
        "project": {
            "arcgentic_v2": {
                "next_role": "auditor",
                "role_sessions": {
                    "orchestrator": {"thread_id": "t1"},
                    "planner": {"thread_id": "t2"},
                    "developer": {"thread_id": "t3"},
                },
            }
        },
    }


def test_render_status_summary_text_lists_round_and_roles() -> None:
    text = render_status_summary_text(_state_with_progress())
    assert "R7" in text
    assert "audit_in_progress" in text
    assert "Auditor: active" in text
    assert "Developer: recorded" in text
    assert "Test: pending" in text
    assert "PASS (5/5 facts passed)" in text


def test_render_status_summary_text_no_active_round() -> None:
    text = render_status_summary_text({})
    assert "no active round" in text


def test_render_status_summary_text_no_verdict_yet() -> None:
    state = _state_with_progress()
    current_round = state["current_round"]
    assert isinstance(current_round, dict)
    del current_round["audit_verdict"]
    text = render_status_summary_text(state)
    assert "No audit verdict yet" in text


def test_render_status_panel_html_contains_round_and_role_rows() -> None:
    html = render_status_panel_html(_state_with_progress())
    assert "R7" in html
    assert "Auditor: active" in html
    assert "<button id=\"dispatch-btn\">" in html
    assert "PASS (5/5 facts passed)" in html


def test_render_status_panel_html_hides_dispatch_button_when_closed() -> None:
    state = _state_with_progress()
    state["current_round"]["state"] = "closed"  # type: ignore[index]
    html = render_status_panel_html(state)
    assert "dispatch-btn" not in html


def test_render_status_panel_html_no_active_round_is_error_panel() -> None:
    html = render_status_panel_html({})
    assert "No active round" in html
    assert "dispatch-btn" not in html


def test_render_status_panel_html_has_polling_script_targeting_the_tool() -> None:
    html = render_status_panel_html(_state_with_progress())
    assert "setInterval(callTool, 5000)" in html
    assert '"toolName": "round_status_panel"' in html or "'toolName': 'round_status_panel'" in html


def test_render_status_panel_html_dispatch_button_sends_prompt_action() -> None:
    html = render_status_panel_html(_state_with_progress())
    assert '"type": "prompt"' in html or "'type': 'prompt'" in html
    assert "请派发下一个角色" in html


def test_render_error_panel_html_shows_message() -> None:
    html = render_error_panel_html("state.yaml is not valid YAML")
    assert "state.yaml is not valid YAML" in html


def test_render_status_panel_html_escapes_malicious_round_id_and_state() -> None:
    state = _state_with_progress()
    current_round = state["current_round"]
    assert isinstance(current_round, dict)
    current_round["id"] = "</h2><script>alert(1)</script>"
    current_round["state"] = "<img src=x onerror=alert(2)>"
    html = render_status_panel_html(state)
    assert "<script>alert(1)</script>" not in html
    assert "<img src=x onerror=alert(2)>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(2)&gt;" in html


def test_render_error_panel_html_escapes_malicious_message() -> None:
    html = render_error_panel_html("boom <script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_render_status_panel_html_polling_script_has_a_poll_count_cap() -> None:
    html = render_status_panel_html(_state_with_progress())
    assert "MAX_POLL_CYCLES = 60" in html
    assert 'id="poll-resume-btn"' in html
    assert 'id="poll-paused-note"' in html
    # The existing 5s-interval polling assertion must still hold.
    assert "setInterval(callTool, 5000)" in html
