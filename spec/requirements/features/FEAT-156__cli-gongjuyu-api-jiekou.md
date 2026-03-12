---
id: FEAT-156
ssot_type: feat
title: CLI 工具与 API 接口
status: archived
version: v1
parent_id: EPIC-021
derived_from_ids: []
source_refs:
- EPIC-021#scope
owner: null
tags: []
properties:
  contract_key: feat_006
  identity_kind: ssot
  superseded_by: EPIC-030
  superseded_reason: Replaced by the canonical ADR-011 feature set FEAT-159 through FEAT-168.
---

# Goal

实现需求链一致性测试的 CLI 工具和 REST API 接口，支持单文档检测、批量检测和配置管理，提供 CI/CD 集成能力
# User Value

开发团队在本地通过 CLI 快速检测需求，CI/CD 流水线自动执行一致性检查，第三方系统集成测试能力到自有工具链
# Inputs

- {'input_name': 'command', 'description': 'CLI 命令或 API 端点', 'format': 'string'}
- {'input_name': 'target_path', 'description': '目标文档或目录路径', 'format': 'file_path | directory_path'}
- {'input_name': 'config', 'description': '检测配置参数', 'format': 'JSON'}
- {'input_name': 'output_format', 'description': '输出格式', 'format': 'enum[json, yaml, table, silent]', 'default': 'json'}
- {'input_name': 'api_key', 'description': 'API 认证密钥（API 调用时）', 'format': 'string'}
# Processing

- 解析 CLI 参数或 API 请求，验证输入有效性
- 加载默认配置、项目配置和命令行参数
- 调用各维度检测引擎执行测试
- 聚合结果并按指定格式输出
- 生成 CI 系统可解析的输出格式和退出码
# Outputs

- CLI 标准输出
- API 响应
- CLI 退出码（CI 集成用）
# Acceptance

- 命令行工具（单文档检测、批量检测、配置管理）功能完整
- REST API 接口（同步检测、异步任务、结果查询）文档完整（OpenAPI 规范）
- CI/CD 集成适配（GitHub Actions/GitLab CI/Jenkins）零代码配置（通过环境变量）
- 身份认证与权限校验（复用 LEE Auth）实现
- API 速率限制与配额管理机制
# Acceptance Checks

## AC-021-006-001

- Scenario: CLI 单文档检测
- Given: 本地存在 FEAT 文档，CLI 已安装
- When: 执行 "lee-test validate feat-001.yaml"
- Then: 输出 JSON 格式检测结果，包含各维度测试状态
- Trace Hints: TASK, TESTSET, TECH

## AC-021-006-002

- Scenario: CLI 批量检测
- Given: 目录包含多个需求文档
- When: 执行 "lee-test validate ./specs/ --batch"
- Then: 生成批量检测报告，汇总所有文档结果
- Trace Hints: TASK, TESTSET, TECH

## AC-021-006-003

- Scenario: API 同步检测
- Given: API 服务运行，提供有效认证
- When: POST /api/v1/validate 请求
- Then: 返回 JSON 格式同步检测结果
- Trace Hints: TASK, TESTSET, TECH

## AC-021-006-004

- Scenario: CI/CD 集成
- Given: GitHub Actions 工作流配置环境变量
- When: 流水线执行 lee-test 步骤
- Then: 检测执行成功，exit code 为0（即使发现问题）
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- EPIC-021
- FEAT-021-001
- FEAT-021-004
# Non Goals

- 不实现 Web UI 界面
- 不实现 IDE 插件
- 不做分布式任务调度（由外部系统管理）
- 不实现 SLA 保证（尽力而为服务）
