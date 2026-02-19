# Gate Review Slash Command 故障排除

## 问题
重启 Claude Code 后，`/gate-review` 显示 "Unknown skill: gate-review"

## 诊断步骤

### 1. 验证工具文件存在

```bash
cd E:\ai\LEE
ls .claude/tools/
```

**预期输出**:
```
gate-approval.json
gate-review.json       # ← 这个文件必须存在
pm-workflow.json
README.md
```

### 2. 验证 Python 模块可以导入

```bash
cd E:\ai\LEE
python -c "from flowcore.api import gate_review_handler; print('✅ OK')"
```

**预期输出**: `✅ OK`

### 3. 验证 handler 功能正常

```bash
cd E:\ai\LEE
python -c "
from flowcore.api import gate_review_handler
result = gate_review_handler(action='list', project_dir='.')
print(result['markdown'])
"
```

**预期输出**: 显示 pending gates 列表

### 4. 检查 Claude Code 配置

在 Claude Code 中执行：
```
@example
测试 gate_review 工具是否可用
```

或者直接调用：
```python
gate_review(action="list", project_dir=".")
```

## 解决方案

### 方案 A: 硬重启 Claude Code

1. **完全关闭** Claude Code (不是仅仅重启)
2. **等待 10 秒**
3. **重新打开** Claude Code
4. **测试**: `/gate-review`

### 方案 B: 检查 Python Path

确保 LEE 项目在 Python path 中：

```bash
cd E:\ai\LEE
python -c "
import sys
print('Python path:')
for p in sys.path:
    print(f'  {p}')
"
```

### 方案 C: 使用 Python API 代替

如果 slash command 仍不工作，可以直接在 Claude Code 中使用 Python API：

```python
# 列出待审批 gates
from flowcore.api import gate_review_handler
result = gate_review_handler(action='list', project_dir='.')
print(result['markdown'])
```

```python
# 查看特定 gate
result = gate_review_handler(action='show', gate_id='freeze_market_signals', project_dir='.')
print(result['markdown'])
```

```python
# 审批 gate
result = gate_review_handler(
    action='decide',
    gate_id='freeze_market_signals',
    decision='approve',
    comment='通过',
    checklist=[
        {'item': '分析一致性', 'ok': True, 'note': ''},
        {'item': '置信度达标', 'ok': True, 'note': '>70%'},
        {'item': '可验证性', 'ok': True, 'note': '可验证'}
    ],
    project_dir='.'
)
print(result['markdown'])
```

## 工具配置文件位置

```
E:\ai\LEE\.claude\tools\gate-review.json
```

**配置内容**:
```json
{
  "name": "gate_review",
  "description": "Gate Review - List pending gates, show details with upstream analysis...",
  "handler": "flowcore.api:gate_review_handler",
  ...
}
```

## 当前状态

| 项目 | 状态 |
|------|------|
| 工具文件 | ✅ `.claude/tools/gate-review.json` |
| Handler 函数 | ✅ `flowcore.api:gate_review_handler` |
| Python 导入 | ✅ 可以正常导入 |
| 功能测试 | ✅ 正常工作 |

**建议**: 先使用 Python API (`gate_review_handler`)，如果需要 slash command，尝试硬重启 Claude Code。
