# Deploy Plan Template
# 部署计划模板

kind: template
id: template.devops.deploy_plan
name: 部署计划模板
version: "1.0.0"
department: devops

description: >
  这是部署计划的模板文件，用于记录详细的部署步骤和注意事项。

  使用方法：
  1. 在部署前填写此计划
  2. 经过审批后执行
  3. 部署完成后记录结果

# ============================================
# 模板定义
# ============================================
template:
  # 基本信息
  basic_info:
    version: "<version>"
    target_environment: "<environment>"
    deployment_type: "<type>"  # initial/upgrade/rollback
    planned_at: "<planned_timestamp>"
    executor: "<executor_name>"

  # 部署目标
  deployment_target:
    services:
      - name: "<service_name_1>"
        current_version: "<current_version>"
        target_version: "<target_version>"
        replicas: "<replica_count>"

      - name: "<service_name_2>"
        current_version: "<current_version>"
        target_version: "<target_version>"
        replicas: "<replica_count>"

    infrastructure:
      - name: "<infra_component_1>"
        action: "<action>"
        details: "<details>"

  # 前置条件检查
  pre_deployment_checks:
    - check: "环境配置文件已准备"
      status: "pending"
      verification_method: "检查 env/env-config.<env>.yaml"

    - check: "数据库迁移脚本已准备"
      status: "pending"
      verification_method: "检查 scripts/migrate-<version>.sql"

    - check: "回滚脚本已准备"
      status: "pending"
      verification_method: "检查 deploy/rollback-<env>.sh"

    - check: "监控告警已配置"
      status: "pending"
      verification_method: "检查监控配置"

    - check: "备份已完成"
      status: "pending"
      verification_method: "检查备份记录"

  # 部署步骤
  deployment_steps:
    - step: 1
      name: "<step_name>"
      description: "<step_description>"
      command: "<command_to_execute>"
      estimated_time: "<estimated_duration>"
      success_criteria: "<success_criteria>"
      failure_handling: "<failure_handling>"

    - step: 2
      name: "<step_name>"
      description: "<step_description>"
      command: "<command_to_execute>"
      estimated_time: "<estimated_duration>"
      success_criteria: "<success_criteria>"
      failure_handling: "<failure_handling>"

    - step: 3
      name: "<step_name>"
      description: "<step_description>"
      command: "<command_to_execute>"
      estimated_time: "<estimated_duration>"
      success_criteria: "<success_criteria>"
      failure_handling: "<failure_handling>"

  # 验证步骤
  verification_steps:
    - step: 1
      name: "<verification_name>"
      description: "<verification_description>"
      command: "<command_to_execute>"
      expected_result: "<expected_result>"

    - step: 2
      name: "<verification_name>"
      description: "<verification_description>"
      command: "<command_to_execute>"
      expected_result: "<expected_result>"

  # 回滚计划
  rollback_plan:
    trigger_conditions:
      - "<trigger_condition_1>"
      - "<trigger_condition_2>"

    rollback_steps:
      - step: 1
        name: "<rollback_step_name>"
        command: "<command_to_execute>"
        estimated_time: "<estimated_duration>"

      - step: 2
        name: "<rollback_step_name>"
        command: "<command_to_execute>"
        estimated_time: "<estimated_duration>"

    rollback_verification:
      - "<verification_step_1>"
      - "<verification_step_2>"

  # 风险评估
  risk_assessment:
    risk_level: "<risk_level>"  # low/medium/high/critical
    risks:
      - risk: "<risk_description>"
        impact: "<impact_description>"
        mitigation: "<mitigation_strategy>"

      - risk: "<risk_description>"
        impact: "<impact_description>"
        mitigation: "<mitigation_strategy>"

  # 应急联系人
  emergency_contacts:
    - role: "DevOps Lead"
      name: "<contact_name>"
      phone: "<phone_number>"
      email: "<email_address>"

    - role: "Tech Lead"
      name: "<contact_name>"
      phone: "<phone_number>"
      email: "<email_address>"

    - role: "Product Owner"
      name: "<contact_name>"
      phone: "<phone_number>"
      email: "<email_address>"

  # 审批记录
  approvals:
    - phase: "plan_review"
      approver: "<approver_name>"
      approval: "approved"
      comments: "<approval_comments>"
      approved_at: "<approval_timestamp>"

    - phase: "pre_deployment"
      approver: "<approver_name>"
      approval: "pending"
      comments: "<comments>"

    - phase: "post_deployment"
      approver: "<approver_name>"
      approval: "pending"
      comments: "<comments>"

  # 执行记录
  execution_record:
    started_at: "<start_timestamp>"
    completed_at: "<completion_timestamp>"
    total_duration: "<total_duration>"
    status: "<status>"  # success/failed/partial

    steps_completed: "<steps_completed_count>"
    steps_failed: "<steps_failed_count>"

    issues_encountered:
      - issue: "<issue_description>"
        resolution: "<resolution>"
        timestamp: "<issue_timestamp>"

  # 部署后检查
  post_deployment_checks:
    - check: "服务健康检查"
      status: "pending"
      verification_method: "curl http://<service>:<port>/health"

    - check: "关键功能验证"
      status: "pending"
      verification_method: "<verification_method>"

    - check: "日志正常收集"
      status: "pending"
      verification_method: "检查日志系统"

    - check: "监控告警正常"
      status: "pending"
      verification_method: "检查监控系统"

# ============================================
# 部署类型说明
# ============================================
deployment_types:
  initial:
    description: "首次部署"
    additional_checks:
      - "基础设施创建"
      - "数据库初始化"
      - "配置文件生成"

  upgrade:
    description: "版本升级"
    additional_checks:
      - "数据迁移"
      - "配置兼容性"
      - "API 兼容性"

  rollback:
    description: "回滚到上一个版本"
    additional_checks:
      - "回滚脚本验证"
      - "数据回滚"
      - "服务恢复验证"

# ============================================
# 占位符说明
# ============================================
placeholder_guide:
  all_placeholders:
    - "<version>": "版本号"
    - "<environment>": "目标环境"
    - "<type>": "部署类型"
    - "<timestamp>": "时间戳"
    - "<service_name>": "服务名称"
    - "<step_name>": "步骤名称"
    - "<command>": "要执行的命令"
    - "<approver_name>": "审批人姓名"

# ============================================
# 版本历史
# ============================================
changelog:
  - version: "1.0.0"
    date: "2026-01-29"
    changes:
      - "初始版本：定义部署计划模板"
