# {round_name} — Admin Handoff

**Phase**: {phase_label}
**Round**: {round_name} (admin: {entry-admin | close-admin | meta-admin-sweep})
**Type**: admin (docs-only governance)
**Prior-round anchor**: `{prior_round_anchor}` ({prior_round_name})
**Audit script**: `arcgentic audit-check docs/audits/phase-{P}/{round}.md --strict-extended`

---

## 1. Scope (admin-only; no code)

### 1.1 What this admin round delivers (governance objectives)
### 1.2 What this admin round does NOT touch (anti-scope)

## 2. Files modified

{list of admin docs to update: CLAUDE.md / state.yaml / mandate registry / etc.}

## 3. State transitions

{If state.yaml changes: from → to transition table}

## 4. Mandate amendments (if any)

{If this round amends mandates: amendment-ID + before/after + rationale}

## 5. Forward-debt updates

{Inherited forward-debt count: before → after; admin rounds may RESOLVE debts}

## 6. 4-commit chain plan (typically 1-2 commits for admin)

### Commit 1 — Admin handoff + state refresh
### Commit 2 (optional) — Follow-up amendments

(Admin rounds compress 4-commit chain to 1-2 commits since no BA / dev body.)

## 7. Quality gates (no-op since no code)

### 7.1 Markdown linting (if available)
### 7.2 JSON / YAML schema validation for any state file touched

## 8. Self-audit fact-shape targets (smaller; ~10-15 facts)

### 8.1 Commit chain anchors (2-4 facts)
### 8.2 Doc structural facts (3-5 facts: section counts / table rows / etc.)
### 8.3 State / schema validation facts (3-4 facts)
### 8.4 No-regression facts (1-2 facts: existing rounds still verified)

## 9. Audit handoff target path + format

{Path + format per spec § 9 self-audit template.}

## 10. Next round preview

{What round opens after this admin closes}

---

*Admin-round handoff written by planner agent (arcgentic v{VERSION}).*
