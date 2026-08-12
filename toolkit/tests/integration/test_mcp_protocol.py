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
