# L3 模板 Lint 检查 - 阿里云 Flow 配置指南

## 概述

本目录包含 L3 Workflow Template 的 Lint 检查工具和在阿里云 Flow 上运行 CI 的配置。

## 文件说明

```
.ai/
├── flow-lint-l3.yml          # 阿里云 Flow 流水线配置
└── LINT_README.md            # 本文件
```

## 在阿里云 Flow 配置 CI

### 方式一：使用现有配置文件

1. 登录 [阿里云 Flow 控制台](https://flow.console.aliyun.com/)

2. 选择你的项目（LEE）

3. 点击「流水线」→「创建流水线」

4. 选择「导入 YAML 配置」

5. 上传或选择 `.azure-pipelines/flow-lint-l3.yml` 文件

6. 点击「创建」

### 方式二：手动配置

1. 登录 [阿里云 Flow 控制台](https://flow.console.aliyun.com/)

2. 选择你的项目（LEE）

3. 点击「流水线」→「创建流水线」

4. 选择「空白模板」

5. 配置触发器：
   - 代码推送：选择 `main` 和 `master` 分支
   - 路径过滤：添加 `spec-global/departments/**/workflows/**/*.yaml`

6. 添加构建步骤：
   ```bash
   # 环境设置
   pip3 install --quiet pyyaml jsonschema
   
   # 运行 Lint
   python3 scripts/lint_l3_templates.py spec-global/departments
   ```

7. 保存并启用流水线

### 方式三：使用 azure-pipelines.yml（根目录）

阿里云 Flow 也支持 Azure Pipelines 格式，根目录的 `azure-pipelines.yml` 会被自动识别。

## 触发条件

Lint 检查会在以下情况自动运行：

- **Push 到 main/master 分支**，且修改了：
  - `spec-global/departments/**/workflows/**/*.yaml`
  - `spec-global/departments/**/workflows/**/*.yml`
  - `scripts/lint_l3_templates.py`

- **创建 Merge Request** 到 main/master 分支，且修改了上述路径

## 本地测试

在推送之前，可以在本地运行 Lint 检查：

```bash
# 安装依赖
pip install pyyaml jsonschema

# 运行检查
python scripts/lint_l3_templates.py spec-global/departments

# 检查特定文件
python scripts/lint_l3_templates.py spec-global/departments/qa/workflows/templates/test-set-l3-template.yaml
```

## 修复 Lint 错误

如果 Lint 检查失败，可以使用迁移脚本自动修复：

```bash
# 预览变更（dry-run）
python scripts/migrate_l3_templates.py spec-global/departments

# 实际执行迁移
python scripts/migrate_l3_templates.py spec-global/departments --no-dry-run
```

## 通知配置（可选）

可以在流水线配置中添加钉钉通知：

```yaml
notifications:
  failure:
    - type: dingtalk
      webhook: $(DINGTALK_WEBHOOK)
```

在阿里云 Flow 控制台配置环境变量 `DINGTALK_WEBHOOK`。

## 相关文档

- [阿里云 Flow 产品文档](https://help.aliyun.com/product/44895.html)
- [Flow YAML 配置参考](https://help.aliyun.com/document_detail/175837.html)
- [CodeUp 代码托管](https://help.aliyun.com/product/44893.html)
