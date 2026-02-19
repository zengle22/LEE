---
title: LLM Platform Integration Guide
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# LLM Platform Integration Guide

本指南说明如何将 Workflow Orchestrator 集成到不同的 LLM 平台。

## 核心集成模式

```
┌─────────────────────────────────────────────────────────────────────┐
│                        集成架构                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    LLM Agent Context                         │   │
│  │  ┌─────────────────────────────────────────────────────┐    │   │
│  │  │ System Prompt + Current State + Token               │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              │ Tool Call                            │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Tool Interceptor                          │   │
│  │  1. Extract token from context                               │   │
│  │  2. Validate token with orchestrator                         │   │
│  │  3. Check tool permissions                                   │   │
│  │  4. Allow or Block                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Orchestrator CLI                          │   │
│  │  - State management                                          │   │
│  │  - Token validation                                          │   │
│  │  - Event logging                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 1. Claude Code 集成

### 方式 A: CLAUDE.md 指令 (推荐)

在 `CLAUDE.md` 中添加以下规则：

```markdown
## 工作流执行规则 (强制)

在执行任何开发任务前，你必须严格遵守以下流程：

### 1. 检查当前状态
执行任何操作前，先运行：
\`\`\`bash
python -m orchestrator status .
\`\`\`

如果显示 **BLOCKED** 或有 **Pending Gates**，则：
- 不要执行任何写操作
- 告知用户需要审批
- 提供审批命令

### 2. 获取步骤令牌
在开始一个步骤前，获取令牌：
\`\`\`bash
python -m orchestrator start . <step_id> --agent claude
\`\`\`

将返回的 `WORKFLOW_TOKEN:xxx` 记录下来，后续操作需要携带。

### 3. 完成步骤
完成后声明产物：
\`\`\`bash
python -m orchestrator complete . <step_id> --outputs file1.go,file2.go
python -m orchestrator validate . <step_id>
\`\`\`

### 4. 门禁处理
如果步骤需要人类审批，告知用户：
\`\`\`
⏳ 步骤 <step_id> 需要人类审批
审批命令: python -m orchestrator approve . <gate_id> --approver <name>
\`\`\`

### 违规处理
- 如果尝试在 BLOCKED 状态下执行写操作 → 立即停止并报告
- 如果令牌无效或过期 → 重新获取令牌
- 如果产物验证失败 → 修复问题后重新验证

### 当前状态注入
在每次对话开始时，自动读取并展示：
\`\`\`bash
python -m orchestrator status .
\`\`\`
```

### 方式 B: Claude Code Hooks

如果 Claude Code 支持 hooks，可以配置：

```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": {
      "Edit|Write|Bash": "python -m orchestrator check . --token $WORKFLOW_TOKEN --tool $TOOL_NAME"
    },
    "PostToolUse": {
      "Edit|Write": "python -m orchestrator log-tool . $TOOL_NAME $WORKFLOW_TOKEN"
    }
  }
}
```

## 2. OpenAI Codex 集成

### Codex Constitution 方式

在 `codex-constitution.yaml` 中配置：

```yaml
# codex-constitution.yaml
version: 1.0

rules:
  - name: workflow_check
    trigger: before_any_action
    action: |
      Run: python -m orchestrator status .
      If blocked, refuse to proceed.

  - name: require_token
    trigger: before_write
    action: |
      Validate token: python -m orchestrator check . --token $TOKEN
      If invalid, request new token.

  - name: complete_step
    trigger: after_step_done
    action: |
      Complete: python -m orchestrator complete . $STEP_ID
      Validate: python -m orchestrator validate . $STEP_ID

hooks:
  pre_execute: "python -m orchestrator check . --token $STEP_TOKEN || exit 1"
  post_execute: "python -m orchestrator log-event . tool_executed"
```

### Codex CLI 集成脚本

```bash
#!/bin/bash
# codex-workflow-wrapper.sh

# 检查状态
status=$(python -m orchestrator status . --json 2>/dev/null)
if echo "$status" | grep -q '"run_state": "paused"'; then
    echo "ERROR: Workflow is paused. Waiting for gate approval."
    exit 1
fi

# 检查令牌
if [ -n "$WORKFLOW_TOKEN" ]; then
    python -m orchestrator check . --token "$WORKFLOW_TOKEN" || exit 1
fi

# 执行 codex
codex "$@"
```

## 3. Google Gemini 集成

### System Instruction 注入

```python
# gemini_orchestrator_adapter.py

import subprocess
import json

def get_workflow_context(project_dir: str) -> str:
    """生成注入到 Gemini system instruction 的上下文"""

    # 获取状态
    result = subprocess.run(
        ["python", "-m", "orchestrator", "status", project_dir, "--json"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        return "No active workflow."

    state = json.loads(result.stdout)

    context = f"""
## Current Workflow State

- Run ID: {state['run_id']}
- State: {state['run_state']}
- Current Step: {state.get('current_step', 'None')}

### Pending Gates (BLOCKING)
{chr(10).join(f"- {g}" for g in state.get('pending_gates', [])) or 'None'}

### Ready Steps
{chr(10).join(f"- {s}" for s in state.get('ready_steps', [])) or 'None'}

## Rules
1. If state is 'paused', do NOT perform any write operations
2. Before starting a step, run: python -m orchestrator start . <step_id>
3. After completing, run: python -m orchestrator complete . <step_id>
4. If a gate is pending, inform the user and provide approval command

## Active Token
{state.get('current_token', 'No active token')}
"""
    return context


def create_gemini_session(project_dir: str):
    """创建带有 workflow 上下文的 Gemini 会话"""
    import google.generativeai as genai

    workflow_context = get_workflow_context(project_dir)

    model = genai.GenerativeModel(
        'gemini-pro',
        system_instruction=f"""
You are a development assistant working within a workflow-controlled environment.

{workflow_context}

IMPORTANT: You must follow the workflow rules strictly.
Do not attempt to bypass gates or skip steps.
"""
    )

    return model.start_chat()
```

### Gemini Function Calling 守卫

```python
# gemini_tool_guard.py

def guarded_function_call(func_name: str, args: dict, token: str):
    """带守卫的函数调用"""

    # 验证令牌
    result = subprocess.run(
        ["python", "-m", "orchestrator", "check", ".", "--token", token, "--tool", func_name],
        capture_output=True
    )

    if result.returncode != 0:
        raise PermissionError(f"Tool {func_name} blocked: {result.stderr}")

    # 执行函数
    return execute_function(func_name, args)
```

## 4. 通用集成模式

### 状态注入模式

任何 LLM 都可以通过以下方式集成：

```python
def inject_workflow_state(system_prompt: str, project_dir: str) -> str:
    """将工作流状态注入到系统提示词"""

    # 运行 orchestrator status
    result = subprocess.run(
        ["python", "-m", "orchestrator", "status", project_dir],
        capture_output=True, text=True
    )

    state_info = result.stdout if result.returncode == 0 else "No workflow state"

    return f"""
{system_prompt}

---
## Workflow State (Auto-injected)
{state_info}

## Workflow Rules
- Check state before any action
- Obtain token before starting step
- Validate outputs after completion
- Wait for gate approval when blocked
---
"""
```

### Pre/Post Hook 模式

```python
class WorkflowHooks:
    """工作流钩子"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def pre_action(self, action_type: str, token: str = None) -> bool:
        """操作前检查"""
        # 检查状态
        result = subprocess.run(
            ["python", "-m", "orchestrator", "status", self.project_dir, "--json"],
            capture_output=True, text=True
        )

        state = json.loads(result.stdout) if result.returncode == 0 else {}

        # 如果暂停且是写操作，拒绝
        if state.get("run_state") == "paused" and action_type in ["write", "execute"]:
            return False

        # 验证令牌
        if token:
            check = subprocess.run(
                ["python", "-m", "orchestrator", "check", self.project_dir, "--token", token],
                capture_output=True
            )
            return check.returncode == 0

        return True

    def post_action(self, action_type: str, outputs: list = None):
        """操作后记录"""
        subprocess.run([
            "python", "-m", "orchestrator", "log-event", self.project_dir,
            "tool_executed", "--data", json.dumps({"type": action_type, "outputs": outputs})
        ])
```

## 5. 能力隔离实现

### 工具权限矩阵

```yaml
# tool_permissions.yaml
permissions:
  read:
    - Read
    - Glob
    - Grep
    - WebFetch
    - WebSearch
    requires_token: false  # 读操作不需要令牌

  write:
    - Write
    - Edit
    - NotebookEdit
    requires_token: true
    requires_step: true  # 需要当前步骤上下文

  execute:
    - Bash
    - Task
    requires_token: true

  deploy:
    - Bash:kubectl
    - Bash:docker
    - Bash:deploy
    requires_token: true
    requires_approval: true  # 需要门禁审批

  commit:
    - Bash:git commit
    - Bash:git push
    requires_token: true
    requires_approval: true
```

### 实现示例

```python
class CapabilityGuard:
    """能力守卫 - 控制 LLM 可调用的工具"""

    PERMISSIONS = {
        "read": ["Read", "Glob", "Grep"],
        "write": ["Write", "Edit"],
        "execute": ["Bash"],
        "deploy": ["Bash:kubectl", "Bash:docker"],
        "commit": ["Bash:git"]
    }

    def __init__(self, token_manager, state_machine):
        self.token_mgr = token_manager
        self.state_machine = state_machine

    def can_use_tool(self, tool_name: str, token_id: str = None) -> tuple[bool, str]:
        """检查是否可以使用工具"""

        # 确定需要的权限
        required_perm = self._get_required_permission(tool_name)

        # 读操作通常不需要令牌
        if required_perm == "read":
            return True, "read allowed"

        # 其他操作需要令牌
        if not token_id:
            return False, "token required"

        # 验证令牌
        valid, reason = self.token_mgr.validate_token(token_id, required_permission=required_perm)
        if not valid:
            return False, reason

        # deploy/commit 需要审批
        if required_perm in ["deploy", "commit"]:
            token = self.token_mgr.load_token(token_id)
            if token.requires_approval:
                has_approval, _ = self.state_machine.has_valid_approval(token.step_id)
                if not has_approval:
                    return False, "approval required for this operation"

        return True, "allowed"

    def _get_required_permission(self, tool_name: str) -> str:
        for perm, tools in self.PERMISSIONS.items():
            for t in tools:
                if tool_name.startswith(t):
                    return perm
        return "read"
```

## 6. 迁移检查清单

将 Orchestrator 集成到新平台时，确保：

- [ ] 状态文件可被 LLM 环境读取 (`.workflow/state.yaml`)
- [ ] CLI 可在 LLM 环境中执行 (`python -m orchestrator`)
- [ ] System prompt 包含工作流规则
- [ ] 写操作前检查令牌有效性
- [ ] 门禁阻断时拒绝执行
- [ ] 操作后更新状态和日志
- [ ] 产物验证后才能进入下一步

## 7. 调试与故障排除

### 常见问题

**Q: LLM 忽略了工作流规则**
A: 加强 system prompt 中的强制性语言，使用 "MUST"、"NEVER"、"FAIL if"

**Q: 令牌总是过期**
A: 调整 `DEFAULT_VALIDITY_HOURS` 或在步骤开始时刷新

**Q: 状态文件不同步**
A: 确保所有写操作后都调用 `orchestrator complete`

### 调试命令

```bash
# 查看详细状态
python -m orchestrator status . --verbose

# 查看事件日志
python -m orchestrator log . --limit 20

# 导出审计报告
python -m orchestrator export . --format json

# 验证令牌
python -m orchestrator check . --token TKN-xxx --tool Write
```
