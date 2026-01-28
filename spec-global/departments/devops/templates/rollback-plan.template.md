# Rollback Plan Template
# 回滚计划模板

kind: template
id: template.devops.rollback_plan
name: 回滚计划模板
version: "1.0.0"
department: devops

description: >
  这是回滚计划的模板文件，用于定义如何回滚到上一个版本。

  核心原则：
  - 回滚必须快速、安全、可验证
  - 回滚前必须有完整的数据备份
  - 回滚后必须验证关键功能

# ============================================
# 模板定义
# ============================================
template:
  # 基本信息
  basic_info:
    current_version: "<current_version>"
    rollback_to_version: "<rollback_version>"
    rollback_trigger: "<rollback_trigger>"
    planned_at: "<planned_timestamp>"
    executor: "<executor_name>"

  # 回滚触发条件
  rollback_triggers:
    - trigger: "部署失败"
      condition: "deployment_steps_failed > threshold"
      action: "自动触发回滚"

    - trigger: "严重功能异常"
      condition: "critical_functionality_down"
      action: "人工决策后回滚"

    - trigger: "性能严重下降"
      condition: "performance_degradation > threshold"
      action: "人工决策后回滚"

    - trigger: "安全漏洞"
      condition: "security_vulnerability_detected"
      action: "立即回滚"

  # 回滚前准备
  pre_rollback_checks:
    - check: "确认上一个版本可用"
      status: "pending"
      verification_method: "检查上一个版本的部署记录"

    - check: "确认回滚脚本可用"
      status: "pending"
      verification_method: "在测试环境验证回滚脚本"

    - check: "确认数据备份完整"
      status: "pending"
      verification_method: "验证数据备份"

    - check: "通知相关人员"
      status: "pending"
      verification_method: "发送通知到应急联系人"

  # 回滚步骤
  rollback_steps:
    - step: 1
      order: 1
      name: "<step_name>"
      description: "<step_description>"
      command: "<command_to_execute>"
      estimated_time: "<estimated_duration>"
      success_criteria: "<success_criteria>"
      failure_handling: "<failure_handling>"

    - step: 2
      order: 2
      name: "<step_name>"
      description: "<step_description>"
      command: "<command_to_execute>"
      estimated_time: "<estimated_duration>"
      success_criteria: "<success_criteria>"
      failure_handling: "<failure_handling>"

    - step: 3
      order: 3
      name: "<step_name>"
      description: "<step_description>"
      command: "<command_to_execute>"
      estimated_time: "<estimated_duration>"
      success_criteria: "<success_criteria>"
      failure_handling: "<failure_handling>"

    - step: 4
      order: 4
      name: "数据回滚（如需要）"
      description: "<data_rollback_description>"
      command: "<data_rollback_command>"
      estimated_time: "<estimated_duration>"
      success_criteria: "<data_rollback_success_criteria>"
      failure_handling: "<data_rollback_failure_handling>"

  # 回滚验证步骤
  rollback_verification:
    - step: 1
      name: "服务健康检查"
      description: "验证所有服务健康状态"
      command: "<health_check_command>"
      expected_result: "所有服务健康检查通过"

    - step: 2
      name: "关键功能验证"
      description: "验证关键功能可用"
      command: "<functionality_check_command>"
      expected_result: "关键功能响应正常"

    - step: 3
      name: "数据完整性验证"
      description: "验证数据完整性"
      command: "<data_integrity_check_command>"
      expected_result: "数据完整性检查通过"

    - step: 4
      name: "性能验证"
      description: "验证性能指标正常"
      command: "<performance_check_command>"
      expected_result: "性能指标在正常范围"

  # 回滚后监控
  post_rollback_monitoring:
    - metric: "服务可用性"
      check_interval: "<interval>"
      threshold: "<threshold>"
      alert_contacts:
        - "<contact_1>"
        - "<contact_2>"

    - metric: "错误率"
      check_interval: "<interval>"
      threshold: "<threshold>"
      alert_contacts:
        - "<contact_1>"
        - "<contact_2>"

    - metric: "响应时间"
      check_interval: "<interval>"
      threshold: "<threshold>"
      alert_contacts:
        - "<contact_1>"
        - "<contact_2>"

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

  # 风险评估
  risk_assessment:
    rollback_risks:
      - risk: "<risk_description>"
        impact: "<impact_description>"
        probability: "<probability>"
        mitigation: "<mitigation_strategy>"

    data_rollback_risks:
      - risk: "数据回滚可能导致数据丢失"
        impact: "严重"
        probability: "低"
        mitigation: "确保数据备份完整，在测试环境验证回滚脚本"

    service_disruption_risks:
      - risk: "回滚期间服务不可用"
        impact: "中等"
        probability: "中等"
        mitigation: "选择低峰期执行回滚，提前通知用户"

  # 回退方案（如果回滚失败）
  fallback_plan:
    scenario: "回滚失败时的应急方案"
    steps:
      - step: 1
        description: "<fallback_step_1>"
        command: "<fallback_command_1>"

      - step: 2
        description: "<fallback_step_2>"
        command: "<fallback_command_2>"

  # 审批记录
  approvals:
    - phase: "rollback_plan_review"
      approver: "<approver_name>"
      approval: "approved"
      comments: "<approval_comments>"
      approved_at: "<approval_timestamp>"

    - phase: "rollback_execution"
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

  # 回滚后行动计划
  post_rollback_actions:
    - action: "分析回滚原因"
      owner: "<owner>"
      deadline: "<deadline>"

    - action: "修复问题"
      owner: "<owner>"
      deadline: "<deadline>"

    - action: "准备重新部署"
      owner: "<owner>"
      deadline: "<deadline>"

# ============================================
# 回滚场景说明
# ============================================
rollback_scenarios:
  deployment_failure:
    description: "部署过程中失败"
    triggers:
      - "部署脚本执行失败"
      - "服务启动失败"
      - "健康检查失败"
    rollback_type: "quick"
    estimated_time: "< 10 minutes"

  functionality_failure:
    description: "部署后发现严重功能问题"
    triggers:
      - "关键功能不可用"
      - "数据异常"
      - "API 错误率过高"
    rollback_type: "full"
    estimated_time: "< 30 minutes"

  performance_degradation:
    description: "性能严重下降"
    triggers:
      - "响应时间超过阈值"
      - "错误率超过阈值"
      - "资源使用率异常"
    rollback_type: "selective"
    estimated_time: "< 20 minutes"

  security_issue:
    description: "发现安全问题"
    triggers:
      - "安全漏洞被检测到"
      - "未授权访问"
      - "数据泄露风险"
    rollback_type: "immediate"
    estimated_time: "< 5 minutes"

# ============================================
# 占位符说明
# ============================================
placeholder_guide:
  all_placeholders:
    - "<current_version>": "当前版本号"
    - "<rollback_version>": "要回滚到的版本号"
    - "<rollback_trigger>": "回滚触发原因"
    - "<timestamp>": "时间戳"
    - "<executor_name>": "执行人姓名"
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
      - "初始版本：定义回滚计划模板"
