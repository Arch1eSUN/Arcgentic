"""Unit tests for audit_check — mechanical fact-verification engine.

TDD: these tests are written BEFORE audit_check.py implementation.
They verify parse_facts, execute_fact, check_ac1_clause_*, check_ac3, run(), main().
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from arcgentic.audit_check import (
    AuditCheckResult,
    Fact,
    FactResult,
    _strip_backticks,
    _unescape_command,
    check_ac1_clause_a,
    check_ac1_clause_b,
    check_ac1_clause_c,
    check_ac3,
    execute_fact,
    main,
    parse_facts,
    run,
)


# ── Helpers ────────────────────────────────────────────────────────────


def _make_sample_audit(tmp_path: Path, fact_lines: list[str]) -> Path:
    """Construct a minimal audit handoff with the given fact rows."""
    facts_md = "\n".join(fact_lines)
    audit_path = tmp_path / "test_audit.md"
    audit_path.write_text(
        f"""# Test audit

## § 7. Mechanical audit facts

| # | Command | Expected | Comment |
|---|---|---|---|
{facts_md}

## § 8. Verdict

STATUS: DONE. 3/3 PASS verified.
""",
        encoding="utf-8",
    )
    return audit_path


def _make_fact(
    index: int = 1,
    command: str = "git --version",
    expected: str = "git version 2.0.0",
    comment: str = "test",
    line_no: int = 10,
) -> Fact:
    return Fact(
        index=index,
        command=command,
        expected=expected,
        comment=comment,
        line_no=line_no,
    )


# ── _unescape_command ──────────────────────────────────────────────────


def test_unescape_command_replaces_escaped_pipe() -> None:
    assert _unescape_command(r"git log --oneline \| wc -l") == "git log --oneline | wc -l"


def test_unescape_command_no_escapes() -> None:
    assert _unescape_command("git --version") == "git --version"


# ── _strip_backticks ───────────────────────────────────────────────────


def test_strip_backticks_removes_surrounding_backticks() -> None:
    assert _strip_backticks("`5`") == "5"


def test_strip_backticks_no_backticks() -> None:
    assert _strip_backticks("5") == "5"


def test_strip_backticks_strips_whitespace_first() -> None:
    assert _strip_backticks("  `hello`  ") == "hello"


# ── parse_facts ────────────────────────────────────────────────────────


def test_parse_facts_empty_doc_returns_empty() -> None:
    facts = parse_facts("# No table here\n\nJust prose.")
    assert facts == []


def test_parse_facts_no_section_7_returns_empty() -> None:
    md = textwrap.dedent("""\
        # Round

        ## § 1. Scope

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git --version` | `git version 2.0.0` | git installed |
    """)
    # Table is in § 1, not § 7 — should return empty
    facts = parse_facts(md)
    assert facts == []


def test_parse_facts_happy_path_3_rows() -> None:
    md = textwrap.dedent("""\
        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git --version` | `git version 2.0.0` | git installed |
        | 2 | `bash --version \\| head -1` | `GNU bash` | bash present |
        | 3 | `uv run python3 --version` | `Python 3.13.5` | python ok |
    """)
    facts = parse_facts(md)
    assert len(facts) == 3
    assert facts[0].index == 1
    assert facts[1].index == 2
    assert facts[2].index == 3
    assert facts[0].comment == "git installed"


def test_parse_facts_unescapes_pipe_in_command() -> None:
    md = textwrap.dedent(r"""\
        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git log --oneline \| wc -l` | `5` | count commits |
    """)
    facts = parse_facts(md)
    assert len(facts) == 1
    assert "|" in facts[0].command
    assert r"\|" not in facts[0].command


def test_parse_facts_strips_backticks_from_expected() -> None:
    md = textwrap.dedent("""\
        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git --version` | `git version 2` | check version |
    """)
    facts = parse_facts(md)
    assert facts[0].expected == "git version 2"
    # No surrounding backticks
    assert not facts[0].expected.startswith("`")


def test_parse_facts_skips_separator_row() -> None:
    md = textwrap.dedent("""\
        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git --version` | `git version 2` | check |
    """)
    facts = parse_facts(md)
    # Only 1 data row, not 2 (separator should be skipped)
    assert len(facts) == 1


def test_parse_facts_skips_non_numeric_index_row() -> None:
    md = textwrap.dedent("""\
        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | - | placeholder | n/a | header |
        | 1 | `git --version` | `git` | valid |
    """)
    facts = parse_facts(md)
    # The '- placeholder' row should be skipped (non-numeric index)
    assert len(facts) == 1
    assert facts[0].index == 1


def test_parse_facts_stops_at_next_section() -> None:
    md = textwrap.dedent("""\
        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git --version` | `git` | ok |

        ## § 8. Verdict

        | 2 | `echo hello` | `hello` | should not be parsed |
    """)
    facts = parse_facts(md)
    assert len(facts) == 1
    assert facts[0].index == 1


# ── execute_fact ───────────────────────────────────────────────────────


def test_execute_fact_unrecognized_prefix_gives_skip() -> None:
    fact = _make_fact(command="echo hello", expected="hello")
    result = execute_fact(fact)
    assert result.status == "SKIP"
    assert result.error is not None
    assert "recognized prefix" in result.error.lower() or "prefix" in result.error.lower()


def test_execute_fact_recognized_prefix_git() -> None:
    # git is available; this should not be SKIP
    fact = _make_fact(command="git --version", expected="anything")
    result = execute_fact(fact)
    assert result.status in ("PASS", "FAIL")  # not SKIP


def test_execute_fact_pass_when_output_matches_expected() -> None:
    fact = _make_fact(command="git --version", expected="git --version")
    # We can't guarantee the exact git version output, so mock subprocess.run
    with patch("arcgentic.audit_check.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="git version 2.49.0\n",
            stderr="",
            returncode=0,
        )
        fact_match = _make_fact(command="git --version", expected="git version 2.49.0")
        result = execute_fact(fact_match)
    assert result.status == "PASS"
    assert result.actual == "git version 2.49.0"


def test_execute_fact_fail_when_output_mismatches() -> None:
    with patch("arcgentic.audit_check.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="git version 2.49.0\n",
            stderr="",
            returncode=0,
        )
        fact = _make_fact(command="git --version", expected="git version 9.0.0")
        result = execute_fact(fact)
    assert result.status == "FAIL"
    assert result.error is not None
    assert "9.0.0" in result.error


def test_execute_fact_timeout_gives_fail() -> None:
    with patch("arcgentic.audit_check.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=1)
        fact = _make_fact(command="git slow-command")
        result = execute_fact(fact, timeout_seconds=1)
    assert result.status == "FAIL"
    assert result.error is not None
    assert "timeout" in result.error.lower()


def test_execute_fact_bash_prefix_recognized() -> None:
    with patch("arcgentic.audit_check.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok\n", stderr="", returncode=0)
        fact = _make_fact(command="bash -c 'echo ok'", expected="ok")
        result = execute_fact(fact)
    assert result.status == "PASS"


def test_execute_fact_uv_run_prefix_recognized() -> None:
    with patch("arcgentic.audit_check.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok\n", stderr="", returncode=0)
        fact = _make_fact(command="uv run python3 -c 'print(\"ok\")'", expected="ok")
        result = execute_fact(fact)
    assert result.status == "PASS"


def test_execute_fact_arcgentic_prefix_recognized() -> None:
    with patch("arcgentic.audit_check.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="arcgentic 0.2.0\n", stderr="", returncode=0)
        fact = _make_fact(command="arcgentic --version", expected="arcgentic 0.2.0")
        result = execute_fact(fact)
    assert result.status == "PASS"


def test_execute_fact_cd_prefix_recognized() -> None:
    with patch("arcgentic.audit_check.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok\n", stderr="", returncode=0)
        fact = _make_fact(command="cd /tmp && echo ok", expected="ok")
        result = execute_fact(fact)
    assert result.status == "PASS"


# ── check_ac1_clause_a ─────────────────────────────────────────────────


def test_check_ac1_clause_a_match_no_violation() -> None:
    md = "5/5 PASS all facts verified.\n"
    violations = check_ac1_clause_a(md, fact_count=5)
    assert violations == []


def test_check_ac1_clause_a_mismatch_gives_violation() -> None:
    md = "3/5 PASS verified.\n"
    violations = check_ac1_clause_a(md, fact_count=5)
    assert len(violations) == 1
    assert "Clause A" in violations[0]
    assert "3" in violations[0]
    assert "5" in violations[0]


def test_check_ac1_clause_a_no_pattern_no_violation() -> None:
    # If prose has no detectable count pattern, no violation raised
    md = "STATUS: DONE.\n"
    violations = check_ac1_clause_a(md, fact_count=5)
    assert violations == []


# ── check_ac1_clause_b ─────────────────────────────────────────────────


def test_check_ac1_clause_b_resolved_ref_no_violation() -> None:
    md = textwrap.dedent("""\
        ## § 1. Scope

        See § 1 for scope details.
    """)
    violations = check_ac1_clause_b(md)
    assert violations == []


def test_check_ac1_clause_b_unresolved_ref_gives_violation() -> None:
    md = textwrap.dedent("""\
        ## § 1. Scope

        See § 99.9 for details that don't exist.
    """)
    violations = check_ac1_clause_b(md)
    assert len(violations) == 1
    assert "Clause B" in violations[0]
    assert "99.9" in violations[0]


def test_check_ac1_clause_b_subsection_ref_resolved() -> None:
    md = textwrap.dedent("""\
        ## § 7. Facts

        ### 7.1 Sub-section

        See § 7.1 for details.
    """)
    violations = check_ac1_clause_b(md)
    assert violations == []


# ── check_ac1_clause_c ─────────────────────────────────────────────────


def test_check_ac1_clause_c_prose_all_pass_but_fact_fail_gives_violation() -> None:
    md = "All gates PASS and everything is fine.\n"
    fail_result = FactResult(
        fact=_make_fact(),
        status="FAIL",
        actual="wrong",
        error="mismatch",
    )
    violations = check_ac1_clause_c(md, [fail_result])
    assert len(violations) == 1
    assert "Clause C" in violations[0]


def test_check_ac1_clause_c_no_prose_all_pass_with_fail_no_violation() -> None:
    md = "STATUS: DONE with 1 failure noted.\n"
    fail_result = FactResult(
        fact=_make_fact(),
        status="FAIL",
        actual="wrong",
        error="mismatch",
    )
    violations = check_ac1_clause_c(md, [fail_result])
    assert violations == []


def test_check_ac1_clause_c_all_pass_no_violation() -> None:
    md = "All tests PASS successfully.\n"
    pass_result = FactResult(fact=_make_fact(), status="PASS", actual="expected")
    violations = check_ac1_clause_c(md, [pass_result])
    assert violations == []


# ── check_ac3 ─────────────────────────────────────────────────────────


def test_check_ac3_vacuous_ge_unicode_gives_violation() -> None:
    fact = _make_fact(expected="≥ 5")
    violations = check_ac3([fact])
    assert len(violations) == 1
    assert "AC-3" in violations[0]
    assert "≥" in violations[0]


def test_check_ac3_vacuous_ge_ascii_gives_violation() -> None:
    fact = _make_fact(expected=">= 5")
    violations = check_ac3([fact])
    assert len(violations) == 1
    assert "AC-3" in violations[0]


def test_check_ac3_vacuous_le_unicode_gives_violation() -> None:
    fact = _make_fact(expected="≤ 10")
    violations = check_ac3([fact])
    assert len(violations) == 1


def test_check_ac3_vacuous_le_ascii_gives_violation() -> None:
    fact = _make_fact(expected="<= 10")
    violations = check_ac3([fact])
    assert len(violations) == 1


def test_check_ac3_tight_value_no_violation() -> None:
    fact = _make_fact(expected="5")
    violations = check_ac3([fact])
    assert violations == []


def test_check_ac3_exact_text_no_violation() -> None:
    fact = _make_fact(expected="git version 2.49.0")
    violations = check_ac3([fact])
    assert violations == []


# ── run() ──────────────────────────────────────────────────────────────


def test_run_missing_file_returns_exit_code_2(tmp_path: Path) -> None:
    result = run(audit_path=tmp_path / "nonexistent.md")
    assert result.exit_code == 2
    assert "not found" in result.summary_text.lower() or "FAILED" in result.summary_text


def test_run_all_pass_strict_exit_0(tmp_path: Path) -> None:
    audit_path = _make_sample_audit(
        tmp_path,
        [r"| 1 | `git --version \| head -1` | `anything` | skip test |"],
    )
    # Patch execute_fact to return PASS for all
    with patch("arcgentic.audit_check.execute_fact") as mock_ef:
        mock_ef.return_value = FactResult(
            fact=_make_fact(),
            status="PASS",
            actual="anything",
        )
        result = run(audit_path=audit_path, strict=True)
    assert result.exit_code == 0
    assert result.pass_count == 1
    assert result.fail_count == 0


def test_run_strict_mode_with_fail_gives_exit_1(tmp_path: Path) -> None:
    audit_path = _make_sample_audit(
        tmp_path,
        [r"| 1 | `git --version` | `wrongvalue` | will fail |"],
    )
    with patch("arcgentic.audit_check.execute_fact") as mock_ef:
        mock_ef.return_value = FactResult(
            fact=_make_fact(),
            status="FAIL",
            actual="git version 2.49.0",
            error="mismatch",
        )
        result = run(audit_path=audit_path, strict=True)
    assert result.exit_code == 1


def test_run_strict_mode_with_skip_gives_exit_1(tmp_path: Path) -> None:
    audit_path = _make_sample_audit(
        tmp_path,
        [r"| 1 | `echo hello` | `hello` | unrecognized prefix — skip |"],
    )
    # 'echo hello' is an unrecognized prefix → SKIP
    result = run(audit_path=audit_path, strict=True)
    assert result.exit_code == 1
    assert result.skip_count == 1


def test_run_strict_extended_ac1_violation_exit_1(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.md"
    audit_path.write_text(
        textwrap.dedent("""\
        # Audit

        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git --version` | `git` | ok |
        | 2 | `git log` | `commit` | ok |

        ## § 8. Verdict

        100/100 PASS verified.
        """),
        encoding="utf-8",
    )
    with patch("arcgentic.audit_check.execute_fact") as mock_ef:
        mock_ef.return_value = FactResult(fact=_make_fact(), status="PASS", actual="ok")
        result = run(audit_path=audit_path, strict_extended=True)
    # AC-1 Clause A: claims 100 facts but table has 2
    assert result.exit_code == 1
    assert len(result.ac1_violations) > 0


def test_run_strict_extended_ac3_violation_exit_1(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.md"
    audit_path.write_text(
        textwrap.dedent("""\
        # Audit

        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `git --version` | `≥ 2.0` | vacuous check |

        ## § 8. Verdict

        1/1 PASS.
        """),
        encoding="utf-8",
    )
    with patch("arcgentic.audit_check.execute_fact") as mock_ef:
        mock_ef.return_value = FactResult(fact=_make_fact(), status="PASS", actual="ok")
        result = run(audit_path=audit_path, strict_extended=True)
    assert result.exit_code == 1
    assert len(result.ac3_violations) > 0


def test_run_default_mode_fail_still_exit_0(tmp_path: Path) -> None:
    audit_path = _make_sample_audit(
        tmp_path,
        [r"| 1 | `git --version` | `wrongvalue` | will fail |"],
    )
    with patch("arcgentic.audit_check.execute_fact") as mock_ef:
        mock_ef.return_value = FactResult(
            fact=_make_fact(),
            status="FAIL",
            actual="git version 2.49.0",
            error="mismatch",
        )
        result = run(audit_path=audit_path, strict=False, strict_extended=False)
    # Default mode: exit 0 even on FAIL
    assert result.exit_code == 0


def test_run_summary_text_format(tmp_path: Path) -> None:
    audit_path = _make_sample_audit(
        tmp_path,
        [r"| 1 | `git --version` | `git` | ok |"],
    )
    with patch("arcgentic.audit_check.execute_fact") as mock_ef:
        mock_ef.return_value = FactResult(fact=_make_fact(), status="PASS", actual="git")
        result = run(audit_path=audit_path)
    assert "PASS" in result.summary_text
    assert "FAIL" in result.summary_text
    assert "SKIP" in result.summary_text


# ── main() CLI ────────────────────────────────────────────────────────


def test_main_missing_file_exits_2(tmp_path: Path) -> None:
    code = main([str(tmp_path / "no_such_file.md")])
    assert code == 2


def test_main_strict_flag_propagated(tmp_path: Path) -> None:
    audit_path = _make_sample_audit(
        tmp_path,
        [r"| 1 | `echo hello` | `hello` | skip - unrecognized |"],
    )
    # --strict + SKIP → exit 1
    code = main([str(audit_path), "--strict"])
    assert code == 1


def test_main_strict_extended_flag_propagated(tmp_path: Path) -> None:
    # strict-extended on a file with AC-3 violation
    audit_path = tmp_path / "audit.md"
    audit_path.write_text(
        textwrap.dedent("""\
        # Audit

        ## § 7. Mechanical audit facts

        | # | Command | Expected | Comment |
        |---|---|---|---|
        | 1 | `echo hello` | `>= hello` | vacuous check |

        ## § 8. Verdict

        1/1 PASS.
        """),
        encoding="utf-8",
    )
    code = main([str(audit_path), "--strict-extended"])
    # AC-3 violation detected (and echo is SKIP too) → exit 1
    assert code == 1


def test_main_default_no_strict_exit_0(tmp_path: Path) -> None:
    # echo hello is SKIP in default mode → exit 0 (no --strict)
    audit_path = _make_sample_audit(
        tmp_path,
        [r"| 1 | `echo hello` | `hello` | skip - unrecognized |"],
    )
    code = main([str(audit_path)])
    assert code == 0
