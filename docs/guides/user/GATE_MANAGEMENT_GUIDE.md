---
title: LEE 门禁管理指南
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
---

# LEE 门禁管理指南

## 🎯 统一的门禁管理入口

LEE 提供了新的 `lee gates` 命令组，作为统一的所有门禁管理入口。

## 📋 可用命令

### 1. lee gates list - 列出门禁

列出指定工作流的所有门禁：

```bash
lee gates list <workflow_id>
```

**示例输出：**
```
工作流: wf_task_738a4957
状态: paused
当前步骤: s5_2_review_commits

门禁列表:
  ⏳ gate_s5_2_review_commits
     状态: pending
```

### 2. lee gates show - 显示门禁详情

显示门禁详情和相关的产物文件（artifacts）：

```bash
lee gates show <workflow_id>
```

**示例输出：**
```
工作流: wf_task_738a4957
状态: paused
当前步骤: s5_2_review_commits

📂 相关产物文件:

workspace-cleanup/:
  - commit-plan.yaml
  - doc-organization.yaml
  - file-analysis.yaml

tech-debt/:
  - tech-debt-2025-02-19.yaml
  - tech-debt-2025-02-19.md

📝 最近执行的步骤:
  ✅ s5_1_plan_commits (completed)
  ✅ s4_1_review_code_docs (completed)
  ✅ s3_1_organize_docs (completed)
  ✅ s2_1_update_gitignore (completed)
  ✅ s1_1_analyze_files (completed)
```

### 3. lee gates approve - 批准门禁

批准门禁，查看产物文件后确认：

```bash
lee gates approve <workflow_id> <gate_id> --approver <your-name> [--comments "审批意见"]
```

**功能：**
- 显示门禁信息
- 显示相关的产物文件（如 commit-plan.yaml）
- 提示确认
- 执行批准操作

**示例：**
```bash
lee gates approve wf_task_738a4957 gate_s5_2_review_commits --approver zengle
```

### 4. lee gates reject - 拒绝门禁

拒绝门禁，触发重试：

```bash
lee gates reject <workflow_id> <gate_id> --approver <your-name> [--comments "拒绝原因"]
```

**功能：**
- 显示拒绝后会发生什么
- 提示确认
- 执行拒绝操作

**示例：**
```bash
lee gates reject wf_task_738a4957 gate_s5_2_review_commits --approver zengle --comments "需要调整提交分组"
```

## 🔄 Reject 后的行为

### 工作流配置示例

```yaml
gates:
  s5_2_review_commits:
    type: human_review
    on_reject:
      trigger: commits_rejected
      action: retry_step
      retry_step: s5_1_plan_commits  # ← 返回这里重新规划
```

### Reject 后的流程

1. **不会回到 s4**（代码审查）
2. **会回到 s5_1_plan_commits**（重新规划提交）
3. 重新生成提交计划
4. 再次等待审核

这是合理的设计，因为：
- ✅ 如果提交计划有问题，需要重新规划
- ❌ 不需要重新审查代码（代码审查已完成）
- ❌ 不需要重新整理文档

## 📊 完整的工作流示例

### 场景：审核提交计划

```bash
# 1. 查看当前状态
lee status wf_task_738a4957

# 2. 查看门禁详情和产物
lee gates show wf_task_738a4957

# 3. 查看提交计划（可选）
cat workspace-cleanup/commit-plan.yaml

# 4. 批准门禁
lee gates approve wf_task_738a4957 gate_s5_2_review_commits --approver zengle

# 5. 监控后续执行
lee watch wf_task_738a4957
```

### 场景：拒绝并重新规划

```bash
# 1. 查看提交计划
lee gates show wf_task_738a4957

# 2. 拒绝门禁
lee gates reject wf_task_738a4957 gate_s5_2_review_commits \
   --approver zengle \
   --comments "commit-001 和 commit-002 应该合并"

# 3. 监控重新规划
lee watch wf_task_738a4957
```

## 🆕 与旧命令的对比

### 旧命令（仍然可用）

```bash
lee approve <workflow_id> <gate_id> --approver <name>
```

### 新命令（推荐）

```bash
# 新命令提供更多功能
lee gates approve <workflow_id> <gate_id> --approver <name>
lee gates show <workflow_id>        # 查看详情和产物
lee gates list <workflow_id>         # 列出门禁
```

**新命令的优势：**
- ✅ 统一的入口
- ✅ 自动显示产物文件
- ✅ 显示提交计划内容
- ✅ 确认提示，避免误操作
- ✅ 显示失败原因

## 🎯 使用建议

1. **审核前必看**：
   ```bash
   lee gates show <workflow_id>
   ```

2. **仔细查看产物**：
   - 提交计划：`workspace-cleanup/commit-plan.yaml`
   - 技术债报告：`tech-debt/tech-debt-*.yaml`
   - 其他输出文件

3. **批准或拒绝**：
   ```bash
   # 批准
   lee gates approve <workflow_id> <gate_id> --approver <name>
   
   # 拒绝
   lee gates reject <workflow_id> <gate_id> --approver <name> --comments "原因"
   ```

4. **监控后续执行**：
   ```bash
   lee watch <workflow_id>
   ```

## 📝 总结

- **lee gates** 是统一的门禁管理入口
- **Reject 会回到 s5_1**（重新规划提交），不是 s4
- **所有产物文件都会自动显示**
- **确认提示避免误操作**
