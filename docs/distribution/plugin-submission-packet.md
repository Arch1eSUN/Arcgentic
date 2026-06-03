# Arcgentic plugin submission packet

Repository: https://github.com/Arch1eSUN/Arcgentic
Release: v1.0.0
PyPI: https://pypi.org/project/arcgentic/
GitHub Release: https://github.com/Arch1eSUN/Arcgentic/releases/tag/v1.0.0
Privacy Policy: https://github.com/Arch1eSUN/Arcgentic/blob/main/PRIVACY.md

## Current distribution status

| Surface | Status | Evidence |
|---|---|---|
| Python CLI | Published | `arcgentic 1.0.0` on PyPI |
| Claude Code plugin | Ready for marketplace submission | `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` validate locally |
| Codex plugin | Ready for workspace/internal distribution | `.codex-plugin/plugin.json` validates locally |
| OpenClaw bundle | Ready for git-source install | `openclaw.plugin.json` |

## Claude Code community marketplace submission

Official entry points:
- Claude.ai: https://claude.ai/settings/plugins/submit
- Console: https://platform.claude.com/plugins/submit

Submission fields:

| Field | Value |
|---|---|
| Plugin name | Arcgentic |
| Repository URL | `https://github.com/Arch1eSUN/Arcgentic` |
| Marketplace source | `Arch1eSUN/Arcgentic` |
| Marketplace name | `arc-studio` |
| Install command | `/plugin marketplace add Arch1eSUN/Arcgentic` then `/plugin install arcgentic@arc-studio` |
| Version | `1.0.0` |
| License | MIT |
| Privacy policy URL | `https://github.com/Arch1eSUN/Arcgentic/blob/main/PRIVACY.md` |
| Category | Productivity / Developer tools |
| Author | Arc Studio |

Short description:

> Mechanical plan/dev/self-audit/external-audit gates for AI coding agents.

Long description:

> Arcgentic packages rigorous round-driven development as installable agent workflow discipline. It provides Claude Code, Codex, and OpenClaw-compatible skills and agents for planning, implementation, self-audit, external audit, reference tracking, lesson codification, project-level session-mode selection, orchestrator dispatch, verdict completeness, and PASS-only closeout. A Python CLI enforces the mechanical layer: handoff validation, audit fact-table checks, quality gates, cross-session handoffs, source-intake, capability registry, and V1 release-readiness.

Validation evidence:

```bash
claude plugin validate "/Users/archiesun/Desktop/Arc Studio/arcgentic"
/opt/anaconda3/bin/python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/archiesun/plugins/arcgentic
/opt/anaconda3/bin/python3 -m pip index versions arcgentic
```

Expected results:

```text
Claude plugin validation: passed
Codex plugin validation: passed
PyPI latest: arcgentic 1.0.0
```

## Claude Code official marketplace path

Fact: Anthropic's public submission form is for the community marketplace. The official `claude-plugins-official` marketplace is curated separately by Anthropic, and the public docs state there is no direct application process for official inclusion.

Recommendation:

1. Submit Arcgentic to the community marketplace first.
2. Keep the project-owned marketplace install path live for immediate users.
3. Use adoption, audits, release evidence, and safety posture as the case for later Anthropic-curated official inclusion.

## Codex / OpenAI review packet

Fact: OpenAI's public Codex plugin docs describe workspace/admin plugin controls and app-backed access controls, but do not expose a public third-party "submit to official Codex plugin library" flow.

Recommended review packet:

| Review area | Arcgentic answer |
|---|---|
| External systems | None required for core plugin use. Git and shell are used only through the host coding agent environment. |
| Paid APIs | None. Arcgentic makes no OpenAI, Anthropic, Gemini, Cohere, embedding, reranker, or vector-store API calls. |
| Background processes | None. All commands are foreground and user/session initiated. |
| Secrets | No secret reads. No `.env`, keychain, credential store, or token exfiltration path is part of the plugin. |
| Write actions | Writes repo-local state, handoff docs, audit docs, and lessons only when the active agent/session performs those steps. |
| Confirmation boundary | Publish/tag/push, destructive git actions, and writes outside the current repo remain user-confirmed workflow actions. |
| Data residency | State and artifacts are repo-local unless the user pushes them to a remote repository. |
| Test evidence | 323 pytest tests, `mypy --strict` clean, `ruff` clean, plugin validators passed, V1 release-readiness passed. |

Codex-facing summary:

> Arcgentic is a local workflow plugin for rigorous AI coding sessions. It adds skills and agent-role instructions for planning, development, self-audit, external audit, reference tracking, lesson codification, session-mode selection, orchestrator dispatch, and PASS-only round closeout. It does not provide external data access, paid API calls, background daemons, or secret access. Its Python CLI enforces mechanical gates over repo-local documents and state files.

## Self-hosted Claude marketplace install path

Arcgentic already ships a marketplace catalog at `.claude-plugin/marketplace.json`.

Users can install it in Claude Code with:

```text
/plugin marketplace add Arch1eSUN/Arcgentic
/plugin install arcgentic@arc-studio
```

After updates:

```text
/plugin marketplace update arc-studio
/plugin update arcgentic@arc-studio
/reload-plugins
```

## Submission checklist

- [x] v1.0.0 release exists.
- [x] PyPI package `arcgentic 1.0.0` exists.
- [x] `.claude-plugin/plugin.json` version is `1.0.0`.
- [x] `.claude-plugin/marketplace.json` version is `1.0.0`.
- [x] `.codex-plugin/plugin.json` version is `1.0.0`.
- [x] `PRIVACY.md` exists for plugin submission.
- [x] Claude plugin validation passes locally.
- [x] Codex plugin validation passes locally.
- [ ] Submit via Claude.ai or Console community plugin form.
- [ ] After approval, verify catalog entry in `anthropics/claude-plugins-community`.
- [ ] If OpenAI exposes a public Codex plugin submission channel or partnership contact, submit this review packet.
