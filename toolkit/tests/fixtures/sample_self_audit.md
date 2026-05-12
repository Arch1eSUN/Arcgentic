# R0-audit-check-dogfood — Self-Audit Handoff

> Minimal fixture for `test_audit_check.py` integration tests and fixture-loading smoke tests.
> Contains 3 facts: 1 recognized+PASS-able, 1 unrecognized→SKIP, 1 recognized+may-FAIL.

## § 1. Scope

This round audited the `audit_check.py` module. See § 7 for mechanical facts.

## § 7. Mechanical audit facts

| # | Command | Expected | Comment |
|---|---|---|---|
| 1 | `git --version` | `git version 2.49.0` | git is installed and reachable |
| 2 | `echo hello world` | `hello world` | unrecognized prefix — SKIP expected |
| 3 | `bash -c 'echo arcgentic-ok'` | `arcgentic-ok` | bash echo roundtrip |

## § 8. Verdict

STATUS: DONE. 3/3 facts in § 7 table. Fact #2 will SKIP (unrecognized prefix `echo`).
All recognized facts (1, 3) are expected to PASS in a standard dev environment.
