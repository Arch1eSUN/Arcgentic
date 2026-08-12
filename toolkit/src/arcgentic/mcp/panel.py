"""Pure HTML/text rendering for the arcgentic MCP-UI round-status panel.

No file IO, no network — every function here takes an already-parsed
state.yaml dict (or an error message) and returns a string. See
docs/plans/2026-08-12-arcgentic-mcp-ui-status-panel-design.md.

All values sourced from state.yaml (round_id, round_state, verdict summary)
or from the caller (the error `message`) are HTML-escaped before
interpolation — state.yaml is untrusted input and this panel's script has a
privileged postMessage(prompt) channel into the live conversation.

The embedded polling script caps itself at 60 poll cycles (5 minutes at the
5-second interval) and then pauses with a manual "resume" control; whether a
host actually re-renders the panel on each poll (and thus whether pausing has
any visible effect) is host behavior this server cannot observe or control —
it can only control how many times it asks.
"""

from __future__ import annotations

import html

_ROLE_ORDER: tuple[str, ...] = ("orchestrator", "planner", "developer", "test", "auditor")
_ROLE_TITLES: dict[str, str] = {
    "orchestrator": "Orchestrator",
    "planner": "Planner",
    "developer": "Developer",
    "test": "Test",
    "auditor": "Auditor",
}
_STATUS_COLOR: dict[str, str] = {
    "active": "#2563eb",
    "recorded": "#16a34a",
    "pending": "#9ca3af",
}


def _current_round(state: dict[str, object]) -> tuple[str, str]:
    current_round = state.get("current_round")
    if not isinstance(current_round, dict):
        return ("", "")
    return (str(current_round.get("id") or ""), str(current_round.get("state") or ""))


def _v2_block(state: dict[str, object]) -> dict[str, object]:
    project = state.get("project")
    if not isinstance(project, dict):
        return {}
    v2 = project.get("arcgentic_v2")
    return v2 if isinstance(v2, dict) else {}


def _role_progress(state: dict[str, object]) -> list[dict[str, str]]:
    v2 = _v2_block(state)
    role_sessions_raw = v2.get("role_sessions")
    role_sessions = role_sessions_raw if isinstance(role_sessions_raw, dict) else {}
    next_role = str(v2.get("next_role") or "")
    rows: list[dict[str, str]] = []
    for role in _ROLE_ORDER:
        if role == next_role:
            status = "active"
        elif role in role_sessions:
            status = "recorded"
        else:
            status = "pending"
        rows.append({"role": role, "title": _ROLE_TITLES[role], "status": status})
    return rows


def _audit_verdict_summary(state: dict[str, object]) -> str:
    current_round = state.get("current_round")
    verdict = current_round.get("audit_verdict") if isinstance(current_round, dict) else None
    if not isinstance(verdict, dict):
        return "No audit verdict yet"
    outcome = str(verdict.get("outcome") or "UNKNOWN")
    total = verdict.get("fact_table_total")
    passed = verdict.get("fact_table_pass")
    if isinstance(total, int) and isinstance(passed, int) and total > 0:
        return f"{outcome} ({passed}/{total} facts passed)"
    return outcome


def render_status_summary_text(state: dict[str, object]) -> str:
    """Plain-text fallback: the LLM-visible tool result, and what non-Apps hosts see."""
    round_id, round_state = _current_round(state)
    if not round_id:
        return "arcgentic: no active round (.agentic-rounds/state.yaml has no current_round)."
    lines = [f"arcgentic round {round_id} — state: {round_state or 'unknown'}"]
    for row in _role_progress(state):
        lines.append(f"  {row['title']}: {row['status']}")
    lines.append(f"Audit verdict: {_audit_verdict_summary(state)}")
    return "\n".join(lines)


def render_error_panel_html(message: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>body {{ font-family: system-ui, sans-serif; margin: 12px; color: #b91c1c; }}</style>
</head><body><p>{html.escape(message)}</p></body></html>"""


def render_status_panel_html(state: dict[str, object]) -> str:
    """Self-contained ui:// HTML resource. No external requests."""
    round_id, round_state = _current_round(state)
    if not round_id:
        return render_error_panel_html(
            "No active round — .agentic-rounds/state.yaml has no current_round."
        )

    is_closed = round_state == "closed"
    rows_html = "".join(
        f'<li style="color:{_STATUS_COLOR[row["status"]]}">'
        f'{row["title"]}: {row["status"]}</li>'
        for row in _role_progress(state)
    )
    # Role titles/statuses above come from _ROLE_TITLES / the fixed
    # active|recorded|pending vocabulary — internal, not external input — so
    # they don't need escaping. round_id/round_state/verdict below come from
    # state.yaml and DO need it.
    safe_round_id = html.escape(round_id)
    safe_round_state = html.escape(round_state)
    verdict = html.escape(_audit_verdict_summary(state))
    dispatch_button = "" if is_closed else '<button id="dispatch-btn">派发下一角色</button>'
    dispatch_script = "" if is_closed else """
      var dispatchBtn = document.getElementById("dispatch-btn");
      if (dispatchBtn) {
        dispatchBtn.addEventListener("click", function () {
          window.parent.postMessage(
            { "type": "prompt", "payload": { "prompt": "请派发下一个角色" } },
            "*"
          );
        });
      }"""

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: system-ui, sans-serif; margin: 12px; }}
  h2 {{ margin: 0 0 8px; font-size: 16px; }}
  ul {{ list-style: none; padding: 0; margin: 8px 0; }}
  li {{ padding: 2px 0; }}
  button {{ margin-top: 8px; padding: 6px 12px; cursor: pointer; }}
</style></head>
<body>
  <h2>Round {safe_round_id} — {safe_round_state}</h2>
  <ul>{rows_html}</ul>
  <p>Audit: {verdict}</p>
  {dispatch_button}
  <p id="poll-paused-note" style="display:none; color:#9ca3af; font-size:12px;">
    Auto-refresh paused — <button id="poll-resume-btn">click refresh to resume</button>
  </p>
  <script>
    (function () {{
      var MAX_POLL_CYCLES = 60; // 5 min at the 5s interval — independent cap, see stopPolling()
      var pollTimer = null;
      var pollCount = 0;
      var isClosed = {str(is_closed).lower()};
      var pausedNote = document.getElementById("poll-paused-note");
      var resumeBtn = document.getElementById("poll-resume-btn");

      function callTool() {{
        pollCount += 1;
        if (pollCount > MAX_POLL_CYCLES) {{
          stopPolling();
          if (pausedNote) {{ pausedNote.style.display = "block"; }}
          return;
        }}
        window.parent.postMessage(
          {{ "type": "tool", "payload": {{ "toolName": "round_status_panel", "params": {{}} }} }},
          "*"
        );
      }}

      function startPolling() {{
        if (isClosed || pollTimer) return;
        pollTimer = setInterval(callTool, 5000);
      }}

      function stopPolling() {{
        if (pollTimer) {{ clearInterval(pollTimer); pollTimer = null; }}
      }}

      if (resumeBtn) {{
        resumeBtn.addEventListener("click", function () {{
          pollCount = 0;
          if (pausedNote) {{ pausedNote.style.display = "none"; }}
          startPolling();
        }});
      }}

      document.addEventListener("visibilitychange", function () {{
        if (document.hidden) {{ stopPolling(); }} else {{ startPolling(); }}
      }});
{dispatch_script}

      startPolling();
    }})();
  </script>
</body></html>"""
