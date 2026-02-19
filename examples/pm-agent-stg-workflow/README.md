---
title: PM Agent 运行 STG 工作流示例
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# PM Agent 运行 STG 工作流示例

本示例展示如何使用 PM Agent API 管理和执行 STG 部门的商业机会发现工作流。

---

## 📋 工作流概述

### STG 商业机会发现 5 层架构

```
Layer 1: Search Agent (事实采集)
   └─ 输出: 搜索信号数据
      关键词、趋势、量级、地理分布

Layer 2: Analysis Agents (分析层 - 并行)
   ├─ User Signal Agent         (谁在搜 & 为什么)
   ├─ Industry Structure Agent  (行业处在哪)
   └─ Supply/Competition Agent  (方案解决得如何)

Layer 3: Market Freeze (冻结层) 🔒
   └─ 输出: 冻结的市场信号
      关键词集、已接受假设、置信度

Layer 4: Business Opportunity (机会构建层)
   └─ 输出: 可验证的商业机会假设
      One-liner、目标用户、Why Now、差异化

Layer 5: Product Handoff (交付层)
   └─ 输出: 标准产品交付文档
      相信的、不知道的、实验建议
```

---

## 🚀 快速开始

### 1. 运行示例

```bash
cd examples/pm-agent-stg-workflow
python run_stg_with_pm_agent.py
```

### 2. 预期输出

```
🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯
  PM Agent 运行 STG 工作流示例
🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯🎯

======================================================================
  🚀 PM Agent: STG 商业机会发现工作流
======================================================================

📁 项目目录: .../spec-global/departments/stg
🤖 PM Agent 角色: 查看 → 决策 → 执行
⚠️  注意: 本示例使用自动模式，PM Agent 会自动做决策

▶ 第 1 轮决策
----------------------------------------------------------------------
📊 工作流状态:
  名称: 商业机会发现工作流
  进度: 0/7 (0.0%)
  失败: 0
  就绪: 1 个步骤

💡 PM Agent 决策:
   执行步骤: search_signals
   描述: 采集市场搜索信号
   依赖: []

⏳ 正在执行...
✅ 步骤完成: search_signals
   耗时: 4.52 秒
   引擎: llm
   输出文件: 1 个

▶ 第 2 轮决策
----------------------------------------------------------------------
...
```

---

## 📖 PM Agent 决策流程

### 1️⃣ 查看状态

```python
state = api_get_state(project_dir)
```

**返回信息**:
- `workflow_name` - 工作流名称
- `total_steps` - 总步骤数
- `completed_steps` - 已完成步骤
- `ready_steps` - 当前可执行的步骤
- `failed_steps` - 失败的步骤

### 2️⃣ 分析情况

```python
analysis = pm_agent.analyze_state(state)
```

**PM Agent 分析维度**:
- ✅ 进度百分比
- ✅ 是否有失败步骤
- ✅ 是否有待审批门控
- ✅ 有多少就绪步骤

### 3️⃣ 做出决策

**决策类型**:

| 情况 | 决策 | 说明 |
|------|------|------|
| 有失败步骤 | `handle_failure` | 处理失败 |
| 有待审批门控 | `check_gates` | 需要人工审批 |
| 有就绪步骤 | `execute_next` | 执行下一步 |
| 无就绪步骤 | `wait` | 等待或结束 |

### 4️⃣ 执行步骤

```python
result = api_run_step(project_dir, step_id)
```

**处理结果**:
- `completed` - 成功，继续下一步
- `failed` - 失败，决定是否重试或跳过
- `timeout` - 超时，可能需要重试

---

## 🔧 自定义 PM Agent 行为

### 修改决策逻辑

```python
class MyPMAgent(STGWorkflowPM):
    def analyze_state(self, state: dict) -> dict:
        analysis = super().analyze_state(state)

        # 添加自定义决策逻辑
        if analysis["progress_pct"] > 50:
            analysis["recommendation"] = "be_careful"
            analysis["reason"] = "已过半，需要更谨慎"

        return analysis
```

### 添加人工确认

```python
async def run_workflow_interactive(self):
    # ... 获取状态和分析

    # 在执行前等待确认
    print(f"\n💡 建议: {analysis['recommendation']}")
    confirm = input("是否执行? (y/n): ")

    if confirm.lower() == 'y':
        result = api_run_step(self.project_dir, step_id)
```

### 添加重试逻辑

```python
async def execute_with_retry(self, step_id: str, max_retries: int = 3):
    for attempt in range(max_retries):
        result = api_run_step(self.project_dir, step_id)

        if result["status"] == "completed":
            return result

        print(f"⚠️  第 {attempt + 1} 次尝试失败")

    print(f"❌ {max_retries} 次尝试后仍然失败")
    return result
```

---

## 📊 实际应用场景

### 场景 1: 自动化执行

```python
# 完全自动运行，无需人工干预
await pm_agent.run_workflow_interactive()
```

**适用**:
- 测试环境
- CI/CD 流程
- 批量处理

### 场景 2: 半自动执行

```python
# PM Agent 提供建议，人工确认
ready_steps = api_list_ready_steps(project_dir)
print(f"就绪步骤: {ready_steps}")

choice = input("选择要执行的步骤 (输入编号): ")
if choice.isdigit():
    step_id = ready_steps[int(choice)]['id']
    result = api_run_step(project_dir, step_id)
```

**适用**:
- 生产环境
- 重要决策点
- 需要审计的场景

### 场景 3: 仅监控状态

```python
# PM Agent 只查看状态，不执行
state = api_get_state(project_dir)
print(f"当前进度: {state['completed_steps']}/{state['total_steps']}")

ready_steps = api_list_ready_steps(project_dir)
print(f"可执行步骤: {[s['id'] for s in ready_steps]}")
```

**适用**:
- 状态监控面板
- 进度报告
- 调试和诊断

---

## 🎯 PM Agent 最佳实践

### ✅ DO - 应该做的

1. **始终先查看状态**
   ```python
   state = api_get_state(project_dir)
   ```

2. **基于真实数据做决策**
   ```python
   ready_steps = api_list_ready_steps(project_dir)
   if ready_steps:
       # 决策逻辑
   ```

3. **记录决策历史**
   ```python
   self.log_decision(step_id, action, reason)
   ```

4. **处理失败情况**
   ```python
   if result["status"] == "failed":
       # 失败处理逻辑
   ```

### ❌ DON'T - 不应该做的

1. **不要假设系统状态**
   ```python
   # ❌ 错误
   if workflow_is_done():  # 不存在这个函数

   # ✅ 正确
   state = api_get_state(project_dir)
   if state['completed_steps'] == state['total_steps']:
   ```

2. **不要直接修改文件**
   ```python
   # ❌ 错误
   with open('output.txt', 'w') as f:
       f.write(data)

   # ✅ 正确
   # 通过 Orchestrator 执行步骤，让系统处理
   result = api_run_step(project_dir, step_id)
   ```

3. **不要忽略错误**
   ```python
   # ❌ 错误
   result = api_run_step(project_dir, step_id)
   # 继续执行，不管结果

   # ✅ 正确
   if result["status"] == "completed":
       # 继续执行
   else:
       # 处理错误
   ```

---

## 🔍 故障排查

### 问题 1: workflow.yaml 未找到

**错误**:
```
Error: workflow.yaml not found
```

**解决**:
```bash
# 确认在正确的目录
cd spec-global/departments/stg
ls workflow.yaml  # 应该存在
```

### 问题 2: 状态未初始化

**错误**:
```
Error: Workflow not initialized. Run 'init' first.
```

**解决**:
```bash
# 初始化工作流状态
python -m flowcore.orchestrator.cli init
```

### 问题 3: 步骤执行失败

**错误**:
```
Step failed: Connection error
```

**解决**:
```python
# 检查 LLM 服务是否运行
curl http://127.0.0.1:8045/v1/models

# 检查环境变量
echo $OPENAI_BASE_URL
echo $OPENAI_API_KEY
```

---

## 📚 相关文档

- **PM Agent 使用指南**: `docs/PM-AGENT-USER-GUIDE.md`
- **PM Agent 协议**: `docs/PM_AGENT_PROTOCOL.md`
- **API 参考**: `flowcore/api.py`
- **STG 部门文档**: `spec-global/departments/stg/README.md`

---

## 🚀 下一步

1. ✅ 运行本示例
2. 📖 阅读 PM Agent 协议文档
3. 🔧 尝试修改决策逻辑
4. 🎯 创建自己的工作流
5. 🤖 集成到 Claude Code

---

**祝你使用愉快！** 🎉
