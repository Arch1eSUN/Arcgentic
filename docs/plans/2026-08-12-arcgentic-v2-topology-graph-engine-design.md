# Arcgentic V2 — Topology Graph Engine Design

**日期**: 2026-08-12
**范围**: `toolkit/src/arcgentic/v2_session_orchestration.py` 及其消费者（`claude_code_broker.py`、`orchestrator_dispatch.py`）
**明确不涉及**: `scripts/state/*.sh` + `schema/state.schema.json` 里的 `states` 字段（V2 Python 引擎——`toolkit/src/arcgentic/v2_session_orchestration.py` 及其消费者——从不读写这些，本次改动不涉及。**更正（2026-08-12 后续调查）**：这不等于"死代码"——`skills/using-arcgentic`、`skills/orchestrate-round`、`skills/audit-round`、`skills/verify-gates` 这些当前仍在 `plugin.json` 里正式声明、未被标记废弃的 skill，会直接调用 `scripts/state/{init,pickup,transition,validate-schema}.sh` 和 `scripts/gates/*.sh`——这是一条独立于 V2 自动化派发、仍然存活且被文档化的"手动/单会话"操作路径（`orchestrate-round` 的 description 明确写着"Use when in single-session mode... or when manually advancing the state machine"），不是被 V2 取代的历史遗留。只有 `init.sh` 是两条路径共用的启动脚本（`skills/arcgentic/SKILL.md` 的 V2 入口本身也调用它来引导 `.agentic-rounds/state.yaml`）。详见调查记录：本文件不再是该判断的权威来源，实际结论以调查时的对话/commit 为准。）

## 1. 背景

Arcgentic V2 的角色调度（orchestrator → planner → developer → test → auditor）目前是 Python 里三张写死的表（见第 3 节的修正说明，最初误记成两张）：`ROLE_ALLOWED_CURRENT_STATES`、`ROLE_ALLOWED_SIGNAL_ROUTES`、`next_role_for_state`。auditor 的 PASS/NEEDS_FIX 分支不是引擎做条件判断的结果，而是 auditor 角色自己决定把 `signal.state` 报成哪个值，引擎只做合法性校验（详见第 3 节修正）。`current_round.state` 的 JSON Schema 是一个锁死的 12 值 enum；`role_sessions`/`pending_role` 是标量，一次只能有一个角色在跑；`project_plan.phases` 是纯线性列表，没有条件跳转或循环。

结论：项目既不能自定义状态拓扑，也没有并行分支/汇合，也没有真正的循环原语——"循环"目前只是硬编码在枚举里的一条特例路径（needs_fix → fix_in_progress → 回到 audit）。

## 2. 目标（本次落地）

用**一份**数据驱动的拓扑配置替换上面三张写死的表，保持 Codex 已验证的调度行为在默认配置下逐位不变。

不做（本次明确推迟，但 schema 形状要留出扩展空间，不产生破坏性迁移）：
- 并行 fan-out/join（给 ba-designer / cr-reviewer / se-contract 一个真正的并发图节点身份）
- `project_plan.phases` 复用同一图解析器实现跨 round 的条件跳转/循环

## 3. 设计

**修正（写计划阶段发现，设计稿原文有误）**：实际读代码后确认，写死的不是两张表，是**三张**独立的表，且互相不是同一份数据的不同视角，必须分别搬到 topology 里，否则自定义拓扑没法完整替代默认行为：

1. `ROLE_ALLOWED_CURRENT_STATES: Role -> frozenset[state]` (`v2_session_orchestration.py:62-70`) — 前置条件：某角色允许在哪些 `current_round.state` 值下发出信号。**注意 orchestrator 和 planner 的允许集合完全相同**（都是 `{intake, planning, passed, closed}`），这不是巧合可以简化掉的重复，是两个角色共享同一组入口状态，topology 必须原样保留这个重叠，不能假设"一个 state 只属于一个角色"。
2. `ROLE_ALLOWED_SIGNAL_ROUTES: Role -> {state: frozenset[Role]}` (`72-96`) — 校验用：角色 R 上报新状态 S 时，允许的下一角色集合。
3. `next_role_for_state: state -> Role` (`426-436`) — 当信号没给 `next_recommended_role` 时的兜底下一角色。

也更正一点：今天**没有基于 `artifacts` 的条件路由**。auditor 是不是 PASS，是 auditor 这个角色自己判断后把 `signal.state` 设成 `"passed"` 或 `"needs_fix"`——引擎只做上面第 2 张表的合法性校验，不读 `signal.artifacts` 做分支决策。所以"条件路由"是全新能力，不是把已有逻辑数据化。为了不改变"谁来决定分支"这个协议契约（agent 自报 state，引擎只校验），本次不做引擎读 `artifacts` 自动选路——那是更大的协议变更，应该单独对齐。`condition` 字段仍然设计进 schema（给未来自定义拓扑用），但默认拓扑的所有边都不使用它。

### 3.1 新增：`project.arcgentic_v2.topology`（可选字段）

不是"节点独占一个角色"的干净图（3.1 修正说明了为什么不能这样简化），而是三张表的字面转录，保留原有的角色重叠语义：

```yaml
topology:
  roles:
    orchestrator: {allowed_current_states: [intake, planning, passed, closed]}
    planner:      {allowed_current_states: [intake, planning, passed, closed]}
    developer:    {allowed_current_states: [awaiting_dev_start, dev_in_progress, needs_fix, fix_in_progress]}
    test:         {allowed_current_states: [awaiting_test, test_in_progress]}
    auditor:      {allowed_current_states: [awaiting_audit, audit_in_progress]}
  routes:
    orchestrator: {planning: [planner], closed: [planner]}
    planner:      {awaiting_dev_start: [developer], planning: [planner], closed: [planner]}
    developer:    {awaiting_test: [test], awaiting_audit: [auditor], needs_fix: [developer]}
    test:         {awaiting_audit: [auditor], needs_fix: [developer]}
    auditor:      {passed: [planner], needs_fix: [developer], audit_in_progress: [auditor]}
  default_next_role:
    intake: planner
    planning: planner
    passed: planner
    closed: planner
    awaiting_dev_start: developer
    dev_in_progress: developer
    needs_fix: developer
    fix_in_progress: developer
    awaiting_test: test
    test_in_progress: test
    awaiting_audit: auditor
    audit_in_progress: auditor
    # default_next_role 的值也可以是一个候选列表而不是裸角色名，按声明顺序对每个
    # candidate 求值 condition，第一个 condition 满足（或没有 condition）的命中：
    # audit_in_progress:
    #   - {role: auditor, condition: {path: "artifacts.foo", equals: "bar"}}
    #   - {role: auditor}   # 无 condition 的兜底边，必须放最后
```

不配置 `topology` 时，引擎使用内置默认拓扑——上面这份就是默认值本身（不是"举例"，是真实的默认拓扑数据），行为完全不变。默认拓扑里所有 `default_next_role` 的值都是裸角色名，不使用候选列表形式。

### 3.2 三处调用点分别替换，不是单点合并

`apply_role_return_signal()` 里有三处独立查表，分别替换成 `Topology` 对象上的三个方法，控制流原样保留（不引入新的黑盒 `resolve_next`，降低和现有校验逻辑分叉的风险）：

- `allowed_current_states = ROLE_ALLOWED_CURRENT_STATES[signal.role]` (`:761`) → `topology.allowed_current_states(signal.role)`
- `route_options = ROLE_ALLOWED_SIGNAL_ROUTES[signal.role]` (`:771`) → `topology.routes_for_role(signal.role)`
- `next_role = signal.next_recommended_role or next_role_for_state(signal.state)` (`:777`) → `signal.next_recommended_role or topology.default_next_role(signal.state, signal.artifacts)`

`condition` 的求值（属性路径 + 相等比较，不引入 eval/通用表达式引擎）只发生在 `default_next_role` 内部，且只在 `next_recommended_role` 为空时才会被调用到；本次默认拓扑的 `default_next_role` 全部是裸角色名，不会走到候选列表分支。

### 3.3 Schema 变更

- `current_round.state`：从 12 值 `enum` 松绑为普通 `string`。JSON Schema 做不了"值必须是当前 topology 的节点名"这种跨字段校验，所以校验移到运行时——Python 侧新增一个 `validate_state_in_topology()`，在 topology 存在时做节点名成员检查；未配置 topology 时保留原 12 值集合作为运行时校验（不是 schema enum，是等价的 Python 端集合校验，行为不变但校验点搬家）。
- `project.arcgentic_v2.topology`：新增可选 object，`additionalProperties: false`，为后续 `join` 字段预留位置但本次不定义它。

### 3.4 兼容性与测试

- `toolkit/tests/unit/test_v2_session_orchestration.py` 新增等价性测试：默认拓扑在所有既有测试用例下必须产出与旧硬编码表完全相同的调度决策（逐用例对比，不是抽样）。
- 新增自定义拓扑 fixture 测试：`default_next_role` 用候选列表形式声明至少一条带 `condition` 的边 + 一条无 `condition` 的兜底边，验证按声明顺序求值、命中即停止的行为。
- `claude_code_broker.py` / `orchestrator_dispatch.py` 不需要改动——它们只消费 `apply_role_return_signal()` 的返回值，不直接碰 `next_role_for_state`/`ROLE_ALLOWED_SIGNAL_ROUTES`。

## 4. 明确排除的范围（供下一轮参考,不在本次实现)

| 项 | 现状 | 为什么先不做 |
|---|---|---|
| 并行 fan-out/join | `role_sessions`/`pending_role` 是标量 | 需要把两处调用点都从标量改成集合,是独立的、更大的改动,应该单开一轮 |
| `project_plan.phases` 图化 | 纯线性 list-walk (`advance_passed_round_from_project_plan`, `547-632`) | 依赖 3.1/3.2 先跑稳,而且跨 round 循环的语义(重试整个 phase？回退到更早的 phase？)需要单独和你对齐,不该在这次顺带决定 |
| ~~V1 bash `scripts/state/*.sh` + schema `states` 字段清理~~ | ~~死代码,V2 从不读写~~ **更正**：只对 V2 Python 引擎而言"从不读写"；插件层面这些脚本被 `using-arcgentic`/`orchestrate-round`/`audit-round`/`verify-gates` 等仍存活的 skill 实际调用,是独立于 V2 的手动操作路径,不是死代码。已在后续调查中核实,无需清理。 | 超出本次范围,后续用 spawn_task 单独标记(该 spawn_task 调查后已澄清,见更正) |

## 5. 验收标准

1. 零配置项目(不写 `topology` 字段)的角色调度决策与改动前逐位相同——用等价性测试保证。
2. 自定义 `topology`(至少一条 `condition` 边)能正确路由,并被运行时校验拒绝非法节点名。
3. `current_round.state` 不再依赖 JSON Schema enum,但非法值仍然在写入前被拒绝(校验点从 schema 搬到 Python,不是校验消失)。
4. 现有 `toolkit/tests/unit/test_v2_session_orchestration.py` 全部通过,新增测试全部通过。
