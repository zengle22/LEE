# LEE Orchestrator 使用手册

**版本**: v1.0
**更新日期**: 2026-01-25

---

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [项目初始化](#项目初始化)
- [工作流命令](#工作流命令)
- [人工门禁](#人工门禁)
- [目录结构管理](#目录结构管理)
- [命令参考](#命令参考)

---

## 概述

LEE Orchestrator 是一个通用 AI 工作流编排器，支持：

- **多步骤工作流执行** - 顺序、并行、循环执行
- **人工门禁** - 在关键节点需要人工批准
- **Token 管理** - 步骤执行令牌系统
- **Agent 集成** - 支持多种 LLM Agent
- **状态追踪** - 完整的执行状态和事件日志
- **项目结构管理** - 固定的目录结构，防止目录漂移

---

## 快速开始

### 1. 初始化工作流

```bash
# 使用默认模板初始化
python -m flowcore.orchestrator.cli init . --workflow workflow.yaml

# 初始化并指定项目名称
python -m flowcore.orchestrator.cli init . --workflow workflow.yaml --project-name my-project
```

### 2. 查看状态

```bash
python -m flowcore.orchestrator.cli status .
```

### 3. 执行下一步

```bash
# 自动选择并执行下一个就绪的步骤
python -m flowcore.orchestrator.cli next .
```

### 4. 启动特定步骤

```bash
# 启动指定步骤
python -m flowcore.orchestrator.cli start . step_id

# 启动并注入 Agent context
python -m flowcore.orchestrator.cli start . step_id --inject-context
```

### 5. 完成步骤

```bash
# 完成步骤并验证输出
python -m flowcore.orchestrator.cli complete . step_id --outputs output_file.yaml
python -m flowcore.orchestrator.cli validate . step_id
```

---

## 项目初始化

### 初始化目录结构

```bash
# 初始化项目目录结构（交互式）
python -m flowcore.orchestrator.cli init-structure .

# 指定项目名称
python -m flowcore.orchestrator.cli init-structure . --project-name nutrition-app

# 强制重新初始化
python -m flowcore.orchestrator.cli init-structure . --project-name nutrition-app --force
```

### 目录结构

初始化后会生成以下结构：

```
project-root/
├── .project/              # 项目配置
│   ├── dirs.yaml          # 目录结构配置
│   └── schema/            # 配置 Schema
├── .workflow/             # 工作流状态
│   ├── state.yaml         # 工作流状态文件
│   ├── workspace/         # Agent 工作区
│   ├── gates/             # 门禁状态
│   ├── events/            # 事件日志
│   └── cache/             # 缓存
└── {project-name}/       # 项目内容目录（可选）
    ├── contracts/         # 冻结的分析结果
    ├── docs/              # 生成的文档
    ├── specs/             # 生成的规格
    ├── src/               # 生成的源代码
    ├── outputs/           # 中间输出
    └── tests/             # 生成的测试
```

### 检查目录结构

```bash
python -m flowcore.orchestrator.cli check-structure .
```

---

## 工作流命令

### init - 初始化工作流

```bash
python -m flowcore.orchestrator.cli init . --workflow workflow.yaml [options]

选项:
  --workflow/-w     工作流定义文件 (必需)
  --template/-t     工作流模板文件
  --config/-c       Phase 配置文件
  --skip-structure-init  跳过目录结构初始化
  --force-structure       强制重新初始化目录结构
```

### status - 查看状态

```bash
python -m flowcore.orchestrator.cli status .
```

输出包含：
- Run ID 和状态
- 步骤进度统计
- 门禁状态
- 就绪步骤列表
- 下一步行动建议

### start - 启动步骤

```bash
python -m flowcore.orchestrator.cli start . step_id [options]

选项:
  --agent              指定 Agent ID
  --inject-context     注入 Agent context (默认启用)
  --no-agent           跳过 Agent 加载
  --injector          Context 注入器 (claude_code/auto)
  --context-file      自定义 context 输出路径
```

### next - 执行下一步

```bash
python -m flowcore.orchestrator.cli next .
```

自动选择并执行下一个就绪的步骤。

### complete - 完成步骤

```bash
python -m flowcore.orchestrator.cli complete . step_id --outputs file1.yaml,file2.yaml
```

### validate - 验证输出

```bash
python -m flowcore.orchestrator.cli validate . step_id
```

验证步骤的必需输出是否都已生成。

---

## 人工门禁

### 查看待审批门禁

```bash
python -m flowcore.orchestrator.cli status .
```

在 "Pending Gates" 部分会显示待审批的门禁。

### 批准门禁

```bash
python -m flowcore.orchestrator.cli approve . gate_id --approver your_name --comment "批准原因"
```

### 拒绝门禁

```bash
python -m flowcore.orchestrator.cli reject . gate_id --approver your_name --reason "拒绝原因"
```

### 门禁规则

工作流中可以定义门禁规则：

```yaml
gates:
  approval_criteria:
    - label: 分析一致性
      criteria: 三个分析层输出无明显矛盾
      required: true
    - label: 置信度达标
      criteria: 综合置信度 ≥ 50
      required: true
  rejection_criteria:
    - 分析层输出存在重大矛盾
    - 置信度过低（<30）
```

---

## 目录结构管理

### 创建项目结构

详见 [项目初始化](#项目初始化) 章节。

### 获取输出路径

使用 Python API 获取正确的输出路径：

```python
from flowcore.orchestrator.project_config import get_project_structure

config = get_project_structure(Path('.'))

# 获取合约输出路径
contract_path = config.get_output_path(
    'contract',
    layer='market_signals_freeze',
    version='v1',
    name='freeze'
)
# → {project-name}/contracts/market_signals_freeze/v1/freeze.yaml

# 获取文档输出路径
doc_path = config.get_output_path(
    'doc',
    category='reports',
    title='Test Report'
)
# → {project-name}/docs/reports/2026-01-25-test-report.md

# 获取源代码路径
source_path = config.get_output_path(
    'source',
    module='auth',
    name='service',
    ext='py'
)
# → {project-name}/src/auth/service.py
```

---

## 命令参考

### 工作流管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `init` | 初始化工作流 | `init . --workflow workflow.yaml` |
| `status` | 查看状态 | `status .` |
| `next` | 执行下一步 | `next .` |
| `start` | 启动步骤 | `start . step_id` |
| `complete` | 完成步骤 | `complete . step_id --outputs file.yaml` |
| `validate` | 验证输出 | `validate . step_id` |

### 门禁管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `approve` | 批准门禁 | `approve . gate_id --approver name --comment "通过"` |
| `reject` | 拒绝门禁 | `reject . gate_id --approver name --reason "原因"` |

### 项目结构管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `init-structure` | 初始化目录结构 | `init-structure . --project-name my-app` |
| `check-structure` | 检查目录结构 | `check-structure .` |

### Token 管理

| 命令 | 说明 | 示例 |
|------|------|------|
| `token` | 查看 Token | `token . step_id` |
| `check` | 检查 Token | `check . --token TOKEN_ID` |

### 日志和追踪

| 命令 | 说明 | 示例 |
|------|------|------|
| `log` | 查看事件日志 | `log . --step step_id --limit 10` |
| `trace` | 查看执行追踪 | `trace . --format markdown` |
| `detailed-log` | 生成详细日志 | `detailed-log . --session SESSION_ID` |

### 其他命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `reset` | 重置步骤 | `reset . step_id --reason "重试"` |
| `export` | 导出审计报告 | `export . --format json` |
| `validate-project` | 验证项目配置 | `validate-project .` |
| `context` | 管理 Agent context | `context . --clear` |

---

## Python API

### 初始化项目结构

```python
from flowcore.orchestrator.project_config import init_project_structure
from pathlib import Path

# 初始化项目结构
config = init_project_structure(
    project_dir=Path('.'),
    project_name='my-app',
    force=False
)

print(f"Project name: {config.project_name}")
print(f"Content directory: {config.project_content_dir}")
```

### 获取输出路径

```python
from flowcore.orchestrator.project_config import get_project_structure

config = get_project_structure(Path('.'))

# 获取各种类型的输出路径
contract_path = config.get_output_path('contract', layer='market', version='v1', name='freeze')
doc_path = config.get_output_path('doc', category='reports', title='Analysis')
source_path = config.get_output_path('source', module='api', name='controller', ext='py')
test_path = config.get_output_path('test', type='unit', name='user', ext='py')
```

### 验证输出路径

```python
from flowcore.orchestrator.project_config import get_project_structure

config = get_project_structure(Path('.'))

# 验证输出路径是否符合规范
is_valid, error = config.validate_output_path(
    'my-app/contracts/report.yaml',
    output_type='contract'
)

if not is_valid:
    print(f"Invalid path: {error}")
```

---

## 高级用法

### 使用统一 Engine 接口

```bash
# 使用统一 Engine 接口执行步骤
python -m flowcore.orchestrator.cli run-engine . step_id
```

### 循环执行

```bash
# 开始循环
python -m flowcore.orchestrator.cli loop-start . bug_fix_cycle --iterations 3

# 完成循环迭代
python -m flowcore.orchestrator.cli loop-complete . bug_fix_cycle --iteration 1

# 回退到之前步骤
python -m flowcore.orchestrator.cli loop-back . current_step target_step --reason "Fix approach"
```

### 外部等待

```bash
# 开始等待外部事件
python -m flowcore.orchestrator.cli wait . step_id --event fix_ready --timeout 48h

# 解决外部等待
python -m flowcore.orchestrator.cli resolve . wait_id --resolver developer --data '{"status": "ready"}'
```

---

## 故障排除

### 常见问题

**Q: 提示 "Project structure not initialized"**
A: 运行 `init-structure .` 初始化项目目录结构

**Q: 上下文传递为空**
A: 检查上游步骤是否已完成，确保 freeze gate 已批准并生成冻结合约

**Q: Agent context 注入失败**
A: 检查 `agent_context.py` 模块是否存在，或使用 `--no-agent` 跳过

**Q: API 返回 429 错误**
A: 等待一段时间后重试，或切换到不同的 API Provider

### 调试命令

```bash
# 查看详细状态
python -m flowcore.orchestrator.cli status .

# 查看事件日志
python -m flowcore.orchestrator.cli log . --step step_id

# 查看执行追踪
python -m flowcore.orchestrator.cli trace . --format markdown

# 生成详细执行日志
python -m flowcore.orchestrator.cli detailed-log . --session SESSION_ID
```

---

## 相关文档

- [PM Agent 协议](./PM_AGENT_PROTOCOL.md)
- [Gate Assistant 协议](./GATE_ASSISTANT_PROTOCOL.md)
- [项目结构配置说明](../.project/README.md)
- [工作流状态管理](../.workflow/README.md)
