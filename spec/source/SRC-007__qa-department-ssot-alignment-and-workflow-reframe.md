---
id: SRC-007
ssot_type: src
title: QA department SSOT alignment and workflow reframe
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs:
- ADR-007
owner: null
tags: []
properties:
  contract_key: src
  identity_kind: ssot
frozen_at: '2026-03-13T21:46:36.105057'
---

metadata:
  source_type: adr_document
  source_ref: ADR-007
  domain: qa_department_ssot_alignment
  status: normalized
  version: '1.0'
  normalized_at: '2026-03-12'
core_objectives:
- id: OBJ-001
  title: 建立QA三轴SSOT模型
  description: 实现需求轴、交付轴、证据轴的完整串联
  measurable_criteria: '- 需求轴: FEAT→TESTSET→TC 完整映射

    - 交付轴: RELEASE→TESTPLAN→TASK 完整映射

    - 证据轴: TASK/TSE→BUG/REPORT/EVI 完整映射

    '
  priority: P0
- id: OBJ-002
  title: 完成TESTPLAN正式对象化
  description: TESTPLAN从"规划文档"升格为RELEASE下属的真源对象
  measurable_criteria: '- 具备parent_id绑定到RELEASE

    - 具备derived_from_ids声明覆盖范围

    - 具备go_no_go绑定能力

    '
  priority: P0
- id: OBJ-003
  title: 统一QA执行入口
  description: 所有QA执行必须通过TASK-TESTPLAN-*发起
  measurable_criteria: '- 消除从FEAT直接开工的例外

    - 消除自由输入开工的例外

    - 所有执行产出带完整trace信息

    '
  priority: P0
- id: OBJ-004
  title: 实现端到端可追溯
  description: BUG/REPORT/EVI必须能反查到完整链路
  measurable_criteria: '- BUG可追溯到REPORT和RELEASE

    - REPORT可追溯到TASK和TESTPLAN

    - 满足审计要求的完整溯源链路

    '
  priority: P1
- id: OBJ-005
  title: 重构QA工作流分类
  description: 从单一"测试执行"部门升级为5类工作流
  measurable_criteria: '- 测试集生产(Test Set Production)

    - 发布测试计划(Release Test Planning)

    - 测试任务执行(Test Task Execution)

    - 缺陷分流与回归(Bug Triage & Regression)

    - 出测评估与发布门禁(Go/No-Go Assessment)

    '
  priority: P1
business_drivers:
- id: DRV-001
  title: SSOT主链完整性
  priority: P0
  current_pain: 'TESTSET已完成FEAT化，但TESTPLAN/TASK/REPORT未完成release化，

    导致QA产物无法进入正式SSOT判定链

    '
  expected_value: 'QA判定成为发布门禁的正式输入，消除"自由文本可出测"的经验主义

    '
- id: DRV-002
  title: 可追溯性合规
  priority: P1
  current_pain: '当前BUG无法强制追溯到发现它的REPORT和RELEASE，

    无法满足审计要求

    '
  expected_value: '满足合规审计对完整溯源链路的要求

    '
- id: DRV-003
  title: 交付承诺固化
  priority: P1
  current_pain: 'TESTPLAN当前只是非SSOT的规划文档，

    不具备正式验证承诺效力

    '
  expected_value: 'TESTPLAN成为RELEASE下的正式验证承诺，具备go/no-go决策绑定

    '
- id: DRV-004
  title: 消除数据孤岛
  priority: P2
  current_pain: '"测试计划文档+测试集文档+运行目录"各自为政，

    缺乏统一对象边界

    '
  expected_value: '统一8个核心对象的定位与父子关系

    '
- id: DRV-005
  title: 阻断非规范执行
  priority: P2
  current_pain: '存在无release、无task、无trace的QA执行通道

    '
  expected_value: '通过validator/CLI/CI阻断非规范执行路径

    '
target_users:
- role: QA工程师
  segment: executor
  core_needs: 明确执行入口与产物归属
  usage_scenario: '通过TASK-TESTPLAN-*执行验证，

    产出带完整trace的TSE/REPORT/EVI

    '
- role: QA工作流设计师
  segment: designer
  core_needs: 基于三轴模型设计标准化流程
  usage_scenario: '使用5类workflow template设计部门标准作业程序

    '
- role: 发布经理
  segment: decision_maker
  core_needs: 基于真源数据做出go/no-go决策
  usage_scenario: '查看REPORT(go_no_go)作为RELEASE判定输入

    '
- role: 研发工程师
  segment: consumer
  core_needs: 快速定位缺陷来源与影响范围
  usage_scenario: '从BUG反查到FEAT/RELEASE/slice，理解缺陷上下文

    '
- role: 合规审计员
  segment: auditor
  core_needs: 验证完整可追溯链路
  usage_scenario: '审计TESTSET→FEAT、TESTPLAN→RELEASE、BUG→REPORT→TASK的链路完整性

    '
- role: Agent开发者
  segment: developer
  core_needs: 基于标准化schema开发自动化工具
  usage_scenario: '使用test-plan/test-set-execution等contract开发agent

    '
key_constraints:
  ssot_ownership:
  - object: TESTSET
    canonical_role: 需求轴测试真源
    parent: FEAT
    rules:
    - 单FEAT归属
    - 冻结后不可原地修改
  - object: TESTPLAN
    canonical_role: 交付轴验证承诺
    parent: RELEASE
    rules:
    - 必须声明覆盖的FEAT@version
    - 必须声明覆盖的TESTSET
  - object: TASK
    canonical_role: 交付轴执行单元
    parent: TESTPLAN
    rules:
    - 每个必需slice至少一个验证任务
  - object: REPORT
    canonical_role: 证据轴正式结论
    parent: RELEASE或TASK
    rules:
    - test_execution/regression/go_no_go三类
  - object: BUG
    canonical_role: 证据轴缺陷对象
    parent: FEAT或REPORT
    rules:
    - 必须有release/slice来源
  - object: TSE
    canonical_role: 运行态实例
    parent: 非主链
    rules:
    - 必须引用task_id+testplan_id+release_id
  traceability_rules:
  - rule_id: TR-001
    description: TESTSET必须且只能derived_from一个FEAT@version
    mandatory: true
  - rule_id: TR-002
    description: TESTPLAN必须parent→RELEASE
    mandatory: true
  - rule_id: TR-003
    description: TESTPLAN必须覆盖release中所有必需FEAT slice
    mandatory: true
  - rule_id: TR-004
    description: QA执行入口必须是TASK-TESTPLAN-*
    mandatory: true
  - rule_id: TR-005
    description: TSE必须引用task_id+testplan_id+release_id+test_set_id
    mandatory: true
  - rule_id: TR-006
    description: BUG必须引用source_report_id+found_in_release
    mandatory: true
  - rule_id: TR-007
    description: REPORT(test_execution)必须能回溯到TASK
    mandatory: true
  - rule_id: TR-008
    description: REPORT(go_no_go)的subject_id必须是RELEASE
    mandatory: true
  - rule_id: TR-009
    description: EVI只能作为证据载体，不能代替REPORT
    mandatory: true
  - rule_id: TR-010
    description: 若有governing_adrs，则decision_refs/decision_constraints必须可审计
    mandatory: true
  migration_order:
  - step: 1
    action: 冻结QA对象边界
    depends_on: []
  - step: 2
    action: 升级contract
    depends_on:
    - 1
  - step: 3
    action: 升级workflow template
    depends_on:
    - 2
  - step: 4
    action: 迁移项目级样本
    depends_on:
    - 3
  - step: 5
    action: 接入validator/CLI/CI
    depends_on:
    - 4
  out_of_scope:
  - EPIC级设计决策
  - 技术架构选型
  - 研发排期与资源分配
critical_success_factors:
- factor: TESTPLAN schema升格
  description: 最大断点，需优先完成RELEASE绑定语义
  priority: 1
- factor: TASK正式化
  description: '执行层关键，需将test-set-execute-l3-template输入

    从test_run_id+test_set_id扩展为task_id+testplan_id+release_id+test_set_ref

    '
  priority: 2
- factor: 项目级样本补齐
  description: 验证手段，需先完成一个完整TESTSET样本验证单FEAT trace可行性
  priority: 3
