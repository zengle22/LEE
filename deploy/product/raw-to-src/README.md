# Raw-to-Src 部署说明

这不是独立服务栈部署，而是 `workflow.product.task.raw_to_src` 的独立运行配置。

## 流程概述

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Raw Input   │ ──▶ │ Source      │ ──▶ │ Source      │
│ (ADR/Raw)   │     │ Normalization│     │ Review      │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ SRC Freeze  │ ◀── │ Approval    │ ◀── │ Review      │
│ (冻结)      │     │ Gate        │     │ (六大维度)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           ▲
                    ┌──────┴──────┐
                    │ Auto Check  │
                    │ (ADR-025)   │
                    └─────────────┘
```

## 运行

### 基本用法

```powershell
./run.ps1 -ProjectDir E:\ai\LEE -SpecPath E:\ai\LEE\spec\adr\ADR-012__raw-to-src-yu-src-to-epic-fencengchaifen.md
```

### 使用 ADR 作为输入

```powershell
./run.ps1 -ProjectDir C:\path\to\LEE -SpecPath C:\path\to\LEE\spec\adr\ADR-025__ssot-requirement-axis-acceptance-governance.md
```

## ADR-025 验收卡点

### 验收流程

根据 ADR-025，SRC 冻结前必须通过以下验收卡点：

| 步骤 | 类型 | 检查内容 | Gate 类型 |
|------|------|----------|-----------|
| `src_acceptance_auto_check` | Auto Gate | Schema/Contract/Completeness/Dependency | Auto |
| `src_acceptance_review` | Review Gate | 六大维度评审（功能逻辑、用户体验、功能完整、逻辑漏洞、行业差距、改进空间） | Review |
| `src_acceptance_approval_gate` | Approval Gate | P0/P1 缺陷清零验证 | Approval |

### 验收报告

验收完成后，验收报告存储在：
```
.artifacts/active/product/src/{src_id}/acceptance-report-v{version}.yaml
```

### 缺陷处理

| 严重性 | 处理要求 |
|--------|----------|
| P0 | 必须修复，不允许绕过 |
| P1 | 原则必须修复，特殊情况需 PO + Tech Lead 共同决策可延期 |
| P2 | 记录为技术债务，纳入 backlog |
| P3 | 改进建议，可选实施 |

## 健康检查

```powershell
python -m lee.cli.main workflow-registry health --layer raw-to-src --project-dir E:\ai\LEE
```

健康项：

- workflow template 已注册
- template 引用的 contract 可解析
- raw 层无需预置 canonical SRC 输入
- ADR-025 验收卡点 agent 已配置

## 回滚

- 停止新的 `product.raw-to-src` 运行
- 回退 `config/workflow-registry.yaml`
- 回退 `spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml`

## 联合部署

- `raw-to-src` 可独立运行
- 若需要联动完整主链，继续执行 `product.main`

## 参考文档

- ADR-025: SSOT Requirement Axis Acceptance Governance
- ADR-005: Gate 三分类治理模型
