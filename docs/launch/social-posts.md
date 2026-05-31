# Arcgentic launch copy

Repository: https://github.com/Arch1eSUN/Arcgentic
PyPI: https://pypi.org/project/arcgentic/

Assets:
- GitHub/X/LinkedIn preview: `assets/social-preview.jpg`
- Xiaohongshu cover: `assets/xhs-cover.jpg`

## One-line positioning

Arcgentic adds mechanical plan/dev/self-audit/external-audit gates to AI coding agents, so agentic development stops drifting on memory and starts moving through verifiable round boundaries.

## X post

I open-sourced Arcgentic.

It is a Claude Code / Codex / OpenClaw workflow plugin plus a Python CLI for people who do not want AI coding sessions to drift.

The loop is simple:

plan -> dev+self-audit -> external audit -> reference tracking

Every step has mechanical gates. If the fact table, handoff, commit chain, or audit contract is wrong, the workflow refuses to advance.

Install:

```bash
pipx install arcgentic
arcgentic audit-check --help
```

Repo: https://github.com/Arch1eSUN/Arcgentic

## X thread

1/ I open-sourced Arcgentic: mechanical gates for AI coding agents.

It is the workflow discipline I extracted from 30+ Moirai development rounds and packaged as a Claude Code / Codex / OpenClaw plugin plus Python CLI.

https://github.com/Arch1eSUN/Arcgentic

2/ The problem: AI coding agents are powerful, but long sessions drift.

They forget the plan, skip verification, claim tests passed without proof, or merge implementation details into audit language.

Arcgentic turns those soft rules into hard gates.

3/ The core loop:

plan-round
execute-round
self-audit
external audit
track-refs
codify-lesson

Every role has a skill. Every transition has a state machine gate.

4/ The CLI handles the mechanical layer:

```bash
pipx install arcgentic
arcgentic audit-check docs/audits/R1.md --strict-extended
arcgentic validate-handoff docs/plans/R1.md
arcgentic cross-session-handoff read
```

5/ This is not a chatbot wrapper.

It is a workflow harness for people who want AI-assisted development to produce fixed evidence: handoffs, fact tables, audit verdicts, commit-chain proof, reference tracking, and lessons that become future rules.

6/ Current package:

- PyPI CLI
- Claude Code plugin manifest
- Codex plugin manifest
- OpenClaw manifest
- 10 skills
- 9 agents
- 277 pytest tests
- mypy strict clean
- ruff clean

Repo: https://github.com/Arch1eSUN/Arcgentic

## Xiaohongshu

Title:

别让 AI 写代码一路漂移：我把开发流程做成了可审计状态机

Body:

我开源了一个自己从 Moirai 项目里提炼出来的 AI coding workflow：Arcgentic。

它不是“再套一层提示词”，而是把开发纪律变成机械 gate：

1. plan-round：先写清楚 scope / refs / verification / stop condition
2. execute-round：按 handoff 执行，开发后必须 self-audit
3. audit-check：外审 verdict 必须有可机械验证的 fact table
4. track-refs：引用来源要可追踪
5. codify-lesson：同类问题反复出现，就沉淀成下一轮规则

核心目标很简单：不要再靠“记得验证”“记得审计”“记得别乱改”这种人肉记忆。

如果 gate 不过，状态机就不往前走。

现在已经支持：

- Claude Code plugin
- Codex local plugin
- OpenClaw / ClawHub bundle manifest
- PyPI CLI：`pipx install arcgentic`

适合谁：

- 经常用 Claude Code / Codex 做真实项目的人
- 需要计划、开发、自审、外审分离的人
- 不想接受“AI 说测试过了但没证据”的团队
- 想把开发轮次沉淀成可复用流程的人

GitHub 搜索：Arch1eSUN/Arcgentic

Tags:

#AI编程 #ClaudeCode #Codex #开源项目 #软件工程 #AI工具 #开发流程 #Agent

## Hacker News / Reddit

Title:

Arcgentic: mechanical audit gates for AI coding agents

Post:

I built Arcgentic after running 30+ strict AI-assisted development rounds on another project.

The core problem I wanted to solve: AI coding agents can follow discipline in one turn, but long-running projects drift. Plans get vague, test claims become unverifiable, audit documents mix implementation and review language, and lessons do not reliably feed into the next round.

Arcgentic packages that workflow as a Claude Code / Codex / OpenClaw plugin plus a Python CLI:

- plan/dev/self-audit/external-audit roles
- state-machine round boundaries
- handoff validation
- audit fact-table checking
- reference tracking
- lesson codification

Install:

```bash
pipx install arcgentic
arcgentic --help
```

Repo: https://github.com/Arch1eSUN/Arcgentic

It is early alpha, but the toolkit has 277 pytest tests, mypy strict, ruff, and a PyPI release.

## Marketplace listing

Name:

Arcgentic

Short description:

Mechanical plan/dev/self-audit/external-audit gates for AI coding agents.

Long description:

Arcgentic packages rigorous round-driven development as installable agent workflow discipline. It provides Claude Code, Codex, and OpenClaw-compatible skills and agents for planning, implementation, self-audit, external audit, reference tracking, and lesson codification. A Python CLI enforces the mechanical layer: handoff validation, audit fact-table checks, quality gates, cross-session handoffs, and source-rule validators.

Install command:

```bash
pipx install arcgentic
```

Claude Code install:

```text
/plugin marketplace add Arch1eSUN/Arcgentic
/plugin install arcgentic@arc-studio
```

OpenClaw install after ClawHub publish:

```bash
openclaw plugins install clawhub:arcgentic
```

Tags:

ai-coding, claude-code, codex, openclaw, software-audit, developer-tools, workflow, state-machine

## Submission status

- GitHub repository metadata: updated.
- OpenClaw manifest: added.
- ClawHub remote dry-run: passed against `Arch1eSUN/Arcgentic@main`.
- ClawHub publish: pending authenticated `clawhub login`.
- GitHub social preview: asset generated, manual upload required in GitHub Settings because GitHub does not expose a supported CLI upload path.
- X / Xiaohongshu: copy and image assets prepared; publishing requires authenticated browser sessions.
