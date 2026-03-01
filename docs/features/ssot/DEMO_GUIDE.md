# SSOT v1.0/v1.5 Demo 指南

**文档版本**: 1.0
**适用版本**: SSOT v1.0/v1.5
**更新日期**: 2026-03-01

---

## 1. 概述

SSOT v1.0/v1.5 目前没有独立的 demo 文件，但提供了**完整的测试用例**作为示例。本指南介绍如何通过测试用例和手动运行来演示 SSOT 功能。

### 1.1 Demo 内容

| Demo 类型 | 文件 | 说明 |
|---------|------|------|
| **SSOT 校验 Demo** | `test_ssot_service.py` | 真理链校验示例 |
| **Context Bundle Demo** | `test_context_builder.py` | Context Bundle 创建示例 |
| **Task Brief Demo** | `test_task_brief.py` | Task Brief 创建示例 |
| **Gate 集成 Demo** | `test_ssot_integration.py` | Gate 审批集成示例 |
| **CLI 命令 Demo** | `test_ssot_cli.py`, `test_context_cli.py`, `test_task_brief_cli.py` | CLI 命令示例 |

---

## 2. 快速 Demo (5 分钟)

### 2.1 准备环境

```bash
# 进入项目目录
cd /path/to/LEE/framework

# 确保 LEE 已安装
pip install -e .

# 验证安装
lee --version
```

### 2.2 Demo 1: SSOT 校验 (2 分钟)

```bash
# 1. 空环境校验
lee ssot validate
# 输出：✅ SSOT validation passed.

# 2. 创建一个 PRD
python << 'EOF'
from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType, GovernanceKind

m = ArtifactManager()
prd = m.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="# 用户管理模块 PRD",
    run_id="demo-run",
    governance_kind=GovernanceKind.TRANSFER,
    title="用户管理模块需求"
)
print(f"创建 PRD: {prd.id}")
EOF

# 3. 创建一个 API (故意不添加 derived_from，演示错误)
python << 'EOF'
from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType, GovernanceKind

m = ArtifactManager()
api = m.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="# 用户管理 API",
    run_id="demo-run",
    governance_kind=GovernanceKind.TRANSFER,
    title="用户管理 API"
)
print(f"创建 API: {api.id}")
EOF

# 4. 运行校验 (应该失败)
lee ssot validate --run-id demo-run
# 输出：❌ SSOT validation failed:
#   - api_contract ART-XXXX missing derived_from
```

### 2.3 Demo 2: 完整真理链 (3 分钟)

```bash
# 创建完整的真理链
python << 'EOF'
from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType, GovernanceKind

m = ArtifactManager()

# 1. 创建 PRD
prd = m.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="# PRD: 用户管理模块",
    run_id="demo-chain",
    governance_kind=GovernanceKind.TRANSFER,
)
print(f"PRD: {prd.id}")

# 2. 创建 API (关联 PRD)
api = m.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="# API: 用户管理接口",
    run_id="demo-chain",
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd.id,  # 关键：关联 PRD
)
print(f"API: {api.id} (derived_from: {prd.id})")

# 3. 创建代码实现 (关联 API)
code = m.create(
    artifact_type=ArtifactType.CODE_REF,
    category="implementation",
    content="def create_user(): ...",
    run_id="demo-chain",
    governance_kind=GovernanceKind.DELIVERABLE,
    implements=[api.id],  # 关键：实现 API
)
print(f"Code: {code.id} (implements: {api.id})")

# 4. 创建测试计划 (关联 PRD 和 API)
test = m.create(
    artifact_type=ArtifactType.TEST,
    category="test_plan",
    content="# Test Plan: 用户管理测试",
    run_id="demo-chain",
    governance_kind=GovernanceKind.TRANSFER,
    verifies=[prd.id, api.id],  # 关键：验证 PRD 和 API
)
print(f"Test: {test.id} (verifies: {prd.id}, {api.id})")

print("\n真理链创建完成!")
print(f"  {prd.id} (PRD) -> {api.id} (API) -> {code.id} (Code)")
print(f"                       ↓                    ↓")
print(f"                  {test.id} (Test) <- (also verifies PRD)")
EOF

# 运行 SSOT 校验
lee ssot validate --run-id demo-chain
# 输出：✅ SSOT validation passed.

# 查看真理链
lee ssot show-chain <api_id>
# 输出：
# Truth chain for ART-XXXX:
#
# [0] ART-XXXX (api_contract)
#   [1] ART-XXXX (prd_contract)

# 影响分析
lee ssot impact <prd_id>
# 输出：
# Impact analysis for ART-XXXX:
#
# Direct Dependents:
#   - ART-XXXX (api_contract)
#
# Verifiers (Tests):
#   - ART-XXXX (test_plan)
```

---

## 3. 完整 Demo (15 分钟)

### 3.1 Demo 3: Context Bundle 创建

```bash
python << 'EOF'
from lee.orchestrator.execution.artifacts import ArtifactManager, ContextBuilder, PromptSnapshot, LLMConfig

# 初始化
manager = ArtifactManager()
builder = ContextBuilder(manager)

# 创建 v1.0 完整版 Context Bundle
bundle = builder.record_llm_call_v1_0(
    run_id="demo-context",
    step_id="step-1",
    prompt=PromptSnapshot(
        system="你是一个 Python 专家，擅长编写高质量代码。",
        user="请帮我实现一个用户管理类，支持 CRUD 操作。",
        history=[
            {"role": "user", "content": "什么是 CRUD?"},
            {"role": "assistant", "content": "CRUD 是 Create, Read, Update, Delete..."},
        ],
    ),
    response="好的，我来实现一个用户管理类...",
    department="backend",
    artifacts={
        "prd": ["ART-001"],
        "api_contracts": ["ART-002"],
    },
    config=LLMConfig(
        model="claude-3-5-sonnet",
        temperature=0.7,
        max_tokens=4096,
    ),
)

# 保存为 artifact
artifact = builder.save_bundle(bundle)

print(f"创建 Context Bundle: {bundle.id}")
print(f"Artifact ID: {artifact.id}")
print(f"Run ID: {bundle.run_id}")
print(f"Step ID: {bundle.step_id}")
print(f"Department: {bundle.department}")
EOF

# 查看 Context Bundles 列表
lee context list

# 查看 Context Bundle 详情
lee context show <bundle_id>

# 查看 JSON 格式
lee context show <bundle_id> --format json
```

### 3.2 Demo 4: Task Brief 创建

```bash
# 使用 CLI 创建 Task Brief
lee task-brief create \
  --run-id demo-brief \
  --department backend \
  --title "用户管理模块 - 后端实现" \
  --description "实现用户管理模块的后端功能，包括 API 接口和数据库操作。" \
  --task-type feature \
  --scope-include "用户 CRUD 接口" \
  --scope-include "用户数据验证" \
  --scope-exclude "用户认证（由 auth 模块负责）" \
  --scope-exclude "用户界面（由前端负责）" \
  --acceptance "所有 API 通过单元测试" \
  --acceptance "API 响应时间 < 100ms" \
  --acceptance "代码覆盖率 > 80%" \
  --risks "数据库 schema 变更可能影响现有功能" \
  --risks "需要与前端协调接口格式"

# 列出 Task Briefs
lee task-brief list

# 查看 Task Brief 详情
lee task-brief show <brief_id>

# 查看 JSON 格式
lee task-brief show <brief_id> --format json
```

### 3.3 Demo 5: Gate 审批集成

```bash
python << 'EOF'
from lee.orchestrator.execution.artifacts import (
    ArtifactManager, ArtifactType, GovernanceKind,
    GateArtifactHandler
)

# 创建测试 artifacts
manager = ArtifactManager()

# 创建完整的真理链
prd = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="# PRD",
    run_id="demo-gate",
    governance_kind=GovernanceKind.TRANSFER,
)

api = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="# API",
    run_id="demo-gate",
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd.id,
)

print(f"创建真理链: {prd.id} -> {api.id}")

# Gate 审批
handler = GateArtifactHandler()

print("\n执行 Gate 审批...")
result = handler.approve_gate_artifacts(
    run_id="demo-gate",
    gate_id="GATE-DEMO-001",
    enforce=True,  # 强制模式
)

print(f"冻结 artifacts: {result['frozen_count']}")
print(f"SSOT 校验：{'通过' if result['ssot_validated'] else '失败'}")
print(f"冻结列表：{result['frozen_artifacts']}")
EOF
```

---

## 4. 运行测试用例作为 Demo

### 4.1 运行单个测试用例

```bash
# SSOT 服务层测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_ssot_service.py::TestSSOTService::test_full_truth_chain_passes -v -s

# Context Builder 测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_context_builder.py::TestTaskContextBundle::test_task_context_bundle_v1_0_full -v -s

# Task Brief 测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_task_brief.py::TestTaskBriefGenerator::test_create_manual -v -s

# Gate 集成测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_ssot_integration.py::TestGateSSOTIntegration::test_approve_gate_artifacts_with_valid_ssot -v -s
```

### 4.2 运行完整测试套件

```bash
# 所有 SSOT 相关测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/ -v --tb=short

# 生成覆盖率报告
python -m pytest src/lee/orchestrator/execution/artifacts/tests/ \
    --cov=lee/orchestrator/execution/artifacts \
    --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # macOS/Linux
start htmlcov\index.html  # Windows
```

---

## 5. Demo 脚本

### 5.1 完整 Demo 脚本

创建一个完整的 demo 脚本 `demo_ssot.py`：

```python
#!/usr/bin/env python3
"""
SSOT v1.0/v1.5 完整 Demo 脚本

运行方式：
    python demo_ssot.py
"""

import tempfile
import shutil
from pathlib import Path

from lee.orchestrator.execution.artifacts import (
    ArtifactManager, ArtifactType, GovernanceKind,
    ContextBuilder, PromptSnapshot, LLMConfig,
    TaskBriefGenerator,
    GateArtifactHandler,
    SSOTService,
)


def run_demo():
    """运行完整 SSOT Demo"""

    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp())
    print(f"使用临时目录：{temp_dir}")

    try:
        manager = ArtifactManager(root_path=temp_dir)

        # ========== Demo 1: SSOT 真理链 ==========
        print("\n" + "="*60)
        print("Demo 1: SSOT 真理链创建与校验")
        print("="*60)

        prd = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="# 用户管理模块 PRD\n\n功能需求：...",
            run_id="demo-001",
            governance_kind=GovernanceKind.TRANSFER,
            title="用户管理模块需求",
        )
        print(f"✓ 创建 PRD: {prd.id}")

        api = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="# 用户管理 API\n\n接口定义：...",
            run_id="demo-001",
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
            title="用户管理 API",
        )
        print(f"✓ 创建 API: {api.id} (derived_from: {prd.id})")

        code = manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="class UserManager:\n    def create_user(self, ...): ...",
            run_id="demo-001",
            governance_kind=GovernanceKind.DELIVERABLE,
            implements=[api.id],
            title="用户管理实现",
        )
        print(f"✓ 创建 Code: {code.id} (implements: {api.id})")

        test = manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_plan",
            content="# 用户管理测试计划\n\n测试用例：...",
            run_id="demo-001",
            governance_kind=GovernanceKind.TRANSFER,
            verifies=[prd.id, api.id],
            title="用户管理测试计划",
        )
        print(f"✓ 创建 Test: {test.id} (verifies: {prd.id}, {api.id})")

        # SSOT 校验
        service = SSOTService(manager)
        valid, errors = service.validate(run_id="demo-001")
        print(f"\nSSOT 校验：{'✅ 通过' if valid else '❌ 失败'}")
        if not valid:
            for err in errors:
                print(f"  - {err}")

        # 真理链展示
        chain = service.show_chain(api.id)
        print(f"\n真理链路径:")
        for entry in chain:
            relation = f"({entry['relation']})" if entry['relation'] else ""
            print(f"  {entry['id']} ({entry['category']}) {relation}")

        # 影响分析
        impact = service.impact(prd.id)
        print(f"\nPRD 影响范围:")
        print(f"  直接依赖者：{impact['direct_dependents']}")
        print(f"  验证测试：{impact['verifiers']}")

        # ========== Demo 2: Context Bundle ==========
        print("\n" + "="*60)
        print("Demo 2: Context Bundle 创建")
        print("="*60)

        builder = ContextBuilder(manager)
        bundle = builder.record_llm_call_v1_0(
            run_id="demo-001",
            step_id="api-design",
            prompt=PromptSnapshot(
                system="你是一个架构师，擅长设计 RESTful API。",
                user="请设计用户管理模块的 API 接口。",
            ),
            response="好的，我来设计用户管理 API...",
            department="backend",
            artifacts={
                "prd": [prd.id],
            },
        )
        artifact = builder.save_bundle(bundle)
        print(f"✓ 创建 Context Bundle: {bundle.id}")
        print(f"  Artifact: {artifact.id}")

        # ========== Demo 3: Task Brief ==========
        print("\n" + "="*60)
        print("Demo 3: Task Brief 创建")
        print("="*60)

        brief_gen = TaskBriefGenerator(manager)
        brief = brief_gen.create_manual(
            run_id="demo-001",
            department="backend",
            title="用户管理模块 - 后端实现",
            description="实现用户管理模块的后端功能",
            task_type="feature",
            related_ssot={
                "prd_contract": prd.id,
                "api_contract": api.id,
            },
            acceptance=[
                "API 通过单元测试",
                "API 响应时间 < 100ms",
            ],
        )
        brief_artifact = brief_gen.save_brief(brief)
        print(f"✓ 创建 Task Brief: {brief.id}")
        print(f"  Artifact: {brief_artifact.id}")
        print(f"  状态：{brief.status}")

        # ========== Demo 4: Gate 审批 ==========
        print("\n" + "="*60)
        print("Demo 4: Gate 审批")
        print("="*60)

        handler = GateArtifactHandler(project_root=temp_dir)
        result = handler.approve_gate_artifacts(
            run_id="demo-001",
            gate_id="GATE-DEMO-001",
            enforce=True,
        )
        print(f"✓ Gate 审批完成:")
        print(f"  冻结 artifacts: {result['frozen_count']}")
        print(f"  SSOT 校验：{'通过' if result['ssot_validated'] else '失败'}")
        print(f"  冻结列表：{result['frozen_artifacts']}")

        print("\n" + "="*60)
        print("✅ Demo 完成!")
        print("="*60)

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n已清理临时目录")


if __name__ == "__main__":
    run_demo()
```

运行 demo:

```bash
python demo_ssot.py
```

---

## 6. Demo 输出示例

### 6.1 SSOT 校验输出

```
✅ SSOT validation passed.
```

### 6.2 真理链输出

```
Truth chain for ART-00002:

[0] ART-00002 (api_contract)
  [1] ART-00001 (prd_contract)
```

### 6.3 影响分析输出

```
Impact analysis for ART-00001:

Direct Dependents:
  - ART-00002 (api_contract)

Indirect Dependents:
  - ART-00003 (implementation)

Verifiers (Tests):
  - ART-00004 (test_plan)
```

### 6.4 Context Bundle 输出

```yaml
id: TCTX-00001
run_id: demo-001
step_id: api-design
llm_call_id: CALL-001
created_at: "2026-03-01T10:00:00"
artifacts:
  prd: ["ART-00001"]
prompt_snapshot:
  system: "你是一个架构师，擅长设计 RESTful API。"
  user: "请设计用户管理模块的 API 接口。"
```

### 6.5 Task Brief 输出

```yaml
id: TB-00001
run_id: demo-001
department: backend
title: "用户管理模块 - 后端实现"
description: "实现用户管理模块的后端功能"
task_type: feature
related_ssot:
  prd_contract: ART-00001
  api_contract: ART-00002
scope:
  include: []
  exclude: []
acceptance:
  - "API 通过单元测试"
  - "API 响应时间 < 100ms"
status: draft
```

---

## 7. 参考文档

- [SSOT 用户指南](SSOT_USER_GUIDE.md)
- [SSOT API 参考](SSOT_API_REFERENCE.md)
- [SSOT 最佳实践](SSOT_BEST_PRACTICES.md)
- [SSOT 测试指南](TEST_GUIDE.md)
