"""audit_check — mechanical fact-verification engine for audit handoff docs.

Reads the markdown fact table in an audit handoff (typically `§ 7. Mechanical audit facts`),
executes each command, compares actual output against expected backtick-wrapped value,
reports pass/fail/skip counts.

Recognized fact-command prefixes (per spec § 2.11):
- `cd <path> && <cmd>` — chdir then run (path quoted with shquote)
- `git <args>` — git subcommand
- `uv run <args>` — uv-managed Python execution
- `bash <args>` — explicit bash invocation
- `arcgentic <subcmd>` — arcgentic CLI invocation

Modes:
- default: report counts; exit 0 always
- `--strict`: exit 1 on any FAIL or SKIP
- `--strict-extended`: ALSO run AC-1 (3 clauses) + AC-3 (detection-capability)

AC-1 Clause A: verdict-claim vs fact count — the "N facts verified" claim in § 8 verdict
    must match the actual row count in § 7
AC-1 Clause B: section references resolve — `§ X.Y` in prose must correspond to actual headers
AC-1 Clause C: prose claims match expected values — narrative text like "all gates PASS"
    must align with the gate table's actual statuses
AC-3: detection-capability vacuity — `≥` / `>=` / `<=` / `≤` patterns in expected values
    are vacuous (always satisfiable); flag them

Spec reference: docs/plans/2026-05-13-arcgentic-v0.2.0-spec.md § 14
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────

_RECOGNIZED_PREFIXES = ("cd ", "git ", "uv run ", "bash ", "arcgentic ")
_FACT_TABLE_HEADER_RE = re.compile(
    r"\s*\|\s*#\s*\|\s*Command\s*\|\s*Expected\s*\|\s*Comment\s*\|\s*"
)
_VACUOUS_PATTERNS = ["≥", ">=", "<=", "≤"]


# ── Data structures ────────────────────────────────────────────────────


@dataclass(frozen=True)
class Fact:
    """One row from the mechanical audit facts table."""

    index: int  # the # column
    command: str  # raw command string (after unescaping `\|` → `|`)
    expected: str  # expected output (backtick-wrapped → inner content)
    comment: str  # description for humans
    line_no: int  # line number in source doc


@dataclass(frozen=True)
class FactResult:
    """Result of executing one fact's command."""

    fact: Fact
    status: str  # "PASS" | "FAIL" | "SKIP"
    actual: str  # the trimmed stdout (empty on SKIP)
    error: str | None = None  # error message on FAIL or SKIP


@dataclass(frozen=True)
class AuditCheckResult:
    """End-to-end result of running audit-check."""

    fact_results: list[FactResult]
    pass_count: int
    fail_count: int
    skip_count: int
    ac1_violations: list[str] = field(default_factory=list)  # AC-1 issues (strict-extended only)
    ac3_violations: list[str] = field(default_factory=list)  # AC-3 issues (strict-extended only)
    exit_code: int = 0
    summary_text: str = ""


# ── Parsing ────────────────────────────────────────────────────────────


def _unescape_command(s: str) -> str:
    """Unescape `\\|` → `|` for fact-table commands (since `|` is a markdown table separator)."""
    return s.replace(r"\|", "|")


def _strip_backticks(s: str) -> str:
    """Strip surrounding backticks from expected value (e.g. ``5`` → `5`)."""
    s = s.strip()
    if s.startswith("`") and s.endswith("`"):
        return s[1:-1]
    return s


def parse_facts(audit_md: str) -> list[Fact]:
    """Parse the `§ 7 Mechanical audit facts` table from an audit handoff doc.

    Returns the list of Fact rows. If the table is not found, returns empty list.
    """
    facts: list[Fact] = []
    lines = audit_md.splitlines()
    in_table = False
    in_section_7 = False

    for line_no, ln in enumerate(lines, start=1):
        # Strip leading whitespace for header detection (handles indented markdown in raw strings)
        lns = ln.strip()
        # Detect entry into § 7
        if re.match(r"^##\s+§\s*7[.\s]", lns) or re.match(r"^##\s+7\.", lns):
            in_section_7 = True
            continue
        # Detect leaving § 7 (next ## section that is NOT § 7)
        if in_section_7 and lns.startswith("## "):
            if not (re.match(r"^##\s+§\s*7[.\s]", lns) or re.match(r"^##\s+7\.", lns)):
                break
        if not in_section_7:
            continue

        # Detect table header to start parsing rows
        if _FACT_TABLE_HEADER_RE.match(lns):
            in_table = True
            continue
        if in_table and re.match(r"\s*\|\s*[-:]+\s*\|", lns):
            # Header separator row — skip
            continue

        if in_table:
            stripped = lns
            if not stripped or not stripped.startswith("|"):
                # Table ended (blank or non-table line)
                in_table = False
                continue
            # Parse row: | # | Command | Expected | Comment |
            # Temporarily replace escaped pipes \| with a sentinel BEFORE splitting on |,
            # so that `git log \| wc -l` doesn't become extra columns.
            _pipe_sentinel = "\x00PIPE\x00"
            safe_line = stripped.replace(r"\|", _pipe_sentinel)
            cells_raw = [c.strip() for c in safe_line.strip("|").split("|")]
            # Restore sentinel back to | in each cell
            cells = [c.replace(_pipe_sentinel, "|") for c in cells_raw]
            if len(cells) < 4:
                continue
            idx_str, cmd, expected, comment = cells[0], cells[1], cells[2], cells[3]
            try:
                idx = int(idx_str)
            except ValueError:
                continue  # not a numeric index row — skip
            # Strip backtick wrapper from command cell if present
            cmd_clean = cmd.strip()
            if cmd_clean.startswith("`") and cmd_clean.endswith("`"):
                cmd_clean = cmd_clean[1:-1]
            facts.append(
                Fact(
                    index=idx,
                    command=cmd_clean,
                    expected=_strip_backticks(expected),
                    comment=comment,
                    line_no=line_no,
                )
            )

    return facts


# ── Execution ──────────────────────────────────────────────────────────


def _command_is_recognized(cmd: str) -> bool:
    """Check if the command starts with one of the 5 recognized prefixes."""
    return any(cmd.startswith(p) for p in _RECOGNIZED_PREFIXES)


def execute_fact(
    fact: Fact,
    repo_root: Path | None = None,
    timeout_seconds: int = 60,
) -> FactResult:
    """Execute a fact's command via subprocess shell=True. Return FactResult."""
    if not _command_is_recognized(fact.command):
        return FactResult(
            fact=fact,
            status="SKIP",
            actual="",
            error=(
                f"Command does not start with a recognized prefix "
                f"{_RECOGNIZED_PREFIXES}: `{fact.command[:80]}`"
            ),
        )

    cwd = str(repo_root) if repo_root else None
    try:
        result = subprocess.run(
            fact.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return FactResult(
            fact=fact,
            status="FAIL",
            actual="",
            error=f"timeout after {timeout_seconds}s",
        )

    actual = result.stdout.strip()

    if actual == fact.expected:
        return FactResult(fact=fact, status="PASS", actual=actual)
    return FactResult(
        fact=fact,
        status="FAIL",
        actual=actual,
        error=(
            f"expected `{fact.expected}`, got `{actual}` "
            f"(stderr: {result.stderr.strip()[:200]})"
        ),
    )


# ── AC-1 + AC-3 checks (strict-extended) ───────────────────────────────


def check_ac1_clause_a(audit_md: str, fact_count: int) -> list[str]:
    """AC-1 Clause A: verdict-claim section's "N facts verified" matches actual count.

    Looks for a number near the verdict (§ 8) that should match fact_count.
    Returns list of violation strings (empty if compliant).
    """
    violations: list[str] = []
    # Match patterns like "all N facts pass" / "N/N PASS" / "verified N mechanical facts"
    verdict_match = re.search(
        r"(\d+)\s*(?:/\s*(\d+))?\s*(?:PASS|verified|facts)", audit_md, re.IGNORECASE
    )
    if verdict_match:
        claimed = int(verdict_match.group(1))
        if claimed != fact_count:
            violations.append(
                f"AC-1 Clause A: verdict mentions {claimed} facts "
                f"but § 7 table has {fact_count} rows"
            )
    return violations


def check_ac1_clause_b(audit_md: str) -> list[str]:
    """AC-1 Clause B: section references like `§ X.Y` resolve to actual headers."""
    violations: list[str] = []
    # Find all `§ N` or `§ N.M` references in prose
    refs = set(re.findall(r"§\s*(\d+(?:\.\d+)?)", audit_md))
    # Find all headers
    headers: set[str] = set()
    for m in re.finditer(r"^##\s*§?\s*(\d+(?:\.\d+)?)", audit_md, re.MULTILINE):
        headers.add(m.group(1))
    for m in re.finditer(r"^###\s*(\d+\.\d+)", audit_md, re.MULTILINE):
        headers.add(m.group(1))

    for ref in refs:
        # § 1.2 references should resolve to either header 1.2 or top-level 1
        top_level = ref.split(".")[0]
        if ref not in headers and top_level not in headers:
            violations.append(
                f"AC-1 Clause B: § {ref} reference does not resolve to any header"
            )
    return violations


def check_ac1_clause_c(audit_md: str, fact_results: list[FactResult]) -> list[str]:
    """AC-1 Clause C: prose narrative claims align with mechanical fact results.

    Simple heuristic: if prose says "all gates PASS" but any fact-result is FAIL,
    that's a Clause C violation.
    """
    violations: list[str] = []
    has_fails = any(fr.status == "FAIL" for fr in fact_results)
    if has_fails:
        if re.search(
            r"all\s+(gates?|facts?|tests?)\s+(PASS|passed)", audit_md, re.IGNORECASE
        ):
            fail_count = sum(1 for fr in fact_results if fr.status == "FAIL")
            violations.append(
                f"AC-1 Clause C: prose claims 'all PASS' but {fail_count} "
                f"fact result(s) are FAIL"
            )
    return violations


def check_ac3(facts: list[Fact]) -> list[str]:
    """AC-3: detection-capability check — `≥`, `>=`, `<=`, `≤` in expected values are vacuous.

    A vacuous expected like `≥ 5` is always satisfiable by larger values; it doesn't
    actually test anything tight. Flag these.
    """
    violations: list[str] = []
    for fact in facts:
        for pattern in _VACUOUS_PATTERNS:
            if pattern in fact.expected:
                violations.append(
                    f"AC-3: fact #{fact.index} (line {fact.line_no}) uses vacuous comparator "
                    f"`{pattern}` in expected `{fact.expected}` — replace with exact value"
                )
                break  # one violation per fact
    return violations


# ── Main orchestration ─────────────────────────────────────────────────


def run(
    audit_path: Path,
    strict: bool = False,
    strict_extended: bool = False,
    repo_root: Path | None = None,
) -> AuditCheckResult:
    """Read audit handoff at `audit_path`, parse fact table, execute each fact, return result."""
    try:
        audit_md = audit_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return AuditCheckResult(
            fact_results=[],
            pass_count=0,
            fail_count=0,
            skip_count=0,
            exit_code=2,
            summary_text=f"FAILED: audit handoff not found at {audit_path}",
        )

    facts = parse_facts(audit_md)
    fact_results = [execute_fact(f, repo_root=repo_root) for f in facts]

    pass_count = sum(1 for fr in fact_results if fr.status == "PASS")
    fail_count = sum(1 for fr in fact_results if fr.status == "FAIL")
    skip_count = sum(1 for fr in fact_results if fr.status == "SKIP")

    ac1_violations: list[str] = []
    ac3_violations: list[str] = []
    if strict_extended:
        ac1_violations.extend(check_ac1_clause_a(audit_md, len(facts)))
        ac1_violations.extend(check_ac1_clause_b(audit_md))
        ac1_violations.extend(check_ac1_clause_c(audit_md, fact_results))
        ac3_violations.extend(check_ac3(facts))

    # Compute exit_code
    exit_code = 0
    if strict and (fail_count > 0 or skip_count > 0):
        exit_code = 1
    if strict_extended and (ac1_violations or ac3_violations):
        exit_code = 1

    # Compose summary text
    parts = [f"{pass_count}/{len(facts)} PASS, {fail_count} FAIL, {skip_count} SKIP"]
    if strict_extended:
        parts.append(f"AC-1: {len(ac1_violations)} violation(s)")
        parts.append(f"AC-3: {len(ac3_violations)} violation(s)")
    summary_text = " | ".join(parts)

    return AuditCheckResult(
        fact_results=fact_results,
        pass_count=pass_count,
        fail_count=fail_count,
        skip_count=skip_count,
        ac1_violations=ac1_violations,
        ac3_violations=ac3_violations,
        exit_code=exit_code,
        summary_text=summary_text,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: `arcgentic audit-check <path> [--strict|--strict-extended]`."""
    parser = argparse.ArgumentParser(prog="arcgentic audit-check")
    parser.add_argument("audit_file", help="Path to audit handoff markdown")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any FAIL or SKIP",
    )
    parser.add_argument(
        "--strict-extended",
        action="store_true",
        help="Also run AC-1 (3 clauses) + AC-3 checks; exit 1 on violation",
    )
    args = parser.parse_args(argv)

    result = run(
        audit_path=Path(args.audit_file),
        strict=args.strict,
        strict_extended=args.strict_extended,
    )

    print(result.summary_text)

    if result.ac1_violations:
        print("\nAC-1 violations:")
        for v in result.ac1_violations:
            print(f"  - {v}")
    if result.ac3_violations:
        print("\nAC-3 violations:")
        for v in result.ac3_violations:
            print(f"  - {v}")

    # Print per-fact FAIL/SKIP details
    for fr in result.fact_results:
        if fr.status == "FAIL":
            print(f"\nFACT #{fr.fact.index} FAIL: {fr.error}")
        elif fr.status == "SKIP":
            print(f"\nFACT #{fr.fact.index} SKIP: {fr.error}")

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
