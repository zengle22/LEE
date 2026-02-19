---
title: 资产层规范（Asset Layer Specification）
author: LEE Team
date: 2026-02-08
version: 1.0
last_updated: 2026-02-19
---

# 资产层规范（Asset Layer Specification）

版本：v1.0

## 目标

定义项目级 `/spec/`、`/evidence/`、`/env/` 的标准组织方式，确保执行产物可追溯、可验证、可复用。

## 目录结构

```
/project-root/
├── spec/
│   ├── dev/
│   │   ├── feature_xxx.yaml
│   │   └── bugfix_xxx.yaml
│   ├── qa/
│   │   ├── release_xxx.yaml
│   │   └── testcase_xxx.yaml
│   └── devops/
│       ├── staging.yaml
│       └── production.yaml
├── evidence/
│   ├── RUN-YYYYMMDD-XXXX/
│   │   ├── manifest.yaml
│   │   ├── test_report.json
│   │   ├── git_diff.patch
│   │   └── logs/
│   └── RUN-YYYYMMDD-YYYY/
├── env/
│   ├── .devcontainer/
│   ├── secrets.template.yaml
│   ├── staging.env.template
│   └── production.env.template
└── .workflow/
    ├── orchestrator.db
    ├── state.yaml
    └── ...
```

## 规范说明

- `spec/`：项目级意图与约束，不保存执行产物。
- `evidence/`：按 run_id 组织的执行证据，支持回溯与审计。
- `env/`：环境配置与模板，不提交真实密钥。
- `.workflow/`：LEE Orchestrator 运行态目录。

## Evidence 清单

每个 run 必须包含 `manifest.yaml`，记录：

- `run_id`
- `step_id`
- `collected_at`
- `artifacts`（文件/目录列表）

## 禁止事项

- 不允许将执行产物写入 `spec/`。
- 不允许提交真实密钥到 `env/`。
- 不允许跳过 Evidence 收集步骤。
