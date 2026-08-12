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


def test_round_status_panel_reports_unreadable_state_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "state.yaml"
    state_path.write_text("current_round: {id: R1, state: dev_in_progress}\n", encoding="utf-8")
    monkeypatch.setattr(server, "STATE_PATH", state_path)

    def _raise_permission_error(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("permission denied")

    monkeypatch.setattr(server, "_load_current_state", _raise_permission_error)
    text = server.round_status_panel()
    assert "failed to read" in text
    assert "permission denied" in text


def test_round_status_panel_html_reports_unreadable_state_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "state.yaml"
    state_path.write_text("current_round: {id: R1, state: dev_in_progress}\n", encoding="utf-8")
    monkeypatch.setattr(server, "STATE_PATH", state_path)

    def _raise_os_error(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk read error")

    monkeypatch.setattr(server, "_load_current_state", _raise_os_error)
    html = server._round_status_panel_html()
    assert "disk read error" in html


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
    meta = tools[0].meta
    assert meta is not None
    assert meta["ui"]["resourceUri"] == server.RESOURCE_URI
    resources = apps.resources()
    assert len(resources) == 1
    assert resources[0].resource.uri == server.RESOURCE_URI
    assert resources[0].resource.mime_type == "text/html;profile=mcp-app"
    # Must not leak the Python callback's function name (a leading-underscore
    # implementation detail) into the MCP protocol's resources/list output.
    assert resources[0].resource.name == "round-status-panel"
