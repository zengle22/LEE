---
id: TECH-FEAT-171-001
ssot_type: tech
title: tech_design
status: active
version: v1
parent_id: FEAT-171
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

contract_version: v1
feat_id: FEAT-171
architecture_status: FROZEN
generated_at: '2024-05-23T10:00:00Z'
modules:
- id: MOD-API-GW
  name: API Gateway Layer
  technology: Nginx + Lua / Spring Cloud Gateway
  responsibility: Request routing, rate limiting, authentication offloading
  implementation_details: 采用 Spring Cloud Gateway 作为统一入口，集成 Sentinel 进行流控。所有外部请求必须经过
    OAuth2 校验。
- id: MOD-CORE-SVC
  name: Core Business Service
  technology: Java 17 + Spring Boot 3
  responsibility: Core business logic execution, transaction management
  implementation_details: 无状态服务设计，支持横向扩展。事务边界控制在 Service 层，采用 @Transactional 注解管理本地事务。
- id: MOD-DATA-PERSIST
  name: Data Persistence Layer
  technology: PostgreSQL 14 + MyBatis Plus
  responsibility: Data storage, ACID compliance
  implementation_details: 主从架构，写操作主库，读操作从库。关键表采用分区表设计以优化查询性能。
- id: MOD-ASYNC-PROC
  name: Asynchronous Processing
  technology: Kafka + Spring Kafka
  responsibility: Decoupling heavy tasks, event-driven workflows
  implementation_details: 核心业务完成后发送事件，异步消费者处理非关键路径逻辑（如通知、报表）。
dependencies:
- name: PostgreSQL Cluster
  type: Database
  version: 14+
  criticality: CRITICAL
  failure_impact: Service unavailable, data loss risk
- name: Redis Cluster
  type: Cache
  version: 6+
  criticality: HIGH
  failure_impact: Performance degradation, increased DB load
- name: Kafka Cluster
  type: Message Queue
  version: 3.0+
  criticality: HIGH
  failure_impact: Async tasks delayed, eventual consistency lag
- name: External Payment Gateway
  type: Third-party API
  version: v2
  criticality: CRITICAL
  failure_impact: Transaction failure
risk_assessment:
- id: RISK-001
  description: Third-party Payment Gateway latency or downtime
  probability: MEDIUM
  impact: HIGH
  mitigation: Implement Circuit Breaker (Resilience4j). Async fallback to pending
    state for manual reconciliation.
  backup_plan: Switch to备用支付渠道 (if available) or queue for retry with exponential
    backoff.
- id: RISK-002
  description: Database Deadlock under high concurrency
  probability: LOW
  impact: HIGH
  mitigation: Strict lock ordering, optimized indexing, avoid long transactions.
  backup_plan: Automatic retry mechanism for deadlock exceptions. Alert on high retry
    rates.
- id: RISK-003
  description: Cache Penetration/Breakdown
  probability: MEDIUM
  impact: MEDIUM
  mitigation: Bloom Filter for non-existent keys. Random TTL for hot keys.
  backup_plan: Direct DB fallback with rate limiting to prevent DB crash.
approval:
  status: APPROVED
  approver_role: Chief Architect
  freeze_date: '2024-05-23'
  change_control: Any change requires ADR update and re-approval.
