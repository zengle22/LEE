# Smoke Gate Merge API Contract

## 模块概述

本模块定义了 **SRC-058 Dev Smoke Gate - Merge 门禁集成** 的内部 API 协议。

## 版本信息

- **当前版本**: v1.0.0
- **合同 ID**: CONTRACT-SMOKE-GATE-MERGE-20260317-001
- **状态**: pending_freeze
- **创建日期**: 2026-03-17

## 关联需求

- FEAT-SRC-058-001: Smoke Gate Merge 门禁集成
- ADR-023: Dev Smoke Gate 架构

## 核心功能

1. **Smoke Gate 生命周期管理** - 创建、启动、状态追踪
2. **Merge 门禁集成** - 在 merge 流程中集成 Smoke Gate 作为前置条件
3. **自动拦截 Blocker** - 自动拦截 blocker 问题并生成报告
4. **门禁状态可视化** - 在 MR 页面展示门禁状态

## 主要接口

| 接口 | 描述 |
|------|------|
| `SmokeGateManager` | Gate 生命周期管理 |
| `SmokeExecutor` | Smoke 测试执行器 |
| `MergeGateIntegrator` | Merge Gate Git 平台集成 |
| `PreMergeHook` | Pre-merge Git Hook |
| `SmokeStore` | 数据持久化存储 |

## 数据类型

### 枚举
- `SmokeGateStatus` - Gate 状态
- `GateResult` - 判定结果
- `FailureSeverity` - 失败严重程度
- `SmokeGateEvent` - 事件类型

### 数据模型
- `SmokeGateContext` - Gate 执行上下文
- `TestExecutionRecord` - 测试执行记录
- `SmokeGateReport` - Gate 执行报告
- `MergeGateState` - Merge Gate 状态机

## 实现文件

| 组件 | 文件路径 |
|------|---------|
| 枚举/模型定义 | `src/lee/smoke/models.py` |
| Gate 管理器 | `src/lee/smoke/gate/manager.py` |
| 执行器 | `src/lee/smoke/executor.py` |
| Merge 集成 | `src/lee/smoke/integration/merge_gate.py` |
| Git Hook | `src/lee/smoke/hooks/pre_merge.py` |
| 持久化 | `src/lee/smoke/storage/store.py` |

## 依赖

### 内部依赖
- `src/lee/smoke/test_set/` - Test Set 加载
- `src/lee/smoke/environment/` - 环境检查
- `src/lee/orchestrator/` - 工作流集成

### 外部依赖
- pytest >= 7.0
- Playwright >= 1.40
- pytest-xdist >= 3.0
- pytest-html >= 4.0

## 使用说明

### 创建 Gate

```python
manager = SmokeGateManager()
context = await manager.create_gate(
    merge_request_id="MR-123",
    config=SmokeGateConfig(
        test_set_ref="test-set-v1",
        priority_filter=["P0", "P1"],
        retry_count=3,
        timeout_minutes=30
    )
)
```

### 执行测试

```python
executor = SmokeExecutor()
report = await executor.execute(
    context=context,
    test_cases=test_cases
)
```

### 检查 Merge 条件

```python
integrator = MergeGateIntegrator()
state = await integrator.check_merge_eligibility(
    merge_request_id="MR-123"
)

if state.is_mergeable:
    print("允许 merge")
else:
    print(f"阻塞 merge: {state.blocker_issues}")
```

## 状态机

```
NOT_STARTED → RUNNING → {PASSED | FAILED | INVALID}
```

## Changelog

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2026-03-17 | 初始版本 |
