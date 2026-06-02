# Arcgentic

<p align="center">
  <img src="./assets/arcgentic-logo.png" alt="Arcgentic logo" width="168">
</p>

> **A**rc + **agentic** —— 严格轮次驱动开发的 agentic harness（agent 约束容器）。

**English → [README.md](./README.md)**

[![status](https://img.shields.io/badge/status-alpha-orange.svg)](#状态与路线图)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![version](https://img.shields.io/badge/version-v0.2.2--alpha.3-blueviolet.svg)](#状态与路线图)
[![PyPI](https://img.shields.io/pypi/v/arcgentic.svg)](https://pypi.org/project/arcgentic/)

`arcgentic` 是一个兼容 [Claude Code](https://docs.claude.com/zh-CN/docs/claude-code/overview) / Codex 的插件，加上一套 Python CLI。它把四角色工程纪律 ——*规划 / 开发+自审 / 外审 / 引用追踪* —— 变成一套**机械强制 + 状态机驱动**的工作流。

它支持三种入口 / 运行模式：
- **Python CLI**（`arcgentic`）：运行 gate、audit、handoff 和 round 工具
- **项目级 session mode**：项目一次性选择单 session 编排或多 session 角色隔离，并把决定写入 `state.yaml`
- **V1 source/spec 层**：把外部 workflow source、marketplace capability、OpenSpec-style artifact、
  agency role family 记录成可审计的 planning input

这些入口都靠状态机 + 门控脚本把纪律**机械化**：如果质量门没过，状态机拒绝前进。**不需要"记得跑 audit-check"** —— 系统替你跑，不过就拦下来。

---

## 目录

- [为什么用 arcgentic](#为什么用-arcgentic)
- [快速安装](#快速安装)
- [快速上手——5 分钟跑第一轮](#快速上手5-分钟跑第一轮)
- [工作原理](#工作原理)
- [四个角色](#四个角色)
- [状态机](#状态机)
- [单 session vs 多 session](#单-session-vs-多-session)
- [成本纪律](#成本纪律)
- [状态与路线图](#状态与路线图)
- [起源](#起源)
- [参与贡献](#参与贡献)
- [License](#license)

---

## 为什么用 arcgentic

大多数 LLM 辅助开发工作流都有严格的**意图**，但执行靠人**记忆**。"记得跑 audit-check"、"记得先扫 reference"、"记得更新 tech-debt"。第三轮之后纪律就崩塌了。

`arcgentic` 把纪律**机械化**：

| 层 | 机制 |
|---|---|
| **状态机** | 每个 round 都通过强制状态序列（`intake → planning → dev → audit → passed / needs_fix → closed`）。状态存放在 `.agentic-rounds/state.yaml`，由 JSON Schema 校验。 |
| **质量门** | 每个状态转移都有 Bash 脚本把关。Plan 必须有 N 个 section（否则拒绝转移）。Dev commit 必须形成 N-commit chain。审计 verdict 必须包含 fact table，每条 fact 都可独立机械验证。 |
| **Sub-agent 派遣** | Orchestrator 通过 Claude Code 的 `Task` tool 派遣角色 sub-agent。每个 sub-agent 在隔离上下文中跑自己的自纠错循环（TDD red-green / code review / contract verification），返回结构化产物。 |
| **观察层** | `lesson-codifier` sub-agent 扫描最近 N 轮，识别模式。同类问题 3 次出现 → 提议新 mandate。novel preservation type → 宣告 lesson streak 迭代。 |

---

## 快速安装

### 前置依赖

- Bash 4+
- Python 3.13+（CLI toolkit）
- Git
- Claude Code ≥ 1.0 (https://claude.com/claude-code)
- Codex（如果要用 Codex 本地插件）
- 推荐配套：`superpowers` plugin + `plugin-dev` plugin

```bash
# 验证环境
bash --version       # >= 4
python3 --version    # Python package 需要 >= 3.13
```

### 方式 1 —— 从 PyPI 安装 Python CLI

只想使用 `arcgentic` 命令、不想 clone repo 时用这个：

```bash
pipx install arcgentic

# 或者
uv tool install arcgentic

arcgentic --help
arcgentic audit-check --help
```

PyPI package: https://pypi.org/project/arcgentic/

### 方式 2 —— Claude Code 插件市场

```
/plugin marketplace add Arch1eSUN/Arcgentic
/plugin install arcgentic@arc-studio
```

这会从 `.claude-plugin/marketplace.json` 声明的 marketplace 安装 Claude Code 插件。

### 方式 3 —— 手动安装 Claude Code 插件（alpha + 开发模式）

```bash
# 克隆到 Claude Code 的用户级 skills 目录
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone git@github.com:Arch1eSUN/Arcgentic.git arcgentic

# 或者用 HTTPS:
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic

# 验证
ls ~/.claude/skills/arcgentic/.claude-plugin/plugin.json
claude plugin validate ~/.claude/skills/arcgentic
```

安装后，在任意 Claude Code session 里可以调用 arcgentic 的 skills：
- `arcgentic:using-arcgentic`
- `arcgentic:audit-round`
- `arcgentic:orchestrate-round`
- ……

### 方式 4 —— Codex 本地插件（alpha + 开发模式）

`arcgentic` 现在也包含 Codex 插件入口：`.codex-plugin/plugin.json`。
本地 Codex 使用时，把 repo clone 到个人插件目录：

```bash
mkdir -p ~/plugins
cd ~/plugins
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic
cd arcgentic
git checkout v0.2.2-alpha.3

# 校验 Codex plugin manifest
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py ~/plugins/arcgentic
```

V1 本地 source/spec 命令：

```bash
arcgentic session-mode recommend --round R1 --handoff docs/superpowers/plans/R1.md
arcgentic session-mode prompt --round R1 --handoff docs/superpowers/plans/R1.md --mode multi-session --role developer
arcgentic orchestrator-dispatch --round R1 --handoff docs/superpowers/plans/R1.md --mode multi-session
arcgentic source-intake validate docs/source-intake/*.yaml
arcgentic capability-registry build .claude-plugin/marketplace.json
arcgentic spec-governance status openspec/changes/<change>
arcgentic agency-roster inspect references/agency-agents
arcgentic verdict-completeness docs/audits/R1.md
arcgentic close-round --state-file .agentic-rounds/state.yaml --verdict docs/audits/R1.md --audit-commit <sha>
arcgentic v1-release-readiness --repo-root .
```

如果你通过 personal marketplace 管理 Codex 插件，把这段加入
`~/.agents/plugins/marketplace.json`：

```json
{
  "name": "arcgentic",
  "source": {
    "source": "local",
    "path": "./plugins/arcgentic"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

### 方式 5 —— OpenClaw git-source bundle

`arcgentic` 已包含 `openclaw.plugin.json`，OpenClaw 可以把它识别为 bundle plugin。

```bash
openclaw plugins install git:github.com/Arch1eSUN/Arcgentic@main
openclaw plugins inspect arcgentic
```

### 方式 6 —— Toolkit 开发者源码安装

```bash
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic
cd arcgentic/toolkit
python3 -m pip install -e ".[dev]"
arcgentic --help
```

---

## 快速上手——5 分钟跑第一轮

### 1. 在你的项目里初始化状态机

```bash
cd ~/projects/your-project

bash ~/.claude/skills/arcgentic/scripts/state/init.sh \
  --project-root . \
  --project-name "your-project" \
  --round-naming "phase.round[.fix]"
```

这会创建 `.agentic-rounds/state.yaml`，处于 `intake` 状态。从此刻起，这个文件就是所有角色的**唯一事实来源**。

> 提示：`.agentic-rounds/` 默认被 .gitignore 排除。项目可以选择是否纳入版本控制。

### 2. 在项目目录开 Claude Code session

```bash
cd ~/projects/your-project
claude
```

在对话里让 Claude 读取状态 + 告诉你下一步：

```
读取 .agentic-rounds/state.yaml 并运行 pickup.sh，告诉我应该承担什么角色、做什么。
```

Claude 会加载 `arcgentic:using-arcgentic`，跑 `pickup.sh`，然后回复类似：

> *当前状态：`intake`。角色：founder。动作：声明 round 范围（名称 / 目标 / 范围内 / 范围外）。下一状态：`planning`。*

### 3. 声明 round 范围

你声明范围，Claude（在 planner 角色下）写 handoff doc，状态机推进。

### 4. 跑 dev / audit / close

`arcgentic:orchestrate-round` 这个 skill 会带你走完每个状态，在合适的状态点派遣 planner / developer / auditor / reference-tracker sub-agent，并在每个转移点跑对应的 gate。

当 round 到达 `closed` 状态，你就完成了一个完整的、有纪律的开发循环。

### 完整 walkthrough

参见 `docs/plans/2026-05-12-arcgentic-mvp-plan.md` 完整实施 plan + `tests/dogfood/gate-2-live-run/` 里的"live run" dogfood gate 实例。

---

## 工作原理

```
arcgentic/
├── plugin.json                # 插件 manifest
├── schema/state.schema.json   # state.yaml 的 JSON Schema
├── skills/                    # 第 1 层：角色纪律（Markdown SKILL.md）
│   ├── using-arcgentic/       #   入口 skill
│   ├── pre-round-scan/        #   共享前置 —— 每个角色第一动作
│   ├── orchestrate-round/     #   编排器角色
│   ├── audit-round/           #   外审角色
│   ├── close-round/           #   只允许 PASS 后执行的 closeout seam
│   ├── verify-gates/          #   手动 gate 执行器
│   ├── plan-round/            #   规划角色
│   ├── execute-round/         #   开发 + 自审角色
│   ├── track-refs/            #   引用追踪角色
│   ├── codify-lesson/         #   lesson 编码角色
│   └── cross-session-handoff/ #   多 session 交接角色
├── agents/                    # 第 2 层：平台中性的 sub-agent 定义
│   ├── orchestrator.md        #   总编排器
│   ├── auditor.md             #   Task-tool 派遣的外审 sub-agent
│   ├── planner.md             #   规划 sub-agent
│   ├── developer.md           #   开发 sub-agent
│   ├── ba-designer.md         #   设计审查 sub-agent
│   ├── cr-reviewer.md         #   代码审查 sub-agent
│   ├── se-contract.md         #   contract 验证 sub-agent
│   ├── lesson-codifier.md     #   lesson 模式 sub-agent
│   └── ref-tracker.md         #   引用追踪 sub-agent
├── scripts/                   # 第 3 层：状态机 + gate 机械强制（Bash）
│   ├── state/                 #   init / transition / pickup / validate-schema
│   ├── gates/                 #   handoff-doc / round-commit-chain / verdict-fact-table
│   └── lib/                   #   yaml.sh, state.sh 辅助函数
└── hooks/examples/            # 第 4 层：项目可选的 commit 级强制
```

四层架构自上而下：skill 告诉 Claude 在某角色下**如何思考**；agent 让 orchestrator 把某角色**派遣**给 sub-agent；script 在状态机里**强制**纪律；hook 在 commit 时刻**最终防线**。

---

## 四个角色

| 角色 | 职责 | 当前 skill | 当前 agent |
|------|------|---------------|----------------|
| **Planner（规划者）** | 读取 scope → 写 16 章节 handoff doc → 推进到 `awaiting_dev_start` | ✅ `plan-round` | ✅ `planner` |
| **Developer（开发者）** | 读 handoff → 逐 task 执行 + inline 三联自审（BA + CR + SE）→ 产出 N-commit chain | ✅ `execute-round` | ✅ `developer` |
| **External auditor（外审者）** | 读 handoff + commit chain → 写 verdict 含可机械验证的 fact table → 应用 lesson codification 协议 → 推进到 `passed` 或 `needs_fix` | ✅ `audit-round` | ✅ `auditor` |
| **Reference tracker（引用追踪者）** | 每日 `references/` git fetch → 给新克隆分类 → 维护 `INDEX.md` | ✅ `track-refs` | ✅ `ref-tracker` |

外加一个元角色：
- **Orchestrator（编排器）** —— 端到端驱动状态机，在角色切换时派遣 sub-agent，并通过 `close-round` seam 负责 PASS 后 closeout。✅ `orchestrate-round` skill + `orchestrator` agent。

---

## 状态机

```
       ┌─────────┐
       │ intake  │
       └────┬────┘
            │ founder 声明 scope
            ▼
       ┌──────────┐
       │ planning │
       └─────┬────┘
             │ planner 写 handoff
             │ [GATE: handoff-doc-gate.sh]
             ▼
   ┌────────────────────┐
   │ awaiting_dev_start │
   └──────────┬─────────┘
              │
              ▼
   ┌────────────────────┐
   │  dev_in_progress   │ ←──────┐
   └──────────┬─────────┘        │
              │ [GATE: round-commit-chain-gate.sh]
              ▼                  │
   ┌────────────────────┐        │
   │  awaiting_audit    │        │
   └──────────┬─────────┘        │
              │                  │
              ▼                  │
   ┌────────────────────┐        │
   │ audit_in_progress  │        │
   └──────────┬─────────┘        │
              │ [GATE: verdict-fact-table-gate.sh]
        ┌─────┴─────┐            │
        ▼           ▼            │
   ┌────────┐  ┌──────────┐      │
   │ passed │  │needs_fix │      │
   └───┬────┘  └─────┬────┘      │
       │             │           │
       ▼             ▼           │
   ┌────────┐  ┌─────────────┐   │
   │ closed │  │fix_in_progress│ ┘ (→ 回到 awaiting_audit)
   └────────┘  └─────────────┘
```

每个状态转移都由 `scripts/state/transition.sh` 执行：
1. 校验目标状态在当前状态的 `next` 列表里
2. 跑必需的 gate 脚本（gate 失败则拒绝转移）
3. 更新 `current_round.state` + 追加到 `state_history`

想跳过一个状态？拒绝。想 PASS 但 fact table 没验完？拒绝。想没有 PASS audit + strict audit-check 就关 round？拒绝。**状态机就是强制者。**

---

## 单 session vs 多 session

### 模式 A —— 单 session（orchestrator 一人承担一切）

一个 Claude session。加载 `arcgentic:orchestrate-round`。需要角色切换时通过 Task tool 派遣 sub-agent。

**适用场景**：独立开发者 / 小项目 / 概念验证。

### 模式 B —— 多 session（每个角色由不同人承担）

多个 Claude session，每个加载不同角色的 skill：
- Session 1（founder + planner）—— `arcgentic:plan-round`
- Session 2（developer）—— `arcgentic:execute-round`
- Session 3（auditor）—— `arcgentic:audit-round`
- Session 4（ref-tracker）—— `arcgentic:track-refs`

`state.yaml` 是 session 间通信协议。每个 session 启动时第一动作就是读它。

**适用场景**：多人团队 / 长期项目 / 严格审计独立性要求（合规 / 监管）。

两种模式共享同一个 `state.yaml` schema 和 gate 脚本。mode 是项目级决定，存放在
`project.session_mode`；一旦设置，后续 round 不再重复询问，除非项目显式重新配置。

---

## 成本纪律

`arcgentic` **严格遵守成本纪律**：

- ❌ 插件代码里**绝不**调用任何付费 API（OpenAI / Anthropic API / Gemini / 等等）
- ❌ **绝不**启后台进程 / daemon / cron 触发器
- ❌ **绝不**自动从云端 LLM 拉取作为"正常流程"的一部分
- ✅ 所有 LLM 推理都在你的 Claude Code 订阅里完成
- ✅ References 只通过手动 `git fetch` 拉取（无自动 cron）

如果一个通过 Task tool 派遣的 sub-agent 试图违反任何一条，orchestrator 会拒绝 + 上报。

**这条不可妥协。** 来自 Moirai 原项目 `§ 4 成本纪律` mandate。

---

## 状态与路线图

### 当前 —— `v0.2.2-alpha.3`

- ✅ 插件 scaffold + JSON Schema (`schema/state.schema.json`)
- ✅ Foundation：4 个 state 脚本 + 3 个 gate 脚本 + lib 辅助函数 + 测试（48 个 bash assertion，按 TDD 纪律 100% 通过）—— 来自 v0.1.0
- ✅ Python toolkit（`toolkit/` 目录，Path C hybrid monorepo）：
  - 6 个 IDE adapter 实现（ClaudeCode 标准 + Cursor + VSCode-Codex + Codex CLI + Inline 兜底）+ `detect_adapter()` 自动检测
  - audit_check 引擎，支持 AC-1 + AC-3 机械事实核查
  - 4 质量门聚合器（`quality-gate-enforce`）
  - 317 个 pytest 单元 + 属性 + 集成测试；mypy --strict 通过；ruff 通过
- ✅ 11 个 markdown skill（v0.1.0 foundation + plan-round + execute-round + close-round + codify-lesson + track-refs + cross-session-handoff）
- ✅ 9 个 markdown agent（orchestrator/auditor + planner/developer/BA/CR/SE + lesson-codifier + ref-tracker）
- ✅ Hooks：pre-commit-fact-check、quality-gate-enforce、round-boundary-lesson-scan
- ✅ 3 个 handoff 模板 + 3 个收尾模板（18/12/10 章节 handoff + BA 设计 + 自审 + 外审 verdict）
- ✅ P1 完成：`codify-lesson`、`track-refs`、`round-boundary-lesson-scan`、RT classifier、pattern detection
- ✅ P2 完成：`cross-session-handoff`，包含 TTL lock、atomic state write、history snapshot
- ✅ execute-round 自审现在运行 audit-check，不再报告 ER-AUDIT-GATE-4 skipped
- ✅ V1 release hardening：项目级 session mode、orchestrator dispatch
  顺序输出、按角色生成 identity prompt、结构化 verdict completeness、
  以及带 strict audit-check 的 `close-round` seam
- ✅ Python CLI 已发布到 PyPI：`arcgentic==0.2.2a3`
- ✅ GitHub Actions trusted publishing 工作流已接入 PyPI 发布
- ✅ Claude Code 插件 manifest + marketplace：`.claude-plugin/`
- ✅ Codex 本地插件 manifest：`.codex-plugin/plugin.json`
- ✅ OpenClaw git-source bundle manifest：`openclaw.plugin.json`
- ✅ Dogfood Gate 1（对 Moirai R10-L3-llm verdict 回放验证 —— PASS，来自 v0.1.0）
- ✅ Dogfood Gate 2（v0.1.0-alpha.2-meta round 闭环 PASS —— 来自 v0.1.0）
- ✅ Dogfood Gate 2 v0.2.0（协议已记录于 `tests/dogfood/gate-2-v0.2.0/PROTOCOL.md`；live execute-round 运行计划在 release 后执行）
- ⏳ Dogfood Gate 3（跨项目可移植性）—— 推迟到 pre-stable

### 下一版 —— `v0.3.0`

- OpenSpec ingest，作为上游 spec/source-of-truth 层
- Superpowers Marketplace capability scan，作为可选 plugin registry 输入
- GitHub reference discovery/search 接入 `track-refs`
- 从 commit chain 和 changed files 生成更丰富的 execute-round fact table
- ER-RETRY：sub-agent 派遣的带上下文重试循环

### `v1.0.0` 稳定版

Gate 3 在 2-3 个非 Moirai 项目验证通过后：晋升 stable + 提交到 Claude Code plugin marketplace。

---

## 起源

`arcgentic` 提炼自 [Moirai](https://github.com/Arch1eSUN/Moirai) 项目 **30+ 轮严格开发**的实战经验 —— 一个本地优先的认知基础设施，founder 为工程纪律支付高额代价：

- Manus-grade 类型化错误（runtime 边界 0 raw exception）
- 每条声明 invariant 都有 hypothesis property test
- 跨多 impl 的 protocol-parity 测试
- `doc-vs-impl` re-grep mandate（claim spec 前先重读 impl 源码）
- Reference-first development order（6 步：references/ → 融合 → 改写 → 评估非 Python → external GitHub → 从头写）
- 4-列 reference triplet（用了哪个 / 为什么用 / 用了什么部分 / 没用什么）
- RT0–RT3 reference tier 分类（inspiration / source adapt / binary vendor / full dep）
- Lesson codification 协议（观察 3 次 → 推断 → 验证 → 编码 → 宣告 NOVEL preservation type）

**经历最多 NEEDS_FIX 迭代后存活下来的纪律**，才进入这个插件。

arcgentic 里有什么：**模式（patterns）**。
arcgentic 里**没有**什么：**Moirai 特定实例**（Phase 编号 / fact-shape #1-16+ / EventLog 8 invariants / V2 envelope schema / ...）。

---

## 参与贡献

当前是 `v0.2.2-alpha.3`，插件在战场验证阶段。如果你有：
- **Bug 报告** —— 提 issue，附最小复现步骤
- **可移植性 bug** —— 提 issue 加 `portability` 标签，注明项目类型 / 操作系统 / Claude Code 版本
- **功能建议** —— 开 discussion（我们会对照[路线图](#状态与路线图)评估）
- **Pull request** —— 请先开 issue 讨论；未经讨论的 PR 可能推迟到 v1.0.0 之后处理

---

## License

[MIT](./LICENSE) —— Copyright (c) 2026 Arc Studio
