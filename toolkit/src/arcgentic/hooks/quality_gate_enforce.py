"""quality-gate-enforce — run all 4 quality gates; exit 0 only if all pass.

Gates (per spec § 17):
1. mypy --strict on configured source/test dirs
2. pytest with --tb=no
3. ruff check .
4. arcgentic audit-check on a target handoff (if provided)

Per spec § 6.3, this hook is invoked:
- By execute-round Phase 3 (programmatically; not yet integrated — ER-AUDIT-GATE-4
  forward-debt; this module is the Python implementation that ER will eventually call)
- By developer agents pre-commit (manual run via `arcgentic quality-gate-enforce`)
- By Claude Code Stop hook events (if user installs in .claude/hooks/)

Uses shquote() from _local_env for path safety (paths-with-spaces protection).

CLI: `arcgentic quality-gate-enforce [--repo-root PATH] [--audit-handoff PATH]
      [--skip-audit-check]`

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 6.3 + § 17.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from arcgentic.adapters._local_env import shquote


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED"
    exit_code: int
    output_tail: str = ""  # last ~10 lines of output for diagnostics
    error: str | None = None


@dataclass(frozen=True)
class QualityGateEnforceResult:
    gates: list[GateResult]
    all_pass: bool
    exit_code: int  # 0 if all_pass else 1
    summary_text: str

    def __str__(self) -> str:
        lines = [self.summary_text, ""]
        for g in self.gates:
            lines.append(f"  {g.name}: {g.status}")
            if g.status != "PASS" and g.output_tail:
                # Indent diagnostic tail
                for tl in g.output_tail.splitlines()[-10:]:
                    lines.append(f"    | {tl}")
        return "\n".join(lines)


def _run_command(cmd: str, timeout_seconds: int = 600) -> tuple[str, str, int]:
    """Run shell command. Returns (stdout, stderr, exit_code)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {timeout_seconds}s", 124


def _gate_mypy(repo_root: Path) -> GateResult:
    rr = shquote(str(repo_root))
    stdout, stderr, code = _run_command(
        f"cd {rr} && mypy --strict toolkit/src/ toolkit/tests/"
    )
    return GateResult(
        name="mypy",
        status="PASS" if code == 0 else "FAIL",
        exit_code=code,
        output_tail=stdout if code == 0 else (stderr or stdout),
    )


def _gate_pytest(repo_root: Path) -> GateResult:
    rr_toolkit = shquote(str(repo_root / "toolkit"))
    stdout, stderr, code = _run_command(f"cd {rr_toolkit} && pytest --tb=no -q")
    return GateResult(
        name="pytest",
        status="PASS" if code == 0 else "FAIL",
        exit_code=code,
        output_tail=stdout if code == 0 else (stderr or stdout),
    )


def _gate_ruff(repo_root: Path) -> GateResult:
    rr_toolkit = shquote(str(repo_root / "toolkit"))
    stdout, stderr, code = _run_command(f"cd {rr_toolkit} && ruff check .")
    return GateResult(
        name="ruff",
        status="PASS" if code == 0 else "FAIL",
        exit_code=code,
        output_tail=stdout if code == 0 else (stderr or stdout),
    )


def _gate_audit_check(audit_handoff: Path) -> GateResult:
    """Gate 4: audit-check on the target handoff."""
    if not audit_handoff.exists():
        return GateResult(
            name="audit-check",
            status="SKIPPED",
            exit_code=0,
            error=f"handoff not found at {audit_handoff}",
        )
    audit_path = shquote(str(audit_handoff))
    stdout, stderr, code = _run_command(
        f"arcgentic audit-check {audit_path} --strict-extended"
    )
    return GateResult(
        name="audit-check",
        status="PASS" if code == 0 else "FAIL",
        exit_code=code,
        output_tail=stdout if code == 0 else (stderr or stdout),
    )


def run(
    *,
    repo_root: Path | None = None,
    audit_handoff: Path | None = None,
    skip_audit_check: bool = False,
) -> QualityGateEnforceResult:
    """Run all 4 quality gates. Return aggregated result.

    Args:
        repo_root: where to run gates from. Defaults to git rev-parse
            --show-toplevel or cwd if not in a git repo.
        audit_handoff: path to audit handoff doc for gate 4 (audit-check).
            If None, gate 4 is SKIPPED with an error note.
        skip_audit_check: if True, gate 4 is SKIPPED unconditionally (even
            if audit_handoff is provided).

    Returns:
        QualityGateEnforceResult. exit_code = 0 if all gates are PASS,
        else 1. SKIPPED counts as not-PASS, so exit_code=1 if any gate
        is SKIPPED.
    """
    if repo_root is None:
        stdout, _, code = _run_command("git rev-parse --show-toplevel")
        repo_root = (
            Path(stdout.strip())
            if code == 0 and stdout.strip()
            else Path.cwd()
        )

    gates: list[GateResult] = []
    gates.append(_gate_mypy(repo_root))
    gates.append(_gate_pytest(repo_root))
    gates.append(_gate_ruff(repo_root))

    if skip_audit_check:
        gates.append(
            GateResult(
                name="audit-check",
                status="SKIPPED",
                exit_code=0,
                error="--skip-audit-check flag set",
            )
        )
    elif audit_handoff is None:
        gates.append(
            GateResult(
                name="audit-check",
                status="SKIPPED",
                exit_code=0,
                error="no audit handoff path provided (--audit-handoff missing)",
            )
        )
    else:
        gates.append(_gate_audit_check(audit_handoff))

    all_pass = all(g.status == "PASS" for g in gates)
    exit_code = 0 if all_pass else 1
    n_pass = sum(1 for g in gates if g.status == "PASS")
    n_fail = sum(1 for g in gates if g.status == "FAIL")
    n_skip = sum(1 for g in gates if g.status == "SKIPPED")
    summary_text = (
        f"quality-gate-enforce: {n_pass} PASS, {n_fail} FAIL, {n_skip} SKIPPED"
    )

    return QualityGateEnforceResult(
        gates=gates,
        all_pass=all_pass,
        exit_code=exit_code,
        summary_text=summary_text,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arcgentic quality-gate-enforce")
    parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        help="Repo root path (defaults to git rev-parse --show-toplevel)",
    )
    parser.add_argument(
        "--audit-handoff",
        dest="audit_handoff",
        default=None,
        help="Path to audit handoff for gate 4 (audit-check)",
    )
    parser.add_argument(
        "--skip-audit-check",
        action="store_true",
        help="Skip gate 4 (audit-check) unconditionally",
    )
    args = parser.parse_args(argv)

    result = run(
        repo_root=Path(args.repo_root) if args.repo_root else None,
        audit_handoff=Path(args.audit_handoff) if args.audit_handoff else None,
        skip_audit_check=args.skip_audit_check,
    )
    print(result)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
