# L3 模板 Lint 检查 - 配置指南

## 概述

本目录包含 L3 Workflow Template 的 Lint 检查工具和 CI/CD 配置。

## 文件说明

```
.ai/
├── flow-lint-l3.yml          # 阿里云 Flow 流水线配置
├── LINT_README.md            # 本文件
scripts/
├── lint_l3_templates.py      # L3 模板 Lint 检查工具
├── migrate_l3_templates.py   # L3 模板迁移工具
├── detect-hardcoded-paths.py # 硬编码路径检测工具
├── git-pre-commit-hook.py    # Git pre-commit hook 实现
├── git-pre-push-hook.py      # Git pre-push hook 实现
└── install-git-hooks.py      # Git hooks 安装脚本
```

## 方式一：本地 Git Hooks（推荐）

### 安装 Git Hooks

```bash
# 安装 hooks
python scripts/install-git-hooks.py

# 查看安装状态
python scripts/install-git-hooks.py --status

# 卸载 hooks
python scripts/install-git-hooks.py --uninstall
```

### Hooks 功能

| Hook | 触发时机 | 检查内容 |
|------|----------|----------|
| pre-commit | `git commit` 时 | 硬编码路径检测 |
| pre-push | `git push` 时 | L3 模板 Lint 检查 |

### Hook 失败处理

```bash
# 先修复本地检查失败项，再重新执行
git commit
git push
```

本仓库约束：

- 不要使用 `--no-verify` 跳过本地 hooks
- 本地校验失败时，先修复再提交/推送

## 方式二：阿里云 Flow CI/CD

### 自动触发

CI 流程会在以下情况自动运行：

- **Push 到 main/master 分支**
- **创建 Pull Request**
- **修改路径**：
  - `spec-global/departments/**/workflows/**/*.yaml`
  - `scripts/lint_l3_templates.py`
  - `scripts/detect-hardcoded-paths.py`
  - `src/**/*.py`

### 在阿里云 Flow 控制台配置

1. 登录 [阿里云 Flow 控制台](https://flow.console.aliyun.com/)

2. 选择你的项目（LEE/framework）

3. 点击「流水线」→「创建流水线」

4. 选择「导入 YAML 配置」

5. 上传或选择 `azure-pipelines.yml` 文件

6. 点击「创建」并启用流水线

### 手动配置

1. 登录 [阿里云 Flow 控制台](https://flow.console.aliyun.com/)

2. 选择项目 → 点击「流水线」→「创建流水线」

3. 选择「空白模板」

4. 配置触发器（同上）

5. 添加构建步骤：
   ```bash
   # 安装依赖
   pip3 install --quiet pyyaml jsonschema
   
   # 硬编码路径检测
   python3 scripts/detect-hardcoded-paths.py src/
   
   # L3 模板 Lint 检查
   python3 scripts/lint_l3_templates.py spec-global/departments
   ```

6. 保存并启用

## 本地测试

在 commit/push 之前，可以在本地运行检查：

```bash
# 安装依赖
pip install pyyaml jsonschema

# 硬编码路径检测
python scripts/detect-hardcoded-paths.py src/

# L3 模板 Lint 检查
python scripts/lint_l3_templates.py spec-global/departments

# 检查特定文件
python scripts/lint_l3_templates.py spec-global/departments/qa/workflows/templates/test-set-l3-template.yaml
```

## 修复问题

### 硬编码路径

如果检测到硬编码路径：

```bash
# 使用路径变量替代硬编码
# 错误：.artifacts/qa/test-sets/
# 正确：{{ qa_specs_dir }}/test-sets/
```

### L3 模板格式问题

如果 Lint 检查失败，可以使用迁移脚本自动修复：

```bash
# 预览变更（dry-run）
python scripts/migrate_l3_templates.py spec-global/departments

# 实际执行迁移
python scripts/migrate_l3_templates.py spec-global/departments --no-dry-run
```

## Schema 规则

- ✅ 根节点必须使用 `stages`（禁止根级别 `steps`）
- ✅ 每个 `stage` 必须有 `kind: stage`
- ✅ `step` 支持 `agent` 和 `skill` 两种类型
- ✅ `agent` step 必须有 `agent_id`
- ✅ `skill` step 必须有 `skill_id`

## 相关文档

- [阿里云 Flow 产品文档](https://help.aliyun.com/product/44895.html)
- [Flow YAML 配置参考](https://help.aliyun.com/document_detail/175837.html)
- [CodeUp 代码托管](https://help.aliyun.com/product/44893.html)
