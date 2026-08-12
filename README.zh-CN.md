# Arcgentic

<p align="center">
  <img src="./assets/arcgentic-logo.png" alt="Arcgentic logo" width="168">
</p>

> **Arcgentic 是 AI coding agent 的工程 harness，把随意 prompting 变成有阶段、
> 有自审、有外审、有测试门禁的工程流程。**

**English -> [README.md](./README.md)**

[![status](https://img.shields.io/badge/status-stable-brightgreen.svg)](#状态)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![version](https://img.shields.io/badge/version-v2.2.0-blueviolet.svg)](#状态)
[![PyPI](https://img.shields.io/pypi/v/arcgentic.svg)](https://pypi.org/project/arcgentic/)
[![npm](https://img.shields.io/npm/v/arcgentic.svg)](https://www.npmjs.com/package/arcgentic)

Arcgentic 帮助 Codex 和 Claude Code 把软件开发变成一套有纪律的流程：
先澄清想法，再规划，再开发，再开发者自审，必要时做真实用户测试，
再外部审计，最后只有证据足够时才 close。

它适合已经高频使用 AI coding 工具的人：你不想每次 session 都靠模型记忆、
靠 prompt 运气、靠“它说做完了”来判断项目是否真的完成。

## 它从哪里来

Arcgentic 来自 [Moirai](https://github.com/Arch1eSUN/Moirai) 项目的真实开发纪律。
Moirai 是一个长期 agent 项目，在 30+ 轮严格开发、反复 `NEEDS_FIX`、
多 session handoff、开发者自审、外部审计和可恢复状态管理里，沉淀出了一套可复用工作流。

Arcgentic 把这些“存活下来的模式”封装成插件，让 Codex 和 Claude Code 用户可以用在自己的复杂项目里。
它不是新的 coding agent，也不是 Moirai 的复制品；它不包含 Moirai 特定的 phase 编号、
fact shape、runtime 内部结构。它提取的是真实 agent 开发中的工程流程。

## Harness engineering

Arcgentic 位于 coding agent 外面的 harness 层。

Codex 和 Claude Code 是负责写代码的 agent。Arcgentic 是套在它们外面的工程
harness：给 agent 加角色、handoff、stop state、审计 gate 和证据记录。
这和 Karpathy 说的从 vibe coding 走向 agentic engineering 是同一条方向：
重点不只是怎么 prompt 模型，而是怎么设计模型外面的工作流，让输出可以被检查、
被路由、被追责。

相关参考：

- [Martin Fowler / Thoughtworks: Harness engineering for coding agent users](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html)
- Andrej Karpathy 关于 “vibe coding -> agentic engineering” 的讨论

## 30 秒版本

| 问题 | 回答 |
|---|---|
| 它是什么？ | 一层给 Codex / Claude Code 用的工程 harness：在 coding agent 外面加角色、handoff、审计、stop state 和 pass/fix gate。 |
| 它解决什么问题？ | AI coding session 容易漂移：范围被悄悄改变、上下文丢失、测试被跳过，“完成”经常只是 assistant 自己说完成。 |
| 谁应该用？ | 高频使用 Codex / Claude Code 的 senior engineer、agent builder、小型 AI-native 工程团队，以及做复杂 repo、多轮开发、重构、agent 产品的人。 |
| 它增加什么？ | 一套可重复的门禁流程，并自动派发角色：计划、开发者自审、可选真实用户测试、外部审计、closeout。 |
| 它不做什么？ | 它不替代你的判断、测试或 code review。它让这些步骤更难被跳过。 |

## 平台状态

| 平台 | V2 状态 | 验证情况 |
|---|---|---|
| **Codex** | 完整 V2 | 已在真实 Codex 项目工作流中实机验证，包括自动标记 Orchestrator、创建/复用角色 thread、派发 prompt 和等待回传。 |
| **Claude Code** | 完整 V2 | 已在真实 Claude Code session 中验证 `single-session-subagent` 模式：通过前台 `Agent` 调用完成的 tier-0 broker 派发，详见 `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`。这次 gate 只覆盖了单次 Planner 角色派发，不是完整的 Planner→Developer→Auditor 一轮流程。这次 gate 也没有触发 `SendMessage` 的 footer 纠错重试路径（第一次返回的 footer 就是合法的），也没有用到 `ListAgents`；`multi-session-subthread` 模式和 hook 兜底路径同样尚未验证。 |

Codex 是目前最完整的体验。在已验证的 Codex 路径里，当前项目对话会成为
`Orchestrator`；Arcgentic 会创建或复用角色 thread、命名它们、发送对应角色 prompt、
等待角色回传，再自动派发下一步。中间不需要用户手动创建 thread 或搬运 prompt。

Claude Code 版本的 `single-session-subagent` 模式现在已经有实机 dogfood 验证——具体是通过
前台 `Agent` 调用完成的 tier-0 broker 派发，可以视为这条路径已验证。但 `SendMessage` 的
footer 纠错重试路径和 `ListAgents` 都没有被这次 gate 实际触发过，`multi-session-subthread`
模式和 hook 兜底路径也还没有经过真实 Claude Code session 的验证，这些都仍应视为未经证明。

## 分发状态

| 渠道 | 状态 | 用途 |
|---|---|---|
| [GitHub Release](https://github.com/Arch1eSUN/Arcgentic/releases/tag/v2.2.0) | 已发布 `v2.2.0` | Release notes、源码归档、验证背景。 |
| [PyPI](https://pypi.org/project/arcgentic/) | 已发布 `arcgentic==2.2.0` | Python CLI：gate、V2 state helper、Claude Code broker、audit 工具。 |
| [npm](https://www.npmjs.com/package/arcgentic) | 已发布 `arcgentic@2.2.0` | 插件资产包和 Codex 本地安装 helper。 |
| Claude Code plugin marketplace | Manifest 已就绪 | Claude Code 主安装路径；`single-session-subagent` 模式已通过前台 `Agent` 的 tier-0 broker 派发获得实机 dogfood 验证，但 `multi-session-subthread` 模式和 hook 兜底路径仍未验证。 |

## 安装

### Codex 本地安装

```bash
git clone https://github.com/Arch1eSUN/Arcgentic.git arcgentic
cd arcgentic
bash scripts/install-codex-local.sh --plugin-root .
```

然后在一个已保存的项目 workspace 里开始：

```text
Use Arcgentic to build this idea: <your idea>
```

### npm bundle 安装

如果你希望通过 npm 获取 Arcgentic 插件资产：

```bash
npm install -g arcgentic
arcgentic install-codex-local
```

npm 包是零依赖的插件资产包和 Codex 本地安装 helper。它包含 skills、agents、
scripts、schemas、templates 和平台 manifest。Python CLI 仍然单独通过 PyPI 发布。

### Claude Code 安装

```text
/plugin marketplace add Arch1eSUN/Arcgentic
/plugin install arcgentic@arc-studio
```

然后在你的项目里开始：

```text
Use Arcgentic to build this idea: <your idea>
```

Claude Code V2 实验工作流设置：

如果当前 Claude Code session 自己的工具列表里已经包含 `Agent`、
`SendMessage` 和 `ListAgents`（原生工具，即 "tier 0"），不需要任何安装
步骤——session broker 会直接使用这些工具，这也是首选的、已有 dogfood
验证的路径（见上面的“平台状态”）。下面的 `install-hooks` 只在缺少这三
个工具时作为兜底方案使用：

```bash
arcgentic claude-code-broker install-hooks \
  --settings .claude/settings.local.json \
  --state .agentic-rounds/state.yaml
```

### 只安装 CLI

如果你只需要命令行工具：

```bash
pipx install arcgentic
arcgentic --help
```

## 最小例子

不用 Arcgentic：

```text
User: Build a small expense splitter.
AI: writes code
AI: says it is done
User: later discovers missing edge cases, unclear scope, no audit trail
```

使用 Arcgentic：

```text
User idea
-> current conversation becomes Orchestrator
-> Orchestrator creates or reuses Planner and sends the planning prompt
-> Planner returns the plan to Orchestrator
-> Orchestrator creates or reuses Developer and sends the dev prompt
-> Developer implements and returns a self-audit
-> Orchestrator dispatches optional Test only if realistic use needs it
-> Orchestrator creates or reuses Auditor and sends the audit prompt
-> Auditor returns PASS / NEEDS_FIX / AUDIT_INCOMPLETE
-> Orchestrator routes the next step
```

关键差异不是 AI 写了更多文字，而是每个角色有边界，每个阶段有停止条件，
“done” 必须能解释为什么可以 done。

## Arcgentic 会先推荐模式

当你用一个新想法启动 Arcgentic，当前 session 会成为 `Orchestrator`。
在进入规划或开发前，Orchestrator 应该先判断这是小型快速项目，还是需要更强审计的大型项目。
然后它会推荐一个项目级模式，并让你确认或覆盖。

| 模式 | 适合什么时候 | 取舍 |
|---|---|---|
| **单 session，多智能体** | 想更快完成，或者做较小项目 / demo。 | 速度更快，审计隔离更弱。Planner、Developer、Test、Auditor 在当前 Orchestrator session 内以固定命名 role agent 运行，并在后续 round 复用。 |
| **多 session，多 thread** | 想要更强的 planning / dev / test / audit 隔离。 | 速度更慢，审计纪律更强。Planner、Developer、Test、Auditor 使用固定项目 thread。 |

这个选择是项目级决定。Arcgentic 不应该每一轮都重新问，除非你开启新项目或显式重置工作流。

## 真实使用时发生了什么变化

### Before

- 一个很长的 AI coding session 试图记住所有事情。
- assistant 在同一个上下文里混合 planning、coding、review、closeout。
- fix 有时被误当成 audit 工作。
- 下一次 session 需要重新猜之前发生了什么。
- “pass” 经常只是 assistant 感觉自己有信心。

### After

- 当前 session 是 Orchestrator。
- Planner、Developer、Test、Auditor 是独立角色。
- Developer 负责开发、修复、本地验证和自审。
- Auditor 负责更严格的独立审计。
- Test 只在需要真实用户行为验证时运行。
- 项目或 phase 条件满足后才 close。

## V2 工作流

Arcgentic V2 的流程是：

```text
idea
-> brainstorm and planning
-> round handoff
-> development
-> developer self-audit
-> optional user-test
-> external audit
-> pass or fix
-> next round, next phase, or closeout
```

角色固定：

| 角色 | 负责什么 |
|---|---|
| **Orchestrator** | 总控、派发、等待、决定下一个角色。 |
| **Planner** | brainstorm、项目计划、phase/round 划分、handoff、closeout 判断。 |
| **Developer** | 开发、修复、本地验证、开发者自审。 |
| **Test** | 在计划认为需要时，执行真实用户/session 级测试。 |
| **Auditor** | 独立证据审查，并给出 `PASS` / `NEEDS_FIX` / `AUDIT_INCOMPLETE`。 |

Arcgentic 不会每轮创建新的角色身份。角色名始终固定：
`Orchestrator`、`Planner`、`Developer`、`Test`、`Auditor`。

## 自定义角色/状态拓扑

决定"下一步该谁来做"的角色/状态路由，不再是写死的表。它现在是一个
`Topology`（`toolkit/src/arcgentic/topology.py`），项目可以通过 `state.yaml`
里的 `project.arcgentic_v2.topology` 覆盖——包括路由规则、每个角色允许在
哪些状态下行动，以及基于返回角色 `artifacts` 内容的条件路由（比如根据审计
结果字段走不同分支）。零配置项目拿到的行为和之前逐位相同；自定义拓扑在
解析阶段就会被校验（未知的角色名、没有对应目标状态的路由，都会在项目卡在
半轮之前被拒绝）。这是给需要和默认 plan/dev/audit 循环不一样的角色图的
项目用的——大多数项目不需要碰它。

## Codex V2

Codex V2 使用 Codex 的 project thread 能力完成多 session / 多 thread 编排。

已经实机验证的自动化流程是：

```text
用户在项目对话里启动 Arcgentic
-> Arcgentic 把当前对话标记为 Orchestrator
-> Orchestrator 询问或记录项目模式
-> Orchestrator 创建或复用固定角色 thread / agent
-> Orchestrator 投放对应角色 prompt 和 artifact 指针
-> 角色完成后主动回传给 Orchestrator
-> Orchestrator 消费回传信息并派发下一个角色
```

在已验证的 Codex 流程里，用户不应该手动创建 Planner、Developer、Test 或 Auditor thread。

在多 thread 模式下：

```text
Current thread -> Orchestrator
-> create/reuse Planner thread and send Planner prompt
-> Planner returns to Orchestrator
-> create/reuse Developer thread and send Developer prompt
-> Developer returns to Orchestrator
-> create/reuse optional Test thread only when needed
-> create/reuse Auditor thread and send Auditor prompt
-> Auditor returns to Orchestrator
```

Orchestrator 派发任务后应该休眠。角色完成工作后主动把结果返回 Orchestrator，
Orchestrator 再决定下一步。

在单 session 模式下：

```text
Current thread -> Orchestrator
role agent -> Planner
role agent -> Developer
role agent -> Test
role agent -> Auditor
```

这些 role agent 也应该复用，不应该每一轮重新创建 `R1 Developer`、`R2 Developer`。

## Claude Code V2 实验版

Claude Code 版本的目标是和 Codex V2 使用同一套 workflow contract。
区别在于 Claude Code 需要 session broker 帮它接近 Codex 的 thread 编排能力。

当前状态：

- V2 workflow contract 已完成。
- Claude Code session broker 已提供 hooks 安装路径。
- role identity、return signal、mode 选择、fixed role reuse 都已按 V2 设计适配。
- `single-session-subagent` 模式已经通过前台 `Agent` 的 tier-0 broker 派发完成真实 Claude
  Code session 验证（详见 `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`）；
  `multi-session-subthread` 模式和 hook 兜底路径还没有完成端到端实机验证。

目标行为是和 Codex 一样自动化：

```text
current session = Orchestrator
-> create/reuse Planner session and send Planner prompt
-> Planner returns
-> create/reuse Developer session and send Developer prompt
-> Developer returns
-> optional Test only when needed
-> create/reuse Auditor session and send Auditor prompt
-> Auditor returns
```

Claude Code experimental mode 会通过 session broker 尽量达到同样的无手动路由行为。
这套完整自动化还没有经过真实 Claude Code session 验证。如果 push-return 在你的环境里不可用，
先使用显式 copy-back：把角色输出的自然语言总结和 `arcgentic-role-return` footer 粘回 Orchestrator。

## MCP-UI 状态面板

arcgentic 现在自带一个可选的 MCP server，通过
[MCP Apps](https://modelcontextprotocol.io/specification/draft/extensions/apps)
（2026 年 1 月成为 MCP 官方扩展，用于在对话里渲染可交互 UI）暴露一个实时的
round 状态面板。安装：

```bash
pip install 'arcgentic[mcp]'
```

在项目的 `.mcp.json` 里声明：

```json
{
  "mcpServers": {
    "arcgentic": {
      "command": "arcgentic",
      "args": ["mcp-serve"]
    }
  }
}
```

调用 `round_status_panel` 这个 tool，会把 round id、各角色派发进度、最近一次
audit verdict 渲染成内嵌面板，带客户端自动轮询（有上限，面板不在前台时暂停）和
一个"派发下一角色"按钮——按钮发的是一条对话消息，不是直接改状态，面板本身
没有任何写权限，状态机始终只能由 Orchestrator 推进。在不支持 MCP Apps 的
host 上（包括纯终端的 Codex/Claude Code 会话），同一个 tool 调用会退化成纯
文本摘要，而不是报错。

MCP Apps 的 host 生态还比较新——这个功能是给支持 MCP-UI 的图形化客户端用的，
不是给纯终端会话用的。

## 什么时候适合用 Arcgentic

最适合：

- 高频使用 Codex / Claude Code 的 senior engineer。
- agent builder。
- 小型 AI-native 工程团队。
- 做复杂 repo、多轮开发、重构、agent 产品的人。
- 需要证明“AI 写的代码经过计划、测试、审计”的团队。

Arcgentic 比普通 prompting 更重。如果你的任务不复杂、不需要审计证据、
不需要多轮上下文恢复，那么它可能是杀鸡用牛刀。

不适合：

- 一次性小脚本；
- 你已经能完全掌控上下文的小修小改；
- 不需要审计性的快速实验；
- 只想让 assistant 快速改一行代码；
- 你不关心 auditability 的工作。

## 一次好的 Arcgentic run 应该产出什么

- 一个项目计划或 round handoff。
- Developer 实现结果和自审。
- 必要时的真实用户/session 测试报告。
- Auditor 外部审计 verdict。
- PASS / NEEDS_FIX / AUDIT_INCOMPLETE 的明确结论。
- closeout 或下一轮 handoff。
- 可被后续 session 读取的状态和证据。

## Demo 和例子

当前 README 先优先解决 onboarding。下一批 adoption assets 应该包括：

- 一个短 demo GIF 或 demo video，展示 Orchestrator -> Planner -> Developer -> Auditor。
- 一个小型 example project，展示不用 Arcgentic 和使用 Arcgentic 的差异。
- Claude Code `multi-session-subthread` 模式和 hook 兜底路径的真实 session 验证记录
  （`single-session-subagent` 模式的验证记录已经在
  `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`）。

## 常见问题

### 它创建了太多 session

V2 不应该每轮创建新角色。正确名称只有：

```text
Orchestrator
Planner
Developer
Test
Auditor
```

如果看到 `R1 Developer`、`R2 Auditor` 之类的名字，那不是目标行为。

### Orchestrator 派发后还在继续工作

Orchestrator 派发角色后应该等待。Developer、Planner、Test、Auditor 完成后主动返回信息。
如果 Orchestrator 一边派发一边继续实现功能，说明流程没有遵守 V2。

### Audit 一直循环

Audit 不应该无限循环。Auditor 决定 `PASS`、`NEEDS_FIX` 或 `AUDIT_INCOMPLETE`。
如果是 fix，工作应该回到 Developer。相同 audit gap 无法通过重复 audit 解决时，
应该停下来暴露问题，而不是继续创建 audit 循环。

### Test 每轮都运行

Test 不是每轮必跑。它只在需要真实用户行为、UI 使用、模拟 session、
性能感知、交互细节或更严格体验审查时运行。

## 状态

当前 release surface：

- Python CLI: `arcgentic`
- Codex 本地插件 manifest
- Claude Code 插件 manifest
- V2 workflow prompts and state helpers
- npm bundle 已发布：`arcgentic@2.2.0`
- Codex V2 实机验证完成
- Claude Code V2 实验适配完成；`single-session-subagent` 模式的首次派发
  （`create`）路径已有真实 session dogfood 验证，`multi-session-subthread`
  模式、`SendMessage` 重复派发（`reuse`）路径和 hook 兜底路径仍在等待验证
- 自定义角色/状态拓扑完成；零配置行为不变，自定义拓扑解析阶段即校验
- MCP-UI 状态面板完成，可选安装（`pip install arcgentic[mcp]`），依赖 host
  的 MCP Apps 支持

## 路线图

近期重点不是继续堆复杂功能，而是降低使用门槛：

- README first screen 更清楚；
- demo GIF / demo video；
- example project；
- Before / After 对比；
- issue template / feedback loop；
- Claude Code V2 `multi-session-subthread` 模式、`SendMessage` 重复派发路径
  和 hook 兜底路径的实机验证记录（`single-session-subagent` 模式的首次派发
  路径已有验证记录）。

## 反馈

如果你试用 Arcgentic，最有价值的反馈是：

- 安装失败；
- 不知道下一步该做什么；
- workflow 不适配你的项目；
- Orchestrator / Planner / Developer / Auditor 行为混乱；
- audit gate 太重或太轻；
- Claude Code experimental flow 无法完整跑通。

请在 GitHub issue 里附上：

- 平台：Codex 或 Claude Code；
- 模式：single-session-subagent 或 multi-session-subthread；
- 项目类型；
- 你输入的 idea；
- 卡住的阶段；
- 相关 `.agentic-rounds` 状态或角色输出。

## License

[MIT](./LICENSE) - Copyright (c) 2026 Arc Studio
