# LEE 框架 v2 方案总结

> 核心代码包重命名 + Spec 按部门组织 + 完善文档体系

## 📋 方案概览

### 两个核心调整

1. **核心代码包命名**：从 `lee` 改为 **`flowcore`**
2. **spec-global 组织**：按部门组织，采用 core/departments/cross 三层结构

### 文档和 Release Notes

- **模块级文档**：每个模块都有 README、ARCHITECTURE、DESIGN
- **框架级文档**：docs/ 下的完整文档
- **变更日志**：changelogs/ 下的版本管理

---

## 🎯 核心代码包：flowcore

### 为什么叫 flowcore？

- **简洁**：一个单词，易输入易记
- **语义清晰**：flow（流程）+ core（核心）= 流程编排核心
- **专业**：符合技术命名惯例
- **可扩展**：未来可以有 flowcore-* 相关包

### 目录结构

```
flowcore/
├── orchestrator/           # 工作流编排器
│   ├── README.md           # 使用文档
│   ├── ARCHITECTURE.md     # 架构文档
│   ├── DESIGN.md           # 设计文档
│   └── *.py                # 代码文件
├── engines/                # 执行引擎
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── base.py             # LEE 接口定义
│   ├── python_exec.py
│   ├── single_agent.py
│   └── metagpt/            # MetaGPT 适配层
│       └── README.md
├── utils/                  # 工具模块
│   └── README.md
└── cli/                    # 命令行工具
    └── README.md
```

### Import 示例

```python
# 核心模块
from flowcore.orchestrator.runner import run_workflow
from flowcore.orchestrator.state_machine import StateMachine

# 引擎
from flowcore.engines.base import LEERequest, LEEResult
from flowcore.engines.metagpt.adapter import run_lee_unit

# 工具
from flowcore.utils.logging import setup_logger
from flowcore.utils.ids import generate_run_id

# CLI
python -m flowcore.cli.main status
```

---

## 🏢 spec-global：按部门组织

### 三层结构

```
spec-global/
├── core/           # 平台级基础规范（不归任何部门）
├── departments/    # 按部门垂直切分
└── cross/          # 跨部门流程和接口
```

### 1. core/ - 平台级基础规范

**不归属于任何部门的基础概念**：

```
core/
├── workflows/      # 通用技术流程
│   ├── _template.yaml
│   └── test_round.yaml
├── work_items/     # 基础对象定义
│   ├── bug.yaml
│   ├── feature.yaml
│   └── incident.yaml
├── gates/          # 通用门禁策略
│   ├── test_coverage.yaml
│   └── release_policy.yaml
├── contracts/      # 通用 contract
│   └── acceptance_report_contract.yaml
└── teams/          # 通用 team 模板
    ├── code_impl_team.yaml
    └── arch_debate_team.yaml
```

### 2. departments/ - 按部门垂直切分

**每个部门内部按类型细分**：

```
departments/{dept}/
├── workflows/      # 部门内部流程
├── agents/         # 部门专属 agent
├── skills/         # 部门技能
└── contracts/      # 部门交付物契约
```

**部门列表**：

- **pm/**：产品管理部门
  - workflows: 机会分析、需求录入、PRD 评审
  - agents: 产品经理、业务分析师、需求评审员
  - contracts: PRD、用户故事

- **dev/**：开发部门
  - workflows: 架构设计、代码实现、代码审查、自测
  - agents: 技术架构师、后端工程师、前端工程师、代码审查员
  - contracts: API 规范、设计文档

- **qa/**：测试部门
  - workflows: 用例设计、测试执行、Bug 分析、测试报告
  - agents: 测试设计师、测试执行员、Bug 分析师
  - contracts: 测试计划、Bug 报告、测试报告

- **ops/**：运维部门
  - workflows: 部署、监控、故障响应
  - agents: DevOps 工程师、SRE
  - contracts: 部署计划

### 3. cross/ - 跨部门协作

**跨部门流程和接口**：

```
cross/
├── workflows/          # E2E 跨部门流程
│   ├── pm-dev-qa/
│   │   └── e2e_feature_delivery.yaml
│   ├── dev-qa-ops/
│   │   └── release_pipeline.yaml
│   └── all/
│       └── incident_response.yaml
├── interfaces/         # 部门间接口/契约
│   ├── pm-dev/
│   │   ├── requirement_package_contract.yaml
│   │   └── design_feedback_contract.yaml
│   ├── dev-qa/
│   │   ├── test_input_contract.yaml
│   │   └── bug_report_contract.yaml
│   └── qa-ops/
│       └── release_readiness_checklist.yaml
└── teams/              # 跨部门团队定义
    ├── feature_squad.yaml
    └── incident_swat_team.yaml
```

### Spec ID 逻辑命名

使用简短的逻辑 ID，通过映射表转换为文件路径：

```
pm/workflows/requirement_intake.yaml
→ spec-global/departments/pm/workflows/requirement_intake.yaml

dev/workflows/code_impl.yaml
→ spec-global/departments/dev/workflows/code_impl.yaml

cross/workflows/pm-dev-qa/e2e_feature_delivery.yaml
→ spec-global/cross/workflows/pm-dev-qa/e2e_feature_delivery.yaml

cross/interfaces/pm-dev/requirement_package_contract.yaml
→ spec-global/cross/interfaces/pm-dev/requirement_package_contract.yaml
```

---

## 📚 文档体系

### 三层文档结构

1. **模块级文档**（代码包内）：每个模块的 README、ARCHITECTURE、DESIGN
2. **框架级文档**（docs/）：面向用户的完整文档
3. **变更日志**（changelogs/）：版本变更记录

### 模块级文档示例

```
flowcore/
├── orchestrator/
│   ├── README.md           # 使用文档
│   ├── ARCHITECTURE.md     # 架构文档
│   └── DESIGN.md           # 设计文档
├── engines/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   └── metagpt/
│       └── README.md
├── utils/
│   └── README.md
└── cli/
    └── README.md
```

### 框架级文档

```
docs/
├── AI-CONSTITUTION.md           # AI 宪法
├── LEE-Overview.md              # 框架总览
├── LEE-Interface-Spec.md        # 接口规范
├── Workflow-Spec-Guide.md       # Workflow 编写指南
├── Orchestrator-Guide.md        # 编排器指南
├── Integration-Guide.md         # 集成指南
├── MetaGPT-Integration.md       # MetaGPT 集成
├── Workspace-Config.md          # Workspace 配置
└── Spec-Organization.md         # Spec 组织结构说明
```

### 变更日志

```
changelogs/
├── README.md         # 总览和索引
├── v0.1.0.md         # 版本 0.1.0 变更
└── unreleased.md     # 未发布的变更
```

每个版本包含：

- **新增** (Added)：新功能
- **变更** (Changed)：功能改进
- **废弃** (Deprecated)：计划移除的功能
- **移除** (Removed)：已移除的功能
- **修复** (Fixed)：Bug 修复
- **安全** (Security)：安全修复
- **兼容性** (Compatibility)：破坏性变更说明

---

## 🔄 Import 路径变化

### 原始

```python
from orchestrator.core.state_machine import StateMachine
from metagpt.lee.protocol import LEERequest
```

### 目标

```python
from flowcore.orchestrator.state_machine import StateMachine
from flowcore.engines.metagpt.protocol import LEERequest
```

---

## 📁 生成的文件

### 核心文档

- `README.md` - 框架总览
- `MIGRATION_PLAN.md` - 详细迁移计划（v2）
- `GETTING_STARTED.md` - 快速开始指南
- `CHANGELOG.md` - 变更日志总览

### 配置模板

- `config/workspace.template.yaml` - Workspace 配置模板

### 工具脚本

- `tools/migrate.sh` - 自动化迁移脚本
- `tools/update_imports.py` - Python import 批量更新

### 变更日志

- `changelogs/README.md` - 变更日志总览
- `changelogs/v0.1.0.md` - v0.1.0 版本变更
- `changelogs/unreleased.md` - 未发布变更

---

## 🚀 快速开始

```bash
# 1. 创建备份
cp -r . ../LEE-backup-$(date +%Y%m%d)

# 2. 执行迁移
bash tools/migrate.sh

# 3. 更新 imports
python tools/update_imports.py

# 4. 验证
python -m py_compile flowcore/**/*.py

# 5. 清理（确认无误后）
rm -rf orchestrator ai-spec MetaGPT/metagpt/lee
```

---

## 💡 关键设计决策

### Q1: 为什么核心代码包叫 flowcore？

**A**: 简洁、语义清晰、专业、可扩展。

### Q2: spec-global 为什么要按部门组织？

**A**: 符合"AI 一人公司"的组织思想：
- **core/**：平台级基础规范
- **departments/**：按部门垂直切分
- **cross/**：跨部门流程和接口

既体现组织结构，又为跨部门协作提供专门区域。

### Q3: 跨部门流程和接口放哪里？

**A**: 放在 `cross/` 目录：
- **cross/workflows/**：E2E 跨部门流程
- **cross/interfaces/**：部门间接口契约
- **cross/teams/**：跨部门团队定义

这样避免了"归属争夺战"，让跨部门协作有专门的地方。

---

## 📖 相关文档

- [MIGRATION_PLAN.md](MIGRATION_PLAN.md) - 详细迁移计划（v2）
- [GETTING_STARTED.md](GETTING_STARTED.md) - 快速开始指南
- [README.md](README.md) - 框架总览
- [changelogs/v0.1.0.md](changelogs/v0.1.0.md) - v0.1.0 版本变更
