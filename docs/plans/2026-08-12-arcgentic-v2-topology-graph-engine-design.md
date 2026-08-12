# Arcgentic V2 — Topology Graph Engine Design

**日期**: 2026-08-12
**范围**: `toolkit/src/arcgentic/v2_session_orchestration.py` 及其消费者（`claude_code_broker.py`、`orchestrator_dispatch.py`）
**明确不涉及**: `scripts/state/*.sh` + `schema/state.schema.json` 里的 `states` 字段（V1 遗留，V2 从不读写，属于死代码，本次不清理，另行标记）

## 1. 背景

Arcgentic V2 的角色调度（orchestrator → planner → developer → test → auditor）目前是 Python 里两张写死的表：

- `next_role_for_state()` (`v2_session_orchestration.py:426-436`) — `current_round.state` 字符串 → 固定 `Role`
- `ROLE_ALLOWED_SIGNAL_ROUTES` (`v2_session_orchestration.py:72-96`) — 每个角色允许交接给谁的白名单

条件路由（比如 auditor 的 PASS/NEEDS_FIX 决定走向 planner 还是 developer）已经存在，但被硬编码在这个封闭的 5 角色枚举里；`current_round.state` 的 JSON Schema 是一个锁死的 12 值 enum；`role_sessions`/`pending_role` 是标量，一次只能有一个角色在跑；`project_plan.phases` 是纯线性列表，没有条件跳转或循环。

结论：项目既不能自定义状态拓扑，也没有并行分支/汇合，也没有真正的循环原语——"循环"目前只是硬编码在枚举里的一条特例路径（needs_fix → fix_in_progress → 回到 audit）。

## 2. 目标（本次落地）

用**一个**数据驱动的图解析器替换上面两张写死的表，保持 Codex 已验证的调度行为在默认配置下逐位不变。

不做（本次明确推迟，但 schema 形状要留出扩展空间，不产生破坏性迁移）：
- 并行 fan-out/join（给 ba-designer / cr-reviewer / se-contract 一个真正的并发图节点身份）
- `project_plan.phases` 复用同一图解析器实现跨 round 的条件跳转/循环

## 3. 设计

### 3.1 新增：`project.arcgentic_v2.topology`（可选字段）

邻接表形状，和 `schema/state.schema.json` 里已声明但从未被 V2 使用的 `states` 字段同构：

```yaml
topology:
  nodes:
    dev_in_progress:
      role: developer
      next:
        - to: awaiting_test
        - to: awaiting_audit
          when_signal: skip_test
    audit_in_progress:
      role: auditor
      next:
        - to: passed
          condition: "artifacts.audit_verdict.outcome == 'PASS'"
        - to: needs_fix
          condition: "artifacts.audit_verdict.outcome == 'NEEDS_FIX'"
    needs_fix:
      role: developer
      next:
        - to: awaiting_audit
    # ... 其余节点是今天 5 角色图的逐一转录
```

不配置 `topology` 时，引擎使用内置默认拓扑——今天硬编码表的字面转录，行为完全不变。

### 3.2 解析器替换写死的表

`apply_role_return_signal()` 里 `next_role = signal.next_recommended_role or next_role_for_state(signal.state)` (`v2_session_orchestration.py:777`) 是唯一的落点。改为：

```python
next_role = topology.resolve_next(current_node=signal.state, signal=signal) \
    or signal.next_recommended_role \
    or next_role_for_state(signal.state)  # 兼容兜底，未配置 topology 时原样生效
```

`resolve_next` 遍历当前节点的 `next` 边，按声明顺序求值 `condition`（对 `signal.artifacts` 做简单属性访问 + 相等/布尔比较，不引入通用表达式引擎/eval），第一个满足的边命中；没有 `condition` 的边视为默认边。

### 3.3 Schema 变更

- `current_round.state`：从 12 值 `enum` 松绑为普通 `string`。JSON Schema 做不了"值必须是当前 topology 的节点名"这种跨字段校验，所以校验移到运行时——Python 侧新增一个 `validate_state_in_topology()`，在 topology 存在时做节点名成员检查；未配置 topology 时保留原 12 值集合作为运行时校验（不是 schema enum，是等价的 Python 端集合校验，行为不变但校验点搬家）。
- `project.arcgentic_v2.topology`：新增可选 object，`additionalProperties: false`，为后续 `join` 字段预留位置但本次不定义它。

### 3.4 兼容性与测试

- `toolkit/tests/unit/test_v2_session_orchestration.py` 新增等价性测试：默认拓扑在所有既有测试用例下必须产出与旧硬编码表完全相同的调度决策（逐用例对比，不是抽样）。
- 新增自定义拓扑 fixture 测试：至少一条带 `condition` 的边、一条无 `condition` 的默认边，验证 `resolve_next` 的求值顺序与兜底行为。
- `claude_code_broker.py` / `orchestrator_dispatch.py` 不需要改动——它们只消费 `apply_role_return_signal()` 的返回值，不直接碰 `next_role_for_state`/`ROLE_ALLOWED_SIGNAL_ROUTES`。

## 4. 明确排除的范围（供下一轮参考,不在本次实现)

| 项 | 现状 | 为什么先不做 |
|---|---|---|
| 并行 fan-out/join | `role_sessions`/`pending_role` 是标量 | 需要把两处调用点都从标量改成集合,是独立的、更大的改动,应该单开一轮 |
| `project_plan.phases` 图化 | 纯线性 list-walk (`advance_passed_round_from_project_plan`, `547-632`) | 依赖 3.1/3.2 先跑稳,而且跨 round 循环的语义(重试整个 phase？回退到更早的 phase？)需要单独和你对齐,不该在这次顺带决定 |
| V1 bash `scripts/state/*.sh` + schema `states` 字段清理 | 死代码,V2 从不读写 | 超出本次范围,后续用 spawn_task 单独标记 |

## 5. 验收标准

1. 零配置项目(不写 `topology` 字段)的角色调度决策与改动前逐位相同——用等价性测试保证。
2. 自定义 `topology`(至少一条 `condition` 边)能正确路由,并被运行时校验拒绝非法节点名。
3. `current_round.state` 不再依赖 JSON Schema enum,但非法值仍然在写入前被拒绝(校验点从 schema 搬到 Python,不是校验消失)。
4. 现有 `toolkit/tests/unit/test_v2_session_orchestration.py` 全部通过,新增测试全部通过。
