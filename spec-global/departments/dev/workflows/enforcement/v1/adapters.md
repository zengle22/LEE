# CLI Adapters for Workflow Enforcement

本文档描述如何将 `workflow-guard` 工具集成到不同的 AI Agent 执行环境中。

## 架构概述

```
┌─────────────────────────────────────────────────────────────────┐
│                    workflow-guard (核心工具)                      │
│                                                                   │
│  • CLI 无关的 Python 脚本                                         │
│  • 读写 .workflow/state.yaml 和 execution-state.yaml             │
│  • 验证产出物、管理门禁、检查依赖                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ Claude Code │  │   Cursor    │  │   Codex     │
    │   Adapter   │  │   Adapter   │  │   Adapter   │
    └─────────────┘  └─────────────┘  └─────────────┘
              │               │               │
              ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │   Hooks     │  │  Settings   │  │    YAML     │
    │ settings.json│  │ .cursor/   │  │  codex.yaml │
    └─────────────┘  └─────────────┘  └─────────────┘
```

## 1. Claude Code 适配

### 方式 A: Hooks 配置

在项目根目录创建 `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|Bash",
        "command": "python scripts/workflow-guard.py check-state --phase ."
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "python scripts/workflow-guard.py verify --phase ."
      }
    ]
  }
}
```

### 方式 B: CLAUDE.md 指令

在 `CLAUDE.md` 中添加强制检查指令:

```markdown
## 工作流强制执行

在执行任何步骤前，必须：

1. **检查执行状态**
   ```bash
   python scripts/workflow-guard.py check-state --phase {phase_dir}
   ```
   如果返回非 0 退出码，停止执行并报告阻断原因。

2. **开始步骤前**
   ```bash
   python scripts/workflow-guard.py check-start --step {step_id} --phase {phase_dir}
   ```

3. **完成步骤后**
   ```bash
   python scripts/workflow-guard.py complete --step {step_id} --phase {phase_dir}
   ```
   这会自动验证产出物是否存在。

4. **遇到人类门禁时**
   停止执行，提示用户运行:
   ```bash
   python scripts/workflow-guard.py approve {gate_id} --phase {phase_dir}
   ```
```

### 方式 C: Agent 规范集成

在 Agent YAML 规范中添加 workflow 检查:

```yaml
# agent.yaml
execution:
  workflow_aware: true

  pre_execution:
    - command: "python scripts/workflow-guard.py check-state --phase {phase_dir}"
      on_failure: abort

  post_execution:
    - command: "python scripts/workflow-guard.py verify --phase {phase_dir}"
      on_failure: warn
```

## 2. Cursor 适配

### .cursor/settings.json

```json
{
  "workspaceRules": {
    "onSave": {
      "command": "python scripts/workflow-guard.py verify --phase ."
    },
    "beforeEdit": {
      "command": "python scripts/workflow-guard.py check-state --phase ."
    }
  }
}
```

### .cursorrules

```
# Workflow Enforcement Rules

Before any code modification:
1. Run: python scripts/workflow-guard.py check-state --phase .
2. If blocked, stop and inform user about pending gates

After completing a workflow step:
1. Run: python scripts/workflow-guard.py complete --step {step_id} --phase .
2. Verify all outputs exist before marking complete
```

## 3. Codex 适配

### codex.yaml

```yaml
hooks:
  pre_edit:
    command: "python scripts/workflow-guard.py check-state --phase ."
    on_failure: block

  post_edit:
    command: "python scripts/workflow-guard.py verify --phase ."
    on_failure: warn

  pre_commit:
    command: "python scripts/workflow-guard.py verify --phase ."
    on_failure: block
```

## 4. 自定义 Agent 适配

### Python SDK 集成

```python
import subprocess
from pathlib import Path

class WorkflowAwareAgent:
    def __init__(self, phase_dir: str):
        self.phase_dir = Path(phase_dir)
        self.guard_script = "scripts/workflow-guard.py"

    def _run_guard(self, *args) -> tuple[int, str]:
        result = subprocess.run(
            ["python", self.guard_script] + list(args),
            capture_output=True,
            text=True,
            cwd=self.phase_dir
        )
        return result.returncode, result.stdout + result.stderr

    def check_can_proceed(self) -> bool:
        code, output = self._run_guard("check-state", "--phase", ".")
        if code != 0:
            print(f"Blocked: {output}")
            return False
        return True

    def start_step(self, step_id: str) -> bool:
        code, output = self._run_guard("check-start", "--step", step_id, "--phase", ".")
        if code != 0:
            print(f"Cannot start: {output}")
            return False
        return True

    def complete_step(self, step_id: str) -> bool:
        code, output = self._run_guard("complete", "--step", step_id, "--phase", ".")
        if code != 0:
            print(f"Validation failed: {output}")
            return False
        return True

    def execute_step(self, step_id: str, action):
        if not self.check_can_proceed():
            return False

        if not self.start_step(step_id):
            return False

        try:
            action()  # Execute the actual work
        except Exception as e:
            print(f"Step failed: {e}")
            return False

        return self.complete_step(step_id)
```

### TypeScript/Node.js 集成

```typescript
import { execSync } from 'child_process';
import { resolve } from 'path';

interface GuardResult {
  success: boolean;
  output: string;
}

class WorkflowGuard {
  constructor(private phaseDir: string) {}

  private run(...args: string[]): GuardResult {
    try {
      const output = execSync(
        `python scripts/workflow-guard.py ${args.join(' ')}`,
        { cwd: this.phaseDir, encoding: 'utf-8' }
      );
      return { success: true, output };
    } catch (error: any) {
      return { success: false, output: error.stdout + error.stderr };
    }
  }

  checkState(): boolean {
    const { success, output } = this.run('check-state', '--phase', '.');
    if (!success) console.log('Blocked:', output);
    return success;
  }

  checkStart(stepId: string): boolean {
    return this.run('check-start', '--step', stepId, '--phase', '.').success;
  }

  complete(stepId: string): boolean {
    return this.run('complete', '--step', stepId, '--phase', '.').success;
  }

  approve(gateId: string, notes?: string): boolean {
    const args = ['approve', gateId, '--phase', '.'];
    if (notes) args.push('--notes', notes);
    return this.run(...args).success;
  }
}
```

## 5. Git Hooks 集成

### pre-commit

```bash
#!/bin/bash
# .git/hooks/pre-commit

# 查找当前 phase 目录
PHASE_DIR=$(find . -path "*/dev/phase*/.workflow/state.yaml" -exec dirname {} \; | head -1 | xargs dirname)

if [ -n "$PHASE_DIR" ]; then
    python scripts/workflow-guard.py verify --phase "$PHASE_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ Workflow verification failed. Fix issues before committing."
        exit 1
    fi
fi

exit 0
```

### pre-push

```bash
#!/bin/bash
# .git/hooks/pre-push

# 确保所有必选步骤已完成
python scripts/workflow-guard.py verify --phase .
if [ $? -ne 0 ]; then
    echo "❌ Cannot push: workflow verification failed"
    exit 1
fi

exit 0
```

## 6. CI/CD 集成

### GitHub Actions

```yaml
# .github/workflows/workflow-guard.yml
name: Workflow Guard

on:
  pull_request:
    paths:
      - 'project/**/dev/phase*/**'

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pyyaml

      - name: Find phase directories
        id: phases
        run: |
          PHASES=$(find . -path "*/dev/phase*/.workflow/state.yaml" -exec dirname {} \; | xargs dirname | tr '\n' ' ')
          echo "phases=$PHASES" >> $GITHUB_OUTPUT

      - name: Verify workflows
        run: |
          for phase in ${{ steps.phases.outputs.phases }}; do
            echo "Verifying $phase..."
            python scripts/workflow-guard.py verify --phase "$phase"
          done
```

## 退出码参考

| 退出码 | 含义 | 处理方式 |
|--------|------|----------|
| 0 | 成功 | 继续执行 |
| 1 | 验证失败 | 修复产出物后重试 |
| 2 | 门禁阻断 | 等待人类审批 |
| 3 | 配置错误 | 检查状态文件 |

## 调试模式

设置环境变量启用详细输出:

```bash
export WORKFLOW_GUARD_DEBUG=1
python scripts/workflow-guard.py status --phase .
```
