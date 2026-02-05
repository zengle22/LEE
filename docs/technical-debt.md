# LEE 框架技术债务文档

## 概述

本文档记录 LEE 框架平台的能力缺口、已知问题和后续改进建议。

最后更新：2026-02-05

---

## 一、平台能力缺口修复状态

### ✅ 已修复 (2026-02-05)

| Ticket | 缺口描述 | 优先级 | 状态 |
|--------|---------|--------|------|
| Ticket 1 | Markdown 到契约格式转换能力缺失 | P0 | ✅ 已完成 |
| Ticket 2 | 技术架构契约生成能力缺失 | P0 | ✅ 已完成 |
| Ticket 3 | 测试用例设计工作流未注册 | P0 | ✅ 已完成 |
| Ticket 4 | 缺少输入契约文件的自动发现机制 | P1 | ✅ 已完成 |
| Ticket 5 | UI 页面契约生成器 Agent 未实现 | P0 | ✅ 已完成 |

### 新增能力

1. **Markdown 到契约转换**
   - `skill.prd.markdown_to_contract`: PRD Markdown → frozen-detailed-prd-contract
   - `skill.ui.markdown_to_contract`: UI Spec Markdown → frozen-ui-prototype-contract

2. **技术架构契约生成**
   - `agent.dev.architecture_contract_generator`: PRD → frozen-technical-architecture-contract

3. **测试用例设计工作流**
   - `workflow.qa.test_case_design_pipeline`: 完整的测试用例设计流程
   - 相关 Agents、Skills、Gates 已注册

4. **契约自动发现**
   - `ContractDiscovery` 服务：自动扫描和发现契约文件
   - 支持工作流输入自动匹配

---

## 二、已知问题

### 🔴 P0 - 阻塞性问题

#### 问题 1: 测试套件部分无法运行 (部分修复)

**状态**: 🟡 部分修复
**影响**: 部分测试无法通过
**已修复** (2026-02-05):
- ✅ `test_core.py` - 4/4 测试通过
- ✅ 修复了 `SimpleStateMachine` → `WorkflowStateMachine`
- ✅ 修复了 `MemoryEventBus` → `EventBus`
- ✅ 修复了 `WorkflowInstance` 构造参数 (`parent_level` 移除)

**仍需修复**:
- ❌ `test_execution.py` - 2/10 测试通过
- 原因：测试需要实际的模板文件 (`project_main`, `dept_dev` 等)
- `test_llm_executor` 失败：API 429 错误 (外部服务问题)

**修复建议**:
1. 创建测试用的模板文件
2. 或使用 Mock 模板管理器
3. 为 LLM Executor 测试添加 API mock

**文件位置**:
- `tests/orchestrator/test_core.py` ✅ 已修复
- `tests/orchestrator/test_execution.py` 🟡 部分修复

---

#### 问题 2: 契约发现服务未集成到 Orchestrator

**状态**: 未修复
**影响**: 工作流无法自动使用契约发现功能
**根因**:
- `ContractDiscovery` 服务已创建但未集成到 Orchestrator 主流程
- 缺少 CLI 命令来触发契约扫描

**修复建议**:
1. 在 `WorkflowLoader` 中集成 `ContractDiscovery`
2. 添加 `lee contract discover` CLI 命令
3. 在工作流启动时自动查找和验证输入契约

**相关文件**:
- `src/lee/orchestrator/core/workflow_loader.py` (需要确认文件路径)
- `src/lee/orchestrator/cli/main.py`

---

### 🟡 P1 - 重要问题

#### 问题 3: 缺少契约文件验证 CLI 工具

**状态**: 未实现
**影响**: 无法快速验证契约文件是否符合 schema
**建议**:
- 添加 `lee contract validate <path>` 命令
- 支持批量验证项目中的所有契约文件
- 提供详细的验证错误报告

---

#### 问题 4: 契约版本管理缺失

**状态**: 未实现
**影响**: 无法追踪契约变更历史
**建议**:
1. 添加契约版本字段 (`contract_version`)
2. 实现契约迁移机制
3. 记录契约变更历史

---

#### 问题 5: 缺少契约依赖关系可视化

**状态**: 未实现
**影响**: 难以理解契约之间的依赖关系
**建议**:
- 生成契约依赖关系图
- 支持 Mermaid 格式输出
- 在文档中自动生成依赖图

---

### 🟢 P2 - 优化性问题

#### 问题 6: 新创建的 Skills 和 Agents 未编写测试

**状态**: 未完成
**影响**: 无法验证新功能的正确性
**需要测试的文件**:
1. `spec-global/departments/prd/skills/markdown-to-contract/v1/skill.yaml`
2. `spec-global/departments/ui/skills/markdown-to-contract/v1/skill.yaml`
3. `spec-global/departments/dev/agents/architecture-contract-generator/v1/agent.yaml`
4. `src/lee/orchestrator/core/contract_discovery.py`

**建议**:
- 为每个新功能编写单元测试
- 创建测试契约文件作为测试数据
- 验证输入输出符合 schema

---

#### 问题 7: 缺少端到端集成测试

**状态**: 未实现
**影响**: 无法验证完整的工作流执行
**建议**:
- 创建测试用例验证 `workflow.qa.test_case_design_pipeline`
- 从 PRD Markdown → 测试用例的完整流程测试
- 验证契约发现服务与工作流的集成

---

## 三、后续改进建议

### 短期 (1-2 周)

1. **修复测试套件**
   - 修复导入路径问题
   - 更新测试以适配新 API
   - 确保所有测试通过

2. **契约发现服务集成**
   - 集成到 Orchestrator
   - 添加 CLI 命令

3. **契约验证工具**
   - 实现 `lee contract validate` 命令
   - 支持 JSON Schema 验证

### 中期 (1-2 月)

1. **契约版本管理**
   - 实现契约迁移机制
   - 添加契约变更历史追踪

2. **契约依赖可视化**
   - 生成依赖关系图
   - 集成到文档生成

3. **完整集成测试**
   - 测试用例设计工作流端到端
   - 验证所有契约转换链路

### 长期 (3-6 月)

1. **契约市场**
   - 共享和复用契约模板
   - 契约版本管理服务

2. **契约编辑器**
   - 可视化契约编辑
   - 实时 schema 验证

3. **契约监控**
   - 监控契约使用情况
   - 检测过期或未使用的契约

---

## 四、技术债务跟踪

### 已知技术债务

| ID | 描述 | 优先级 | 状态 | 负责人 |
|----|------|--------|------|--------|
| TD-001 | 测试套件无法运行 | P0 | 🔴 待修复 | - |
| TD-002 | 契约发现服务未集成 | P0 | 🔴 待修复 | - |
| TD-003 | 缺少契约验证 CLI | P1 | 🟡 待实现 | - |
| TD-004 | 契约版本管理缺失 | P1 | 🟡 待实现 | - |
| TD-005 | 新功能缺少测试 | P2 | 🟢 待实现 | - |
| TD-006 | 缺少端到端集成测试 | P2 | 🟢 待实现 | - |

---

## 五、变更日志

### 2026-02-05

**新增**:
- 创建技术债务文档
- 完成平台能力缺口修复 (Ticket 1-5)
- 新增 1 个 workflow, 6 个 agents, 2 个 skills, 2 个 gates
- 创建契约自动发现服务 `ContractDiscovery`

**修复**:
- ✅ `test_core.py` - 4/4 测试通过
- ✅ 修复了导入路径问题 (`SimpleStateMachine` → `WorkflowStateMachine`)
- ✅ 修复了 `MemoryEventBus` → `EventBus`
- ✅ 修复了 `WorkflowInstance` 构造参数

**仍需修复**:
- 🟡 `test_execution.py` - 2/10 测试通过，需要模板文件或 mock
- 🔴 契约发现服务未集成到主流程

---

## 六、审查流程

技术债务文档应定期审查：

1. **每周**: 更新 P0 问题状态
2. **每月**: 评估和更新优先级
3. **每季度**: 归档已解决的问题，添加新发现的问题
