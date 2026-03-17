# Gate Dual-Axis API Contract Module

## Overview

本模块定义了 SRC-041 Gate 双轴模型改造的 API 协议，将 Gate 分类从单一的 `gate_type` 轴收敛到双轴模型（`purpose` + `decision_mode`）。

## Version

- **当前版本**: 1.0.0
- **状态**: draft → pending freeze
- **发布日期**: 2026-03-16

## Source References

- TECH-FEAT-SRC-041-001: Gate 双轴模型技术架构设计
- ADR-017: Gate 治理语义归一化与人工审批上下文统一治理
- FEAT-SRC-041-001: Gate purpose 与 decision mode 目标与移动界

## Core Concepts

### Dual-Axis Model

| 轴 | 类型 | 值域 | 用途 |
|---|------|------|------|
| purpose | GatePurpose | review, approval | 定义 Gate 的职责语义 |
| decision_mode | GateDecisionMode | auto, conditional_human, human_required | 定义 Gate 的决策方式 |

### Valid Combinations

| purpose | decision_mode | 组合合法性 | 说明 |
|---------|---------------|-----------|------|
| REVIEW | AUTO | ✓ 合法 | 自动质量检查 |
| REVIEW | CONDITIONAL_HUMAN | ✓ 合法 | 条件触发人工审核 |
| REVIEW | HUMAN_REQUIRED | ✓ 合法 | 必须人工审核 |
| APPROVAL | AUTO | ✗ 非法 | 正式确认不能自动 |
| APPROVAL | CONDITIONAL_HUMAN | ✗ 非法 | 正式确认不能条件触发 |
| APPROVAL | HUMAN_REQUIRED | ✓ 合法 | 正式确认必须人工 |

## Module Contents

```
dev/src/api-contract/modules/gate-dual-axis/v1/
├── api-contract.yaml          # API 协议定义
├── contract-analysis.yaml     # 需求分析
├── contract-selfcheck.json    # 自检报告
└── README.md                  # 本文件
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/gate-approvals | POST | 创建 Gate Approval |
| /api/v1/gate-approvals/{gate_id} | GET | 获取 Gate Approval |
| /api/v1/workflows/{workflow_id}/gates | GET | 列出 Gates |
| /api/v1/gate-approvals/{gate_id}/decide | POST | 决策 Gate |

## Data Model Extensions

### GateApproval 新增字段

```python
purpose: GatePurpose                      # 必填：Gate 目的
decision_mode: GateDecisionMode           # 必填：决策方式
legacy_gate_type: Optional[str]           # 可选：历史分类映射
```

## Validation Rules

| Rule ID | Description | Severity |
|---------|-------------|----------|
| VR-001 | purpose 必须是 REVIEW 或 APPROVAL | blocker |
| VR-002 | decision_mode 必须是 AUTO/CONDITIONAL_HUMAN/HUMAN_REQUIRED | blocker |
| VR-003 | APPROVAL + AUTO 组合非法 | blocker |
| VR-004 | APPROVAL + CONDITIONAL_HUMAN 组合非法 | blocker |

## Legacy Compatibility

历史 `gate_type` 会自动映射到双轴模型：

| legacy_gate_type | purpose | decision_mode |
|-----------------|---------|---------------|
| code_review | REVIEW | HUMAN_REQUIRED |
| quality_gate | REVIEW | HUMAN_REQUIRED |
| freeze | APPROVAL | HUMAN_REQUIRED |
| release | APPROVAL | HUMAN_REQUIRED |
| merge | APPROVAL | HUMAN_REQUIRED |

## Self-Check Status

- **自检结果**: PASSED (10/10)
- **自检时间**: 2026-03-16
- **准备冻结**: Yes

## Next Steps

1. Contract Freeze Gate 审批
2. 基于 Contract 进行后端实现 (TECH-FEAT-SRC-041-001)
3. 更新 CLI 展示层（P1）
4. 数据库迁移（P1）

## Related Modules

- `src/lee/orchestrator/storage/models.py`: GateApproval 数据模型
- `src/lee/orchestrator/execution/runners/gate_runner.py`: HumanGateRunner 实现
