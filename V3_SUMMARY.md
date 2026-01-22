# LEE 框架重组方案 v3 - 完整总结

## 🎯 核心调整

### 1. 核心代码包命名
- 从 `lee` → **`flowcore`**
- 语义：flow（流程）+ core（核心）

### 2. Spec 按部门组织（7 个部门）

```
spec-global/departments/
├── stg/        # 战略部门（新增）
├── prd/        # 产品部门（原 pm 改名）
├── ui/         # UI 设计部门（新增）
├── dev/        # 开发部门
├── qa/         # 测试部门
├── ops/        # 运维部门
└── office/     # 办公室/行政（新增）
```

### 3. 每个部门的结构

每个部门现在包含 **6 个部分**：

```
departments/{dept}/
├── README.md       # 部门说明文档（迁移后自动创建）
├── workflows/      # 部门工作流
├── gates/          # 部门门禁（新增）
├── agents/         # 部门专属 agent
├── skills/         # 部门技能
└── contracts/      # 部门交付物契约
```

### 4. 部门职责对比

| 部门 | 原名称 | 职责 | 主要 Agent |
|------|--------|------|-----------|
| **stg** | 新增 | 战略分析、市场研究、商业洞察 | business-opportunity-analyzer, supply-analyzer, google-keyword-searcher |
| **prd** | pm | 产品需求文档（PRD）编写 | prd-writer, requirement-reviewer |
| **ui** | 新增 | UI 设计、设计系统 | ui-designer, icon-generator |
| **dev** | - | 架构设计、代码实现 | tech-architect, backend-engineer |
| **qa** | - | 测试用例设计、测试执行 | test-case-creator, test-executor |
| **ops** | - | 部署、监控、故障响应 | devops-engineer, sre |
| **office** | 新增 | 暂时不属于其它部门的 spec | （待添加） |

## 📂 生成的文件

### 核心文档
- `README.md` - 框架总览
- `MIGRATION_PLAN.md` - 迁移计划 v3
- `GETTING_STARTED.md` - 快速开始
- `CHANGELOG.md` - 变更日志

### 工具脚本
- `tools/migrate.sh` - 迁移脚本（已更新）
- `tools/update_imports.py` - Import 更新工具
- `tools/create_department_readmes.py` - 部门 README 生成器（新增）

### 配置模板
- `config/workspace.template.yaml` - Workspace 配置模板

### 变更日志
- `changelogs/README.md`
- `changelogs/v0.1.0.md`
- `changelogs/unreleased.md`

## 🚀 执行迁移

```bash
# 1. 查看迁移计划
cat MIGRATION_PLAN.md

# 2. 创建备份
cp -r . ../LEE-backup-$(date +%Y%m%d)

# 3. 执行迁移
bash tools/migrate.sh

# 4. 更新 imports
python tools/update_imports.py

# 5. 验证
python -m py_compile flowcore/**/*.py

# 6. 查看部门 README
ls spec-global/departments/*/README.md
cat spec-global/departments/stg/README.md
```

## 📋 迁移后的部门 README

迁移脚本会自动为每个部门创建完整的 README.md，包含：

1. **部门职责**：部门定位和主要职责
2. **目录结构**：部门的文件组织
3. **工作流列表**：所有工作流及输入输出
4. **门禁列表**：所有门禁及触发条件
5. **Agent 列表**：所有 agent 及职责
6. **技能列表**：所有技能及说明
7. **契约列表**：所有契约及说明
8. **跨部门协作**：与其他部门的协作关系

### 示例：战略部门 README

```markdown
# 战略部门 (stg)

## 部门职责

负责商业机会分析、市场研究、供应链分析、行业洞察和趋势研究

### 主要职责

- 市场机会识别与评估
- 商业洞察生成
- 供应链分析
- 行业趋势研究
- 竞争分析

## 工作流 (workflows)

| 工作流 | 说明 | 输入 | 输出 |
|--------|------|------|------|
| market_research.yaml | 市场研究工作流 | 市场研究需求 | 市场研究报告 |
| opportunity_analysis.yaml | 机会分析工作流 | 业务机会 | 机会评估报告 |
| supply_analysis.yaml | 供应链分析工作流 | 供应链数据 | 供应链分析报告 |

## 门禁 (gates)

| 门禁 | 触发条件 | 检查项 |
|------|----------|--------|
| business_value_check.yaml | 商业价值检查 | 提交 PRD 前 | 商业价值评分 >= 80 |
| market_fit_gate.yaml | 市场契合度检查 | 产品发布前 | 市场需求验证通过 |

## Agent 列表

| Agent | 职责 | 说明 |
|-------|------|------|
| business-opportunity-analyzer.yaml | 商业机会分析 | 识别和分析商业机会 |
| supply-analyzer.yaml | 供应链分析 | 分析供应链结构和成本 |
| google-keyword-searcher.yaml | 关键词搜索 | 搜索市场关键词数据 |
| google-trend-analyzer.yaml | 趋势分析 | 分析市场趋势 |
| industry-structure-analyzer.yaml | 行业结构分析 | 分析行业结构和竞争格局 |

## 跨部门协作

| 协作部门 | 接口契约 | E2E 工作流 |
|----------|----------|------------|
| prd | stg-prd 业务需求契约 | 市场到产品 E2E 工作流 |
```

## ✨ 主要改进

### 相比 v2 的改进

1. **新增 3 个部门**：stg、ui、office
2. **pm → prd**：更聚焦于产品需求文档
3. **每个部门增加 gates**：完整的质量控制
4. **自动生成部门 README**：迁移完成后自动创建
5. **更完整的跨部门协作**：明确列出接口契约

## 📊 Agent 迁移映射

### 迁移到 stg（战略部门）

```
ai-spec/specs/common/agents/
├── business-opportunity-analyzer.yaml  → stg/agents/
├── supply-analyzer.yaml                  → stg/agents/
├── google-keyword-searcher.yaml        → stg/agents/
├── google-trend-analyzer.yaml          → stg/agents/
└── industry-structure-analyzer.yaml    → stg/agents/
```

### 迁移到 ui（UI 设计部门）

```
ai-spec/specs/common/agents/
├── icon-generator.yaml           → ui/agents/
├── ui-contract-generator.yaml    → ui/agents/
└── ui-contract-validator.yaml    → ui/agents/
```

### 迁移到 prd（产品部门，原 pm）

```
ai-spec/specs/common/agents/
├── prd-writer.yaml               → prd/agents/
├── requirement-reviewer.yaml      → prd/agents/
└── product-goal-analyzer.yaml    → prd/agents/
```

## 🎁 迁移后自动创建的内容

### 7 个部门的 README.md

每个部门都会自动生成完整的 README 文档，包含：

- 部门职责说明
- 工作流、门禁、Agent、技能、契约清单
- 跨部门协作关系

### 自动创建的部门文档

```
spec-global/departments/
├── stg/README.md    # 战略部门
├── prd/README.md    # 产品部门
├── ui/README.md     # UI 设计部门
├── dev/README.md    # 开发部门
├── qa/README.md     # 测试部门
├── ops/README.md    # 运维部门
└── office/README.md # 办公室/行政
```

## 🔧 工具说明

### migrate.sh

自动化迁移脚本，执行以下步骤：

1. 创建目录结构（7 个部门）
2. 迁移 orchestrator
3. 迁移 MetaGPT 适配层
4. 迁移 ai-spec（按部门重组）
5. 创建基础文件
6. **调用 create_department_readmes.py 创建部门 README**
7. 生成迁移报告

### create_department_readmes.py

部门 README 生成器：

- 定义了 7 个部门的完整配置
- 自动生成每个部门的 README.md
- 包含职责、工作流、门禁、Agent、技能、契约、协作

## 📖 相关文档

- **MIGRATION_PLAN.md** - 详细迁移计划 v3
- **GETTING_STARTED.md** - 快速开始指南
- **README.md** - 框架总览
- **changelogs/v0.1.0.md** - v0.1.0 版本变更

## ✅ 审核检查清单

在执行迁移前，请确认：

- [ ] 已审核 MIGRATION_PLAN.md
- [ ] 已创建备份
- [ ] 理解 7 个部门的划分
- [ ] 了解每个部门的 gates 结构
- [ ] 知道 pm → prd 的变更

## 🎯 执行迁移

```bash
bash tools/migrate.sh
```

迁移完成后：
1. 查看迁移报告：`cat MIGRATION_REPORT.md`
2. 查看部门文档：`ls spec-global/departments/*/README.md`
3. 更新 imports：`python tools/update_imports.py`
4. 验证：`python -m py_compile flowcore/**/*.py`
