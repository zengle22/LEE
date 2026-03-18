# ADR-027 端到端验证指南

> **版本**: 1.0
> **创建日期**: 2026-03-17
> **状态**: 待执行

## 概述

本文档描述如何在产品项目 (如 running-coach) 中验证 ADR-027 创建的新工作流模板。

## 前置条件

### 1. 环境准备

```bash
# 确保 LEE 框架已更新到最新版本
cd running-coach/LEE
git pull origin main

# 安装依赖
pip install -e .

# 验证新模板已存在
ls -la spec-global/workflows/core/
# 应包含:
# - feat2release-l3-template.yaml
# - release2devplan-l3-template.yaml
# - release2testplan-l3-template.yaml
# - feat2plan-l2-template.yaml

# 验证新 Gate 已存在
ls -la spec-global/core/gates/
# 应包含:
# - release-generate-gate/v1/gate.yaml
# - release-validate-gate/v1/gate.yaml
# - output-contract-gate/v1/gate.yaml
# - task-validate-gate/v1/gate.yaml
# - devplan-freeze-gate/v1/gate.yaml
# - test-set-validate-gate/v1/gate.yaml
# - testplan-freeze-gate/v1/gate.yaml
```

### 2. 测试数据准备

需要准备以下测试数据：

#### 2.1 FEAT Bundle (frozen)

```yaml
# spec/requirements/FEAT-001.yaml
id: FEAT-001
ssot_type: FEAT
status: frozen
title: "用户验证码登录功能"
description: "支持用户通过手机号 + 验证码方式登录"
acceptance_criteria:
  - id: AC-001
    description: "验证码发送 API 正常调用"
    steps: [...]
    expected: "API 返回成功，用户收到验证码"
  - id: AC-002
    description: "主方案失败时自动切换备用方案"
    steps: [...]
    expected: "备用方案启动，用户仍能收到验证码"
source_refs:
  - EPIC-001
  - SRC-001
```

#### 2.2 Delivery Prep 输出 (TASK/TECH/UI frozen)

```yaml
# spec/tasks/FEAT-001/TASK-FEAT-001-001.yaml
id: TASK-FEAT-001-001
ssot_type: TASK
status: frozen
feat_ref: FEAT-001
title: "验证码发送 API 实现"
description: "实现验证码发送 API，支持主备方案切换"
role: backend
assignee: dev-backend-001
estimated_effort: 4h

# spec/tasks/FEAT-001/TASK-FEAT-001-002.yaml
id: TASK-FEAT-001-002
ssot_type: TASK
status: frozen
feat_ref: FEAT-001
title: "验证码登录前端页面实现"
description: "实现验证码登录前端页面和交互"
role: frontend
assignee: dev-frontend-001
estimated_effort: 4h

# spec/tech/FEAT-001/tech.yaml
id: TECH-FEAT-001
ssot_type: TECH
status: frozen
feat_ref: FEAT-001
architecture: "前后端分离"
components:
  - name: "验证码服务"
    description: "负责验证码生成、发送、验证"
  - name: "短信服务"
    description: "对接短信服务商 API"
```

## 验证步骤

### Step 1: 运行 FEAT2PLAN L2 工作流

```bash
# 使用 lee 命令运行 FEAT2PLAN 工作流
lee run workflow.core.feat2plan \
  --feat-bundle FEAT-001 \
  --release-id release-001

# 或使用 Python 脚本
python -m lee.orchestrator.cli run workflow.core.feat2plan \
  --input '{"feat_bundle_refs": ["FEAT-001"], "release_id": "release-001"}'
```

### Step 2: 验证 L3 执行

#### 2.1 验证 FEAT2RELEASE (L3-1)

检查输出：
```bash
cat spec/releases/release-001.yaml
```

期望输出：
```yaml
id: release-001
ssot_type: RELEASE
status: draft
version: "1.0.0"
release_type: minor
feat_refs:
  - FEAT-001
release_window:
  start_date: "2026-03-17"
  end_date: "2026-03-31"
```

#### 2.2 验证 RELEASE2DEVPLAN (L3-2)

检查输出：
```bash
cat spec/devplans/devplan-001.yaml
cat spec/devplans/001/task_execution_order.yaml
```

期望输出：
```yaml
# devplan-001.yaml
id: devplan-001
ssot_type: DEVPLAN
status: frozen
release_ref: release-001
task_refs:
  - TASK-FEAT-001-001
  - TASK-FEAT-001-002

# task_execution_order.yaml
task_execution_order:
  - lane: backend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-001
        depends_on: []
        assignee: dev-backend-001
  - lane: frontend
    priority: P0
    tasks:
      - task_id: TASK-FEAT-001-002
        depends_on: [TASK-FEAT-001-001]
        assignee: dev-frontend-001
```

#### 2.3 验证 RELEASE2TESTPLAN (L3-3)

检查输出：
```bash
cat spec/testplans/testplan-001.yaml
cat spec/testplans/001/test_strategy.yaml
cat qa_specs_dir/test-sets/ts-verification-code.yaml
```

期望输出：
```yaml
# testplan-001.yaml
id: testplan-001
ssot_type: TESTPLAN
status: frozen
release_ref: release-001
test_strategy_ref: "spec/testplans/001/test_strategy.yaml"
test_set_refs:
  - ts-verification-code

# ts-verification-code.yaml
id: ts-verification-code
ssot_type: TESTSET
status: frozen
feat_ref: FEAT-001
test_cases:
  - id: tc-001
    type: smoke
    priority: P0
    description: "验证码发送 API 正常调用"
    steps: [...]
    expected: "API 返回成功，用户收到验证码"
    trace_to:
      - FEAT-001.AC-001
```

### Step 3: 验证输出 Contract

检查输出 Contract 验证结果：
```bash
cat .workflow/release-001/output_contract.json
```

期望输出：
```json
{
  "release_id": "release-001",
  "devplan_status": "frozen",
  "testplan_status": "frozen",
  "devplan_path": "spec/devplans/devplan-001.yaml",
  "testplan_path": "spec/testplans/testplan-001.yaml",
  "traceability": {
    "devplan_traceability": true,
    "testplan_traceability": true,
    "all_feats_covered": true
  },
  "validation_passed": true,
  "ready_for_downstream": true
}
```

### Step 4: 验证驱动下游工作流

#### 4.1 验证驱动 Dev 执行

```bash
# 查看生成的 Dev L2 实例
cat .workflow/release-001/downstream_instances.yaml
```

#### 4.2 验证驱动 QA 执行

```bash
# 查看生成的 QA L2 实例
cat .workflow/release-001/qa_execution_instance.yaml
```

## 验收标准

### 功能验收

- [ ] FEAT Bundle 输入后，自动生成 RELEASE 对象 (draft)
- [ ] RELEASE 可正确派生 DEVPLAN (frozen) 和 TESTPLAN (frozen)
- [ ] DEVPLAN 包含所有 FEAT 的 TASK，执行顺序合理
- [ ] TESTPLAN 包含所有 FEAT 的 Test Set，追溯性完整
- [ ] 输出 Contract 验证通过
- [ ] DEVPLAN/TESTPLAN 可驱动现有 Dev/QA 工作流

### 质量验收

- [ ] 所有 Gate 正确执行（自动检查 + 人类审批）
- [ ] 错误场景正确处理（如 FEAT 未冻结、TASK 缺失）
- [ ] 输出 YAML Schema 验证通过
- [ ] 端到端执行成功率 >= 95%

## 错误场景测试

### 场景 1: FEAT 未冻结

```bash
# 修改 FEAT 状态为 draft
# spec/requirements/FEAT-001.yaml
status: draft  # 应该是 frozen

# 运行工作流，应该失败
lee run workflow.core.feat2plan --feat-bundle FEAT-001

# 期望错误消息
# Error: FEAT-001 is not frozen, cannot proceed
```

### 场景 2: TASK 缺失

```bash
# 删除 TASK 文件
rm spec/tasks/FEAT-001/TASK-FEAT-001-001.yaml

# 运行 RELEASE2DEVPLAN，应该失败
# 期望错误消息
# Error: TASK coverage validation failed, FEAT-001 has no TASK
```

### 场景 3: Test Set 追溯性缺失

```bash
# 修改 Test Set，移除 trace_to
# qa_specs_dir/test-sets/ts-verification-code.yaml
test_cases:
  - id: tc-001
    # trace_to: [...]  # 移除追溯性

# 运行 RELEASE2TESTPLAN，应该失败
# 期望错误消息
# Error: Traceability validation failed, tc-001 missing trace_to
```

## 调试指南

### 查看工作流日志

```bash
# 查看工作流执行日志
cat .workflow/release-001/workflow.log

# 查看 Gate 执行日志
cat .workflow/release-001/gate_logs/
```

### 查看 SSOT Registry

```bash
# 查看 SSOT Registry，确认新对象已注册
python scripts/check-ssot-governance.py

# 验证 SSOT 链完整性
python scripts/git_ssot_hook_checks.py --verbose
```

## 后续行动

### 调试通过后

1. 记录调试过程和结果
2. 更新 ADR-027 实施状态
3. 准备 Phase 2 (L2 编排优化)

### 遇到问题

1. 记录错误日志
2. 分析问题根因
3. 修复模板或 Gate 定义
4. 重新运行验证

---

## 附录：完整命令参考

```bash
# 运行完整 FEAT2PLAN 工作流
lee run workflow.core.feat2plan \
  --feat-bundle FEAT-001 \
  --release-id release-001 \
  --verbose

# 仅运行 FEAT2RELEASE L3
lee run template.core.feat2release \
  --feat-bundle FEAT-001 \
  --release-id release-001

# 仅运行 RELEASE2DEVPLAN L3
lee run template.core.release2devplan \
  --release-ref release-001 \
  --task-bundle spec/tasks/FEAT-001/

# 仅运行 RELEASE2TESTPLAN L3
lee run template.core.release2testplan \
  --release-ref release-001 \
  --feat-ac spec/requirements/FEAT-001.yaml \
  --tech-spec spec/tech/FEAT-001/tech.yaml

# 查看 Gate 状态
lee gate list --workflow release-001

# 批准 Gate
lee gate approve gate.dev.devplan_freeze_gate --workflow release-001
```
