# repo_scope 规范 v1.0

> 定义 step bundle 中 `repo_scope` 字段的使用规则。

---

## 一、字段定义

每个 step bundle 必须声明 `repo_scope`：

```yaml
steps:
  - id: fix-backend-api
    kind: claude_code
    repo_scope: [app-backend]        # 必填
    path_allowlist: ["internal/**"]  # 可选，细化写路径
    # ...
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repo_scope` | `List[str]` | ✅ | 允许操作的 repo_id 列表 |
| `path_allowlist` | `List[str]` | ❌ | 写路径白名单（覆盖 repo 级 path_policy） |

---

## 二、分类规则

### 单 repo step（90% 场景）

```yaml
repo_scope: [app-backend]
```

Runtime 行为：
- 分配 `<run_id>/worktrees/app-backend/repo/` 为 cwd
- 注入 `LEE_REPO_ID=app-backend`
- 写文件限制在 repo 的 `path_policy` 内

### 跨 repo step（必须拆步）

跨 repo 需求**不允许**单个 step 声明多个 repo_id。  
必须由 L2 拆分为多个单 repo step：

```yaml
# ❌ 错误：跨 repo 漫游
- id: update-all
  repo_scope: [proto-contract, app-backend, app-frontend]

# ✅ 正确：L2 拆步
- id: step-1-update-proto
  repo_scope: [proto-contract]
- id: step-2-update-backend
  repo_scope: [app-backend]
- id: step-3-update-frontend
  repo_scope: [app-frontend]
- id: step-4-integration-test
  repo_scope: [app-backend]   # 只跑测试，不改代码
- id: step-5-update-docs
  repo_scope: [docs]
  path_allowlist: ["changelog/**"]
```

---

## 三、硬规则（Executor Contract）

1. **repo_id 必填** — executor 接口不接受裸路径，只接受 repo_id
2. **cwd 强制 + git root 校验** — `git rev-parse --show-toplevel` 必须匹配
3. **产物必须 patch 化** — 没有 patch/receipt 不算完成
4. **越界写入 = 立即 fail** — 写路径不在白名单即失败

---

## 四、环境变量注入

Runtime 在启动 executor 时自动注入：

| 变量 | 说明 |
|------|------|
| `LEE_REPO_ID` | 当前 repo_id |
| `LEE_WORKDIR` | 当前工作目录（worktree） |
| `LEE_REPO_ROOT_EXPECTED` | 期望的 git root 路径 |

---

*Created: 2026-02-17 | Version: 1.0*
