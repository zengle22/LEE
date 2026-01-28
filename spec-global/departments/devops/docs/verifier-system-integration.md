# DevOps Verifier System 集成文档

> **LEE Orchestrator v3.1 - Verifier System 集成指南**
>
> 文档版本: 1.0
> 创建日期: 2026-01-29
> 状态: ✅ 已完成

---

## 📋 目录

- [一、系统概述](#一系统概述)
- [二、目录结构](#二目录结构)
- [三、验证契约（Contract）](#三验证契约contract)
- [四、验证引擎（Engine）](#四验证引擎engine)
- [五、验证规则（Rules）](#五验证规则rules)
- [六、AI 验收 Agent](#六ai-验收-agent)
- [七、工作流集成](#七工作流集成)
- [八、执行流程](#八执行流程)
- [九、Demo 示例](#九demo-示例)

---

## 一、系统概述

### 1.1 Verifier System 是什么？

**Verifier System** 是 LEE Orchestrator 的质量验证子系统，负责验证 AI Agent 产出的质量和完整性。

**核心思想**：
> **AI 说完成了不算完成，必须通过验证才能进入下一阶段。**

### 1.2 解决的问题

| 问题 | 解决方案 |
|------|----------|
| AI 生成的架构设计不完整 | 自动检查结构完整性 |
| AI 生成的代码有安全隐患 | 自动扫描安全最佳实践 |
| AI 生成的脚本无法执行 | 验证脚本可执行性 |
| 产出质量无法评估 | AI Agent 评分和建议 |

### 1.3 核心特性

1. **双重验证机制**
   - 程序型检查：文件、格式、结构
   - AI 型检查：语义、合理性、质量

2. **灵活的失败策略**
   - 自动重试
   - 人工审查
   - 流程中止

3. **完整的审计跟踪**
   - 验证结果记录
   - 建议和风险提示
   - 可追溯的历史

---

## 二、目录结构

```
spec-global/departments/devops/
├── contracts/                           # 验证契约
│   ├── phase1.architecture.v1.yaml       # Phase 1 契约
│   └── phase2.cicd.v1.yaml              # Phase 2 契约
│
├── verifier/                            # 验证引擎
│   ├── config.yaml                       # 引擎配置
│   ├── engine.py                         # 验证引擎
│   └── rules/                            # 验证规则
│       ├── devops_phase1_structure.py  # Phase 1 规则
│       └── devops_phase2_structure.py  # Phase 2 规则
│
├── agents/                              # Agent 定义
│   ├── devops-architect.agent.yaml       # 架构师 Agent
│   ├── devops-implementation.agent.yaml  # 实施工程师 Agent
│   ├── devops-verification.agent.yaml    # 验收工程师 Agent
│   └── devops-reviewer.agent.yaml        # [新增] AI 审查 Agent
│
├── agents/
│   └── devops-reviewer-acceptance.md      # [新增] AI 审查验收标准
│
└── workflows/
    └── devops-deployment/
        └── v1/
            └── workflow.yaml           # [已更新] 集成 Verifier
```

---

## 三、验证契约（Contract）

### 3.1 Contract 结构

```yaml
kind: contract
id: devops.phase1.architecture.v1
version: "1.0.0"

target:
  workflow: "workflow.devops.deployment"
  phase: "p1_architecture"
  step: "devops_arch_design"

artifacts:
  - id: architecture_doc
    path: "devops/phase1/infra-architecture.yaml"
    required: true

checks:
  - id: file_exists
    name: "产物文件存在性检查"
    type: program
    script: "verifier/rules/devops_phase1_structure.py"
    severity: error

  - id: architecture_semantic
    name: "架构设计语义合理性检查"
    type: ai
    agent: "devops-reviewer-agent"
    severity: error

validation_strategy:
  on_failure:
    - action: auto_retry
      max_retries: 1

    - action: request_human_review
      assignee_role: devops_lead

    - action: abort
```

### 3.2 两类 Contract

#### Phase 1: 架构设计验证

**文件**: `contracts/phase1.architecture.v1.yaml`

**验证内容**：
1. 文件存在性（3 个文件）
2. YAML 格式有效性（2 个文件）
3. 架构文档结构完整性（8 个必需章节）
4. 环境矩阵完整性（2 个环境）
5. 架构设计语义合理性（AI，min_score: 0.8）
6. 运维可落地性（AI，warning 级别，min_score: 0.6）
7. 跨文档引用一致性（warning 级别）

**总检查数**: 7 项（4 个 error 级别，3 个 warning 级别）

#### Phase 2: CI/CD 实现验证

**文件**: `contracts/phase2.cicd.v1.yaml`

**验证内容**：
1. 文件存在性（4 个文件）
2. Shell 脚本可执行性（2 个脚本）
3. Docker Compose 有效性（服务、健康检查）
4. 安全最佳实践（无硬编码密钥、健康检查、回滚脚本）
5. 部署脚本完整性（7 个必需函数、错误处理）
6. CI/CD Pipeline 完整性（AI，min_score: 0.8）
7. 代码质量（AI，warning 级别，min_score: 0.7）
8. 占位符一致性（warning 级别）

**总检查数**: 8 项（5 个 error 级别，3 个 warning 级别）

---

## 四、验证引擎（Engine）

### 4.1 Engine 架构

```python
class VerifierEngine:
    def verify(contract_id, artifacts, base_dir):
        """执行验证的核心方法"""
        # 1. 加载契约
        contract = load_contract(contract_id)

        # 2. 执行检查
        check_results = []
        for check in contract["checks"]:
            if check["type"] == "program":
                result = run_program_check(check, artifacts)
            elif check["type"] == "ai":
                result = run_ai_check(check, artifacts)
            check_results.append(result)

        # 3. 聚合结果
        overall_status = aggregate_status(check_results)

        # 4. 保存结果
        return VerificationResult(...)
```

### 4.2 程序型检查

**执行流程**:
1. 动态加载规则模块
2. 调用模块的 `verify()` 函数
3. 解析返回结果
4. 转换为 CheckResult

**规则模块接口**:
```python
def verify(params, artifacts, base_dir="."):
    """验证函数必须遵循此接口"""
    return {
        "status": "pass",  # pass/fail
        "detail": "验证通过",
        "suggestions": []
    }
```

### 4.3 AI 型检查

**调用流程**:
1. 获取 Agent 配置
2. 准备审查参数
3. 调用 Orchestrator Agent API
4. 解析评分和建议
5. 转换为 CheckResult

**伪代码**:
```python
def run_ai_check(check, artifacts):
    agent_name = check["agent"]
    spec_path = check["spec"]
    params = check["params"]

    # 调用 orchestrator
    review_result = orchestrator.call_agent(
        agent_name,
        spec_path,
        artifacts,
        params
    )

    # 根据评分判断状态
    min_score = params.get("min_score", 0.8)
    status = "pass" if review_result["score"] >= min_score else "fail"

    return CheckResult(
        check_id=check["id"],
        status=status,
        detail=review_result["summary"],
        score=review_result["score"],
        suggestions=review_result["suggestions"]
    )
```

---

## 五、验证规则（Rules）

### 5.1 Phase 1 规则

**文件**: `verifier/rules/devops_phase1_structure.py`

**功能**:
- `file_exists`: 检查必需文件是否存在
- `yaml_valid`: 验证 YAML 格式正确性
- `architecture_structure`: 检查架构文档必需章节
- `env_matrix_structure`: 检查环境矩阵完整性
- `cross_reference`: 检查跨文档引用一致性

### 5.2 Phase 2 规则

**文件**: `verifier/rules/devops_phase2_structure.py`

**功能**:
- `file_exists`: 检查必需文件是否存在
- `script_executable`: 检查脚本可执行性
- `docker_compose_valid`: 验证 Docker Compose 配置
- `security_practices`: 检查安全最佳实践
- `deploy_script_structure`: 检查部署脚本完整性
- `placeholder_consistency`: 检查环境变量占位符

### 5.3 规则开发规范

**命名规范**:
```python
devops_phase{N}_{type}.py

# 例如:
devops_phase1_structure.py
devops_phase2_security.py
```

**接口规范**:
```python
def verify(params, artifacts, base_dir=".") -> Dict[str, Any]:
    """
    Args:
        params: 检查参数
        artifacts: 产物字典
        base_dir: 基础目录

    Returns:
        {
            "status": "pass" | "fail",
            "detail": str,
            "suggestions": List[str]
        }
    """
```

---

## 六、AI 验收 Agent

### 6.1 Agent 定义

**文件**: `agents/devops-reviewer.agent.yaml`

**核心能力**:
- `architecture_review`: 架构设计语义审查
- `cicd_review`: CI/CD Pipeline 完整性审查
- `ops_feasibility_review`: 运维可行性评估
- `code_quality_review`: 生成代码质量评估

### 6.2 验收标准

**文件**: `agents/devops-reviewer-acceptance.md`

**评分标准**:
- 架构设计: min_score=0.8 (5 个评估项)
- CI/CD Pipeline: min_score=0.8 (6 个评估项)
- 运维可行性: min_score=0.6 (5 个评估项)
- 代码质量: min_score=0.7 (5 个评估项)

### 6.3 审查流程

```
┌─────────────────────────────────────────────────────┐
│              AI 审查 Agent 执行流程                │
└─────────────────────────────────────────────────────┘

1. 接收审查任务
   ├─ contract_params.review_type
   ├─ artifacts (产物文件)
   └─ context (项目、阶段)

2. 选择验收标准
   ├─ 根据 review_type 选择对应标准
   ├─ architecture → architecture_review_criteria
   └─ cicd_pipeline → cicd_pipeline_review_criteria

3. 执行审查
   ├─ 读取产物文件
   ├─ 根据 evaluation_criteria 逐项评估
   ├─ 计算加权平均分
   └─ 生成建议

4. 输出结果
   ├─ score: 0.85 (综合评分)
   ├─ status: "pass"
   ├─ summary: "架构设计合理，包含所有必需组件"
   ├─ risks: ["监控指标不够完整"]
   └─ suggestions: ["建议添加更多监控指标"]
```

---

## 七、工作流集成

### 7.1 Workflow 字段扩展

在 Workflow 的 Step 中新增 `verify` 字段：

```yaml
- id: p1_architecture
  name: 环境与发布架构设计
  kind: agent
  agent: agent.devops.architect
  outputs:
    - path: devops/infra-architecture.yaml
    - path: devops/env-matrix.yaml

  # ============================================
  # Verifier System 集成
  # ============================================
  verify:
    contract: devops.phase1.architecture.v1
    enabled: true

    on_fail:
      - action: auto_retry
        max_retries: 1

      - action: request_human_review
        assignee_role: devops_lead

      - action: abort
        reason: "验证失败且人工审查未通过"
```

### 7.2 Orchestrator 集成伪代码

```python
def run_step(step, context):
    # 1. 执行 Agent
    agent_result = run_agent(step.agent, step.inputs)
    artifacts = save_outputs(agent_result, step.outputs)

    # 2. 如果有 verify 配置，执行验证
    if hasattr(step, "verify") and step.verify.get("enabled", False):
        contract_id = step.verify["contract"]
        vresult = verifier_engine.verify(contract_id, artifacts, context.base_dir)

        # 记录验证结果
        log_verification_result(step.id, vresult)

        # 3. 根据状态决定后续动作
        if vresult.overall_status == VerificationStatus.PASS:
            return {"status": "ok"}

        # 4. 处理验证失败
        for rule in step.verify.get("on_fail", []):
            if rule["action"] == "auto_retry":
                if rule.get("max_retries", 0) > 0:
                    return run_step_with_retry(step, context, rule["max_retries"])

            elif rule["action"] == "request_human_review":
                request_human_review(
                    step, vresult,
                    assignee_role=rule.get("assignee_role"),
                    message=rule.get("gate_message")
                )
                return {"status": "waiting_human"}

            elif rule["action"] == "abort":
                raise WorkflowAbortedException(
                    f"Step {step.id} verification failed: {vresult.summary}"
                )

    return {"status": "ok"}
```

---

## 八、执行流程

### 8.1 Phase 1 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│              Phase 1: 架构设计 + 验证                         │
└─────────────────────────────────────────────────────────────┘

Step 1: Agent 执行
├─ Agent: agent.devops.architect
├─ 输入: system_arch.md, non_functional_requirements.yaml
├─ 执行: 生成架构设计文档
└─ 输出: infra-architecture.yaml, env-matrix.yaml, release-strategy.md

                    ↓

Step 2: Verifier 执行
├─ Contract: devops.phase1.architecture.v1
├─ 程序型检查（7 项）
│  ├─ file_exists: PASS
│  ├─ yaml_valid: PASS
│  ├─ architecture_structure: PASS
│  ├─ env_matrix_structure: PASS
│  ├─ architecture_semantic: AI 评分 0.85 → PASS
│  ├─ ops_feasibility: AI 评分 0.75 → WARNING
│  └─ cross_reference: WARNING
└─ 聚合状态: WARNING

                    ↓

Step 3: 判断后续动作
├─ 无 error 级别失败
├─ 有 warning 级别失败
├─ on_fail 策略:
│  ├─ warning 级别: 记录警告，继续执行
│  └─ error 级别: 人工审查
└─ 决策: 继续执行（warning 不阻断）

                    ↓

Step 4: 进入 Human Gate（原有流程）
├─ 审批者: devops_lead + tech_lead
├─ 审批内容: 架构设计 + 验证报告
└─ 审批结果: APPROVED

                    ↓

Phase 1 完成
```

### 8.2 失败处理流程

```
┌─────────────────────────────────────────────────────────────┐
│              验证失败处理流程                                 │
└─────────────────────────────────────────────────────────────┘

验证失败 (ERROR 级别)
├─ 策略 1: auto_retry
│  ├─ Agent 重新生成产物
│  └─ 重新运行验证
│
├─ 策略 2: request_human_review
│  ├─ 创建 Human Gate
│  ├─ 分配给 devops_lead
│  ├─ 人工审查问题
│  ├─ 人工修正产物或调整要求
│  └─ 提交修正后的结果
│
└─ 策略 3: abort
   ├─ 记录失败原因
   ├─ 生成失败报告
   └─ 中止工作流
```

---

## 九、Demo 示例

### 9.1 成功场景

**场景**: Phase 1 架构设计验证通过

```
执行验证:
$ python verifier/engine.py devops.phase1.architecture.v1

验证结果:
{
  "contract_id": "devops.phase1.architecture.v1",
  "verification_time": "2026-01-29T10:05:00Z",
  "overall_status": "pass",
  "total_checks": 7,
  "passed_checks": 5,
  "failed_checks": 0,
  "warning_checks": 2,
  "summary": "Verifier status=pass, checks=7 (passed=5, failed=0, warning=2)"
}

检查结果:
  ✓ file_exists: PASS - 所有必需文件都存在
  ✓ yaml_valid: PASS - YAML 格式正确
  ✓ architecture_structure: PASS - 架构文档结构完整
  ✓ env_matrix_structure: PASS - 环境矩阵完整
  ✓ architecture_semantic: PASS (score: 0.85)
  ⚠ ops_feasibility: WARNING (score: 0.75) - 监控指标不够完整
  ⚠ cross_reference: WARNING - 环境变量占位符有轻微不一致

决策: PASS (无 error 级别失败)
动作: 继续执行到下一阶段
```

### 9.2 失败场景

**场景**: Phase 2 CI/CD 实现验证失败

```
执行验证:
$ python verifier/engine.py devops.phase2.cicd.v1

验证结果:
{
  "overall_status": "fail",
  "failed_checks": 2,
  "summary": "Verifier status=fail, checks=8 (passed=5, failed=2, warning=1)"
}

失败项:
  ✗ docker_compose_valid: FAIL
     detail: "Docker Compose 配置发现问题"
     suggestions:
       - "缺少必需服务: nginx"
       - "以下服务缺少健康检查: app, db"

  ✗ security_practices: FAIL
     detail: "安全检查发现问题"
     suggestions:
       - "docker-compose.yml:15: 可能包含硬编码的 password"
       - "缺少回滚脚本: deploy/rollback-dev-test.sh"

决策: FAIL (有 error 级别失败)
动作:
   1. 自动重试 1 次
   2. 重试后仍失败 → 创建 Human Gate
  3. 分配给 devops_lead 人工审查
```

### 9.3 人工审查场景

```
Human Gate 创建:
┌─────────────────────────────────────────────────────────────┐
│              Human Gate: 验证失败人工审查                     │
└─────────────────────────────────────────────────────────────┘

Gate ID: devops.p1_architecture.verify_fail
Reviewers: devops_lead
Status: pending

验证结果:
  - 失败项: docker_compose_valid, security_practices
  - 建议数量: 5 个

审查清单:
  [ ] docker-compose.yml 是否缺少 nginx 服务
  [ ] 是否有硬编码的密钥（应该使用占位符）
  [ ] 是否存在回滚脚本
  [ ] 健康检查是否完整
  [ ] 是否需要修正产物或调整需求

人工操作:
1. devops_lead 查看验证失败详情
2. 审查 AI 生成的产物
3. 选择操作：
   - APPROVE: 产物合格，标记为通过（需要说明理由）
   - REJECT: 产物不合格，需要返工
   - MODIFY: 提出修改要求，Agent 重新生成

4. 提交审查结果
```

---

## 十、使用指南

### 10.1 部署前准备

1. **确保依赖安装**
   ```bash
   # Python 3.8+
   python --version

   # PyYAML
   pip install pyyaml
   ```

2. **配置 Verifier**
   ```bash
   cd spec-global/departments/devops/verifier
   # 编辑 config.yaml（如需要）
   ```

### 10.2 运行验证

**命令行方式**:
```bash
python verifier/engine.py \
  devops.phase1.architecture.v1 \
  --artifacts artifacts.json \
  --base-dir /path/to/project
```

**Orchestrator 集成方式**:
```python
from verifier.engine import VerifierEngine

engine = VerifierEngine()
result = engine.verify(
    contract_id="devops.phase1.architecture.v1",
    artifacts={"architecture_doc": "devops/phase1/infra-architecture.yaml"},
    base_dir="/path/to/project"
)

if result.overall_status == "pass":
    # 继续执行
    pass
else:
    # 处理失败
    handle_verification_failure(result)
```

### 10.3 查看验证结果

**YAML 结果**:
```bash
cat devops/phase1/verification-result.yaml
```

**Markdown 报告**:
```bash
cat devops/phase1/verification-report.md
```

---

## 十一、扩展指南

### 11.1 添加新的验证规则

1. 在 `verifier/rules/` 创建新规则文件
2. 实现 `verify()` 函数
3. 在 Contract 中引用

**示例**:
```python
# verifier/rules/devops_phase3_security.py

def verify(params, artifacts, base_dir="."):
    # 自定义验证逻辑
    return {
        "status": "pass",
        "detail": "安全检查通过"
    }
```

**Contract 中引用**:
```yaml
- id: security_check
  type: program
  script: "verifier/rules/devops_phase3_security.py"
  severity: error
```

### 11.2 添加新的 Contract

1. 在 `contracts/` 创建新 Contract 文件
2. 定义 artifacts 和 checks
3. 在 Workflow 中引用

**示例**:
```yaml
kind: contract
id: devops.phase3.security.v1
artifacts:
  - path: "devops/phase3/security-scan.yaml"
checks:
  - id: vulnerability_scan
    type: ai
    agent: "devops-reviewer-agent"
    min_score: 0.9
```

### 11.3 扩展到其他部门

Verifier System 是通用的，可以扩展到其他部门：

1. **Dev 部门**:
   - 代码质量验证
   - 测试覆盖率验证
   - 架构决策验证

2. **QA 部门**:
   - 测试用例完整性验证
   - 测试结果有效性验证

3. **UI 部门**:
   - 设计规范符合性验证
   - 组件可复用性验证

---

**文档版本**: 1.0
**最后更新**: 2026-01-29
**维护者**: LEE Team
**状态**: ✅ 已完成
