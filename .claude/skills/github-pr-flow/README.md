# GitHub PR Flow Skill 配置指南

## 概述

`github-pr-flow` skill 允许你：
- 推送当前分支到 GitHub
- 创建或复用 Pull Request
- 监控 GitHub Actions 检查直到完成

## 配置步骤

### 1. 生成 GitHub Personal Access Token

1. 访问 GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 "Generate new token (classic)"
3. 选择以下 scopes：
   - `repo` - Full control of private repositories
   - `read:org` - Read org membership (如果需要访问组织仓库)
   - `workflow` - Update GitHub Action workflows
4. 生成并复制 token

### 2. 配置 Token

有两种方式配置 token：

#### 方式 A: 环境变量（推荐）

在 shell 配置文件中添加：

```bash
# ~/.bashrc, ~/.zshrc, 或 ~/.profile
export GITHUB_TOKEN="ghp_your_token_here"
```

然后重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

#### 方式 B: 本地配置文件

复制 `.claude/settings.local.json.example` 到 `.claude/settings.local.json` 并填入 token：

```json
{
  "env": {
    "GH_TOKEN": "ghp_your_token_here"
  }
}
```

**注意：** 不要将包含真实 token 的配置文件提交到 git！

### 3. 验证配置

```bash
# 检查 gh CLI 是否安装
gh --version

# 检查 token 是否生效
gh auth status
```

### 4. 使用 Skill

```bash
/github-pr-flow
```

或在对话中输入：
```
/github-pr-flow
```

## 文件说明

| 文件 | 说明 | 是否提交 |
|------|------|----------|
| `.claude/commands/github-pr-flow.md` | Skill 定义文件 | ✅ 是 |
| `.claude/skills/github-pr-flow/SKILL.md` | Skill 文档 | ✅ 是 |
| `.claude/settings.local.json` | 本地配置（含 token） | ❌ 否 |
| `.gitignore` | 忽略本地配置文件 | ✅ 是 |

## 安全提示

- **永远不要**将包含真实 token 的文件提交到 git
- 定期轮换你的 GitHub token
- 如果 token 泄露，立即在 GitHub 上撤销并重新生成
- 使用只读权限的 token 用于只读操作

## 故障排查

### "gh: command not found"

安装 GitHub CLI：
- macOS: `brew install gh`
- Windows: `winget install GitHub.cli`
- Linux: 参见 https://github.com/cli/cli#installation

### "authentication required"

运行以下命令重新认证：
```bash
gh auth logout
gh auth login
```

### "permission denied"

检查你的 token 是否有足够的 scopes：
```bash
gh auth status -v
```
