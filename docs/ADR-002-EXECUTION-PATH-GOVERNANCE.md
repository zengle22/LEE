# ADR-002: Execution Path Governance — orchestrator/ vs runtime/

**Status**: Accepted  
**Date**: 2026-02-14  
**Deciders**: LEE Core Team

## Context

LEE 当前存在两条执行路径：

| 路径 | 模块 | 状态 | 技术栈 |
|------|------|------|--------|
| **生产路径** | `orchestrator/execution/` | ✅ Production | YAML workflows + StepRunnerMixin |
| **实验路径** | `runtime/executor/` | 🧪 Experimental | LangGraph + 状态图 |

两条路径共存已导致以下问题：
1. 新贡献者不确定使用哪条路径
2. 相似功能出现在两处（executor factory、registry 等）
3. 测试和维护成本翻倍

## Decision

1. **`orchestrator/execution/`** 保持生产（Production）状态，所有新工作流开发首选此路径
2. **`runtime/executor/`** 标记为实验（Experimental），添加运行时警告
3. **评估时间线**: 2026 Q2 评估 LangGraph 路径的价值：
   - 如果 LangGraph 显著优于现有方案 → 制定迁移计划
   - 如果差异不大 → 归档 `runtime/executor/`，合并有价值的功能到生产路径
4. 在评估期间，新功能不应添加到 `runtime/executor/`

## Consequences

- 开发者明确知道首选路径
- 实验代码不会意外进入生产链路
- Q2 会有明确的技术决策点

## References

- [Orchestrator Architecture](./Orchestrator-Architecture.md)
- [LangGraph Executor Architecture](./04-executor-langgraph-architecture.md)
