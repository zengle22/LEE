# Verifier System 快速开始指南

> **LEE Orchestrator v3.1 - Verifier System**
>
> 快速开始版本: 1.0
> 创建日期: 2026-01-29

---

## 🚀 5 分钟快速上手

### 步骤 1: 理解核心概念

**Verifier System** = "AI 产物质量检查器"

```
Agent 生成产物
    ↓
Verifier 检查产物
    ├─ 程序型检查: 文件、格式、结构
    └─ AI 型检查: 语义、质量、合理性
    ↓
    ↓
通过? → 进入下一阶段
    ↓
失败? → 重试 / 人工审查 / 中止
```

### 步骤 2: 查看现有文件

```bash
# 1. 查看验证契约
ls contracts/
# phase1.architecture.v1.yaml  - Phase 1 契约
# phase2.cicd.v1.yaml         - Phase 2 契约

# 2. 查看验证规则
ls verifier/rules/
# devops_phase1_structure.py  - Phase 1 规则
# devops_phase2_structure.py  - Phase 2 规则

# 3. 查看验证引擎
cat verifier/engine.py

# 4. 查看 AI 审查 Agent
cat agents/devops-reviewer.agent.yaml
cat agents/devops-reviewer-acceptance.md
```

### 步骤 3: 理解验证流程

**Phase 1 验证流程**:
```
1. architect Agent 生成架构文档
2. Verifier 自动检查:
   ✓ 文件存在 (3 个文件)
   ✓ YAML 格式正确
   ✓ 结构完整 (8 个章节)
   ✓ AI 评分: 0.85 → PASS
   ⚠️  AI 评分: 0.75 → WARNING (监控不够)
   ⚠️  占位符不一致
3. 决策: WARNING 不阻断 → 继续
4. 进入 Human Gate 审批
```

**Phase 2 验证流程**:
```
1. implementation Agent 生成代码
2. Verifier 自动检查:
   ✓ 文件存在 (4 个文件)
   ✓ 脚本可执行
   ✓ Docker Compose 有效
   ✗ 安全检查失败 (有硬编码密钥)
   ✗ 回滚脚本缺失
3. 决策: ERROR → 重试 1 次
4. 重试后仍失败 → Human Gate
5. devops_lead 审查并修正
6. 重新验证 → PASS
```

---

## 📖 验证类型说明

### 程序型检查

**特点**:
- 快速（秒级）
- 可靠（100% 确定）
- 检查结构、格式、存在性

**检查项**:
- 文件是否存在
- YAML/JSON 格式是否正确
- 必需字段是否存在
- 命名规范是否符合

### AI 型检查

**特点**:
- 较慢（分钟级）
- 智能评估
- 检查语义、质量、合理性

**检查项**:
- 架构设计是否合理
- CI/CD Pipeline 是否完整
- 代码质量是否达标
- 运维方案是否可行

---

## 🎯 实战示例

### 示例 1: 正常验证（通过）

```bash
# 1. 运行验证
python verifier/engine.py devops.phase1.architecture.v1 \
  --artifacts '{"architecture_doc": "devops/phase1/infra-architecture.yaml"}' \
  --base-dir project/

# 2. 查看结果
cat project/devops/phase1/verification-result.yaml

# 3. 查看报告
cat project/devops/phase1/verification-report.md

# 输出:
# overall_status: "pass"
# passed_checks: 5
# warning_checks: 2
```

### 示例 2: 验证失败（需人工审查）

```bash
# 1. 运行验证
python verifier/engine.py devops.phase2.cicd.v1 \
  --base_dir project/

# 2. 查看结果
cat project/devops/phase2/verification-result.yaml

# 输出:
# overall_status: "fail"
# failed_checks: 2

# 3. Orchestrator 自动创建 Human Gate
gate_id: "devops.p2_infra_code.verify_fail"
reviewers: [devops_lead]

# 4. devops_lead 查看失败详情
#  - docker_compose_valid: 缺少 nginx 服务
#  - security_practices: 发现硬编码密钥

# 5. devops_lead 选择操作:
#    a) 要求修正并重试
#    b) APPROVE（说明理由）
#    c) REJECT（要求返工）
```

---

## 🔧 集成到 Orchestrator

### 方式 1: 函数调用

```python
from verifier.engine import VerifierEngine

# 初始化
engine = VerifierEngine(config_path="verifier/config.yaml")

# 执行验证
result = engine.verify(
    contract_id="devops.phase1.architecture.v1",
    artifacts={
        "architecture_doc": "devops/phase1/infra-architecture.yaml",
        "env_matrix": "devops/phase1/env-matrix.yaml",
    },
    base_dir="/path/to/project"
)

# 判断结果
if result.overall_status.value == "pass":
    # 继续执行
    next_step()
else:
    # 处理失败
    handle_failure(result)
```

### 方式 2: CLI 调用

```bash
# 执行验证
python verifier/engine.py \
  devops.phase1.architecture.v1 \
  --artifacts artifacts.json \
  --base-dir /path/to/project \
  --output result.yaml

# 检查退出码
if [ $? -eq 0 ]; then
    echo "验证通过"
else
    echo "验证失败"
    # 查看 result.yaml 了解详情
fi
```

### 方式 3: Orchestrator 集成伪代码

```python
def execute_step_with_verification(step, context):
    # 1. 执行 Agent
    agent_result = execute_agent(step.agent, step.inputs)
    artifacts = save_artifacts(agent_result, step.outputs)

    # 2. 如果有 verify 配置，执行验证
    if step.verify.get("enabled", False):
        contract_id = step.verify["contract"]
        vresult = verify_engine.verify(contract_id, artifacts, context.base_dir)

        # 3. 记录结果
        context.verification_results[step.id] = vresult

        # 4. 处理验证失败
        if vresult.overall_status == VerificationStatus.FAIL:
            for rule in step.verify.get("on_fail", []):
                if rule["action"] == "auto_retry":
                    if rule.get("max_retries", 0) > 0:
                        return retry_step(step, rule["max_retries"])

                elif rule["action"] == "request_human_review":
                    create_human_gate(
                        step, vresult,
                        assignee_role=rule.get("assignee_role"),
                        message=rule.get("gate_message", "验证未通过，请审查")
                    )
                    return "waiting_human"

                elif rule["action"] == "abort":
                    raise WorkflowAbortedException(
                        f"Step {step.id} verification failed: {vresult.summary}"
                    )

    # 5. 验证通过，继续
    return "ok"
```

---

## 📊 验证级别说明

### Error 级别

- **阻断流程**: 不通过就不能进入下一阶段
- **触发人工审查**: 自动创建 Human Gate
- **适用场景**:
  - 文件缺失
  - 格式错误
  - 关键结构缺失
  - 安全问题（硬编码密钥）

### Warning 级别

- **不阻断流程**: 记录警告但继续执行
- **触发人工审查**: 可选
- **适用场景**:
  - 监控不够完整
  - 文档注释不足
  - 可优化的配置
  - 跨文档小的不一致

---

## 🧪 测试 Verifier System

### 测试 1: 正常流程

```bash
# 1. 确保 demo 文件完整
cd spec-global/departments/devops/demo/01-architecture/

# 2. 运行验证
python ../../../verifier/engine.py \
  devops.phase1.architecture.v1 \
  --artifacts '{}' \
  --base-dir ../../

# 3. 应该通过（因为 demo 文件是完整的）
```

### 测试 2: 失败流程

```bash
# 1. 故意删除必需文件
rm infra-architecture.yaml

# 2. 运行验证
python ../../../verifier/engine.py \
  devops.phase1.architecture.v1 \
  --artifacts '{}' \
  --base_dir ../../

# 3. 应该失败
# 4. 查看 verification-result.yaml 了解详情
```

### 测试 3: AI 验证

```bash
# 1. 确保有产物文件
cd spec-global/departments/devops/demo/02-implementation/

# 2. 运行验证
python ../../../verifier/engine.py \
  devops.phase2.cicd.v1 \
  --artifacts '{}' \
  --base-dir ../../

# 3. 检查 AI 审查结果（如果有实现）
```

---

## ❓ 常见问题

**Q: Verifier System 会替换 Human Gate 吗？**
A: 不会。Verifier System 是自动化检查，Human Gate 是人工审批。两者配合使用：
- Verifier: 自动检查，快速发现问题
- Human Gate: 人工审查，处理复杂情况

**Q: 验证失败一定会中止流程吗？**
A: 不一定。取决于验证级别：
- Error 级别：会触发重试或人工审查，可能中止
- Warning 级别：记录警告但不阻断

**Q: 如何自定义验证规则？**
A: 在 `verifier/rules/` 创建新的规则文件，实现 `verify()` 函数，然后在 Contract 中引用。

**Q: AI 型检查如何实现？**
A: 需要集成 Orchestrator 的 Agent 调用，可以参考 `devops-reviewer-agent` 的实现。

**Q: 验证结果存在哪里？**
A: 两处：
- `devops/phase1/verification-result.yaml` - YAML 格式结果
- `devops/phase1/verification-report.md` - Markdown 报告

**Q: 如何调试验证失败？**
A:
1. 查看 `verification-result.yaml` 了解失败详情
2. 查看 `verification-report.md` 了解建议
3. 查看 Orchestrator 日志了解执行过程

---

## 📚 相关文档

- **完整集成文档**: `docs/verifier-system-integration.md`
- **DevOps 部门规范**: `README.md`
- **Demo 演示**: `demo/README.md`
- **Contract 定义**: `contracts/phase1.architecture.v1.yaml`

---

**快速开始版本**: 1.0
**创建日期**: 2026-01-29
**维护者**: LEE Team
**状态**: ✅ 可用于演示和测试
