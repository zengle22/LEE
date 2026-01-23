# Dev Execute Skill

> 临时研发需求执行技能 - 按照标准 OpenSpec 13 步流程执行研发任务

## 概述

这个 Skill 用于执行临时研发需求，确保所有研发工作都遵循标准的 OpenSpec 流程，使用 Orchestrator 进行状态管理和流程控制。

## 触发命令

```
/dev-execute <需求描述> [options]
```

## 核心原则

### 1. 流程强制

- 必须遵循 13 步 OpenSpec 流程
- 禁止跳过任何步骤
- 所有步骤必须通过 Orchestrator 执行

### 2. 自动推进

- 无人工门禁的步骤自动连续执行
- 遇到人工门禁时停下等待审批
- 审批通过后继续自动推进

### 3. 质量保证

- 每步必须产出指定交付物
- 交付物必须通过验证
- 整改机制确保质量达标

## 执行流程详解

### Phase 1: 初始化准备

#### 1.1 解析需求

从用户输入中提取：

```yaml
requirement:
  title: <从需求描述提取>
  description: <完整需求描述>
  scope: <影响范围>
  acceptance_criteria: <验收标准>
```

#### 1.2 确定 Phase 信息

```python
# 自动生成 Phase ID
phase_id = f"phase{next_number}-{slug(title)}"

# 确定目录
project_dir = "project/AI跑步教练"  # 或用户指定
phase_dir = f"{project_dir}/dev/{phase_id}"
```

#### 1.3 创建 Phase 配置

创建 `{phase_dir}/phase-config.yaml`:

```yaml
# Phase 配置文件 - 由 /dev-execute 自动生成
id: phase12-avatar-upload
name: 用户头像上传
description: |
  实现用户头像上传功能，支持裁剪和压缩。

  功能要求:
  - 支持从相册选择或拍照
  - 提供裁剪框，支持正方形裁剪
  - 自动压缩到合适尺寸
  - 上传到 OSS 并更新用户信息

phase_dir: project/AI跑步教练/dev/phase12-avatar-upload
project_dir: project/AI跑步教练
change_id: CHG-001

metadata:
  type: adhoc
  priority: P1
  created_at: "2026-01-13T18:30:00"
  created_by: claude
  original_requirement: |
    实现用户头像上传功能，支持裁剪和压缩
```

### Phase 2: 生成 Workflow

#### 2.1 调用 Workflow Generator

```bash
python -m orchestrator generate-workflow \
  --template ai-spec/specs/org/development/workflows/phase-openspec-flow/v1/workflow.yaml \
  --config "$PHASE_DIR/phase-config.yaml" \
  --output "$PHASE_DIR/workflow.yaml"
```

#### 2.2 验证生成结果

确认生成的 workflow.yaml 包含 13 个必需步骤：

| # | Step ID | 名称 |
|---|---------|------|
| 1 | p1_openspec_init | OpenSpec 初始化 |
| 2 | p2_requirement_calibration | 需求校准 |
| 3 | p3_test_contract | 测试契约生成 |
| 4 | p4_openspec_proposal | OpenSpec 变更提案 |
| 5 | p5_implementation | 代码实现 |
| 6 | p6_unit_test | 单元测试 |
| 7 | p7_code_review | Code Review |
| 8 | p8_retrospective | Phase 复盘 |
| 9 | p9_knowledge_update | 知识沉淀 |
| 10 | p10_openspec_archive | OpenSpec 归档 |
| 11 | p11_phase_acceptance | Phase 验收 |
| 12 | p12_knowledge_merge | 知识合并 |
| 13 | p13_handover | Phase 交接 |

### Phase 3: 初始化 Orchestrator

```bash
python -m orchestrator init "$PHASE_DIR" --workflow "$PHASE_DIR/workflow.yaml"
```

预期输出：
```
✅ Workflow initialized successfully
   Run ID: RUN-20260113-183000
   Steps: 13
   Human gates: 2 (h3_proposal_review, h5_acceptance_review)
```

### Phase 4: 执行流程

#### 4.1 步骤执行模板

对每个步骤，执行以下流程：

```bash
# 1. 检查当前状态
python -m orchestrator status "$PHASE_DIR"

# 2. 获取步骤令牌
python -m orchestrator start "$PHASE_DIR" <step_id> --agent claude

# 3. 执行步骤任务 (根据步骤定义生成交付物)

# 4. 完成步骤
python -m orchestrator complete "$PHASE_DIR" <step_id> --outputs <files>

# 5. 验证
python -m orchestrator validate "$PHASE_DIR" <step_id>
```

#### 4.2 各步骤详细说明

##### p1_openspec_init - OpenSpec 初始化

**任务**: 创建 OpenSpec 工作空间

**交付物**:
- `openspec/project.md` - 项目标记文件
- `openspec/specs/` - 规范目录
- `openspec/03-proposals/` - 提案目录

**执行**:
```bash
mkdir -p "$PHASE_DIR/openspec/"{specs,03-proposals/CHG-001}
touch "$PHASE_DIR/openspec/project.md"
```

##### p2_requirement_calibration - 需求校准

**任务**: 从研发视角校准需求，确保可实现性

**交付物**:
- `openspec/01-requirements/calibrated-requirements.md`
- `openspec/01-requirements/tech-constraints.md`
- `openspec/01-requirements/assumptions.md`

**内容模板**:
```markdown
# 校准后需求

## 功能需求
- FR-001: <需求项>

## 非功能需求
- NFR-001: <性能/安全等>

## 技术约束
- TC-001: <约束条件>

## 假设
- AS-001: <假设条件>
```

##### p3_test_contract - 测试契约生成

**任务**: 设计测试用例 (只设计不实现)

**交付物**:
- `openspec/02-test-contracts/test-contract.yaml`
- `openspec/02-test-contracts/scenarios/`

**契约格式**:
```yaml
version: "1.0"
test_suites:
  - id: TS-001
    name: <测试套件名>
    scenarios:
      - id: TC-001
        name: <用例名>
        given: <前置条件>
        when: <操作>
        then: <预期结果>
```

##### p4_openspec_proposal - OpenSpec 变更提案

**任务**: 创建详细的实现提案

**交付物**:
- `openspec/03-proposals/CHG-001/proposal.md`
- `openspec/03-proposals/CHG-001/tasks.md`
- `openspec/03-proposals/CHG-001/design.md`

**人工门禁**: `h3_proposal_review`

```
⏳ 步骤 p4_openspec_proposal 需要人类审批

审批文件:
- openspec/03-proposals/CHG-001/proposal.md
- openspec/03-proposals/CHG-001/design.md

审批命令:
  python -m orchestrator approve "$PHASE_DIR" h3_proposal_review --approver <name>
```

##### p5_implementation - 代码实现

**任务**: 按照提案实现代码

**交付物**:
- `openspec/04-implementation/` - 代码实现
- `openspec/03-proposals/CHG-001/tasks.md` - 更新任务状态

**规则**:
- 遵循 tasks.md 中的任务顺序
- 增量提交
- 测试驱动

##### p6_unit_test - 单元测试

**任务**: 实现测试代码

**交付物**:
- `openspec/05-unit-tests/` - 测试代码
- `openspec/05-unit-tests/coverage-report.json` - 覆盖率报告

**质量要求**:
- 覆盖率 >= 80%
- 所有测试通过
- 无跳过的测试

##### p7_code_review - Code Review

**任务**: 审查代码质量

**交付物**:
- `openspec/06-review/review-report.md`
- `openspec/06-review/review-checklist.md`

**条件人工门禁**:
- Critical 问题 > 0
- High 问题 > 3
- 安全漏洞 > 0
- 代码质量评分 < 6

##### p8_retrospective - Phase 复盘

**任务**: 总结经验教训

**交付物**:
- `openspec/07-retrospective/retrospective.md`
- `openspec/07-retrospective/lessons-learned.yaml`
- `openspec/07-retrospective/improvement-actions.md`

##### p9_knowledge_update - 知识沉淀

**任务**: 提取可复用知识

**交付物**:
- `openspec/08-knowledge/` - 知识库

**知识类型**:
- patterns/ - 技术模式
- pitfalls/ - 踩坑记录
- best-practices/ - 最佳实践
- tips/ - 技巧提示

##### p10_openspec_archive - OpenSpec 归档

**任务**: 归档变更记录

**交付物**:
- `openspec/09-archive/{date}-CHG-001/`

##### p11_phase_acceptance - Phase 验收

**任务**: 验收整个 Phase

**交付物**:
- `output/acceptance-report.yaml`

**人工门禁**: `h5_acceptance_review` (整改超过 5 次时触发)

**验收清单**:
- 步骤完成率 100%
- 交付物完整率 100%
- 测试通过率 100%
- 代码覆盖率 >= 80%
- Critical/High 问题 = 0

##### p12_knowledge_merge - 知识合并

**任务**: 将 Phase 知识合并到项目级

**交付物**:
- `{project_dir}/knowledge/patterns/`
- `{project_dir}/knowledge/pitfalls/`

##### p13_handover - Phase 交接

**任务**: 生成交接文档

**交付物**:
- `output/handover.yaml`
- `output/artifacts.md`

### Phase 5: 完成报告

流程完成后输出执行摘要：

```markdown
## Phase 执行完成

### 基本信息
- Phase ID: phase12-avatar-upload
- 名称: 用户头像上传
- 执行时间: 2h 15m
- Run ID: RUN-20260113-183000

### 步骤统计
| 指标 | 数值 |
|------|------|
| 总步骤 | 13 |
| 已完成 | 13 |
| 人工审批 | 2 |
| 整改次数 | 0 |

### 质量指标
| 指标 | 数值 | 标准 |
|------|------|------|
| 测试覆盖率 | 85% | >= 80% |
| 测试通过率 | 100% | 100% |
| Critical 问题 | 0 | 0 |
| High 问题 | 0 | 0 |

### 交付物清单
- 验收报告: output/acceptance-report.yaml
- 交接文档: output/handover.yaml
- 产物清单: output/artifacts.md

### 知识贡献
- 模式: 2 个
- 踩坑: 1 个
- 最佳实践: 1 个
```

## 自动继续规则

当 `orchestrator status` 显示以下条件时，**必须立即自动继续**：

```yaml
next_step_human_gate: false
action: continue
```

只有以下情况才允许停下：
- `next_step_human_gate: true`
- `action: wait_for_approval`
- 遇到技术错误

## 错误处理

### 步骤失败

```bash
# 获取错误详情
python -m orchestrator status "$PHASE_DIR" --verbose

# 根据错误类型决定:
# - 补充缺失文件
# - 修复代码问题
# - 重新执行步骤
```

### 验收失败

验收失败时自动触发整改：
1. 分析失败原因
2. 回滚到责任步骤
3. 修复问题
4. 重新执行后续步骤

最多整改 5 次，超过后触发人工门禁。

## 最佳实践

1. **需求描述要清晰** - 包含功能点、验收标准、技术约束
2. **及时保存交付物** - 每步完成后立即保存
3. **认真对待 Review** - 代码审查是质量保证的关键
4. **知识沉淀要具体** - 记录可复用的经验

## 相关资源

- 标准工作流: `ai-spec/specs/org/development/workflows/phase-openspec-flow/v1/workflow.yaml`
- Workflow Generator: `orchestrator/core/workflow_generator.py`
- Orchestrator 命令: `python -m orchestrator --help`

## 示例场景

### 场景 1: 简单功能开发

```
/dev-execute 添加用户头像上传功能
```

### 场景 2: 指定详细参数

```
/dev-execute 重构日志模块，添加脱敏功能 --project project/AI跑步教练 --phase-id phase12-log-refactor
```

### 场景 3: 复杂需求

```
/dev-execute 实现训练计划智能推荐功能，需要:
1. 分析用户历史训练数据
2. 结合目标赛事计算配速
3. 生成个性化周计划
4. 支持计划调整和反馈
```
