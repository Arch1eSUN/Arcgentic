# Arcgentic Claude Code V2 — Native-Tooling Broker Upgrade — Design

**日期**: 2026-08-12
**范围**: `skills/claude-code-session-broker/SKILL.md` 的 dispatch 流程改写,新增一档"原生工具"transport;README.md 状态行;一次真实 dogfood 验证并写 RESULT 记录
**明确不涉及**:`toolkit/src/arcgentic/v2_session_orchestration.py`、`toolkit/src/arcgentic/cli.py`、`toolkit/src/arcgentic/claude_code_broker.py` 的 Python 代码——现有 CLI 接口(`v2-session-plan`/`v2-record-session`/`v2-dispatch-role`/`v2-return-signal`)已经是 host-agnostic 的结构化数据层,不需要改;hook-backed broker 原样保留作为 fallback,不删除、不重构

## 1. 背景

`skills/claude-code-session-broker/SKILL.md` 现在的 "Broker priority" 列了四档 transport:

1. Hook-backed broker(Stop/SubagentStop footer capture)
2. Agent Teams(when enabled and stable)
3. Background subagents + hooks
4. Explicit copy-back

第 2/3 档从写下来那天起就是空话——"uses Claude Code subagents, Agent Teams, hooks... depending on what the host supports",没有绑定到任何具体工具调用,因为当年这个能力还不稳定/不存在。README 把 Claude Code V2 标成"Complete V2 experimental — not yet verified in a real Claude Code session",跟 Codex 那条"Complete V2, verified"形成对比。

现在这个会话的工具集里有 `Agent`(前台调用会阻塞并直接拿到返回值;后台调用完成时有 task-notification,可用 `SendMessage` 恢复)、`SendMessage`(按名字给任意 agent/session 发消息并恢复带完整上下文)、`ListAgents`(发现其他活跃会话)。这些正是第 2/3 档一直空缺的具体落地。

现有 hook 机制的本质是"事后侦测":Orchestrator 睡眠后,靠外部 Stop 事件解析 `last_assistant_message` 里的 footer。用前台 `Agent` 调用时,派发本身就是同步的——拿到返回值那一刻就是角色完成的那一刻,不需要外部 hook 再侦测一次。用后台 `Agent` 调用时,task-notification 到达即角色完成,效果等价于 hook 捕获 Stop 事件,只是原生交付,不需要文件 inbox。

## 2. 为什么这次不改 Python 代码

`Agent`/`SendMessage`/`ListAgents` 只有当前正在跑的 Claude 会话自己能调用——Python CLI 子进程没有能力发起这些工具调用,不存在"写一个 Python 函数去调 Agent 工具"这种做法。而现有的 `v2-session-plan --host claude-code-broker` 命令已经返回 `SessionPlan.to_dict()`,里面 `actions[].prompt` 就是角色该收到的完整 prompt 文本——数据层早就是 host-agnostic 的。缺的只是"Orchestrator 拿到这份 prompt 之后,具体该把它塞进哪个工具调用"这一步的明确指令,这是 skill 文本的职责,不是 Python 的职责。

## 3. 设计

### 3.1 `skills/claude-code-session-broker/SKILL.md` 改写

"Broker priority" 从四档模糊列表改成两档明确档位:

**档位 0 — 原生工具(会话里能看到 `Agent`/`SendMessage`/`ListAgents` 时优先使用)**

- `single-session-subagent` 模式:
  1. `arcgentic v2-session-plan --host claude-code-broker ...` 拿到 `actions[0].prompt`。
  2. 前台调用 `Agent`(`prompt` = 上一步的文本,`subagent_type` 按角色选择,模型按现有"Use the strongest available model for real work"规则选)。
  3. `Agent` 返回后,直接在返回文本里找 `arcgentic-role-return` footer,做和 hook 完全相同的校验(复用同一套判定逻辑描述,不新造校验规则)。footer 缺失时,用 `SendMessage` 恢复同一个 agent,要求补上 footer——这是同一个"block once, 给出纠正理由"的 fail-closed 语义,只是载体从 hook 的 `decision: block` 换成一条 `SendMessage`。
  4. 校验通过后 `arcgentic v2-return-signal --signal-json ...`,然后 `arcgentic v2-dispatch-role`,回到第 1 步派发下一角色。
- `multi-session-subthread` 模式:同样流程,但第 2 步用后台 `Agent` 调用,Orchestrator 结束当前 turn(睡眠语义不变——`orchestrator_status: sleeping` 照旧写入 state.yaml);task-notification 到达时角色输出已经在手上,从第 3 步继续。
- 若会话里看不到这三个工具(比如纯 Codex 会话,或未来某个更简化的 Claude Code 变体),判定原生工具不可用,直接落到档位 1。

**档位 1 — hook-backed broker(fallback,原样保留)**

- 现有 `install-hooks`/`handle-stop` 流程完全不变,文本从"第一优先"改成"档位 0 不可用时的 fallback"。

"Explicit copy-back"作为两档都失败时的最后手段保留一句话,不展开(现状已经够用)。

### 3.2 README.md 状态行

`docs/plans` 目录下没有独立任务去"证明"这套新流程能跑通——validation 本身就是这次设计的一部分:实际跑一轮 dogfood(Orchestrator 派发 Planner,走一遍档位 0 的前台 `Agent` 路径,校验 footer,record signal),把过程和结果写成 `tests/dogfood/gate-3-claude-code-native-broker/RESULT.md`(沿用仓库现有 `tests/dogfood/gate-2-live-run/RESULT.md` 这种记录格式)。RESULT 通过后,README 的状态行才能从"experimental — not yet verified"改成"verified",跟 Codex 那行对齐用词。

### 3.3 验收标准

1. `skills/claude-code-session-broker/SKILL.md` 的档位 0 流程写清楚到可以直接照做的程度(具体到"调 Agent 工具,prompt 用 actions[0].prompt"这一级,不再是"uses subagents, Agent Teams... depending on"这种空话)。
2. 至少完成一次真实 dogfood:这个会话自己用档位 0 的流程派发至少一个角色(建议 Planner,因为它不需要真的改代码,产出一份 handoff 文档即可验证流程),全程记录在 RESULT.md 里,包括 footer 校验通过、`v2-return-signal` 正确记录。
3. README.md 状态行更新,措辞和 Codex 那行对齐(但不夸大——如果 dogfood 只验证了 `single-session-subagent` 模式,不要连 `multi-session-subthread` 一起标成 verified)。
4. hook-backed broker 的 Python 代码和现有测试(`toolkit/tests/unit/test_claude_code_broker.py`)不受影响,全量测试套件继续通过。
