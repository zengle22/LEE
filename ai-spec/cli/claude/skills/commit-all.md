# Commit All Repositories Skill

> 提交所有仓库的代码变更，自动处理临时文件

## 触发命令

```
/commit-all [message]
```

## 功能说明

1. **扫描所有仓库** - 检查以下仓库的变更状态：
   - `ai-constitution` (主仓库)
   - `project/AI跑步教练` (项目仓库)
   - `git/ai-marathon-coach-front` (前端仓库)
   - `git/ai-marathon-coach-server` (后端仓库)

2. **处理临时文件** - 自动将以下文件加入 `.gitignore`：
   - `*-preview.png` (预览截图)
   - `screenshot-*.png` (截图)
   - `phase*-*.png` (阶段截图)
   - `icon-preview.png` (图标预览)
   - `*.tmp`, `*.temp` (临时文件)
   - `tmpclaude-*-cwd` (Claude Code 临时文件)

3. **清理临时文件** - 删除工作区中的临时文件

4. **智能提交** - 根据变更内容生成提交信息

## 执行流程

```
┌─────────────────────────────────────────────────────────┐
│  1. 扫描所有仓库 git status                              │
├─────────────────────────────────────────────────────────┤
│  2. 检查临时文件，更新 .gitignore                        │
├─────────────────────────────────────────────────────────┤
│  3. 删除临时文件 (tmpclaude-*-cwd 等)                    │
├─────────────────────────────────────────────────────────┤
│  4. 对每个有变更的仓库：                                 │
│     - git add -A                                        │
│     - git diff --cached --stat                          │
│     - 生成 commit message                               │
│     - git commit                                        │
├─────────────────────────────────────────────────────────┤
│  5. 输出提交汇总                                        │
└─────────────────────────────────────────────────────────┘
```

## 仓库路径配置

```yaml
repositories:
  - name: ai-constitution
    path: E:/ai/ai-constitution
    type: main

  - name: AI跑步教练
    path: E:/ai/ai-constitution/project/AI跑步教练
    type: project

  - name: ai-marathon-coach-front
    path: E:/ai/ai-constitution/git/ai-marathon-coach-front
    type: frontend

  - name: ai-marathon-coach-server
    path: E:/ai/ai-constitution/git/ai-marathon-coach-server
    type: backend
```

## 临时文件规则

以下模式的文件自动加入 `.gitignore`：

```gitignore
# Screenshots and previews
*-preview.png
screenshot-*.png
phase*-*.png
icon-preview.png

# Temporary files
*.tmp
*.temp

# Claude Code temp files
tmpclaude-*-cwd
```

### 清理操作

执行提交前自动删除以下临时文件：

```bash
rm -f tmpclaude-*-cwd
```

## Commit Message 格式

遵循 Conventional Commits 规范：

```
<type>(<scope>): <description>

[body]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Type 推断规则

| 变更类型 | Type |
|---------|------|
| 新文件 (feature) | `feat` |
| 修复 | `fix` |
| 文档 | `docs` |
| 配置/工具 | `chore` |
| 重构 | `refactor` |
| 测试 | `test` |

### Scope 推断规则

| 仓库/目录 | Scope |
|----------|-------|
| orchestrator/ | `orchestrator` |
| ai-spec/specs/common/agents/ | `agent` |
| ai-spec/specs/common/skills/ | `skill` |
| phase8/ | `phase8` |
| phase9/ | `phase9` |
| src/pages/ | `ui` |
| internal/handler/ | `api` |
| internal/service/ | `service` |

## 输出示例

```
=== 仓库提交汇总 ===

✅ ai-constitution
   7e62246 chore: add screenshot files to gitignore
   1 file changed

✅ AI跑步教练
   9d95d7e feat(phase8-9): complete UI pages and race planning
   105 files changed, +11783

✅ ai-marathon-coach-front
   04676c5 feat(phase9): add race planning pages and TabBar icons
   27 files changed, +22137

✅ ai-marathon-coach-server
   e910ddd feat(phase9): add race planning backend services
   14 files changed, +3578

⏭️ 无变更的仓库已跳过
```

## 使用示例

### 基本用法
```
/commit-all
```

### 指定提交信息
```
/commit-all feat(phase10): implement training analytics
```

### 只检查状态（不提交）
```
/commit-all --dry-run
```

## 注意事项

1. **不会自动 push** - 提交后需要手动 push 到远程
2. **不会修改已暂存的文件** - 只处理未跟踪和已修改的文件
3. **跳过空仓库** - 没有变更的仓库自动跳过
4. **保留 git hooks** - 不会跳过 pre-commit hooks

## 关联 Skills

- `/commit` - 单仓库提交（带交互式消息编辑）
- `/git-status` - 查看所有仓库状态
