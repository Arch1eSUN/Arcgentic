# Arcgentic MCP-UI Status Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give arcgentic its first MCP server, exposing a single read-only tool (`round_status_panel`) that renders the current round's state, role-dispatch progress, and audit verdict as an MCP Apps (SEP-1865) inline panel, with client-side auto-polling and a `prompt`-action "dispatch next role" button — no server-side write path.

**Architecture:** New `toolkit/src/arcgentic/mcp/` subpackage: `panel.py` (pure `state dict -> str` rendering, HTML and plain-text), `server.py` (wires the pure functions into the official `mcp` SDK's `Apps` extension + `MCPServer`, stdio transport). A new `arcgentic mcp-serve` CLI subcommand starts it; a new `.mcp.json` at the plugin root declares it to MCP-UI-capable hosts. No new distribution channel — reuses the already-published `arcgentic` console script.

**Deviation from the design doc's file list (disclosed, not silent):** the design doc's §3.1 lists a separate `tools.py` for tool handlers. Since the corrected v1 scope (after the `prompt`-action finding) has exactly one tool, a dedicated `tools.py` for a single function is unneeded indirection — the tool function lives directly in `server.py`, next to the `Apps`/`MCPServer` wiring that registers it. `panel.py` stays the separate, dependency-free rendering module the design doc calls for.

**Tech Stack:** Python 3.13, official `mcp` SDK (`mcp>=2.0.0`, ships `mcp.server.apps` — the MCP Apps extension — built in), pytest/mypy/ruff per `toolkit/pyproject.toml`.

## Global Constraints

- Design source of truth: [`docs/plans/2026-08-12-arcgentic-mcp-ui-status-panel-design.md`](./2026-08-12-arcgentic-mcp-ui-status-panel-design.md) (as corrected — no server-side write tool; "dispatch" is a `prompt` UI action, not a `tool` call).
- `panel.py` has zero file/network IO — pure functions only, so they're testable without a live MCP host.
- No new write-capable MCP tool. The only tool is `round_status_panel` (read-only).
- The `ui://` resource must regenerate fresh content on every `resources/read` (poll = fresh data) — use `FunctionResource`, not a static `TextResource`.
- `mypy --strict` and `ruff` must pass (existing `toolkit/pyproject.toml` gates).
- HTML panel is self-contained: inline `<style>`/`<script>` only, no external requests (matches the design doc's sandboxing note).

---

### Task 1: Pure panel-rendering functions

**Files:**
- Create: `toolkit/src/arcgentic/mcp/__init__.py` (empty)
- Create: `toolkit/src/arcgentic/mcp/panel.py`
- Test: `toolkit/tests/unit/test_mcp_panel.py`

**Interfaces:**
- Produces: `render_status_panel_html(state: dict[str, object]) -> str`, `render_status_summary_text(state: dict[str, object]) -> str`, `render_error_panel_html(message: str) -> str`.
- Consumes: nothing outside the stdlib — this file must not import from `v2_session_orchestration.py` or do file IO. It only knows the shape of an already-parsed state dict (same shape `v2_session_orchestration.py` produces: `project.arcgentic_v2.role_sessions`/`next_role`, `current_round.id`/`state`/`audit_verdict`).

- [ ] **Step 1: Write the failing tests**

```python
# toolkit/tests/unit/test_mcp_panel.py
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
    del state["current_round"]["audit_verdict"]  # type: ignore[index]
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd toolkit && python -m pytest tests/unit/test_mcp_panel.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcgentic.mcp'`

- [ ] **Step 3: Create the package marker**

```bash
mkdir -p toolkit/src/arcgentic/mcp
touch toolkit/src/arcgentic/mcp/__init__.py
```

- [ ] **Step 4: Implement `toolkit/src/arcgentic/mcp/panel.py`**

```python
"""Pure HTML/text rendering for the arcgentic MCP-UI round-status panel.

No file IO, no network — every function here takes an already-parsed
state.yaml dict (or an error message) and returns a string. See
docs/plans/2026-08-12-arcgentic-mcp-ui-status-panel-design.md.
"""

from __future__ import annotations

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
</head><body><p>{message}</p></body></html>"""


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
    verdict = _audit_verdict_summary(state)
    dispatch_button = "" if is_closed else '<button id="dispatch-btn">派发下一角色</button>'

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
  <h2>Round {round_id} — {round_state}</h2>
  <ul>{rows_html}</ul>
  <p>Audit: {verdict}</p>
  {dispatch_button}
  <script>
    (function () {{
      var pollTimer = null;
      var isClosed = {str(is_closed).lower()};

      function callTool() {{
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

      document.addEventListener("visibilitychange", function () {{
        if (document.hidden) {{ stopPolling(); }} else {{ startPolling(); }}
      }});

      var dispatchBtn = document.getElementById("dispatch-btn");
      if (dispatchBtn) {{
        dispatchBtn.addEventListener("click", function () {{
          window.parent.postMessage(
            {{ "type": "prompt", "payload": {{ "prompt": "请派发下一个角色" }} }},
            "*"
          );
        }});
      }}

      startPolling();
    }})();
  </script>
</body></html>"""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd toolkit && python -m pytest tests/unit/test_mcp_panel.py -v`
Expected: PASS (9 tests)

- [ ] **Step 6: Run mypy and ruff**

Run: `cd toolkit && python -m mypy src/arcgentic/mcp/panel.py && python -m ruff check src/arcgentic/mcp/ tests/unit/test_mcp_panel.py`
Expected: no errors

- [ ] **Step 7: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/src/arcgentic/mcp/__init__.py toolkit/src/arcgentic/mcp/panel.py toolkit/tests/unit/test_mcp_panel.py
git commit -m "feat(mcp): add pure HTML/text renderers for the round-status panel

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: MCP server — wire the renderers into the official SDK's Apps extension

**Files:**
- Create: `toolkit/src/arcgentic/mcp/server.py`
- Modify: `toolkit/pyproject.toml` (add `mcp>=2.0.0` to `dependencies`)
- Test: `toolkit/tests/unit/test_mcp_server.py`

**Interfaces:**
- Consumes: `render_status_panel_html`, `render_status_summary_text`, `render_error_panel_html` (Task 1); `arcgentic.v2_session_orchestration.load_state_file`, `V2SessionOrchestrationError` (existing).
- Produces: `STATE_PATH: Path` (module constant, `.agentic-rounds/state.yaml`, resolved relative to CWD), `RESOURCE_URI: str` (`"ui://arcgentic/round-status.html"`), `round_status_panel() -> str` (the tool function — directly callable/importable for tests, not just through the MCP protocol), `build_apps() -> Apps`, `run_server() -> None`.

**Why `STATE_PATH` is a module-level variable, not a hardcoded literal inline:** tests need to point it at a `tmp_path` fixture instead of the real repo's `.agentic-rounds/state.yaml`. Use `monkeypatch.setattr(server, "STATE_PATH", ...)` in tests — do not parametrize `round_status_panel()` itself with a path argument, since the real MCP tool call takes no arguments (per the design, it's a zero-argument tool).

- [ ] **Step 1: Add the `mcp` dependency**

In `toolkit/pyproject.toml`, change:
```toml
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.0",
]
```
to:
```toml
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.0",
    "mcp>=2.0.0",
]
```
`mcp>=2.0.0` specifically because the MCP Apps extension (`mcp.server.apps`) is only guaranteed present from that version — do not lower this floor without confirming `mcp.server.apps` exists in whatever earlier version you're considering.

- [ ] **Step 2: Install the new dependency locally**

Run: `cd toolkit && pip install -e ".[dev]"`
Expected: installs successfully, `python -c "from mcp.server.apps import Apps, APP_MIME_TYPE; print('ok')"` prints `ok`

- [ ] **Step 3: Write the failing tests**

```python
# toolkit/tests/unit/test_mcp_server.py
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from arcgentic.mcp import server


def _write_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: dict[str, object]) -> None:
    state_path = tmp_path / "state.yaml"
    state_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(server, "STATE_PATH", state_path)


def test_round_status_panel_no_state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "STATE_PATH", tmp_path / "does-not-exist.yaml")
    text = server.round_status_panel()
    assert "no active round" in text


def test_round_status_panel_reads_real_state_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_state(
        tmp_path,
        monkeypatch,
        {
            "current_round": {"id": "R3", "state": "dev_in_progress"},
            "project": {"arcgentic_v2": {"next_role": "developer", "role_sessions": {}}},
        },
    )
    text = server.round_status_panel()
    assert "R3" in text
    assert "Developer: active" in text


def test_round_status_panel_reports_malformed_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "state.yaml"
    state_path.write_text("not: valid: yaml: [", encoding="utf-8")
    monkeypatch.setattr(server, "STATE_PATH", state_path)
    text = server.round_status_panel()
    assert "failed to read" in text


def test_round_status_panel_html_reflects_same_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_state(
        tmp_path,
        monkeypatch,
        {
            "current_round": {"id": "R9", "state": "awaiting_audit"},
            "project": {"arcgentic_v2": {"next_role": "auditor", "role_sessions": {}}},
        },
    )
    html = server._round_status_panel_html()
    assert "R9" in html


def test_build_apps_registers_tool_bound_to_resource() -> None:
    apps = server.build_apps()
    tools = apps.tools()
    assert len(tools) == 1
    assert tools[0].meta["ui"]["resourceUri"] == server.RESOURCE_URI
    resources = apps.resources()
    assert len(resources) == 1
    assert resources[0].resource.uri == server.RESOURCE_URI
    assert resources[0].resource.mime_type == "text/html;profile=mcp-app"
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd toolkit && python -m pytest tests/unit/test_mcp_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcgentic.mcp.server'`

- [ ] **Step 5: Implement `toolkit/src/arcgentic/mcp/server.py`**

```python
"""arcgentic MCP server: exposes the round-status panel via MCP Apps (SEP-1865)."""

from __future__ import annotations

from pathlib import Path

from mcp.server import MCPServer
from mcp.server.apps import APP_MIME_TYPE, Apps
from mcp.server.mcpserver.resources.types import FunctionResource

from arcgentic.mcp.panel import (
    render_error_panel_html,
    render_status_panel_html,
    render_status_summary_text,
)
from arcgentic.v2_session_orchestration import V2SessionOrchestrationError, load_state_file

STATE_PATH = Path(".agentic-rounds/state.yaml")
RESOURCE_URI = "ui://arcgentic/round-status.html"


def _load_current_state() -> dict[str, object] | None:
    """Load state.yaml relative to CWD. None means no round has started yet — not an error."""
    if not STATE_PATH.exists():
        return None
    return load_state_file(STATE_PATH)


def round_status_panel() -> str:
    """MCP tool: the plain-text result (LLM-visible; also what non-Apps hosts see).

    MCP Apps hosts additionally render the ui:// resource this tool is bound to
    (see build_apps()) — that resource is regenerated fresh on every read via
    _round_status_panel_html(), independent of this function's return value.
    """
    try:
        state = _load_current_state()
    except V2SessionOrchestrationError as exc:
        return f"arcgentic: failed to read {STATE_PATH}: {exc}"
    if state is None:
        return "arcgentic: no active round (.agentic-rounds/state.yaml not found)."
    return render_status_summary_text(state)


def _round_status_panel_html() -> str:
    """FunctionResource callback for RESOURCE_URI — re-invoked on every resources/read."""
    try:
        state = _load_current_state()
    except V2SessionOrchestrationError as exc:
        return render_error_panel_html(f"Failed to read {STATE_PATH}: {exc}")
    return render_status_panel_html(state or {})


def build_apps() -> Apps:
    apps = Apps()
    apps.tool(
        resource_uri=RESOURCE_URI,
        description=(
            "Show the current arcgentic round's status, role dispatch progress, "
            "and audit verdict as an inline panel."
        ),
    )(round_status_panel)
    apps.add_resource(
        FunctionResource.from_function(
            _round_status_panel_html,
            uri=RESOURCE_URI,
            mime_type=APP_MIME_TYPE,
        )
    )
    return apps


def run_server() -> None:
    apps = build_apps()
    server = MCPServer("arcgentic", extensions=[apps])
    server.run(transport="stdio")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd toolkit && python -m pytest tests/unit/test_mcp_server.py -v`
Expected: PASS (5 tests)

- [ ] **Step 7: Run mypy and ruff**

Run: `cd toolkit && python -m mypy src/arcgentic/mcp/ && python -m ruff check src/arcgentic/mcp/ tests/unit/test_mcp_server.py`
Expected: no errors. If mypy complains about `FunctionResource.from_function`'s inferred type for a zero-arg callable, add an explicit `-> str` return annotation check on `_round_status_panel_html` (already present above) — that should be sufficient; do not add `# type: ignore` without first confirming the error is a real SDK stub gap.

- [ ] **Step 8: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/pyproject.toml toolkit/src/arcgentic/mcp/server.py toolkit/tests/unit/test_mcp_server.py
git commit -m "feat(mcp): wire round-status panel into an MCP Apps server

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: CLI subcommand — `arcgentic mcp-serve`

**Files:**
- Modify: `toolkit/src/arcgentic/cli.py`

**Interfaces:**
- Consumes: `arcgentic.mcp.server.run_server` (Task 2).

- [ ] **Step 1: Add the subcommand parser**

In `toolkit/src/arcgentic/cli.py`, find the `claude_broker_parser = subparsers.add_parser(...)` block (search for `"claude-code-broker"` — it's the last subcommand parser defined before the closing of the parser-building section). Immediately after that block, add:

```python
    mcp_serve_parser = subparsers.add_parser(
        "mcp-serve",
        help="Run the arcgentic MCP server (stdio) exposing the round-status panel.",
    )
```

- [ ] **Step 2: Add the dispatch branch**

Find the line `elif args.command == "claude-code-broker":` and its two-line body (`from .claude_code_broker import main as broker_main` / `return broker_main(args.broker_args)`), immediately before the trailing `parser.print_help()` / `return 1`. Add a new branch right after that `claude-code-broker` branch:

```python
    elif args.command == "mcp-serve":
        from .mcp.server import run_server

        run_server()
        return 0
```

- [ ] **Step 3: Add a one-line entry to the module docstring**

At the top of `cli.py`, in the docstring's subcommand list (after the `arcgentic claude-code-broker install-hooks|handle-stop` entry), add:

```
- `arcgentic mcp-serve`
  → runs the MCP server (stdio) exposing the round-status panel via MCP Apps
```

- [ ] **Step 4: Verify the subcommand is wired (without actually blocking on stdio)**

`mcp-serve` calls `server.run(transport="stdio")`, which blocks reading stdin — do not run it directly in a test shell. Instead verify wiring via argparse alone:

Run: `cd toolkit && python -c "
from arcgentic.cli import main
import sys
sys.argv = ['arcgentic', 'mcp-serve', '--help']
try:
    main()
except SystemExit as e:
    print('exit code:', e.code)
"`
Expected: prints the `mcp-serve` help text (from argparse) and `exit code: 0` — confirms the subcommand is registered and argparse recognizes it, without invoking `run_server()`.

- [ ] **Step 5: Run the full existing CLI test suite**

Run: `cd toolkit && python -m pytest tests/unit/test_cli.py -v`
Expected: PASS, same test count as before this task (no existing CLI test should reference `mcp-serve`, so nothing should change).

- [ ] **Step 6: Run mypy and ruff**

Run: `cd toolkit && python -m mypy src/arcgentic/cli.py && python -m ruff check src/arcgentic/cli.py`
Expected: no errors

- [ ] **Step 7: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add toolkit/src/arcgentic/cli.py
git commit -m "feat(cli): add arcgentic mcp-serve subcommand

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Plugin manifest, full regression, manual verification checklist

**Files:**
- Create: `.mcp.json` (repo root)
- Create: `toolkit/tests/integration/test_mcp_protocol.py`
- Modify: none else (verification-only for the rest)

**Interfaces:** none — this task declares the server to hosts and runs final checks.

- [ ] **Step 1: Create `.mcp.json` at the plugin root**

```json
{
  "mcpServers": {
    "arcgentic": {
      "command": "arcgentic",
      "args": ["mcp-serve"]
    }
  }
}
```

This follows the same `mcpServers.<name>.command`/`args` convention already used by other Claude Code plugins (verified against `context7`, `terraform`, `aws-serverless`'s `.mcp.json` files during design). `arcgentic` resolves to the console script `toolkit/pyproject.toml` already registers (`arcgentic = "arcgentic.cli:main"`) — requires `pipx install arcgentic` (already the documented install path in `README.md`) or an editable install for local development; no new install step for users who already have the CLI.

- [ ] **Step 2: Validate the manifest is well-formed JSON**

Run: `python3 -c "import json; json.load(open('.mcp.json')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Run the full toolkit test suite**

Run: `cd toolkit && python -m pytest -q`
Expected: all tests pass, including the new `test_mcp_panel.py` and `test_mcp_server.py`, with more tests total than before this plan started.

- [ ] **Step 4: Run mypy and ruff across the whole toolkit**

Run: `cd toolkit && python -m mypy src/ && python -m ruff check src/ tests/`
Expected: no errors.

- [ ] **Step 5: Automated in-memory MCP protocol test (real client-server round trip, no live host needed)**

The design doc scoped real-host verification as manual-only, on the assumption that the MCP wire protocol itself couldn't be exercised without a live graphical host. That's wrong for the protocol layer (only the visual iframe rendering genuinely can't be automated) — the `mcp` SDK ships `mcp.client._memory.InMemoryTransport`, which runs a real `MCPServer` in-process and connects a real `ClientSession` to it over in-memory streams, no network/stdio/browser needed. Add this test to close that gap; it does not replace Step 6's manual check, which is still the only way to verify actual iframe rendering.

`anyio` is already an installed transitive dependency of `mcp` (confirmed during Task 2) — do not add `pytest-asyncio` or any new dev dependency; wrap the async flow in `anyio.run()` inside an ordinary synchronous `def test_...():` function.

Create `toolkit/tests/integration/test_mcp_protocol.py`:

```python
"""Real client<->server round trip over mcp.client._memory.InMemoryTransport.

No stdio, no network, no live MCP-UI host — but a genuine MCP protocol
exchange against the actual server built by arcgentic.mcp.server.build_apps(),
not a hand-mocked stub. Visual iframe rendering is out of scope here (see
docs/plans/2026-08-12-arcgentic-mcp-ui-status-panel-plan.md Task 4 Step 6
for the manual-only check that covers that).
"""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
import yaml
from mcp.client._memory import InMemoryTransport
from mcp.client.session import ClientSession
from mcp.server import MCPServer

from arcgentic.mcp import server as server_module


def test_round_status_panel_over_real_mcp_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "state.yaml"
    state_path.write_text(
        yaml.safe_dump(
            {
                "current_round": {"id": "R12", "state": "awaiting_audit"},
                "project": {"arcgentic_v2": {"next_role": "auditor", "role_sessions": {}}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server_module, "STATE_PATH", state_path)

    async def _run() -> tuple[str, str, str]:
        apps = server_module.build_apps()
        mcp_server = MCPServer("arcgentic", extensions=[apps])
        async with InMemoryTransport(mcp_server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]

                call_result = await session.call_tool("round_status_panel", {})
                text_parts = [
                    block.text for block in call_result.content if hasattr(block, "text")
                ]
                tool_text = "\n".join(text_parts)

                resource = await session.read_resource(server_module.RESOURCE_URI)
                resource_text = ""
                for content in resource.contents:
                    if hasattr(content, "text"):
                        resource_text = content.text
                        break

                return ",".join(tool_names), tool_text, resource_text

    tool_names_csv, tool_text, resource_html = anyio.run(_run)

    assert tool_names_csv == "round_status_panel"
    assert "R12" in tool_text
    assert "Auditor: active" in tool_text
    assert "R12" in resource_html
    assert "<button id=\"dispatch-btn\">" in resource_html
```

Run: `cd toolkit && python -m pytest tests/integration/test_mcp_protocol.py -v`
Expected: PASS (1 test). If it fails with an import error naming `mcp.client._memory` or `mcp.client.session`, do not guess a substitute API — these were confirmed present in the installed `mcp==2.0.0` package during planning; report the exact error instead of working around it, since a wrong workaround here would validate nothing.

Run: `cd toolkit && python -m mypy tests/integration/test_mcp_protocol.py && python -m ruff check tests/integration/test_mcp_protocol.py`
Expected: no errors.

- [ ] **Step 6: Manual end-to-end verification (visual rendering cannot be automated — record the outcome in your task report)**

In an MCP-UI-capable host (this session's environment, or Claude Desktop with the plugin's `.mcp.json` picked up):

1. Start a fresh `.agentic-rounds/state.yaml`-having project (or reuse this repo's own `.agentic-rounds/`), invoke the `round_status_panel` tool.
2. Confirm the panel renders inline (not just text) — round id, role rows with correct active/recorded/pending coloring, verdict line.
3. Wait ~10 seconds without touching anything — confirm the panel content updates on its own (auto-poll working). If `current_round.state` doesn't change during the wait, this at minimum confirms no errors are thrown on repeated automatic re-invocation — a visible content change requires manually advancing the round state in another window during the observation.
4. Switch away from the tab/window for a few seconds, switch back — confirm no errors; polling should have paused and resumed (cannot be directly observed without host devtools, so this step is a smoke check, not a precise assertion).
5. If a round is `closed`, confirm the "派发下一角色" button is absent.
6. If a round is active, click "派发下一角色" — confirm a new message ("请派发下一个角色") appears in the conversation (sent via the `prompt` action) rather than any direct state mutation.

Record which of 1-6 passed, and for anything that didn't, whether it's a host-support gap (e.g. `resources/read` not re-triggered by a `tool` re-invocation on that particular host) versus a bug in this implementation — this distinction matters because host-side MCP Apps support is still young (see design doc §1's Claude Desktop rendering bug reference) and a host limitation is not something this plan can fix. Step 5's automated test already gives strong confidence in the protocol/data-shape layer, so this manual pass can focus entirely on the visual/interactive layer it cannot cover.

- [ ] **Step 7: Commit**

```bash
cd "/Users/archiesun/Desktop/Arc Studio/arcgentic"
git add .mcp.json toolkit/tests/integration/test_mcp_protocol.py
git commit -m "feat(mcp): declare arcgentic MCP server in .mcp.json, add protocol test

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
