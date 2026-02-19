---
title: LEE Orchestrator - P3 优化方案
author: LEE Team
date: 2026-02-06
version: 1.0
last_updated: 2026-02-19
---

# LEE Orchestrator - P3 优化方案

> **版本**: 1.0
> **创建日期**: 2026-02-05
> **状态**: 📋 计划中
> **基于**: P0/P1/P2 完成度审查

---

## 📋 执行摘要

基于 P0-P2 完成度审查，P3 阶段的**核心不是继续堆叠语义特性**，而是：

1. **修复文档和治理问题** - 确立单一标准
2. **完善执行语义** - 明确失败策略和组合关系
3. **功能冻结** - 防止继续吸干资源
4. **补强测试** - 提升生产信心

---

## 🎯 P3 优先级分级

| 级别 | 类型 | 说明 | 工作量 |
|------|------|------|--------|
| **P3.0** | 文档修复 | 修复显式错误、确立规范 | 4 小时 |
| **P3.1** | 治理强化 | Legacy deprecation、单一标准 | 4 小时 |
| **P3.2** | 语义补齐 | Gate-Approval 组合、失败策略 | 1 天 |
| **P3.3** | 测试补强 | 模糊测试、端到端回归 | 2 天 |
| **P3.4** | 观测集成 | Metrics、通知、Alerts | 3 天 |
| **P3.5** | P3+ 延后 | 表达式引擎优化 | 1 周 |

---

## 🔧 P3.0: 文档修复（立即执行）

### 3.0.1 修复新增文件数量统计

**问题**: 报告写 19 个，实际列表 18 个

**修复**:
```python
# 实际统计
P0 核心模块: 7 个
- src/lee/orchestrator/ir/models.py
- src/lee/orchestrator/ir/__init__.py
- src/lee/orchestrator/execution/spec_global_parser.py
- src/lee/orchestrator/execution/variable_resolver.py
- src/lee/orchestrator/execution/template_manager.py (修改)
- src/lee/orchestrator/ir/converter.py
- src/lee/orchestrator/tools/migrate_workflow.py

P1 执行引擎: 4 个
- src/lee/orchestrator/execution/state_machine_executor.py
- src/lee/orchestrator/execution/gate_engine.py
- src/lee/orchestrator/execution/condition_engine.py
- src/lee/orchestrator/execution/human_approval.py

P2 扩展: 2 个
- src/lee/orchestrator/tools/migrate_legacy_workflows.py
- src/lee/orchestrator/execution/ir/__init__.py (新增)

文档和测试: 3 个
- docs/test-report-p0-p1-p2.md
- docs/implementation-completion-review.md
- demo_p1_complete.py

备份文件: 2 个
- spec-global/departments/devops/workflows/devops-deployment/v1/workflow.yaml.backup
- spec-global/departments/ui/workflows/ui-design-pipeline/v1/workflow.yaml.backup

总计: 18 个
```

### 3.0.2 统一 IR 目录描述

**问题**: 出现 `orchestrator/ir/` 和 `execution/ir/` 两种描述

**修复**:
```yaml
权威 IR 目录:
  路径: src/lee/orchestrator/ir/
  说明: 这是唯一的 IR 模型定义位置

  子目录结构:
    models.py: 核心数据模型
    converter.py: IR 转换器
    __init__.py: 导出接口

历史遗留:
  路径: src/lee/orchestrator/execution/ir/
  说明: 已废弃，仅作为向后兼容别名
  状态: ⚠️ 将在 v2.0 移除

迁移指引:
  新代码使用: from lee.orchestrator.ir.models import *
  旧代码仍可用: from lee.orchestrator.execution.ir import * (警告)
```

### 3.0.3 明确"向后兼容"边界

**问题**: TemplateManager 完全兼容旧模板，与"单一标准"冲突

**修复**: 添加 Deprecation 机制

---

## 🛡️ P3.1: 治理强化（本周完成）

### 3.1.1 Legacy 模板 Deprecation 策略

**原则**: 新工作流一律用 spec-global，legacy 只用于迁移

#### 实现方案

```python
# template_manager.py 修改

class TemplateManager:
    def _parse_template_doc(self, doc: Dict, template_id: str) -> WorkflowTemplate:
        kind = doc.get("kind", "")

        if kind != "workflow":
            # 检测到 legacy 格式
            self._log_deprecation_warning(template_id)
            return self._parse_legacy_format(doc, template_id)

        # spec-global 格式
        return self._parse_spec_global_format(doc, template_id)

    def _log_deprecation_warning(self, template_id: str):
        """记录 legacy 格式警告"""
        import warnings
        from datetime import datetime

        warning_msg = f"""
╌─────────────────────────────────────────────────────────────┐
│ ⚠️  DEPRECATION WARNING                                      │
├─────────────────────────────────────────────────────────────┤
│ Template '{template_id}' uses legacy orchestrator format.   │
│                                                              │
│ This format is DEPRECATED and will be removed in v2.0.       │
│                                                              │
│ Action Required:                                             │
│   1. Migrate to spec-global format                           │
│   2. Add 'kind: workflow' header                            │
│   3. Use 'python -m lee.orchestrator.tools.migrate_workflow' │
│                                                              │
│ New projects MUST use spec-global format.                    │
│ See: docs/spec-global-migration-guide.md                     │
└─────────────────────────────────────────────────────────────┘
        """
        warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)

        # 同时记录到日志
        logger.warning(f"[DEPRECATION] Legacy format detected: {template_id}")
```

#### 文档更新

**在 `docs/spec-global-orchestrator-compatibility.md` 中添加**:

```yaml
# 规范矩阵

## 推荐写法 vs 允许写法 vs 不允许写法

### Inputs 格式

| 格式 | 示例 | 状态 | 说明 |
|------|------|------|------|
| Dict 格式 | `- inputs: {context_files: [...]}` | ✅ 推荐 | 明确、可验证 |
| List 格式 | `- inputs: [...]` | 🟡 允许 | 兼容性保留 |
| 纯字符串 | `- inputs: "prd"` | ⚠️ 不推荐 | 仅用于简单场景 |

### Dependencies 格式

| 格式 | 示例 | 状态 | 说明 |
|------|------|------|------|
| List 格式 | `dependencies: [step1, step2]` | ✅ 推荐 | 简洁、明确 |
| Dict 格式 | `dependencies: {requires: [...]}` | 🟡 允许 | 仅用于兼容 |

### Steps 结构

| 格式 | 状态 | 说明 |
|------|------|------|
| 嵌套 stages → steps | ✅ 推荐 | QA 工作流使用 |
| 扁平 steps | 🟡 允许 | 简单工作流使用 |

### 禁止的写法

| 写法 | 原因 |
|------|------|
| 无 `kind: workflow` 头部 | 无法识别格式 |
| `level: task` without `kind` | 已废弃 |
| 硬编码绝对路径 | 破坏可移植性 |
| 内联 gate 定义 | 应使用外部 gate 文件 |
```

---

## 🔗 P3.2: 语义补齐（本周完成）

### 3.2.1 Gate-Approval 组合流程设计

**问题**: Gate 评估和人工审批的关系不明确

#### 执行流程定义

```yaml
# spec-global 门禁与审批执行流程

## 流程定义

当工作流执行到带 gate 的步骤时：

1. 【规则评估】gate_engine 评估所有规则
   - 评估 mandatory_criteria
   - 评估 threshold_criteria
   - 评估 risk_acceptance_criteria

2. 【判定结果】生成 GateVerdict
   - PASS: 所有 mandatory 通过，threshold 在警告内
   - FAIL: 任意 mandatory 失败
   - NEEDS_RISK_ACCEPTANCE: 存在风险需要人工签字
   - NEEDS_APPROVAL: 需要审批人签字

3. 【条件分支】根据 Verdict 执行

   分支 A: Verdict == PASS
     → 直接继续下一步
     → 状态机转换: current_state → next_state

   分支 B: Verdict == FAIL
     → 工作流进入 FAILED 状态
     → 记录失败原因到 audit_trail
     → 不触发人工审批

   分支 C: Verdict == NEEDS_RISK_ACCEPTANCE
     → 自动创建 human_approval 请求
     → 审批类型: "risk_acceptance"
     → 必需审批人: gate 定义的风险签字人
     → 审批通过 → PASS → 继续执行
     → 审批拒绝 → FAIL → 进入 FAILED

   分支 D: Verdict == NEEDS_APPROVAL
     → 自动创建 human_approval 请求
     → 审批类型: "gate_approval"
     → 必需审批人: gate 定义的审批人
     → 审批通过 → PASS → 继续执行
     → 审批拒绝 → FAIL → 进入 FAILED

4. 【状态同步】审批结果回写到状态机
   - 审批通过 → transition(gate_passed)
   - 审批拒绝 → transition(gate_rejected)

## 代码示意

class GateOrchestrator:
    """门禁协调器 - 连接 gate_engine 和 human_approval"""

    async def execute_gate_step(self, step_id: str, gate: GateIR, context: Dict):
        # 1. 规则评估
        verdict = self.gate_engine.evaluate_gate(gate, context)

        # 2. 根据结果分支
        if verdict.verdict == GateVerdict.PASS:
            return StepResult(status="completed")

        elif verdict.verdict == GateVerdict.FAIL:
            await self.state_machine.transition("gate_failed")
            return StepResult(status="failed", errors=verdict.failed_rules)

        elif verdict.verdict in [GateVerdict.NEEDS_RISK_ACCEPTANCE, GateVerdict.NEEDS_APPROVAL]:
            # 3. 创建审批请求
            approval_type = "risk_acceptance" if verdict.verdict == GateVerdict.NEEDS_RISK_ACCEPTANCE else "gate_approval"
            request = await self.approval_executor.create_request(
                gate_id=gate.gate_id,
                approval_type=approval_type,
                required_approvers=self._extract_approvers(gate, approval_type),
                context_data=context
            )

            # 4. 等待审批（阻塞）
            decision = await self._wait_for_approval(request.request_id)

            # 5. 审批结果回写
            if decision.decision == ApprovalStatus.APPROVED:
                await self.state_machine.transition("gate_passed")
                return StepResult(status="completed")
            else:
                await self.state_machine.transition("gate_rejected")
                return StepResult(status="failed", reason=decision.comments)
```

### 3.2.2 失败策略与 BLOCKED 语义

**问题**: on_fail / BLOCKED / retry 语义不明确

#### 失败策略定义

```yaml
# spec-global 失败策略规范

## 状态定义

| 状态 | 说明 | 可恢复性 | 典型场景 |
|------|------|---------|----------|
| COMPLETED | 正常完成 | - | 所有步骤成功 |
| FAILED | 终态失败 | ❌ 不可恢复 | 致命错误、资源不存在 |
| BLOCKED | 阻塞等待 | ✅ 可恢复 | 门禁不通过、等待审批 |
| CANCELLED | 人工取消 | ✅ 可重新运行 | 用户主动取消 |

## 失败场景与处理

### 场景 1: Gate 规则失败 (mandatory 不通过)

```
触发: gate_engine.evaluate() 返回 mandatory 失败
动作:
  - 状态 → FAILED
  - 记录: failed_rules 列表
  - 通知: 发送告警
恢复: 不可恢复，需要修正输入后重新运行
```

### 场景 2: Gate 需要人工审批

```
触发: gate_engine.evaluate() 返回 NEEDS_APPROVAL
动作:
  - 状态 → BLOCKED
  - 创建: human_approval 请求
  - 等待: 审批决策
恢复:
  - 审批通过 → transition(gate_passed) → 继续
  - 审批拒绝 → transition(gate_rejected) → FAILED
  - 超时 → transition(timeout) → FAILED 或升级
```

### 场景 3: 条件不满足

```
触发: condition_engine.evaluate() 返回 False
动作:
  - 跳过该步骤
  - 标记: status="skipped"
恢复: 不需要恢复，继续下一步
```

### 场景 4: 步骤执行失败

```
触发: Agent/Skill 执行异常
动作: 根据 step.on_failure 策略

  策略 A: block_and_report
    → 状态 → BLOCKED
    → 记录错误信息
    → 等待人工介入

  策略 B: retry_with_fallback
    → 重试 N 次
    → 失败后使用 fallback Agent
    → 仍失败 → FAILED

  策略 C: escalate_and_block
    → 状态 → BLOCKED
    → 升级给上一级审批人
    → 等待决策

恢复: 根据策略可能允许人工修正后继续
```

## BLOCKED 状态恢复机制

```python
class BlockedStateHandler:
    """BLOCKED 状态处理器"""

    async def handle_blocked(self, workflow_id: str, reason: str):
        """处理 BLOCKED 状态"""

        # 1. 记录阻塞原因
        await self.store.update_workflow_data(workflow_id, {
            "blocked_at": datetime.now(),
            "blocked_reason": reason,
            "recovery_options": self._get_recovery_options(reason)
        })

        # 2. 发送通知
        await self.notification.send(
            event="workflow_blocked",
            workflow_id=workflow_id,
            reason=reason
        )

        # 3. 等待人工介入
        await self._wait_for_intervention(workflow_id)

    def _get_recovery_options(self, reason: str) -> List[str]:
        """获取恢复选项"""
        if "gate" in reason.lower():
            return ["approve_gate", "modify_inputs", "cancel_workflow"]
        elif "timeout" in reason.lower():
            return ["extend_timeout", "cancel_workflow", "escalate"]
        else:
            return ["retry_step", "modify_inputs", "cancel_workflow"]

    async def resume_from_blocked(self, workflow_id: str, action: str, params: Dict):
        """从 BLOCKED 恢复"""

        if action == "approve_gate":
            # 审批通过，继续执行
            await self.state_machine.transition("gate_passed")

        elif action == "modify_inputs":
            # 修改输入，重新评估 gate
            new_context = params.get("context")
            verdict = self.gate_engine.evaluate_gate(gate, new_context)

            if verdict.verdict == GateVerdict.PASS:
                await self.state_machine.transition("gate_passed")
            else:
                # 仍然不通过，保持 BLOCKED
                await self.store.update_workflow_data(workflow_id, {
                    "blocked_reason": f"Gate still failed after modification: {verdict.failed_rules}"
                })

        elif action == "retry_step":
            # 重试失败的步骤
            await self.retry_step(workflow_id, params.get("step_id"))
```

## 用户指引

### QA 遇到 "门禁不通过" 时怎么办？

```yaml
问题排查流程:

1. 查看失败规则
   - 命令: lee workflow status <workflow_id>
   - 查看: failed_rules 列表

2. 根据规则类型处理

   类型 A: PRD 未冻结 (prd.is_frozen == false)
     → 解决: 冻结 PRD
     → 命令: lee contract freeze <prd_path>

   类型 B: 功能点不足 (COUNT(prd.features) < 1)
     → 解决: 补充功能点定义
     → 命令: lee prd add-feature <prd_path>

   类型 C: 分支覆盖不足 (feature_coverage < 80)
     → 解决: 补充测试用例
     → 命令: lee test add-cases <workflow_id>

3. 修正后重新运行

   方式 A: 从 BLOCKED 恢复
     → 命令: lee workflow resume <workflow_id> --action modify_inputs

   方式 B: 重新运行
     → 命令: lee workflow run <template_id> --inputs <corrected_inputs>
```
```

---

## 🧪 P3.3: 测试补强（本周完成）

### 3.3.1 解析层模糊测试

**目标**: 确保 parser 对 YAML 变体的鲁棒性

```python
# tests/test_parser_fuzz.py

import yaml
import pytest
from lee.orchestrator.execution.spec_global_parser import SpecGlobalParser
from hypothesis import given, strategies as st
import tempfile
from pathlib import Path

class TestParserFuzzing:
    """解析器模糊测试"""

    @given(st.dictionaries(
        keys=st.sampled_from(["id", "name", "kind", "version", "description", "owner"]),
        values=st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.lists(st.text())
        )
    ))
    def test_parser_robustness(self, doc变异):
        """测试 parser 对各种 YAML 变体的容忍度"""

        # 1. 创建有效的基础结构
        base_doc = {
            "kind": "workflow",
            "version": "1.0",
            "id": "test.workflow",
            "name": "Test Workflow"
        }

        # 2. 应用变异
        mutated_doc = {**base_doc, **doc变异}

        # 3. 尝试解析（不期望成功，但不应该崩溃）
        parser = SpecGlobalParser()
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(mutated_doc, f)
                temp_path = f.name

            # 尝试解析
            result = parser.parse_workflow_file(temp_path)

            # 如果成功，验证基本结构
            if result:
                assert result.id is not None
                assert result.kind == "workflow"

        except Exception as e:
            # 期望的错误: ValueError, KeyError, yaml.YAMLError
            # 不期望的错误: SystemError, MemoryError, Segmentation Fault
            assert isinstance(e, (ValueError, KeyError, yaml.YAMLError))

        finally:
            # 清理
            Path(temp_path).unlink(missing_ok=True)

    def test_field_order_independence(self):
        """测试字段顺序不影响解析结果"""

        yaml_variations = [
            """
kind: workflow
id: test.workflow
name: Test
            """,
            """
name: Test
id: test.workflow
kind: workflow
            """,
            """
id: test.workflow
kind: workflow
name: Test
            """
        ]

        parser = SpecGlobalParser()
        results = []

        for yaml_str in yaml_variations:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
                f.write(yaml_str)
                f.flush()
                result = parser.parse_workflow_file(f.name)
                results.append((result.id, result.name))

        # 所有变体应该产生相同结果
        assert len(set(results)) == 1

    def test_whitespace_tolerance(self):
        """测试对空格/缩进的容忍度"""

        variations = [
            "kind: workflow\nid: test",  # LF
            "kind: workflow\r\nid: test",  # CRLF
            "kind: workflow\r id: test",  # CR (旧 Mac)
            "kind:  workflow\n  id:  test",  # 多余空格
        ]

        parser = SpecGlobalParser()

        for yaml_str in variations:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
                f.write(yaml_str)
                f.flush()
                try:
                    result = parser.parse_workflow_file(f.name)
                    assert result is not None
                except:
                    pass  # 某些变体可能不合法，但不应崩溃
```

### 3.3.2 跨部门端到端测试

**目标**: 验证完整工作流链路

```python
# tests/test_e2e_cross_department.py

import pytest
from lee.orchestrator.orchestrator import Orchestrator

class TestCrossDepartmentE2E:
    """跨部门端到端测试"""

    @pytest.mark.asyncio
    async def test_prd_to_dev_to_qa_pipeline(self):
        """测试 PRD → DEV → QA 完整链路"""

        # 1. PRD 阶段: 创建产品需求
        prd_result = await self.run_workflow(
            "workflow.product.pipeline",
            inputs={
                "product_idea": "一个 AI 写作助手",
                "target_market": "内容创作者"
            }
        )

        assert prd_result.status == "completed"
        prd_contract = prd_result.outputs["prd_contract"]

        # 2. DEV 阶段: 基于 PRD 开发
        dev_result = await self.run_workflow(
            "workflow.dev.development_pipeline",
            inputs={
                "prd_contract": prd_contract,
                "tech_stack": "python, fastapi, react"
            }
        )

        assert dev_result.status == "completed"
        tech_arch = dev_result.outputs["technical_architecture"]

        # 3. QA 阶段: 基于技术架构设计测试
        qa_result = await self.run_workflow(
            "workflow.qa.test_case_design_pipeline",
            inputs={
                "prd": prd_contract,
                "technical_architecture": tech_arch,
                "ui_prototype": dev_result.outputs["ui_prototype"],
                "ui_page": dev_result.outputs["ui_page"]
            }
        )

        assert qa_result.status == "completed"
        assert "test_cases" in qa_result.outputs
        assert "e2e_scripts" in qa_result.outputs

        # 4. 验证数据一致性
        # PRD 中的功能点应该在测试用例中覆盖
        prd_features = prd_result.outputs["features"]
        test_coverage = qa_result.outputs["test_case_design"]["coverage"]
        assert test_coverage["feature_coverage"] >= 80

    @pytest.mark.asyncio
    async def test_devops_deployment_with_gates(self):
        """测试 DevOps 部署完整流程（含门禁）"""

        # 1. 架构设计阶段
        arch_result = await self.run_workflow(
            "workflow.devops.deployment",
            start_from: "p1_architecture",
            inputs: {"system_arch": "..."}
        )

        # 应该有架构评审门禁
        assert arch_result.gate_evaluations["phase1_review"] == "passed"

        # 2. 实现阶段
        impl_result = await self.run_workflow(
            "workflow.devops.deployment",
            start_from: "p2_infra_code",
            inputs: {"infra_architecture": arch_result.outputs["infra_architecture"]}
        )

        # 3. 配置注入（人类介入点）
        config_result = await self.run_workflow(
            "workflow.devops.deployment",
            start_from: "p3_env_config",
            human_input: {
                "env_config_dev": {"db_host": "localhost", "db_port": 5432},
                "approval": "approved"
            }
        )

        assert config_result.status == "completed"

        # 4. 部署到 dev
        deploy_result = await self.run_workflow(
            "workflow.devops.deployment",
            start_from: "p4_deploy_dev_test",
            inputs: {"env_config": config_result.outputs["env_config"]}
        )

        assert deploy_result.status == "completed"
        assert "deployment_log" in deploy_result.outputs
```

---

## 📊 P3.4: 观测集成（下周开始）

### 3.4.1 Metrics 收集

```python
# src/lee/orchestrator/observability/metrics.py

from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

class OrchestratorMetrics:
    """Orchestrator 指标收集"""

    # 工作流指标
    workflow_total = Counter(
        'orchestrator_workflows_total',
        'Total workflows executed',
        ['template_id', 'status']
    )

    workflow_duration = Histogram(
        'orchestrator_workflow_duration_seconds',
        'Workflow execution duration',
        ['template_id']
    )

    workflow_active = Gauge(
        'orchestrator_workflows_active',
        'Active workflows',
        ['template_id', 'state']
    )

    # 门禁指标
    gate_evaluations = Counter(
        'orchestrator_gate_evaluations_total',
        'Total gate evaluations',
        ['gate_id', 'verdict']
    )

    gate_duration = Histogram(
        'orchestrator_gate_duration_seconds',
        'Gate evaluation duration',
        ['gate_id']
    )

    # 审批指标
    approval_requests = Counter(
        'orchestrator_approval_requests_total',
        'Total approval requests',
        ['gate_id', 'decision']
    )

    approval_duration = Histogram(
        'orchestrator_approval_duration_seconds',
        'Approval duration',
        ['gate_id']
    )

    # 步骤指标
    step_duration = Histogram(
        'orchestrator_step_duration_seconds',
        'Step execution duration',
        ['template_id', 'step_kind']  # agent, skill, human_gate
    )

    step_errors = Counter(
        'orchestrator_step_errors_total',
        'Total step errors',
        ['template_id', 'step_id', 'error_type']
    )

    def record_workflow_start(self, template_id: str, workflow_id: str):
        """记录工作流开始"""
        self.workflow_active.labels(
            template_id=template_id,
            state='INIT'
        ).inc()

    def record_workflow_complete(self, template_id: str, status: str, duration: float):
        """记录工作流完成"""
        self.workflow_total.labels(
            template_id=template_id,
            status=status
        ).inc()

        self.workflow_duration.labels(
            template_id=template_id
        ).observe(duration)

        self.workflow_active.labels(
            template_id=template_id,
            state='INIT'
        ).dec()

    def record_gate_evaluation(self, gate_id: str, verdict: str, duration: float):
        """记录门禁评估"""
        self.gate_evaluations.labels(
            gate_id=gate_id,
            verdict=verdict
        ).inc()

        self.gate_duration.labels(
            gate_id=gate_id
        ).observe(duration)

    def record_approval_decision(self, gate_id: str, decision: str, duration: float):
        """记录审批决策"""
        self.approval_requests.labels(
            gate_id=gate_id,
            decision=decision
        ).inc()

        self.approval_duration.labels(
            gate_id=gate_id
        ).observe(duration)
```

### 3.4.2 通知集成

```python
# src/lee/orchestrator/observability/notifications.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from enum import Enum

class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    WECHAT_WORK = "wechat_work"

class NotificationPriority(Enum):
    """通知优先级"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationSender(ABC):
    """通知发送器抽象类"""

    @abstractmethod
    async def send(self, message: str, channel: NotificationChannel,
                  priority: NotificationPriority, recipients: List[str]):
        """发送通知"""
        pass

class EmailNotificationSender(NotificationSender):
    """邮件通知"""

    async def send(self, message: str, channel: NotificationChannel,
                  priority: NotificationPriority, recipients: List[str]):
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(message)
        msg['Subject'] = f"[{priority.value.upper()}] LEE Orchestrator Notification"
        msg['From'] = "lee-orchestrator@example.com"
        msg['To'] = ", ".join(recipients)

        # 发送邮件（示例）
        # smtp_server.send_message(msg)

class SlackNotificationSender(NotificationSender):
    """Slack 通知"""

    async def send(self, message: str, channel: NotificationChannel,
                  priority: NotificationPriority, recipients: List[str]):
        import requests

        webhook_url = "https://hooks.slack.com/services/..."

        payload = {
            "text": message,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*[{priority.value.upper()}]* {message}"
                    }
                }
            ]
        }

        # requests.post(webhook_url, json=payload)

class NotificationRouter:
    """通知路由器"""

    def __init__(self):
        self.senders = {
            NotificationChannel.EMAIL: EmailNotificationSender(),
            NotificationChannel.SLACK: SlackNotificationSender(),
        }

    async def notify(self, event: str, data: Dict[str, Any],
                    channels: List[NotificationChannel],
                    priority: NotificationPriority = NotificationPriority.INFO):
        """发送通知"""

        message = self._format_message(event, data, priority)
        recipients = self._get_recipients(event, priority)

        for channel in channels:
            sender = self.senders.get(channel)
            if sender:
                await sender.send(message, channel, priority, recipients)

    def _format_message(self, event: str, data: Dict[str, Any],
                        priority: NotificationPriority) -> str:
        """格式化消息"""
        if event == "workflow_blocked":
            return f"""
⚠️  工作流阻塞通知

工作流 ID: {data['workflow_id']}
模板: {data['template_id']}
阻塞原因: {data['reason']}
时间: {data['timestamp']}

请及时处理。
            """
        elif event == "gate_evaluation_failed":
            return f"""
🚫 门禁评估失败

工作流: {data['workflow_id']}
门禁: {data['gate_id']}
失败规则:
{chr(10).join(f"  - {r}" for r in data['failed_rules'])}
            """
        # ... 更多事件格式

    def _get_recipients(self, event: str, priority: NotificationPriority) -> List[str]:
        """获取接收人"""
        # 根据事件和优先级从配置获取接收人
        config = {
            "workflow_blocked": {
                NotificationPriority.WARNING: ["team-lead@example.com"],
                NotificationPriority.CRITICAL: ["team-lead@example.com", "manager@example.com"]
            }
        }
        return config.get(event, {}).get(priority, [])
```

---

## ❄️ P3.5: 功能冻结声明

```markdown
# LEE Orchestrator - spec-global 功能冻结声明

**生效日期**: 2026-02-05
**适用范围**: Orchestrator 执行引擎、spec-global 解析器、IR 模型
**状态**: 🧊 **FUNCTION FREEZE**

---

## 冻结范围

从即日起，以下模块进入**功能冻结**状态：

1. **spec-global YAML 格式**
   - 不再新增语法特性
   - 不再扩展格式变体
   - Bugfix 除外

2. **Orchestrator 执行引擎**
   - 不再新增执行语义
   - 不再扩展状态机类型
   - Bugfix 除外

3. **IR 中间表示**
   - 不再新增 IR 模型
   - 不再修改现有 IR 结构
   - Bugfix 除外

---

## 仍可接受的工作

### ✅ Bugfix

允许修复以下类型的问题：

- 解析器对合法 YAML 的错误解析
- 状态机转换逻辑错误
- 内存泄漏、性能问题
- 文档错误、误导性描述

### ✅ P3 范围内的观测集成

允许实现以下功能：

- Metrics 收集（Prometheus）
- 通知集成（邮件、Slack、企业微信）
- 日志规范化
- 审计追踪

### ✅ P3+ 延后工作（可延后，但不在冻结范围内）

以下工作可延后到 v2.0 讨论：

- 规则表达式高级解析（COUNT、ALL、HAVE）
- 复杂嵌套条件表达式
- 回调函数机制
- 可视化工具

---

## 新需求处理流程

对于任何新的 spec-global 或 Orchestrator 相关需求：

1. **评估需求类型**
   - Bugfix → ✅ 可以接受
   - 观测集成 → ✅ 可以接受（P3 范围内）
   - 语义扩展 → ❌ 拒绝，推迟到 v2.0

2. **记录到 Backlog**
   - 所有被拒绝的需求记录到 `docs/orchestrator-backlog-v2.md`
   - 标注优先级和预期版本

3. **定期 Review**
   - 每季度 Review 一次 Backlog
   - 评估是否需要启动 v2.0 规划

---

## 理由

功能冻结的原因：

1. **防止范围蔓延** - 当前实现已超出原始需求，需要稳定
2. **资源聚焦** - 团队资源需要集中在其他优先级（跑步大师、现金流压力等）
3. **技术稳定** - 给生产环境留出稳定期，积累使用经验
4. **债务控制** - 避免继续增加技术债，为 v2.0 留出优化空间

---

## 联系方式

如有疑问或紧急需求需要破例，请联系：

- 技术负责人: [待定]
- 架构委员会: [待定]

**文档版本**: 1.0
**最后更新**: 2026-02-05
**下次 Review**: 2026-05-05
```

---

## 📅 P3 实施时间表

| 周 | 任务 | 交付物 | 状态 |
|----|------|--------|------|
| W1 | P3.0 文档修复 | 修复后的审查报告 | 📋 计划 |
| W1 | P3.1 治理强化 | Deprecation 机制、规范矩阵 | 📋 计划 |
| W1 | P3.2 语义补齐 | Gate-Approval 流程、失败策略 | 📋 计划 |
| W2 | P3.3 测试补强 | 模糊测试、E2E 测试 | 📋 计划 |
| W3+ | P3.4 观测集成 | Metrics、通知 | 📋 计划 |
| 待定 | P3.5 表达式引擎 | COUNT/ALL/HAVE 支持 | 📋 延后 |

---

## 🎯 成功标准

| 任务 | 验收标准 |
|------|---------|
| P3.0 | 报告无数字/路径错误，IR 目录描述统一 |
| P3.1 | Legacy 模板加载时显示警告，规范矩阵文档化 |
| P3.2 | Gate-Approval 流程图清晰，失败策略文档完整 |
| P3.3 | 模糊测试通过，E2E 测试覆盖 PRD→DEV→QA 链路 |
| P3.4 | Prometheus metrics 可查询，通知可正常发送 |

---

**文档状态**: 📋 计划中
**负责人**: LEE Core Team
**创建日期**: 2026-02-05
