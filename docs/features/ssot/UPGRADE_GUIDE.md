# SSOT v1.0/v1.5 升级指南

**文档版本**: 1.0
**适用版本**: 从 Artifact Management v2.0 升级到 v2.1 (SSOT v1.0/v1.5)
**更新日期**: 2026-03-01

---

## 1. 概述

本指南帮助你将现有的 LEE 产出物管理系统从 v2.0 升级到 v2.1（SSOT v1.0/v1.5 版本）。

### 1.1 新增功能

| 功能模块 | 版本 | 说明 |
|---------|------|------|
| SSOT 真理链校验 | v1.0 | 确保产出物关联关系完整 |
| Context Bundle | v1.0 | 完整的 LLM 调用上下文记录 |
| Task Brief | v1.5 | 任务简报（压缩视图） |
| Gate SSOT 集成 | v1.5 | Gate 审批时自动校验 SSOT |
| CLI 命令 | v1.5 | `lee ssot`, `lee context`, `lee task-brief` |

### 1.2 兼容性

- **向后兼容**: 是，v2.0 的 artifacts 可无缝迁移
- **Python 版本**: 3.10+
- **依赖变更**: 无新增外部依赖

---

## 2. 升级前检查

### 2.1 系统要求

```bash
# 检查 Python 版本
python --version  # 需要 3.10+

# 检查当前 LEE 版本
lee --version  # 需要 v2.0+
```

### 2.2 备份现有数据

```bash
# 备份 artifacts 目录
cp -r .artifacts .artifacts.backup.$(date +%Y%m%d)

# 备份 spec-global 配置
cp -r spec-global/artifacts spec-global/artifacts.backup.$(date +%Y%m%d)
```

### 2.3 检查现有 artifacts

```bash
# 列出现有 artifacts
ls -la .artifacts/active/

# 检查 manifest 文件
find .artifacts -name "manifest.yaml" | head -10
```

---

## 3. 升级步骤

### 3.1 代码升级

#### 步骤 1: 更新代码库

```bash
# 如果是 git 仓库
git pull origin main

# 或切换到新版本标签
git checkout v2.1.0
```

#### 步骤 2: 验证模块导入

```bash
# 验证新模块可导入
python -c "from lee.orchestrator.execution.artifacts import SSOTService; print('OK')"
python -c "from lee.orchestrator.execution.artifacts import ContextBuilder; print('OK')"
python -c "from lee.orchestrator.execution.artifacts import TaskBriefGenerator; print('OK')"
```

#### 步骤 3: 验证 CLI 命令

```bash
# 验证新 CLI 命令可用
lee ssot --help
lee context --help
lee task-brief --help
```

### 3.2 配置升级

#### 步骤 1: 更新 artifacts 配置

编辑 `spec-global/artifacts/config.yaml`，确保包含以下新类别：

```yaml
artifact_types:
  CONTRACT:
    categories:
      - prd_contract      # 新增：PRD 契约
      - task_card         # 新增：Task Card

  DOCUMENT:
    categories:
      - note              # 新增：通用笔记
      - task_brief        # 新增：Task Brief
      - task_context_bundle  # 新增：Context Bundle

  TEST:
    categories:
      - test_plan         # 新增：测试计划
```

#### 步骤 2: 验证配置加载

```bash
# 验证配置可正确加载
python -c "
from lee.orchestrator.execution.artifacts import ArtifactCategoryRegistry
print('CONTRACT:', ArtifactCategoryRegistry.get_categories('CONTRACT'))
print('DOCUMENT:', ArtifactCategoryRegistry.get_categories('DOCUMENT'))
"
```

### 3.3 数据迁移

#### 步骤 1: 重建 Registry 索引

```bash
# 重建 artifacts registry
python -c "
from lee.orchestrator.execution.artifacts import ArtifactManager
manager = ArtifactManager()
manager.registry.rebuild()
print('Registry rebuilt successfully')
"
```

#### 步骤 2: 验证现有 artifacts

```bash
# 列出所有现有 artifacts
python -c "
from lee.orchestrator.execution.artifacts import ArtifactManager
manager = ArtifactManager()
manager.registry.rebuild()
for artifact in manager.registry._artifacts.values():
    print(f'{artifact.id}: {artifact.category} ({artifact.status.value})')
"
```

#### 步骤 3: 构建 SSOT 索引

```bash
# 构建 SSOT 索引
lee ssot build-index
```

---

## 4. 升级后验证

### 4.1 功能验证

#### 验证 1: SSOT 校验

```bash
# 运行 SSOT 校验
lee ssot validate

# 预期输出：
# ✅ SSOT validation passed.
# 或
# ❌ SSOT validation failed:
#   - <错误列表>
```

#### 验证 2: Context Bundle 列表

```bash
# 列出 Context Bundles
lee context list

# 预期输出：
# No context bundles found.
# 或
# ID          Run ID     Department  Created At
# TCTX-00001  RUN-001    backend     2026-03-01...
```

#### 验证 3: Task Brief 列表

```bash
# 列出 Task Briefs
lee task-brief list

# 预期输出：
# No task briefs found.
# 或
# ID          Run ID     Department  Title  Status
# TB-001      RUN-001    backend     ...    draft
```

### 4.2 集成验证

#### 验证 1: Gate 集成

```python
from lee.orchestrator.execution.artifacts import (
    ArtifactManager, ArtifactType, GovernanceKind,
    GateArtifactHandler
)

# 创建测试 artifacts
manager = ArtifactManager()
prd = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="Test PRD",
    run_id="upgrade-test",
    governance_kind=GovernanceKind.TRANSFER,
)

api = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="Test API",
    run_id="upgrade-test",
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd.id,
)

# 测试 Gate 审批
handler = GateArtifactHandler()
result = handler.approve_gate_artifacts(
    run_id="upgrade-test",
    gate_id="GATE-UPGRADE-TEST",
    enforce=True,
)

print(f"Gate result: {result}")
# 预期：{'frozen_count': 2, 'ssot_validated': True, ...}
```

### 4.3 性能验证

```bash
# 测试 registry 加载时间
time python -c "
from lee.orchestrator.execution.artifacts import ArtifactManager
manager = ArtifactManager()
manager.registry.rebuild()
print(f'Loaded {len(manager.registry._artifacts)} artifacts')
"
```

---

## 5. 常见问题

### 5.1 升级后 SSOT 校验失败

**问题**: `lee ssot validate` 报告大量错误

**原因**: 现有 artifacts 可能缺少 SSOT 关联字段

**解决方案**:

```bash
# 1. 查看详细错误
lee ssot validate

# 2. 对于断链的 artifacts，可选择：
#    a) 重新创建并添加关联字段
#    b) 暂时使用 warning 模式
lee ssot validate --run-id <run_id>  # 不使用 --enforce
```

### 5.2 CLI 命令找不到

**问题**: `lee ssot: command not found`

**原因**: CLI 命令未正确注册

**解决方案**:

```bash
# 1. 验证 CLI 模块安装
python -c "from lee.cli.commands.ssot import ssot; print('OK')"

# 2. 检查 CLI 入口
cat src/lee/cli/main.py | grep -A2 "add_command"

# 3. 重新安装 LEE
pip install -e .
```

### 5.3 Registry 重建失败

**问题**: `registry.rebuild()` 抛出异常

**原因**: manifest 文件格式错误

**解决方案**:

```bash
# 1. 查找问题 manifest
find .artifacts -name "manifest.yaml" -exec python -c "
import yaml, sys
try:
    yaml.safe_load(open(sys.argv[1]))
except Exception as e:
    print(f'Error in {sys.argv[1]}: {e}')
" {} \;

# 2. 修复或删除问题文件
# 3. 重新重建
python -c "from lee.orchestrator.execution.artifacts import ArtifactManager; ArtifactManager().registry.rebuild()"
```

### 5.4 Context Bundle 不显示

**问题**: `lee context list` 始终显示 "No context bundles found"

**原因**: 还没有创建 Context Bundles

**解决方案**:

```python
# 创建测试 Context Bundle
from lee.orchestrator.execution.artifacts import ArtifactManager, ContextBuilder

manager = ArtifactManager()
builder = ContextBuilder(manager)

bundle = builder.record_llm_call_v1_0(
    run_id="test-run",
    step_id="step-1",
    prompt_text="Test prompt",
    response="Test response",
    department="backend",
)

builder.save_bundle(bundle)
print(f"Created bundle: {bundle.id}")
```

---

## 6. 回滚指南

如需回滚到 v2.0，请执行以下步骤：

### 6.1 回滚代码

```bash
# 回滚到上一个版本
git checkout v2.0.0
```

### 6.2 恢复数据

```bash
# 恢复 artifacts
rm -rf .artifacts
mv .artifacts.backup.YYYYMMDD .artifacts

# 恢复配置
rm -rf spec-global/artifacts
mv spec-global/artifacts.backup.YYYYMMDD spec-global/artifacts
```

### 6.3 验证回滚

```bash
# 验证版本
lee --version  # 应该显示 v2.0

# 验证功能
python -c "from lee.orchestrator.execution.artifacts import ArtifactManager; print('OK')"
```

---

## 7. 后续步骤

升级完成后，建议：

1. **阅读用户指南**: [SSOT_USER_GUIDE.md](SSOT_USER_GUIDE.md)
2. **学习最佳实践**: [SSOT_BEST_PRACTICES.md](SSOT_BEST_PRACTICES.md)
3. **配置 CI/CD 集成**: 在 Gate 审批中启用 SSOT 校验
4. **培训团队**: 确保团队成员了解新的工作流程

---

## 8. 支持

如遇到问题，请：

1. 查看 [故障排查指南](SSOT_USER_GUIDE.md#6-故障排查)
2. 检查 [技术债文档](TECH_DEBT.md) 了解已知问题
3. 提交 Issue 到项目仓库

---

**升级检查清单**:

- [ ] 已备份现有数据
- [ ] 代码已升级到 v2.1
- [ ] 新模块导入验证通过
- [ ] CLI 命令验证通过
- [ ] 配置已更新
- [ ] Registry 索引重建完成
- [ ] SSOT 校验验证通过
- [ ] Gate 集成验证通过
- [ ] 团队培训完成
