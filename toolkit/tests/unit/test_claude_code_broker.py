from __future__ import annotations

import json
from pathlib import Path

from arcgentic.claude_code_broker import (
    handle_stop_event,
    install_project_hooks,
)


def _write_state(path: Path, *, pending_role: str = "planner") -> None:
    path.write_text(
        f"""
project:
  root: {path.parent.parent}
  arcgentic_v2:
    host: claude-code-broker
    mode: multi-session-subthread
    orchestrator_status: sleeping
    pending_role: {pending_role}
    pending_thread_id: {pending_role}-session-1
current_round:
  id: R1
  state: intake
""",
        encoding="utf-8",
    )


def test_handle_stop_blocks_pending_role_without_return_footer(tmp_path: Path) -> None:
    state = tmp_path / ".agentic-rounds" / "state.yaml"
    state.parent.mkdir()
    _write_state(state)

    result = handle_stop_event(
        {
            "session_id": "claude-session-1",
            "hook_event_name": "Stop",
            "cwd": str(tmp_path),
            "stop_hook_active": False,
            "last_assistant_message": "Planner wrote a plan but forgot the footer.",
        },
        state_path=state,
    )

    assert result.exit_code == 0
    assert result.output is not None
    assert result.output["decision"] == "block"
    assert "arcgentic-role-return" in str(result.output["reason"])


def test_handle_stop_records_role_return_and_writes_inbox(tmp_path: Path) -> None:
    state = tmp_path / ".agentic-rounds" / "state.yaml"
    state.parent.mkdir()
    _write_state(state)

    result = handle_stop_event(
        {
            "session_id": "claude-session-1",
            "hook_event_name": "Stop",
            "cwd": str(tmp_path),
            "stop_hook_active": False,
            "last_assistant_message": """
Planner completed the plan.

```arcgentic-role-return
{"role":"planner","status":"planned","round_id":"R1","state":"awaiting_dev_start","artifacts":{"handoff":"docs/plans/R1.md"},"next_recommended_role":"developer"}
```
""",
        },
        state_path=state,
    )

    assert result.exit_code == 0
    assert result.output is not None
    assert "recorded planner return" in str(result.output["systemMessage"])
    saved = state.read_text(encoding="utf-8")
    assert "orchestrator_status: active" in saved
    assert "state: awaiting_dev_start" in saved

    inbox = state.parent / "claude-code-broker" / "inbox" / "claude-session-1-planner-R1.json"
    assert inbox.exists()
    payload = json.loads(inbox.read_text(encoding="utf-8"))
    assert payload["signal"]["role"] == "planner"
    assert payload["next_plan"]["next_role"] == "developer"


def test_handle_stop_does_not_block_recursing_stop_hook(tmp_path: Path) -> None:
    state = tmp_path / ".agentic-rounds" / "state.yaml"
    state.parent.mkdir()
    _write_state(state)

    result = handle_stop_event(
        {
            "session_id": "claude-session-1",
            "hook_event_name": "Stop",
            "cwd": str(tmp_path),
            "stop_hook_active": True,
            "last_assistant_message": "Still missing footer.",
        },
        state_path=state,
    )

    assert result.exit_code == 0
    assert result.output is not None
    assert "decision" not in result.output
    assert "waiting for a valid" in str(result.output["systemMessage"])


def test_install_project_hooks_merges_stop_and_subagent_stop(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "echo existing",
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    install_project_hooks(settings, state_path=".agentic-rounds/state.yaml")
    install_project_hooks(settings, state_path=".agentic-rounds/state.yaml")

    payload = json.loads(settings.read_text(encoding="utf-8"))
    stop_hooks = payload["hooks"]["Stop"]
    subagent_hooks = payload["hooks"]["SubagentStop"]
    commands = [
        hook["command"]
        for group in stop_hooks
        for hook in group.get("hooks", [])
        if "command" in hook
    ]
    assert commands.count(
        "arcgentic claude-code-broker handle-stop --state .agentic-rounds/state.yaml"
    ) == 1
    assert subagent_hooks[0]["hooks"][0]["command"].startswith(
        "arcgentic claude-code-broker handle-stop"
    )
