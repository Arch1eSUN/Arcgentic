# Arcgentic MCP-UI Status Panel — Design

**日期**: 2026-08-12
**范围**: 新增一个 MCP server 组件(`toolkit/src/arcgentic/mcp/`),通过 MCP Apps(SEP-1865,2026-01-26 正式成为 MCP 官方扩展,基于社区 MCP-UI 项目,Anthropic + OpenAI 联合起草)把当前 round 状态渲染成内嵌在对话里的可交互面板
**明确不涉及**:纯终端 Codex/Claude Code CLI 会话里的渲染(物理上无法渲染 iframe,只走文本 fallback);面板/MCP server 直接执行任何状态写操作(见 §3.1 更正);真正的 server-push(基于 `resources/subscribe`)——host 生态还不成熟,v1 用客户端轮询

**更正(写实现计划前发现)**:原稿设计的 `dispatch_next_role` tool 有架构性问题——`v2-dispatch-role` 这条 CLI 命令的真实语义是"把已经创建好的角色线程/subagent **登记**进 state.yaml",真正创建新角色线程/subagent 只有当前跑着的 orchestrator agent 自己能做,一个独立的 MCP server 进程做不到。改用 MCP-UI 的 `prompt` action 类型(把请求作为自然语言消息交回当前对话,而不是直接调 tool)代替,详见 §3.1/§3.2。MCP server 因此只需要一个只读 tool,不需要任何写权限的 tool——范围比原设计更小、更安全,也更符合"状态机只能被 agent 驱动"的既有原则。

## 1. 背景与可行性

MCP Apps 目前被 Claude(网页/Desktop)、VS Code GitHub Copilot、Microsoft 365 Copilot、Goose、Postman、MCPJam、Archestra.AI 等**有图形界面的 host** 支持,机制是工具返回结果携带一个 `ui://` HTML 资源(`mimeType: text/html;profile=mcp-app`),host 在 sandboxed iframe 里就地渲染,面板可以通过 postMessage 回调 host 触发新的 MCP tool 调用。

arcgentic 的核心运行场景(按 README)是 Codex CLI / Claude Code **终端**会话里的自动化角色派发——纯 TTY 没有渲染 iframe 的通道。所以本次面板的目标 host 明确限定为**有图形界面的富客户端**(claude.ai、Claude Desktop、VS Code 类 host,以及本次会话所在的这类环境);工具本身仍然对终端 host 可用,只是退化成纯文本(MCP Apps 规范允许 UI 资源和纯文本内容并存,host 不支持 UI 时用文本)。

arcgentic 目前**没有任何 MCP server 组件**——`skills/` 里的 markdown skill 只是指导 agent 去 shell 调用 `arcgentic` CLI(`toolkit/src/arcgentic/cli.py`),不暴露 MCP tool。这次要新增的 MCP server 是全新基础设施,不是在已有代码上加渲染。

## 2. 目标(v1)

一个只读 MCP tool + 面板内三种纯 UI 层交互(不需要额外的写权限 tool):

- 展示:round id、`current_round.state`、五角色派发进度(orchestrator/planner/developer/test/auditor 里谁 active/pending/done,读 `project.arcgentic_v2.role_sessions` + `next_role`)、最近一次 `audit_verdict`(outcome + fact_table_pass/total)。
- 交互一:"刷新" —— 用 MCP-UI 的 `tool` action 重新调用同一个只读 `round_status_panel` tool。
- 交互二:"派发下一角色" —— 用 MCP-UI 的 `prompt` action,把"请派发下一个角色"作为自然语言消息交回当前对话,由 orchestrator agent 按 `skills/arcgentic`/`codex-thread-orchestration` 里定义的正常流程去创建线程、调 CLI——面板本身不执行任何状态写操作。
- 交互三(用户明确要求):**客户端自动轮询** —— 面板内嵌 JS 用 `setInterval` 定期(默认 5 秒)用 `tool` action 自动重新拉取只读 tool,原地刷新内容,不需要人工点"刷新"。

## 3. 设计

### 3.1 组件

- `toolkit/src/arcgentic/mcp/server.py` —— 用官方 MCP Python SDK(`mcp` package,新增到 `toolkit/pyproject.toml` 的 `dependencies`)搭建的 stdio MCP server,注册一个 tool。
- `toolkit/src/arcgentic/mcp/panel.py` —— 纯函数 `render_status_panel_html(state: dict[str, object]) -> str`,输入 state.yaml 解析后的 dict,输出自包含 HTML 字符串(内联 CSS/JS,不发外部请求,和 Artifact 工具同样的沙箱约束)。不碰文件、不碰网络,方便单测。HTML 里的"派发下一角色"按钮直接内联 `prompt` action 的 postMessage 调用,不依赖服务端状态。
- `toolkit/src/arcgentic/mcp/tools.py` —— 一个只读 tool handler:
  - `round_status_panel()`:调用 `v2_session_orchestration.load_state_file` 读 `.agentic-rounds/state.yaml`(复用已有函数,不重新解析),调用 `render_status_panel_html`,包成 `ui://` 资源 + 纯文本 fallback(同一份数据的纯文本摘要)一起返回。state.yaml 不存在或解析失败时返回一个"无活跃 round / 状态文件损坏"的错误面板。

### 3.2 面板内的自动轮询(本轮新增)

面板 HTML 里的 `<script>` 用 `setInterval(..., 5000)` 周期性地向 host 发起同一个只读 tool 调用(MCP-UI 的 UI→host 消息机制,和"刷新"按钮走同一条通道,不是新协议能力),拿到新 HTML 后原地替换面板 DOM。两条防浪费规则:

- 用 Page Visibility API,面板不在前台(标签页/窗口失焦)时暂停轮询,重新可见时恢复。
- `current_round.state == "closed"` 时,面板渲染出来就不再插入轮询定时器——终态没有继续问的意义。

### 3.3 打包声明

在插件根目录新增 `.mcp.json`(参考已有插件的通用约定,`mcpServers.<name>.command`/`args`,`${CLAUDE_PLUGIN_ROOT}` 变量可用):

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

`arcgentic` 命令已经是 Python 包注册的 console script(`toolkit/pyproject.toml`:`arcgentic = "arcgentic.cli:main"`),`mcp-serve` 是本次要新增的 CLI 子命令(在 `cli.py` 里加一个 `subparsers.add_parser("mcp-serve")`,handler 启动 `toolkit/src/arcgentic/mcp/server.py` 的 stdio server)。复用现有发布渠道(pipx install arcgentic),不需要新的安装步骤。

### 3.4 错误处理

- 无 `.agentic-rounds/state.yaml`:面板显示"无活跃 round",不轮询(没有 round 就没有进度可看),"派发下一角色"按钮隐藏(没有 round 就没有下一角色的概念)。
- state.yaml 解析失败:面板显示原始解析错误,fail-closed,不轮询。
- round 已 `closed`:面板显示终态,"派发下一角色"按钮隐藏(prompt 发过去 agent 也只会说"当前已 closed",不如干脆不展示,减少误导)。

### 3.5 测试

- `render_status_panel_html` 是纯函数:用 dict fixture(和 `test_v2_session_orchestration.py` 已有模式一致)断言关键内容存在(round id、各角色状态、verdict outcome、"派发下一角色"按钮在 closed/无 round 时不出现),覆盖"正常/无 round/verdict 为空/closed"四种输入形态。
- tool handler:mock 掉文件 IO,断言正确调用了已有的 `load_state_file`,断言解析失败路径返回错误面板而不是抛出未捕获异常。
- 真实 MCP-UI host 里的端到端渲染(iframe 是否真的显示、轮询是否真的原地刷新、Page Visibility 暂停是否生效、`prompt` action 点击后是否真的把消息送回对话)**只能手动验证**,写进验收标准,不是自动化测试范围——这块本来就是"生态还不成熟"的高风险区,自动化测试给不出比人工验证更强的信心。

## 4. 验收标准

1. 在支持 MCP-UI 的 host(本会话所在环境,或 Claude Desktop)里调用 `round_status_panel`,面板正确渲染当前 round 的状态、角色进度、verdict。
2. 面板自动每 5 秒刷新一次;切到后台标签页后轮询暂停,切回来恢复;round 到 `closed` 后不再轮询。
3. 点"派发下一角色"把"请派发下一个角色"作为一条新消息发回当前对话(用 `prompt` action,不是 `tool` action),后续状态机推进仍然完全由 agent 走既有流程驱动,面板/MCP server 全程不做任何写操作。
4. 在不支持 MCP-UI 的 host 上调用同一个 tool,能拿到有意义的纯文本状态摘要,不报错、不返回空内容。
5. `toolkit/tests/unit/` 下新增的纯函数/handler 测试全部通过。
