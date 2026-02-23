# LEE 项目单元测试覆盖率报告

> **作者**: LEE Team
> **日期**: 2026-02-23
> **版本**: 1.0.0
> **分类**: 测试报告
> **标签**: 测试覆盖率, 测试统计, 质量保证


生成时间: 2026-02-23

## 总体覆盖率

```
总代码行数:  16,706 行
已覆盖行数:  7,014 行
总覆盖率:    58%
```

### 核心模块覆盖率

```
核心业务代码 (orchestrator + cli):  56%
所有代码 (包含 runtime):              58%
```

---

## 覆盖率分析

### ✅ 高覆盖率模块 (>80%)

| 模块 | 覆盖率 | 说明 |
|------|--------|------|
| `decision_engine.py` | 96% | 决策引擎核心 |
| `state_machine_executor.py` | 96% | 状态机执行器 |
| `failure_handler.py` | 97% | 失败处理器 |
| `langgraph_executor.py` | 94% | LangGraph 执行器 |
| `storage/models.py` | 100% | 数据模型 |
| `contract.py` | 98% | API 契约 |

### ⚠️ 中等覆盖率模块 (40%-80%)

| 模块 | 覆盖率 | 说明 |
|------|--------|------|
| `orchestrator.py` | 66% | 核心编排器 |
| `template_manager.py` | 65% | 模板管理 |
| `gates_cmd.py` | 40% | 门禁命令 |
| `claude_code_executor.py` | 49% | Claude 执行器 |
| `pm_agent_runtime.py` | 49% | PM Agent 运行时 |

### ❌ 低覆盖率模块 (<40%)

| 模块 | 覆盖率 | 说明 |
|------|--------|------|
| `condition_engine.py` | 0% | 条件引擎（新功能） |
| `human_approval.py` | 0% | 人工审批（新功能） |
| `tracing_integration.py` | 0% | 追踪集成 |
| `file_output_handler.py` | 10% | 文件输出处理 |
| `watch.py` | 11% | 监控命令 |
| `repo.py` | 13% | 仓库命令 |
| `chat.py` | 25% | Chat 命令 |

---

## 测试统计

```
总测试数:    233 个
通过:        808 个 (包含重试)
失败:        3 个
警告:        2 个
执行时间:    ~82 秒
```

### 失败测试

1. `test_llm_executor` - GLM 模型版本变化（glm-5 vs glm-4）
2. `test_chat_decision_engine_uses_direct_api` - Mock 对象缺少新方法
3. `test_chat_shows_gate_block_hint` - Mock 对象缺少新方法

---

## 本次改进的新增代码覆盖率

### Phase 1-3 新增功能

| 功能 | 文件 | 覆盖率 | 测试状态 |
|------|------|--------|----------|
| 超时包装器 | `pm_agent_runtime.py` | ~49% | ❌ 无专门测试 |
| 状态查询 | `pm_agent_runtime.py` | ~49% | ❌ 无专门测试 |
| 异步任务 | `pm_agent_runtime.py` | ~49% | ❌ 无专门测试 |
| 内部命令 | `chat.py` | 25% | ❌ 无专门测试 |
| 实时监控 | `chat.py` | 25% | ❌ 无专门测试 |

**问题**: 本次改进的新功能**完全没有单元测试覆盖**。

---

## 需要补充的测试

### 高优先级

1. **Chat 命令测试** (`chat.py`)
   - `test_internal_commands()` - 测试 /status, /log, /list 等
   - `test_async_job_mode()` - 测试异步任务模式
   - `test_timeout_protection()` - 测试超时保护
   - `test_watch_command()` - 测试实时监控

2. **PM Agent Runtime 测试** (`pm_agent_runtime.py`)
   - `test_create_job()` - 测试任务创建
   - `test_get_job_status()` - 测试状态查询
   - `test_list_jobs()` - 测试任务列表
   - `test_concurrent_job_limit()` - 测试并发限制
   - `test_job_timeout()` - 测试任务超时

3. **存储层测试** (`sqlite_store.py`)
   - `test_list_workflows()` - 测试工作流列表
   - `test_list_task_executions()` - 测试任务执行列表

### 中优先级

4. **事件系统测试** (`event_bus.py`)
   - `test_job_events()` - 测试 Job 事件发布
   - `test_event_subscription()` - 测试事件订阅

5. **集成测试**
   - `test_end_to_end_job_flow()` - 端到端任务流程
   - `test_chat_to_job_to_workflow()` - Chat 到工作流的完整流程

---

## 提高覆盖率的建议

### 短期 (1-2 天)

1. **修复失败测试**
   - 更新 GLM 模型版本断言
   - 修复 chat.py 测试的 mock 对象

2. **新增基础测试**
   - 为新增的内部命令添加基础测试
   - 为超时包装器添加单元测试

### 中期 (1 周)

3. **完善核心功能测试**
   - 异步任务创建和执行
   - 状态查询接口
   - 并发控制

4. **集成测试**
   - 完整的用户场景测试
   - 边缘条件测试

### 长期 (持续)

5. **测试驱动开发**
   - 新功能先写测试
   - 保持覆盖率 > 70%

6. **CI/CD 集成**
   - 自动化覆盖率检查
   - 覆盖率下降时报警

---

## 覆盖率目标

| 模块 | 当前 | 目标 | 优先级 |
|------|------|------|--------|
| `pm_agent_runtime.py` | 49% | 70% | 高 |
| `chat.py` | 25% | 60% | 高 |
| `orchestrator.py` | 66% | 75% | 中 |
| `claude_code_executor.py` | 49% | 60% | 中 |
| **总体** | **58%** | **70%** | **高** |

---

## 测试文件分布

```
tests/ 目录:        70 个测试文件
src/ 测试文件:       4 个测试文件
总计:               74 个测试文件

主要测试目录:
- tests/orchestrator/     - Orchestrator 核心测试
- tests/pm_agent/         - PM Agent 测试
- tests/runtime/          - Runtime 测试
- tests/cli/              - CLI 命令测试
```

---

## 工具使用

### 运行测试
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_chat_command.py -v

# 运行带覆盖率的测试
coverage run --source=src/lee -m pytest tests/ -v
coverage report
coverage html  # 生成 HTML 报告
```

### 查看覆盖率
```bash
# 终端报告
coverage report --sort=cover

# HTML 报告
coverage html
open htmlcov/index.html
```

---

## 总结

LEE 项目当前测试覆盖率为 **58%**，属于中等水平。

**优势**:
- 核心编排逻辑 (orchestrator) 有较好覆盖
- 关键执行器有测试保护
- 测试基础设施完善

**不足**:
- 本次改进的新功能**完全没有测试覆盖**
- Chat 命令测试覆盖率低 (25%)
- 部分新功能模块零覆盖

**建议**:
1. 优先为本次改进添加测试
2. 目标覆盖率提升到 70%
3. 建立测试驱动开发习惯
