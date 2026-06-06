"""Claude Code broker runtime for Arcgentic V2."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .v2_session_orchestration import (
    RoleReturnSignal,
    V2SessionOrchestrationError,
    apply_role_return_signal,
    build_role_session_plan,
    load_state_file,
    write_state_file,
)


@dataclass(frozen=True)
class BrokerHookResult:
    exit_code: int
    output: dict[str, object] | None = None


def _json_stdout(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _project_v2(state: dict[str, object]) -> dict[str, object]:
    project = state.get("project")
    if not isinstance(project, dict):
        return {}
    v2 = project.get("arcgentic_v2")
    return v2 if isinstance(v2, dict) else {}


def _write_broker_inbox(
    state_path: Path,
    hook_input: dict[str, Any],
    signal: RoleReturnSignal,
    next_plan: dict[str, object],
) -> Path:
    inbox_dir = state_path.parent / "claude-code-broker" / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    session_id = str(hook_input.get("session_id") or "unknown-session")
    filename = f"{session_id}-{signal.role}-{signal.round_id}.json"
    inbox_path = inbox_dir / filename
    inbox_path.write_text(
        json.dumps(
            {
                "hook_event_name": hook_input.get("hook_event_name"),
                "session_id": session_id,
                "role": signal.role,
                "round_id": signal.round_id,
                "signal": signal.to_dict(),
                "next_plan": next_plan,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return inbox_path


def _validate_auditor_pass_gate(
    state: dict[str, object],
    signal: RoleReturnSignal,
    *,
    state_path: Path,
) -> None:
    if signal.role != "auditor" or signal.state != "passed" or signal.status.upper() != "PASS":
        return
    verdict_raw = signal.artifacts.get("verdict")
    if not isinstance(verdict_raw, str) or not verdict_raw.strip():
        raise V2SessionOrchestrationError(
            "auditor PASS return must include artifacts.verdict"
        )
    project = state.get("project")
    project_root_raw = project.get("root") if isinstance(project, dict) else None
    project_root = Path(str(project_root_raw)) if project_root_raw else state_path.parent.parent
    verdict_path = Path(verdict_raw)
    if not verdict_path.is_absolute():
        verdict_path = project_root / verdict_path

    from .audit_check import run as audit_check_run

    audit_check = audit_check_run(
        verdict_path,
        strict=True,
        strict_extended=True,
        repo_root=project_root,
    )
    if audit_check.exit_code != 0:
        raise V2SessionOrchestrationError(
            "auditor PASS strict audit-check failed: "
            f"{audit_check.summary_text}"
        )


def handle_stop_event(
    hook_input: dict[str, Any],
    *,
    state_path: Path,
) -> BrokerHookResult:
    state = load_state_file(state_path)
    v2 = _project_v2(state)
    if str(v2.get("host") or "") not in {"", "claude-code-broker"}:
        return BrokerHookResult(exit_code=0)

    orchestrator_status = str(v2.get("orchestrator_status") or "active")
    if orchestrator_status != "sleeping":
        return BrokerHookResult(exit_code=0)

    message = str(hook_input.get("last_assistant_message") or "")
    try:
        signal = RoleReturnSignal.from_text(message)
    except V2SessionOrchestrationError:
        if bool(hook_input.get("stop_hook_active")):
            return BrokerHookResult(
                exit_code=0,
                output={
                    "systemMessage": (
                        "Arcgentic Claude Code broker is still waiting for a "
                        "valid arcgentic-role-return footer."
                    )
                },
            )
        pending_role = str(v2.get("pending_role") or "unknown")
        return BrokerHookResult(
            exit_code=0,
            output={
                "decision": "block",
                "reason": (
                    "Arcgentic Orchestrator is sleeping and waiting for "
                    f"{pending_role}. Finish the role-owned work and include exactly "
                    "one ```arcgentic-role-return``` footer."
                ),
            },
        )

    try:
        _validate_auditor_pass_gate(state, signal, state_path=state_path)
        updated = apply_role_return_signal(state, signal)
    except V2SessionOrchestrationError as exc:
        return BrokerHookResult(
            exit_code=0,
            output={
                "decision": "block",
                "reason": f"Arcgentic rejected the role return: {exc}",
            },
        )
    write_state_file(state_path, updated)
    next_plan = build_role_session_plan(updated, host="claude-code-broker").to_dict()
    inbox_path = _write_broker_inbox(state_path, hook_input, signal, next_plan)
    return BrokerHookResult(
        exit_code=0,
        output={
            "systemMessage": (
                "Arcgentic broker recorded "
                f"{signal.role} return for {signal.round_id}; inbox={inbox_path}"
            ),
            "suppressOutput": False,
        },
    )


def _arcgentic_hook_command(state_path: str) -> str:
    return f"arcgentic claude-code-broker handle-stop --state {state_path}"


def install_project_hooks(settings_path: Path, *, state_path: str) -> None:
    if settings_path.exists():
        raw = json.loads(settings_path.read_text(encoding="utf-8") or "{}")
        if not isinstance(raw, dict):
            raise ValueError(f"settings file must contain a JSON object: {settings_path}")
    else:
        raw = {}

    hooks = raw.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("settings hooks must be a JSON object")

    command = _arcgentic_hook_command(state_path)
    handler = {"type": "command", "command": command}
    for event in ("Stop", "SubagentStop"):
        event_groups = hooks.setdefault(event, [])
        if not isinstance(event_groups, list):
            raise ValueError(f"hooks.{event} must be a list")
        if _has_hook_command(event_groups, command):
            continue
        event_groups.append({"hooks": [handler]})

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _has_hook_command(event_groups: list[object], command: str) -> bool:
    for group in event_groups:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            if isinstance(handler, dict) and handler.get("command") == command:
                return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arcgentic claude-code-broker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install-hooks")
    install_parser.add_argument("--settings", default=".claude/settings.local.json")
    install_parser.add_argument("--state", default=".agentic-rounds/state.yaml")

    stop_parser = subparsers.add_parser("handle-stop")
    stop_parser.add_argument("--state", default=".agentic-rounds/state.yaml")

    args = parser.parse_args(argv)
    if args.command == "install-hooks":
        install_project_hooks(Path(args.settings), state_path=args.state)
        print(f"installed Claude Code broker hooks: {args.settings}")
        return 0

    if args.command == "handle-stop":
        hook_input = json.loads(sys.stdin.read() or "{}")
        if not isinstance(hook_input, dict):
            raise SystemExit("Claude Code hook input must be a JSON object")
        result = handle_stop_event(hook_input, state_path=Path(args.state))
        if result.output is not None:
            _json_stdout(result.output)
        return result.exit_code

    raise SystemExit(f"unsupported command: {args.command}")
