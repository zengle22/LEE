# SSOT v1.0/v1.5 测试指南

**文档版本**: 1.0
**适用版本**: SSOT v1.0/v1.5
**更新日期**: 2026-03-01

---

## 1. 概述

本指南介绍如何测试 SSOT 真理链管理系统的各项功能，包括单元测试、集成测试和手动测试。

### 1.1 测试范围

| 测试类别 | 测试文件 | 测试用例数 |
|---------|---------|-----------|
| **SSOT 核心测试** | | |
| SSOT 服务层 | `test_ssot_service.py` | 14 |
| Context Builder | `test_context_builder.py` | 19 |
| Task Brief | `test_task_brief.py` | 21 |
| SSOT 集成 | `test_ssot_integration.py` | 11 |
| **SSOT CLI 测试** | | |
| SSOT CLI | `test_ssot_cli.py` | 15 |
| Context CLI | `test_context_cli.py` | 12 |
| Task Brief CLI | `test_task_brief_cli.py` | 17 |
| **基础测试** | | |
| Artifact Manager | `test_manager.py` | 18 |
| Manifest Manager | `test_manifest.py` | 12 |
| Artifact Models | `test_models.py` | 15 |
| Artifact Registry | `test_registry.py` | 14 |
| Integration | `test_integration.py` | 14 |
| Types | `test_types.py` | 7 |
| **总计** | | **189** |

### 1.2 测试环境要求

- Python 3.10+
- pytest 8.0+
- 临时目录写入权限

---

## 2. 运行测试

### 2.1 运行全部测试

```bash
# 运行所有 SSOT 相关测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/ -v

# 运行测试并生成覆盖率报告
python -m pytest src/lee/orchestrator/execution/artifacts/tests/ \
    --cov=lee/orchestrator/execution/artifacts \
    --cov-report=html
```

### 2.2 运行特定测试模块

```bash
# SSOT 服务层测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_ssot_service.py -v

# Context Builder 测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_context_builder.py -v

# Task Brief 测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_task_brief.py -v

# 集成测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_ssot_integration.py -v

# CLI 命令测试
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_ssot_cli.py -v
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_context_cli.py -v
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_task_brief_cli.py -v
```

### 2.3 运行特定测试用例

```bash
# 运行单个测试类
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_ssot_service.py::TestSSOTService -v

# 运行单个测试方法
python -m pytest src/lee/orchestrator/execution/artifacts/tests/test_ssot_service.py::TestSSOTService::test_empty_artifacts_validation -v

# 运行匹配关键字的测试
python -m pytest -k "test_validate" -v
```

---

## 3. 单元测试详解

### 3.1 SSOT 服务层测试

**文件**: `test_ssot_service.py`

#### 测试用例列表

| 测试方法 | 测试内容 | 预期结果 |
|---------|---------|---------|
| `test_empty_artifacts_validation` | 空 artifacts 列表校验 | 校验通过 |
| `test_full_truth_chain_passes` | 完整真理链 (PRD→API→CODE→TEST) | 校验通过 |
| `test_api_without_derived_from_fails` | Rule 1: API 没有 derived_from | 校验失败 |
| `test_implementation_without_implements_fails` | Rule 2: 实现没有 implements | 校验失败 |
| `test_test_plan_without_verifies_fails` | Rule 3: 测试没有 verifies | 校验失败 |
| `test_derived_from_points_to_nonexistent` | derived_from 指向不存在的 artifact | 校验失败 |
| `test_implements_points_to_nonexistent_api` | implements 指向不存在的 API | 校验失败 |
| `test_impact_analysis_with_dependents` | 影响分析 (有依赖者) | 返回正确影响范围 |
| `test_impact_analysis_without_dependents` | 影响分析 (无依赖者) | 返回空影响范围 |
| `test_show_chain_path` | 真理链路径展示 | 返回完整路径 |
| `test_release_tag_filtering` | release tag 过滤校验 | 仅校验指定 release |

#### 示例：手动运行测试

```python
import tempfile
from pathlib import Path
from lee.orchestrator.execution.artifacts import (
    ArtifactManager, ArtifactType, GovernanceKind
)
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService

# 创建临时目录
temp_dir = Path(tempfile.mkdtemp())
manager = ArtifactManager(root_path=temp_dir)
service = SSOTService(manager)

# 创建完整的真理链
prd = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="PRD content",
    run_id="test-run",
    governance_kind=GovernanceKind.TRANSFER,
)

api = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="API content",
    run_id="test-run",
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd.id,
)

impl = manager.create(
    artifact_type=ArtifactType.CODE_REF,
    category="implementation",
    content="Code",
    run_id="test-run",
    governance_kind=GovernanceKind.DELIVERABLE,
    implements=[api.id],
)

test = manager.create(
    artifact_type=ArtifactType.TEST,
    category="test_plan",
    content="Test",
    run_id="test-run",
    governance_kind=GovernanceKind.TRANSFER,
    verifies=[prd.id, api.id],
)

# 运行校验
valid, errors = service.validate(run_id="test-run")
print(f"Valid: {valid}")
print(f"Errors: {errors}")
# 预期输出：Valid: True, Errors: []

# 清理
import shutil
shutil.rmtree(temp_dir)
```

### 3.2 Context Builder 测试

**文件**: `test_context_builder.py`

#### 测试用例列表

| 测试方法 | 测试内容 |
|---------|---------|
| `test_prompt_snapshot_creation` | PromptSnapshot 创建和序列化 |
| `test_task_context_bundle_v1_0` | v1.0 完整版 Bundle |
| `test_task_context_bundle_v0_9` | v0.9 兼容版 Bundle |
| `test_to_dict_v1_0_format` | to_dict() v1.0 格式 |
| `test_to_dict_v0_9_format` | to_dict() v0.9 格式 |
| `test_context_builder_build_v1_0` | ContextBuilder.build_v1_0() |
| `test_context_builder_build_v0_9` | ContextBuilder.build_v0_9() |
| `test_save_bundle_creates_artifact` | save_bundle() 创建 artifact |
| `test_record_llm_call_v1_0_with_artifacts` | record_llm_call_v1_0() |
| `test_record_llm_call_v0_9_simple` | record_llm_call_v0_9() |
| `test_llm_config_default_values` | Config 默认值 |
| `test_llm_config_custom_values` | Config 自定义值 |
| `test_bundle_with_empty_artifacts` | 空 artifacts 边界情况 |
| `test_bundle_with_nested_artifacts` | 嵌套 artifacts 边界情况 |

### 3.3 Task Brief 测试

**文件**: `test_task_brief.py`

#### 测试用例列表

| 测试方法 | 测试内容 |
|---------|---------|
| `test_task_brief_creation` | TaskBrief 基本创建 |
| `test_task_brief_default_values` | 默认值测试 |
| `test_task_brief_to_dict` | to_dict() 序列化 |
| `test_task_brief_to_yaml` | to_yaml() 序列化 |
| `test_generator_create_manual` | TaskBriefGenerator.create_manual() |
| `test_generator_create_from_prd` | create_from_prd() |
| `test_generator_create_from_task_card` | create_from_task_card() |
| `test_generator_save_brief` | save_brief() 创建 artifact |
| `test_generator_create_and_save` | create_and_save() 一步完成 |
| `test_task_brief_feature_type` | feature 任务类型 |
| `test_task_brief_bugfix_type` | bugfix 任务类型 |
| `test_task_brief_incident_type` | incident 任务类型 |
| `test_task_brief_refactor_type` | refactor 任务类型 |
| `test_task_brief_draft_status` | draft 状态 |
| `test_task_brief_confirmed_status` | confirmed 状态 |
| `test_task_brief_completed_status` | completed 状态 |

---

## 4. 集成测试详解

### 4.1 Gate SSOT 集成测试

**文件**: `test_ssot_integration.py`

#### 测试用例列表

| 测试方法 | 测试内容 |
|---------|---------|
| `test_approve_gate_artifacts_with_valid_ssot` | 有效 SSOT 时 Gate 审批成功 |
| `test_approve_gate_artifacts_with_invalid_ssot_enforce_mode` | enforce 模式阻断无效 SSOT |
| `test_approve_gate_artifacts_with_invalid_ssot_warning_mode` | warning 模式允许无效 SSOT |
| `test_approve_gate_artifacts_updates_manifest` | Gate 审批更新 manifest |
| `test_ssot_service_detects_broken_chain` | SSOT 检测断链 |
| `test_ssot_service_full_chain_passes` | SSOT 完整链通过 |
| `test_full_truth_chain_workflow` | 端到端真理链测试 |
| `test_broken_chain_workflow_api_missing_prd` | 断链测试 (API 缺少 PRD) |
| `test_broken_chain_workflow_code_missing_api` | 断链测试 (代码缺少 API) |
| `test_enforce_mode_blocks_invalid_ssot` | enforce 模式阻断 |
| `test_warning_mode_allows_invalid_ssot` | warning 模式允许 |

#### 示例：手动测试 Gate 集成

```python
import tempfile
from pathlib import Path
from lee.orchestrator.execution.artifacts import (
    ArtifactManager, ArtifactType, GovernanceKind
)
from lee.orchestrator.execution.artifacts.integration import GateArtifactHandler

# 创建临时目录
temp_dir = Path(tempfile.mkdtemp())
manager = ArtifactManager(root_path=temp_dir)

# 创建有效真理链
prd = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="PRD",
    run_id="gate-test",
    governance_kind=GovernanceKind.TRANSFER,
)

api = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="API",
    run_id="gate-test",
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd.id,
)

# 测试 Gate 审批
handler = GateArtifactHandler(project_root=temp_dir)
result = handler.approve_gate_artifacts(
    run_id="gate-test",
    gate_id="GATE-TEST-001",
    enforce=True,
)

print(f"Frozen count: {result['frozen_count']}")
print(f"SSOT validated: {result['ssot_validated']}")
# 预期：frozen_count > 0, ssot_validated = True

# 清理
import shutil
shutil.rmtree(temp_dir)
```

---

## 5. CLI 命令测试

### 5.1 SSOT CLI 测试

**文件**: `test_ssot_cli.py`

#### 测试用例列表

| 测试方法 | 测试命令 | 测试内容 |
|---------|---------|---------|
| `test_validate_empty_artifacts` | `lee ssot validate` | 空 artifacts 校验 |
| `test_validate_with_run_id` | `lee ssot validate --run-id xxx` | 按 run ID 校验 |
| `test_validate_with_release_tag` | `lee ssot validate --release v1.0` | 按 release 校验 |
| `test_validate_failure` | `lee ssot validate` | 校验失败场景 |
| `test_validate_with_enforce_flag` | `lee ssot validate --enforce` | enforce 模式 |
| `test_build_index_creates_file` | `lee ssot build-index` | 构建索引文件 |
| `test_build_index_with_artifacts` | `lee ssot build-index` | 有 artifacts 时构建 |
| `test_build_index_with_release_filter` | `lee ssot build-index --release v1.0` | release 过滤 |
| `test_build_index_custom_output_path` | `lee ssot build-index -o /path/to/file.yaml` | 自定义输出路径 |
| `test_show_impact_with_dependents` | `lee ssot impact ART-001` | 有依赖者的影响分析 |
| `test_show_impact_no_dependents` | `lee ssot impact ART-001` | 无依赖者的影响分析 |
| `test_show_impact_json_format` | `lee ssot impact ART-001 --format json` | JSON 格式输出 |
| `test_show_chain_with_derived_from` | `lee ssot show-chain ART-002` | 真理链展示 |
| `test_show_chain_not_found` | `lee ssot show-chain ART-999` | 链条不存在 |
| `test_show_chain_json_format` | `lee ssot show-chain ART-001 --format json` | JSON 格式输出 |

### 5.2 Context CLI 测试

**文件**: `test_context_cli.py`

#### 测试用例列表

| 测试方法 | 测试命令 | 测试内容 |
|---------|---------|---------|
| `test_list_no_bundles` | `lee context list` | 没有 Bundles |
| `test_list_with_bundles` | `lee context list` | 有 Bundles |
| `test_list_with_run_id_filter` | `lee context list --run-id xxx` | run ID 过滤 |
| `test_list_with_department_filter` | `lee context list --department backend` | 部门过滤 |
| `test_list_json_format` | `lee context list --format json` | JSON 格式 |
| `test_list_yaml_format` | `lee context list --format yaml` | YAML 格式 |
| `test_show_not_found` | `lee context show TCTX-999` | Bundle 不存在 |
| `test_show_wrong_category` | `lee context show ART-001` | 类别错误 |
| `test_show_bundle_yaml` | `lee context show TCTX-001` | YAML 格式显示 |
| `test_show_bundle_json` | `lee context show TCTX-001 --format json` | JSON 格式显示 |
| `test_show_bundle_text` | `lee context show TCTX-001 --format text` | 文本格式显示 |
| `test_show_bundle_v1_0` | `lee context show TCTX-001` | v1.0 版本显示 |

### 5.3 Task Brief CLI 测试

**文件**: `test_task_brief_cli.py`

#### 测试用例列表

| 测试方法 | 测试命令 | 测试内容 |
|---------|---------|---------|
| `test_list_no_briefs` | `lee task-brief list` | 没有 Briefs |
| `test_list_with_briefs` | `lee task-brief list` | 有 Briefs |
| `test_list_with_run_id_filter` | `lee task-brief list --run-id xxx` | run ID 过滤 |
| `test_list_with_department_filter` | `lee task-brief list --department backend` | 部门过滤 |
| `test_list_json_format` | `lee task-brief list --format json` | JSON 格式 |
| `test_list_yaml_format` | `lee task-brief list --format yaml` | YAML 格式 |
| `test_list_text_format` | `lee task-brief list --format text` | 文本格式 |
| `test_show_not_found` | `lee task-brief show TB-999` | Brief 不存在 |
| `test_show_yaml` | `lee task-brief show TB-001` | YAML 格式 |
| `test_show_json` | `lee task-brief show TB-001 --format json` | JSON 格式 |
| `test_show_text` | `lee task-brief show TB-001 --format text` | 文本格式 |
| `test_create_basic` | `lee task-brief create --run-id xxx ...` | 基本创建 |
| `test_create_with_scope` | `lee task-brief create --scope-include ...` | 带范围 |
| `test_create_with_acceptance` | `lee task-brief create --acceptance ...` | 带验收标准 |
| `test_create_with_risks` | `lee task-brief create --risks ...` | 带风险项 |
| `test_create_all_options` | `lee task-brief create ...` | 所有选项 |

---

## 6. 手动测试清单

### 6.1 SSOT 校验测试

```bash
# 1. 空环境校验
lee ssot validate
# 预期：✅ SSOT validation passed.

# 2. 创建 artifacts
python -c "
from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType, GovernanceKind
m = ArtifactManager()
prd = m.create(ArtifactType.CONTRACT, 'prd_contract', 'PRD', 'manual-test', GovernanceKind.TRANSFER)
print(f'Created PRD: {prd.id}')
"

# 3. 校验只有 PRD 的环境
lee ssot validate --run-id manual-test
# 预期：✅ SSOT validation passed.

# 4. 添加 API (无 derived_from)
python -c "
from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType, GovernanceKind
m = ArtifactManager()
api = m.create(ArtifactType.CONTRACT, 'api_contract', 'API', 'manual-test', GovernanceKind.TRANSFER)
print(f'Created API: {api.id}')
"

# 5. 校验 (应该失败)
lee ssot validate --run-id manual-test
# 预期：❌ SSOT validation failed:
#   - api_contract ART-XXXX missing derived_from
```

### 6.2 Context Bundle 测试

```bash
# 1. 列出 Bundles (空)
lee context list
# 预期：No context bundles found.

# 2. 创建 Bundle
python -c "
from lee.orchestrator.execution.artifacts import ArtifactManager, ContextBuilder
m = ArtifactManager()
b = ContextBuilder(m)
bundle = b.record_llm_call_v1_0(
    run_id='manual-test',
    step_id='step-1',
    prompt_text='Test prompt',
    response='Test response',
    department='backend'
)
b.save_bundle(bundle)
print(f'Created bundle: {bundle.id}')
"

# 3. 列出 Bundles
lee context list
# 预期：显示新创建的 Bundle

# 4. 查看 Bundle 详情
lee context show <bundle_id>
# 预期：显示 Bundle 详情 (YAML 格式)
```

### 6.3 Task Brief 测试

```bash
# 1. 列出 Briefs (空)
lee task-brief list
# 预期：No task briefs found.

# 2. 创建 Brief
lee task-brief create \
  --run-id manual-test \
  --department backend \
  --title "手动测试任务" \
  --description "这是一个手动测试任务" \
  --task-type feature

# 3. 列出 Briefs
lee task-brief list
# 预期：显示新创建的 Brief

# 4. 查看 Brief 详情
lee task-brief show <brief_id>
# 预期：显示 Brief 详情 (YAML 格式)
```

### 6.4 真理链测试

```bash
# 1. 创建完整真理链
python << 'EOF'
from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType, GovernanceKind

m = ArtifactManager()

# PRD
prd = m.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="# PRD",
    run_id="chain-test",
    governance_kind=GovernanceKind.TRANSFER,
)
print(f"PRD: {prd.id}")

# API (derived_from PRD)
api = m.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="# API",
    run_id="chain-test",
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd.id,
)
print(f"API: {api.id}")

# Code (implements API)
code = m.create(
    artifact_type=ArtifactType.CODE_REF,
    category="implementation",
    content="def func(): ...",
    run_id="chain-test",
    governance_kind=GovernanceKind.DELIVERABLE,
    implements=[api.id],
)
print(f"Code: {code.id}")

# Test (verifies PRD and API)
test = m.create(
    artifact_type=ArtifactType.TEST,
    category="test_plan",
    content="# Test",
    run_id="chain-test",
    governance_kind=GovernanceKind.TRANSFER,
    verifies=[prd.id, api.id],
)
print(f"Test: {test.id}")
EOF

# 2. 校验真理链
lee ssot validate --run-id chain-test
# 预期：✅ SSOT validation passed.

# 3. 查看真理链
lee ssot show-chain <api_id>
# 预期：显示 API → PRD 的链条

# 4. 影响分析
lee ssot impact <prd_id>
# 预期：显示 API 作为依赖者
```

---

## 7. 测试故障排查

### 7.1 常见问题

**Q1: 测试失败提示 `ModuleNotFoundError: No module named 'lee'`**

```bash
# 解决方案：安装 LEE 为可编辑模式
pip install -e .
```

**Q2: 测试失败提示 `fcntl` 错误 (Windows)**

```bash
# 解决方案：已修复，确保代码已更新
# 如果仍有问题，检查是否使用了旧版本
git pull origin main
```

**Q3: CLI 测试失败提示命令不存在**

```bash
# 解决方案：验证 CLI 入口
python -c "from lee.cli.main import cli; cli(['--help'])"

# 如果入口正常但测试失败，检查测试 fixture
# 确保 monkeypatch 正确设置了 ArtifactManager
```

### 7.2 调试技巧

```bash
# 1. 使用 -v 查看详细输出
python -m pytest test_file.py -v

# 2. 使用 -s 查看 print 输出
python -m pytest test_file.py -s

# 3. 使用 --pdb 进入调试器
python -m pytest test_file.py --pdb

# 4. 使用 -k 过滤测试
python -m pytest -k "test_validate" -v

# 5. 使用 --tb=long 查看详细 traceback
python -m pytest test_file.py --tb=long
```

---

## 8. 测试报告

### 8.1 生成测试报告

```bash
# 生成 HTML 报告
python -m pytest src/lee/orchestrator/execution/artifacts/tests/ \
    --html=report.html --self-contained-html

# 生成 XML 报告 (用于 CI/CD)
python -m pytest src/lee/orchestrator/execution/artifacts/tests/ \
    --junitxml=report.xml

# 生成覆盖率报告
python -m pytest src/lee/orchestrator/execution/artifacts/tests/ \
    --cov=lee/orchestrator/execution/artifacts \
    --cov-report=html:cov_html
```

### 8.2 解读测试报告

**通过标准**:
- 所有 189 个测试用例通过
- 测试覆盖率 > 80%
- 无 ERROR 和 WARNING

**失败处理**:
1. 查看失败原因 (`--tb=short`)
2. 定位问题代码
3. 修复后重新运行
4. 确认所有测试通过

---

## 9. 参考文档

- [SSOT 用户指南](SSOT_USER_GUIDE.md)
- [SSOT API 参考](SSOT_API_REFERENCE.md)
- [SSOT 最佳实践](SSOT_BEST_PRACTICES.md)
- [技术债文档](TECH_DEBT.md)
