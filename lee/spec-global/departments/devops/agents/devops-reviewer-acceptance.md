# DevOps 审查 Agent 验收标准
#
# 本文档定义了 DevOps 审查 Agent 的验收标准和评分规则
#
# **重要**: Agent 必须严格按照本文档的标准进行审查，不得随意添加或删除审查项

kind: agent_acceptance_criteria
id: devops-reviewer-acceptance
version: "1.0.0"
agent: "agent.devops.reviewer"
department: devops

description: >
  这是 DevOps 审查 Agent 的验收标准文档。

  使用方法：
  1. Agent 在执行审查时，根据 review_type 选择对应的验收标准
  2. 严格按照 evaluation_criteria 进行评分
  3. 输出结构化的审查结果

# ============================================
# 审查类型映射
# ============================================
review_types_mapping:
  architecture: "architecture_review_criteria"
  cicd_pipeline: "cicd_pipeline_review_criteria"
  ops_feasibility: "ops_feasibility_review_criteria"
  code_quality: "code_quality_review_criteria"

# ============================================
# 架构设计审查标准
# ============================================
architecture_review_criteria:
  review_type: "architecture"
  min_pass_score: 0.8
  min_warning_score: 0.6

  evaluation_criteria:
    - id: "service_topology"
      name: "服务拓扑设计"
      weight: 0.3
      description: "服务之间的依赖关系清晰，拓扑结构合理"
      evaluation_rules:
        - rule: "服务数量合理（2-10 个）"
          score_impact: "full"
          check_method: "统计 services 数量"

        - rule: "依赖关系清晰"
          score_impact: "full"
          check_method: "检查 depends_on 配置"

        - rule: "无循环依赖"
          score_impact: "fail"
          check_method: "检查依赖图是否有环"

        - rule: "分层架构合理"
          score_impact: "partial"
          check_method: "评估架构层次（如：web/app/db）"

      scoring:
        excellent: "服务拓扑清晰、合理、无冗余"
        good: "服务拓扑基本合理，有小问题"
        acceptable: "服务拓扑可用但不够优化"
        poor: "服务拓扑混乱或存在明显问题"
        fail: "服务拓扑不可用或存在严重问题"

    - id: "network_architecture"
      name: "网络架构"
      weight: 0.2
      description: "网络分段、端口配置、安全策略清晰"
      evaluation_rules:
        - rule: "网络配置完整"
          score_impact: "full"
          check_method: "检查 networks 配置"

        - rule: "端口映射合理"
          score_impact: "partial"
          check_method: "检查 ports 配置"

        - rule: "网络隔离考虑"
          score_impact: "partial"
          check_method: "评估不同环境的网络隔离"

      scoring:
        excellent: "网络架构完整、安全、可扩展"
        good: "网络架构基本合理"
        acceptable: "网络架构可用但有改进空间"
        poor: "网络架构存在问题"
        fail: "网络配置错误或不完整"

    - id: "storage_strategy"
      name: "存储策略"
      weight: 0.2
      description: "数据持久化方案可行，备份策略完整"
      evaluation_rules:
        - rule: "持久化配置正确"
          score_impact: "full"
          check_method: "检查 volumes 配置"

        - rule: "备份策略完整"
          score_impact: "full"
          check_method: "检查备份计划和保留策略"

        - rule: "数据安全考虑"
          score_impact: "partial"
          check_method: "评估数据安全措施"

      scoring:
        excellent: "存储策略完整、安全、可靠"
        good: "存储策略基本合理"
        acceptable: "存储策略可用但不够完善"
        poor: "存储策略存在明显问题"
        fail: "缺少持久化或备份策略"

    - id: "security_consideration"
      name: "安全考虑"
      weight: 0.15
      description: "包含认证、授权、加密等安全考虑"
      evaluation_rules:
        - rule: "凭证管理明确"
          score_impact: "fail"
          check_method: "检查是否使用占位符而非硬编码"

        - rule: "HTTPS 配置"
          score_impact: "partial"
          check_method: "检查 test/prod 环境的 HTTPS 配置"

        - rule: "访问控制考虑"
          score_impact: "partial"
          check_method: "评估访问控制策略"

      scoring:
        excellent: "安全措施完整、合理"
        good: "安全措施基本到位"
        acceptable: "有基本安全考虑但不够完善"
        poor: "安全考虑不足"
        fail: "存在明显安全问题（如硬编码密钥）"

    - id: "monitoring_strategy"
      name: "监控方案"
      weight: 0.15
      description: "包含日志、指标、告警等监控方案"
      evaluation_rules:
        - rule: "健康检查配置"
          score_impact: "full"
          check_method: "检查 healthchecks 配置"

        - rule: "日志记录配置"
          score_impact: "partial"
          check_method: "检查日志配置"

        - rule: "监控指标考虑"
          score_impact: "partial"
          check_method: "评估监控指标规划"

      scoring:
        excellent: "监控方案完整、可观测"
        good: "监控方案基本到位"
        acceptable: "有基本监控但不够完善"
        poor: "监控考虑不足"
        fail: "缺少健康检查或日志"

# ============================================
# CI/CD Pipeline 审查标准
# ============================================
cicd_pipeline_review_criteria:
  review_type: "cicd_pipeline"
  min_pass_score: 0.8
  min_warning_score: 0.6

  evaluation_criteria:
    - id: "build_stage"
      name: "构建步骤"
      weight: 0.2
      description: "Pipeline 包含代码构建步骤"
      evaluation_rules:
        - rule: "有构建 job/stage"
          score_impact: "fail"
          check_method: "检查 build 相关的 job"

        - rule: "构建步骤完整"
          score_impact: "full"
          check_method: "检查构建依赖、缓存等配置"

      scoring:
        excellent: "构建步骤完整、优化良好"
        good: "构建步骤基本完整"
        acceptable: "有构建但不够完善"
        poor: "构建步骤有问题"
        fail: "缺少构建步骤"

    - id: "test_stage"
      name: "测试步骤"
      weight: 0.2
      description: "Pipeline 包含自动化测试步骤"
      evaluation_rules:
        - rule: "有测试 job/stage"
          score_impact: "fail"
          check_method: "检查 test 相关的 job"

        - rule: "测试类型完整"
          score_impact: "partial"
          check_method: "检查单元测试、集成测试等"

      scoring:
        excellent: "测试覆盖完整（单元、集成、E2E）"
        good: "有基本的自动化测试"
        acceptable: "有测试但覆盖不足"
        poor: "测试不完整或不可靠"
        fail: "缺少自动化测试"

    - id: "security_scan"
      name: "安全扫描"
      weight: 0.15
      description: "Pipeline 包含安全漏洞扫描"
      evaluation_rules:
        - rule: "有安全扫描 job/stage"
          score_impact: "partial"
          check_method: "检查 security scan 相关的 job"

        - rule: "扫描类型完整"
          score_impact: "partial"
          check_method: "检查依赖扫描、容器扫描等"

      scoring:
        excellent: "安全扫描完整、阻断策略明确"
        good: "有基本安全扫描"
        acceptable: "有安全扫描但不完整"
        poor: "安全扫描不足"
        fail: "缺少安全扫描"

    - id: "deployment_stage"
      name: "部署步骤"
      weight: 0.2
      description: "Pipeline 包含自动化部署步骤"
      evaluation_rules:
        - rule: "有部署 job/stage"
          score_impact: "fail"
          check_method: "检查 deploy 相关的 job"

        - rule: "部署环境完整"
          score_impact: "full"
          check_method: "检查 dev、test 等环境部署"

      scoring:
        excellent: "部署步骤完整、环境隔离清晰"
        good: "有基本部署流程"
        acceptable: "有部署但不够完善"
        poor: "部署流程有问题"
        fail: "缺少部署步骤"

    - id: "environment_isolation"
      name: "环境隔离"
      weight: 0.15
      description: "不同环境有明确隔离"
      evaluation_rules:
        - rule: "环境配置独立"
          score_impact: "full"
          check_method: "检查不同环境的配置文件"

        - rule: "部署顺序正确"
          score_impact: "partial"
          check_method: "评估部署顺序（dev→test→staging→prod）"

      scoring:
        excellent: "环境隔离完善、配置独立"
        good: "有基本环境隔离"
        acceptable: "环境隔离不够严格"
        poor: "环境隔离有问题"
        fail: "缺少环境隔离"

    - id: "approval_gates"
      name: "人工审批点"
      weight: 0.1
      description: "关键节点有人工审批机制"
      evaluation_rules:
        - rule: "有关键环境的审批"
          score_impact: "full"
          check_method: "检查 staging/prod 的审批配置"

        - rule: "审批人配置合理"
          score_impact: "partial"
          check_method: "检查审批人角色配置"

      scoring:
        excellent: "审批机制完整、合理"
        good: "有基本审批机制"
        acceptable: "审批机制不够完善"
        poor: "审批机制有问题"
        fail: "关键环境缺少审批"

# ============================================
# 运维可行性审查标准
# ============================================
ops_feasibility_review_criteria:
  review_type: "ops_feasibility"
  min_pass_score: 0.6
  min_warning_score: 0.4

  evaluation_criteria:
    - id: "deployment_feasibility"
      name: "部署可行性"
      weight: 0.3
      description: "部署流程可执行、有错误处理"
      evaluation_rules:
        - rule: "部署脚本完整"
          score_impact: "full"
          check_method: "检查脚本功能和错误处理"

        - rule: "部署步骤清晰"
          score_impact: "partial"
          check_method: "评估部署流程的清晰度"

        - rule: "有验证步骤"
          score_impact: "partial"
          check_method: "检查健康检查和验证逻辑"

      scoring:
        excellent: "部署脚本完善、错误处理完整"
        good: "部署脚本基本可用"
        acceptable: "部署脚本可用但不够完善"
        poor: "部署脚本有问题"
        fail: "部署脚本不可用"

    - id: "rollback_feasibility"
      name: "回滚可行性"
      weight: 0.3
      description: "回滚方案可行、可执行"
      evaluation_rules:
        - rule: "有回滚脚本"
          score_impact: "fail"
          check_method: "检查回滚脚本存在"

        - rule: "回滚步骤完整"
          score_impact: "full"
          check_method: "检查回滚逻辑完整性"

        - rule: "有回滚验证"
          score_impact: "partial"
          check_method: "检查回滚后的验证步骤"

      scoring:
        excellent: "回滚方案完整、可靠"
        good: "有基本回滚能力"
        acceptable: "有回滚但不够完善"
        poor: "回滚方案有问题"
        fail: "缺少回滚脚本或逻辑"

    - id: "monitoring_feasibility"
      name: "监控可行性"
      weight: 0.2
      description: "关键指标有监控、可查询"
      evaluation_rules:
        - rule: "有健康检查"
          score_impact: "fail"
          check_method: "检查服务健康检查配置"

        - rule: "有日志收集"
          score_impact: "partial"
          check_method: "检查日志配置"

        - rule: "有监控指标"
          score_impact: "partial"
          check_method: "检查监控指标配置"

      scoring:
        excellent: "监控方案完整、可观测"
        good: "有基本监控能力"
        acceptable: "监控不够完善"
        poor: "监控考虑不足"
        fail: "缺少健康检查"

    - id: "resource_allocation"
      name: "资源配置"
      weight: 0.1
      description: "CPU、内存等资源配置合理"
      evaluation_rules:
        - rule: "资源配置合理"
          score_impact: "partial"
          check_method: "评估资源限制和请求"

        - rule: "有资源限制"
          score_impact: "partial"
          check_method: "检查 limits 配置"

      scoring:
        excellent: "资源配置合理、有弹性"
        good: "资源配置基本合理"
        acceptable: "资源配置可用但不优化"
        poor: "资源配置有问题"
        fail: "资源配置不合理"

    - id: "backup_strategy"
      name: "备份策略"
      weight: 0.1
      description: "数据备份策略完整、可验证"
      evaluation_rules:
        - rule: "有备份计划"
          score_impact: "full"
          check_method: "检查备份配置和计划"

        - rule: "备份可验证"
          score_impact: "partial"
          check_method: "检查备份验证机制"

      scoring:
        excellent: "备份策略完整、可验证"
        good: "有基本备份策略"
        acceptable: "备份策略不够完善"
        poor: "备份策略有问题"
        fail: "缺少备份策略"

# ============================================
# 代码质量审查标准
# ============================================
code_quality_review_criteria:
  review_type: "code_quality"
  min_pass_score: 0.7
  min_warning_score: 0.5

  evaluation_criteria:
    - id: "code_structure"
      name: "代码结构"
      weight: 0.25
      description: "代码组织良好、模块划分合理"
      evaluation_rules:
        - rule: "文件组织合理"
          score_impact: "partial"
          check_method: "评估文件和目录组织"

        - rule: "函数/模块划分"
          score_impact: "partial"
          check_method: "评估代码模块化程度"

        - rule: "命名规范"
          score_impact: "partial"
          check_method: "检查命名规范一致性"

      scoring:
        excellent: "代码结构清晰、模块化好"
        good: "代码结构基本合理"
        acceptable: "代码结构可用但有改进空间"
        poor: "代码结构混乱"
        fail: "代码结构不可接受"

    - id: "comments_documentation"
      name: "注释和文档"
      weight: 0.2
      description: "关键逻辑有注释、配置有说明"
      evaluation_rules:
        - rule: "关键逻辑有注释"
          score_impact: "partial"
          check_method: "检查关键函数/配置的注释"

        - rule: "配置有说明"
          score_impact: "partial"
          check_method: "检查配置文件的说明注释"

        - rule: "README 或文档"
          score_impact: "partial"
          check_method: "检查是否有说明文档"

      scoring:
        excellent: "注释完整、文档齐全"
        good: "有基本注释和文档"
        acceptable: "注释不够完善"
        poor: "缺少注释或文档"
        fail: "关键逻辑没有注释"

    - id: "error_handling"
      name: "错误处理"
      weight: 0.25
      description: "有错误处理和异常捕获机制"
      evaluation_rules:
        - rule: "有错误处理"
          score_impact: "full"
          check_method: "检查 try/except、set -e 等"

        - rule: "错误处理完整"
          score_impact: "partial"
          check_method: "评估错误处理的覆盖度"

        - rule: "有回滚机制"
          score_impact: "partial"
          check_method: "检查失败后的回滚逻辑"

      scoring:
        excellent: "错误处理完善、有回滚"
        good: "有基本错误处理"
        acceptable: "错误处理不够完善"
        poor: "错误处理不足"
        fail: "缺少错误处理"

    - id: "logging"
      name: "日志记录"
      weight: 0.15
      description: "关键操作有日志记录"
      evaluation_rules:
        - rule: "有日志记录"
          score_impact: "partial"
          check_method: "检查日志调用"

        - rule: "日志级别合理"
          score_impact: "partial"
          check_method: "评估日志级别使用"

        - rule: "日志格式规范"
          score_impact: "partial"
          check_method: "检查日志格式（JSON/text）"

      scoring:
        excellent: "日志完善、格式规范"
        good: "有基本日志"
        acceptable: "日志不够完善"
        poor: "日志记录不足"
        fail: "缺少关键操作日志"

    - id: "best_practices"
      name: "最佳实践"
      weight: 0.15
      description: "遵循行业最佳实践和规范"
      evaluation_rules:
        - rule: "遵循 Docker 最佳实践"
          score_impact: "partial"
          check_method: "检查 Dockerfile/Compose 规范"

        - rule: "遵循 Shell 最佳实践"
          score_impact: "partial"
          check_method: "检查 Shell 脚本规范"

        - rule: "遵循安全最佳实践"
          score_impact: "partial"
          check_method: "检查安全实践（如：不硬编码密钥）"

      scoring:
        excellent: "完全遵循最佳实践"
        good: "基本遵循最佳实践"
        acceptable: "部分遵循最佳实践"
        poor: "偏离最佳实践"
        fail: "违反关键最佳实践"

# ============================================
# 评分聚合规则
# ============================================
scoring_aggregation:
  # 计算加权平均分
  weighted_average: true

  # 关键项否决
  veto_items:
    - condition: "任何权重 >= 0.3 的项 < 0.5"
      action: "fail"
      reason: "关键项不达标，整体不通过"

    - condition: "任何 fail 级别的检查项"
      action: "fail"
      reason: "存在必须通过的检查项未通过"

  # 评级映射
  grade_mapping:
    - grade: "excellent"
      score_range: [0.9, 1.0]
      description: "优秀"

    - grade: "good"
      score_range: [0.8, 0.9)
      description: "良好"

    - grade: "acceptable"
      score_range: [0.6, 0.8]
      description: "可接受"

    - grade: "poor"
      score_range: [0.0, 0.6]
      description: "差"

# ============================================
# 输出规范
# ============================================
output_requirements:
  # 必须包含的字段
  required_fields:
    - "score"
    - "status"
    - "summary"

  # 建议格式
  suggestions_format:
    - format: "structured"
      fields:
        - "priority": "high/medium/low"
        - "category": "架构/安全/性能/运维/质量"
        - "actionable": true/false
        - "evidence": "具体证据或引用"

  # 示例
  examples:
    - priority: "high"
      category: "安全"
      suggestion: "数据库连接使用硬编码密码，应改为环境变量"
      actionable: true
      evidence: "docker-compose.yml:15"

    - priority: "medium"
      category: "运维"
      suggestion: "建议添加数据库备份的自动化验证"
      actionable: true
      evidence: "backup-plan.md:3"

# ============================================
# 元数据
# ============================================
metadata:
  version: "1.0.0"
  created_at: "2026-01-29T00:00:00Z"
  created_by: "lee-team"
  last_updated: "2026-01-29T00:00:00Z"

  changelog:
    - version: "1.0.0"
      date: "2026-01-29"
      changes:
        - "初始版本：定义 DevOps 审查 Agent 验收标准"
        - "包含 4 种审查类型的完整标准"
        - "定义评分规则和输出规范"
