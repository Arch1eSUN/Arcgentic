"""arcgentic MCP server: exposes the round-status panel via MCP Apps (SEP-1865)."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]
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
    except (V2SessionOrchestrationError, yaml.YAMLError, OSError) as exc:
        return f"arcgentic: failed to read {STATE_PATH}: {exc}"
    if state is None:
        return "arcgentic: no active round (.agentic-rounds/state.yaml not found)."
    return render_status_summary_text(state)


def _round_status_panel_html() -> str:
    """FunctionResource callback for RESOURCE_URI — re-invoked on every resources/read."""
    try:
        state = _load_current_state()
    except (V2SessionOrchestrationError, yaml.YAMLError, OSError) as exc:
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
            name="round-status-panel",
        )
    )
    return apps


def run_server() -> None:
    apps = build_apps()
    server = MCPServer("arcgentic", extensions=[apps])
    server.run(transport="stdio")
