# Executor 双引擎演进：LangGraph 渐进式替换

> **状态**: Draft
> **创建日期**: 2026-02-13
> **分析结论**: 暂不升级，待 L3 workflow 实际需要内部迭代时再激活

---

## 背景

LEE 存在两套执行子系统：

| 维度 | 当前引擎 (`orchestrator/execution/`) | 下一代引擎 (`runtime/executor/`) |
|:----:|:----:|:----:|
| 定位 | 生产引擎 | 下一代 (v0.1.0) |
| 调度 | StateMachine + step-by-step | LangGraph graph.invoke() |
| 类型 | llm / shell / metagpt / mock | l3.impl.coding / l3.test.unit |
| 契约 | `Dict[str, Any]` 松散 | `ExecutorTaskSpec` / `ExecutionResult` 强类型 |
| 追踪 | trace.py | SpanBuilder |
| 代码量 | ~323K (26 files) | ~50K (14 files) |

**这不是重复实现，而是有意的并存设计**（`runtime/__init__.py` 明确注明"渐进式替换策略"）。

---

## 核心价值

**当前引擎**：每个 step = 一次 LLM 调用，step 内部无法做循环/分支。

**LangGraph 引擎**：每个 step 可以是一个内部 DAG（写代码 → 编译 → 测试 → 修 bug → 重测），支持 step 内部多轮迭代。

| 场景 | 适合的引擎 |
|------|-----------|
| L1/L2 Agent（单次 prompt） | 当前引擎 ✅ |
| L3 自动编码（需内部迭代） | LangGraph ✅ |
| Shell / MetaGPT | 当前引擎 ✅ |

---

## 现状

1. **适配器已实现**：`langgraph_executor.py` 继承 `BaseExecutor`，完成 `Dict ↔ ExecutorTaskSpec` 双向转换
2. **Graph Builder 已有 2 个**：`l3.impl.coding` + `l3.test.unit`
3. **注册函数已就绪**：`register_langgraph_executor()`
4. **ARCHITECTURE.md §8** 已文档化双引擎对比和迁移路线

但 `orchestrator.py` **未导入注册函数**，即桥接处于关闭状态。

---

## 激活条件

当以下条件满足时，考虑激活桥接：

1. L3 workflow 实际运行时需要 step 内部迭代（如：写代码→跑测试→失败→自动修复→重跑）
2. 当前引擎的单次 LLM 调用已无法满足 L3 任务质量
3. LangGraph 依赖稳定，不会引入额外的启动延迟

## 激活方式

在 `orchestrator.py` imports 中添加两行：

```python
from lee.orchestrator.execution.langgraph_executor import register_langgraph_executor
register_langgraph_executor()
```

然后 workflow YAML 中使用 `executor: langgraph`。

---

## 迁移路线图

| 阶段 | 内容 | 状态 |
|:----:|------|:----:|
| Phase 0 | 适配器实现 | ✅ |
| Phase 1 | l3.impl.coding + l3.test.unit graph | ✅ |
| Phase 2 | 激活桥接 + 集成测试 | ⬜ 待触发 |
| Phase 3 | 更多 graph (l3.review, l3.deploy) | ⬜ |
| Phase 4 | 统一追踪到 SpanBuilder | ⬜ |
| Phase 5 | 全面切换 | ⬜ 远期 |
