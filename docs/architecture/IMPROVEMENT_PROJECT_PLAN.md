---
title: LEE 改进项目计划
author: LEE Team
date: 2026-02-14
version: 1.0
last_updated: 2026-02-19
---

# LEE 改进项目计划

> **制定日期**: 2026-02-14
> **计划周期**: 短期 (W1-W2) + 中期 (W3-W6)
> **目标**: 从"功能可用"到"投产可靠"，再到"架构健康"

---

## 一、短期改进计划 (W1-W2) — 投产可靠性

> **核心原则**: 不写新功能代码，只做"最后一公里"集成 + 补测试。

### S1: Retry + Trace 挂载到执行主路径

| 属性 | 值 |
|------|-----|
| **优先级** | P1 |
| **预估工时** | 2d |
| **涉及文件** | `step_runners.py`, `orchestrator.py` |
| **前置依赖** | 无 |
| **验收标准** | 1) LLM 步骤失败后自动重试（最多 3 次，指数退避）<br>2) 每步执行产生 Span 记录写入 `.workflow/traces.jsonl`<br>3) 现有测试全部通过 |

**实施步骤**:

1. 在 `step_runners.py` 的 `_execute_step()` 方法中：
   - 导入 `RetryExecutor` 和 `DEFAULT_RETRY_POLICY`
   - 将 executor 调用包裹在 `RetryExecutor.execute()` 中
   - 注意：仅对 `LLMExecutor` 和 `ClaudeCodeExecutor` 启用 Retry（它们天然幂等），`ShellExecutor` 需标记 `idempotent=true` 才启用
2. 在 `orchestrator.py` 的 `run_step()` 方法中：
   - 导入 `Tracer` 和 `Span`
   - 在步骤开始时创建 Span，步骤结束时关闭 Span
   - 记录 step_id、executor_type、duration、success/failure
3. 运行完整测试套件验证无 regression

---

### S2: Contract Schema 输出校验

| 属性 | 值 |
|------|-----|
| **优先级** | P1 |
| **预估工时** | 1d |
| **涉及文件** | `step_runners.py`, `validators/schema_validator.py` |
| **前置依赖** | 无 (可与 S1 并行) |
| **验收标准** | 1) 步骤输出自动校验是否符合 contract schema<br>2) 校验失败时记录警告但不阻塞执行（soft validation 模式）<br>3) 可通过配置切换为 hard validation（校验失败则步骤失败） |

**实施步骤**:

1. 在 `step_runners.py` 的步骤执行完毕后：
   - 查询步骤关联的 output contract（如果有）
   - 调用 `SchemaValidator.validate(result, contract_schema)`
   - 默认 soft mode：校验失败记 warning log + event
   - 支持 `strict_output_validation: true` 配置切换 hard mode
2. 在 `contract_discovery.py` 中添加 `get_step_output_contract(step_id)` 方法
3. 测试：编写 2-3 个测试用例验证 soft/hard 模式

---

### S3: Agent LRU 缓存

| 属性 | 值 |
|------|-----|
| **优先级** | P1 |
| **预估工时** | 0.5d |
| **涉及文件** | `agent_loader.py` |
| **前置依赖** | 无 (可与 S1/S2 并行) |
| **验收标准** | 1) 同一 agent spec 在同一工作流内只解析一次<br>2) 缓存命中率可观测（日志输出）<br>3) 缓存可手动清除 |

**实施步骤**:

1. 在 `AgentLoader` 类中引入 `functools.lru_cache` 或自建 dict 缓存
2. 缓存 key = `(agent_name, agent_version)`
3. 添加 `clear_cache()` 方法和缓存统计（hit/miss 计数）
4. 在日志中输出缓存命中信息

---

### S4: 新模块单元测试

| 属性 | 值 |
|------|-----|
| **优先级** | P1 |
| **预估工时** | 3d |
| **涉及文件** | 新增 4 个测试文件 |
| **前置依赖** | S1 完成后再测 Retry/Trace 集成场景 |
| **验收标准** | 1) 4 个新模块各有独立测试文件<br>2) 核心路径覆盖 ≥ 80%<br>3) 边界条件和异常路径有测试 |

**测试矩阵**:

| 测试文件 | 被测模块 | 关键测试用例 |
|---------|---------|------------|
| `test_retry.py` | `retry.py` | 重试成功、最大重试耗尽、指数退避延迟验证、不同策略行为、幂等性标记 |
| `test_trace.py` | `trace.py` | Span 创建/关闭、嵌套 Span、数据脱敏、JSONL 序列化、大内容引用 |
| `test_variable_resolver.py` | `variable_resolver.py` | `$inputs.xxx` 解析、`$sX_yyy` 解析、嵌套路径、缺失变量报错、表达式求值 |
| `test_state_machine_executor.py` | `state_machine_executor.py` | 合法状态转换、非法转换拒绝、回调触发、历史记录、持久化/恢复 |

---

### 短期里程碑

```
W1 (2/17 - 2/21)
├── Mon-Tue: S1 (Retry + Trace 集成)
├── Wed:     S2 (Schema 输出校验)
├── Thu:     S3 (Agent LRU 缓存)  ← 0.5d, 可提前完成
└── Fri:     S4 开始 (test_retry + test_trace)

W2 (2/24 - 2/28)
├── Mon-Tue: S4 继续 (test_variable_resolver + test_state_machine_executor)
├── Wed:     集成测试 + 回归验证
├── Thu:     代码 review + 修复
└── Fri:     短期改进完成 ✅ Git Tag: v3.2-reliable
```

---

## 二、中期改进计划 (W3-W6) — 架构治理

### M1: step_runners.py 策略模式重构

| 属性 | 值 |
|------|-----|
| **优先级** | P2 |
| **预估工时** | 3d |
| **涉及文件** | `step_runners.py` → 拆分为 `runners/` 目录 |
| **前置依赖** | S1 完成（确保 Retry/Trace 已集成后再重构） |
| **验收标准** | 1) `step_runners.py` 行数 < 200（仅保留注册和分发）<br>2) 每种 step type 有独立 runner 文件<br>3) 现有测试全部通过 |

**实施步骤**:

1. **定义策略接口**:
   ```python
   # execution/runners/base.py
   class StepRunnerStrategy(ABC):
       async def execute(self, step, context) -> StepResult: ...
       def can_handle(self, step_type: str) -> bool: ...
   ```

2. **拆分 runner 实现**:
   ```
   execution/runners/
   ├── __init__.py           # StepRunnerRegistry
   ├── base.py               # StepRunnerStrategy ABC
   ├── llm_runner.py         # LLM/ClaudeCode 步骤
   ├── gate_runner.py        # Gate 审批步骤
   ├── subworkflow_runner.py # 子工作流步骤
   ├── shell_runner.py       # Shell 命令步骤
   └── validation_runner.py  # 校验步骤
   ```

3. **瘦身 step_runners.py**: 只保留 `StepRunnersMixin` 的分发逻辑 + runner 注册
4. **迁移测试**: 确保所有 step type 的测试仍通过

---

### M2: runtime/executor/ 路径定性决策

| 属性 | 值 |
|------|-----|
| **优先级** | P2 |
| **预估工时** | 1d |
| **涉及文件** | `runtime/executor/__init__.py`, 新增 `docs/ARCHITECTURE_DECISION.md` |
| **前置依赖** | 无 |
| **验收标准** | 1) ADR 文档记录决策<br>2) `runtime/executor/` 标记为 experimental<br>3) README 更新选型指南 |

**实施步骤**:

1. 编写 ADR (Architecture Decision Record):
   - **决策**: `runtime/executor/` 定位为 LangGraph 实验性路径
   - **所有生产工作流**: 必须走 `orchestrator/execution/`
   - **评估时间线**: 2026 Q2 末评估是否合并或淘汰
2. 在 `runtime/executor/__init__.py` 添加 experimental 警告
3. 更新 `README.md` 中的架构说明

---

### M3: Workflow on_failure 策略

| 属性 | 值 |
|------|-----|
| **优先级** | P2 |
| **预估工时** | 2d |
| **涉及文件** | `state_machine.py`, `step_runners.py` (或新 runners), workflow YAML schema |
| **前置依赖** | M1 (策略模式重构后更易添加) |
| **验收标准** | 1) workflow.yaml 支持 `on_failure: retry\|skip\|fallback` 声明<br>2) skip 策略：标记步骤为 skipped 继续执行<br>3) fallback 策略：跳转到指定备选步骤 |

**实施步骤**:

1. 扩展 workflow YAML schema，在 step 定义中增加：
   ```yaml
   steps:
     - id: s1_coding
       on_failure:
         strategy: retry    # retry | skip | fallback
         max_retries: 3
         fallback_step: s1_manual_coding  # fallback 时使用
   ```
2. 在 `state_machine.py` 中添加 `skip` 和 `fallback` 状态转换
3. 在 runner 分发逻辑中，步骤失败后查询 `on_failure` 策略
4. 编写测试：retry/skip/fallback 各 2-3 个用例

---

### M4: 配置外部化

| 属性 | 值 |
|------|-----|
| **优先级** | P2 |
| **预估工时** | 2d |
| **涉及文件** | `project_config.py`, 新增 `.lee/config.yaml` schema |
| **前置依赖** | 无 (可与 M1 并行) |
| **验收标准** | 1) 支持 `.lee/config.yaml` 覆盖默认配置<br>2) 至少包含：retry 参数、token 限制、超时时间、日志级别<br>3) 配置变更不需要改代码 |

**实施步骤**:

1. 定义 `.lee/config.yaml` schema:
   ```yaml
   # .lee/config.yaml
   execution:
     retry:
       max_retries: 3
       base_delay: 1.0
       max_delay: 30.0
     timeout:
       step_timeout: 300      # 单步超时 (秒)
       workflow_timeout: 3600  # 工作流超时 (秒)
     validation:
       strict_output: false    # 输出校验是否阻塞
   
   agent:
     cache_size: 128           # LRU 缓存大小
   
   logging:
     level: INFO
     trace_enabled: true
   ```
2. 在 `project_config.py` 中添加配置加载优先级：`.lee/config.yaml` > 环境变量 > 默认值
3. 将 S1-S3 中硬编码的参数替换为配置读取
4. 编写测试：配置覆盖、缺省值回退、无效配置报错

---

### 中期里程碑

```
W3 (3/3 - 3/7)
├── Mon:     M2 (路径定性决策 + ADR)
├── Tue-Thu: M1 开始 (策略接口 + LLM/Gate runner 拆分)
└── Fri:     M4 开始 (config schema 定义)

W4 (3/10 - 3/14)
├── Mon:     M1 完成 (subworkflow/shell/validation runner)
├── Tue:     M1 集成测试 + step_runners.py 瘦身
├── Wed-Thu: M4 完成 (配置加载 + 参数替换)
└── Fri:     M4 测试

W5 (3/17 - 3/21)
├── Mon-Tue: M3 (on_failure schema + state_machine 扩展)
├── Wed:     M3 (runner 中 on_failure 分发)
├── Thu:     M3 测试
└── Fri:     中期回归测试

W6 (3/24 - 3/28)
├── Mon-Tue: 整体回归 + 修复
├── Wed:     代码 review
├── Thu:     文档更新 (README, ARCHITECTURE_DECISION)
└── Fri:     中期改进完成 ✅ Git Tag: v3.3-governed
```

---

## 三、风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|---------|
| S1 Retry 集成导致非幂等 executor 副作用 | 数据重复/状态不一致 | 仅对标记 `idempotent=true` 的 executor 启用自动重试 |
| M1 策略模式重构破坏现有调用链 | 所有工作流执行异常 | 保留 `step_runners.py` 旧路径做 feature flag 切换，逐步迁移 |
| M3 on_failure schema 与现有 workflow 不兼容 | 已有 17 个 workflow 解析失败 | `on_failure` 字段可选，未声明时默认 `retry` 行为（向后兼容） |
| M4 配置外部化后环境差异 | 不同环境行为不一致 | 要求 `.lee/config.yaml` 纳入版本控制，CI 中校验必填字段 |

---

## 四、交付物清单

### 短期交付 (W2 末)

- [ ] `step_runners.py` 集成 Retry + Trace
- [ ] `step_runners.py` 集成 Schema 输出校验
- [ ] `agent_loader.py` LRU 缓存
- [ ] `tests/test_retry.py`
- [ ] `tests/test_trace.py`
- [ ] `tests/test_variable_resolver.py`
- [ ] `tests/test_state_machine_executor.py`
- [ ] Git Tag: `v3.2-reliable`

### 中期交付 (W6 末)

- [ ] `execution/runners/` 策略模式目录
- [ ] `docs/ARCHITECTURE_DECISION.md` (ADR)
- [ ] `.lee/config.yaml` schema + 加载逻辑
- [ ] `state_machine.py` on_failure 支持
- [ ] Workflow YAML schema 扩展
- [ ] Git Tag: `v3.3-governed`
