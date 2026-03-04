# Vibe Kanban 使用指南

## 📖 目录

1. [简介](#简介)
2. [安装与启动](#安装与启动)
3. [核心功能](#核心功能)
4. [快速开始](#快速开始)
5. [项目与任务管理](#项目与任务管理)
6. [AI 代理配置](#ai-代理配置)
7. [Git 工作流](#git-工作流)
8. [高级功能](#高级功能)
9. [配置与定制](#配置与定制)
10. [故障排除](#故障排除)
11. [最佳实践](#最佳实践)

---

## 📝 简介

**Vibe Kanban** 是一款专为 AI 编程时代设计的可视化项目管理工具，由 BloopAI 团队开发。它将传统的看板项目管理与 AI 编码代理（Claude Code、Gemini CLI、Codex、Amp 等）完美结合，让开发者能够高效地编排、管理和审查 AI 编码任务。

### 为什么选择 Vibe Kanban？

在 AI 编程时代，工程师的角色正在从"编写代码"转向"规划、审查和编排任务"。Vibe Kanban 正是为这一转变而设计：

- 🎯 **统一管理**：在一个界面中管理多个 AI 编码代理
- 🔄 **并行执行**：同时运行多个 AI 任务，提升效率 10 倍
- 📊 **可视化跟踪**：实时查看任务进度和状态
- 🔍 **代码审查**：直观地查看 AI 生成的代码变更
- 🌳 **隔离环境**：每个任务使用独立的 Git worktree

### 核心特性

| 特性 | 说明 |
|------|------|
| **多代理支持** | Claude Code、Gemini CLI、Codex、Amp 等 |
| **看板管理** | Todo、In Progress、Done 三列式任务管理 |
| **Git 集成** | 自动创建 worktree、diff 查看、rebase、merge |
| **远程访问** | 支持 SSH 远程编辑和云部署 |
| **MCP 协议** | 支持 Model Context Protocol 配置 |
| **开发服务器** | 一键启动预览服务器 |

---

## 🚀 安装与启动

### 系统要求

- **Node.js**: >= 18
- **pnpm**: >= 8 (仅开发环境)
- **Rust**: latest stable (仅从源码构建)
- **Git**: 任意版本

### 快速启动（推荐）

最简单的启动方式，无需安装：

```bash
npx vibe-kanban
```

这个命令会：
1. 自动下载 vibe-kanban（约 53MB，首次运行需要几分钟）
2. 启动本地服务器
3. 自动在浏览器中打开界面（通常是 `http://localhost:3000`）

### 从源码构建

如果你想从源码构建或参与开发：

```bash
# 1. 克隆仓库
git clone https://github.com/BloopAI/vibe-kanban.git
cd vibe-kanban

# 2. 安装依赖
pnpm install

# 3. 启动开发服务器
pnpm run dev
```

### 环境变量配置

Vibe Kanban 支持以下环境变量：

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `PORT` | 运行时 | 自动分配 | 服务器端口 |
| `HOST` | 运行时 | `127.0.0.1` | 服务器主机 |
| `BACKEND_PORT` | 运行时 | `0` | 后端端口（开发模式） |
| `FRONTEND_PORT` | 运行时 | `3000` | 前端端口（开发模式） |
| `VK_ALLOWED_ORIGINS` | 运行时 | 未设置 | 允许的 API 请求源（反向代理时使用） |
| `DISABLE_WORKTREE_CLEANUP` | 运行时 | 未设置 | 禁用 worktree 清理（调试用） |

**反向代理配置示例：**

```bash
# 设置允许的源
VK_ALLOWED_ORIGINS=https://your-domain.com

# 启动服务
npx vibe-kanban
```

---

## ⭐ 核心功能

### 1. 项目管理

- 添加现有 Git 仓库或创建新项目
- 自动验证 Git 仓库
- 项目范围的文件搜索
- 自定义设置和开发脚本

### 2. 任务管理

看板式任务管理，支持三列：

- **Todo**: 待处理任务
- **In Progress**: 进行中的任务
- **Done**: 已完成的任务

每个任务包含：
- 任务描述和详细信息
- 关联的 AI 代理
- Git 分支和 worktree 信息
- 执行历史记录

### 3. AI 代理集成

支持的 AI 编码代理：

| 代理 | 说明 |
|------|------|
| **Claude Code** | Anthropic 的 Claude 编程助手 |
| **Amp** | 高级模型处理器 |
| **Echo** | 简单的测试/调试代理 |
| **Gemini CLI** | Google 的 Gemini 编程工具 |
| **Codex** | OpenAI 的 Codex |

### 4. Git 工作流

- 🌳 **Worktree 隔离**：每个任务使用独立的 Git worktree
- 📊 **Diff 查看**：实时查看代码变更
- 🔄 **Rebase/Merge**：一键变基和合并
- 🎯 **分支管理**：自动创建和管理任务分支
- 📝 **提交审查**：查看 AI 生成的提交信息

### 5. 开发服务器

- 🚀 一键启动项目的开发服务器
- 🌐 自动配置端口和 URL
- 🛑 随时停止运行的服务器
- 🔊 完成通知音效

---

## 🎓 快速开始

### 第一步：启动应用

```bash
npx vibe-kanban
```

### 第二步：添加项目

1. 点击左侧面板的 **"Add Project"** 按钮
2. 选择添加方式：
   - **Existing Repository**: 添加现有 Git 仓库
   - **New Repository**: 创建新的 Git 仓库

### 第三步：创建任务

1. 在项目卡片中点击 **"New Task"**
2. 填写任务信息：
   - **Title**: 任务标题
   - **Description**: 详细描述
   - **Agent**: 选择 AI 代理
3. 点击 **"Create"** 创建任务

### 第四步：执行任务

1. 点击任务卡片上的 **"Play"** 按钮
2. AI 代理将开始执行任务
3. 实时查看执行日志和进度

### 第五步：审查代码

1. 任务完成后，点击 **"Review"** 按钮
2. 查看 Diff 对比
3. 如果满意，点击 **"Merge"** 合并到主分支
4. 如果不满意，可以：
   - 手动编辑文件
   - 让 AI 继续迭代
   - 放弃本次尝试

---

## 📂 项目与任务管理

### 添加项目

#### 方式一：添加现有仓库

1. 点击 **"Add Project"**
2. 选择 **"Existing Repository"**
3. 填写仓库信息：
   ```
   Repository Path: /path/to/your/repo
   Project Name: My Project (可选)
   ```
4. 点击 **"Add"**

#### 方式二：创建新仓库

1. 点击 **"Add Project"**
2. 选择 **"New Repository"**
3. 填写信息：
   ```
   Repository Path: /path/to/new/repo
   Project Name: My New Project
   Initialize with: README.md / .gitignore / license
   ```
4. 点击 **"Create"**

### 项目配置

每个项目可以自定义配置：

- **Setup Script**: 项目初始化脚本
- **Dev Script**: 开发服务器启动命令
- **Branch Pattern**: 分支命名模式
- **Environment Variables**: 环境变量

### 创建任务

#### 基础任务

```markdown
Title: 修复登录 Bug
Description:
  用户在输入错误密码后无法看到错误提示。
  需要检查认证逻辑并添加友好的错误提示。
Agent: Claude Code
```

#### 高级任务

```markdown
Title: 重构用户认证模块
Description: |
  # 目标
  将现有的 JWT 认证重构为基于 Session 的认证

  # 要求
  1. 保持 API 接口不变
  2. 添加单元测试
  3. 更新文档

  # 技术栈
  - 后端: Express + Passport.js
  - 前端: React + TanStack Query

Agent: Claude Code
Branch: feature/auth-refactor
```

### 任务生命周期

```
Todo → In Progress → Review → Done
  ↓         ↓          ↓       ↓
创建      执行中     审查中   完成
```

### 任务操作

| 操作 | 说明 | 快捷键 |
|------|------|--------|
| **Play** | 开始执行任务 | 点击播放按钮 |
| **Stop** | 停止执行 | 点击停止按钮 |
| **Review** | 查看代码变更 | 点击审查按钮 |
| **Merge** | 合并到主分支 | 审查界面中 |
| **Abandon** | 放弃本次尝试 | 任务菜单中 |
| **Delete** | 删除任务 | 任务菜单中 |

---

## 🤖 AI 代理配置

### 支持的代理

#### 1. Claude Code

**最强的 AI 编程助手**

```json
{
  "name": "claude-code",
  "command": "claude",
  "args": ["--project", "{project_path}"]
}
```

**配置要求：**
- 需要 Anthropic API Key
- 需要安装 Claude Code CLI

**适用场景：**
- 复杂的代码重构
- 多文件修改
- 架构设计

#### 2. Amp

**高级模型处理器**

```json
{
  "name": "amp",
  "command": "amp",
  "args": ["--project", "{project_path}"]
}
```

**适用场景：**
- 快速原型开发
- 代码生成

#### 3. Echo

**简单测试/调试代理**

```json
{
  "name": "echo",
  "command": "echo",
  "args": ["{task_description}"]
}
```

**适用场景：**
- 测试任务执行流程
- 调试配置

#### 4. Gemini CLI

**Google 的 Gemini 编程工具**

```json
{
  "name": "gemini-cli",
  "command": "gemini",
  "args": ["--project", "{project_path}"]
}
```

**配置要求：**
- 需要 Google API Key
- 需要安装 Gemini CLI

### 全局代理配置

在 **Settings → Agents** 中配置全局代理：

1. 点击左侧边栏的 **Settings** 图标
2. 选择 **Agents** 标签
3. 点击 **"Add Agent"** 添加新代理
4. 填写配置：
   ```
   Name: My Agent
   Command: agent-command
   Arguments: --arg1 {arg1_value} --arg2 {arg2_value}
   Environment Variables:
     API_KEY=your_api_key
   ```
5. 点击 **"Save"** 保存

### 项目级代理配置

在项目设置中覆盖全局配置：

1. 打开项目卡片
2. 点击 **Settings** 图标
3. 在 **Agents** 部分配置项目专属代理

---

## 🌳 Git 工作流

### Worktree 隔离

Vibe Kanban 为每个任务创建独立的 Git worktree，确保：

- ✅ 不同任务互不干扰
- ✅ 可以同时处理多个任务
- ✅ 主分支保持稳定
- ✅ 易于实验和回滚

**Worktree 结构：**

```
my-project/
├── .git/
├── main/           # 主分支
├── task-1-branch/  # 任务 1 的 worktree
├── task-2-branch/  # 任务 2 的 worktree
└── task-3-branch/  # 任务 3 的 worktree
```

### Diff 查看与代码审查

#### 查看 Diff

1. 任务完成后，点击 **"Review"** 按钮
2. 在 **Changes** 标签中查看所有变更文件
3. 点击文件查看详细 Diff

#### Diff 界面

```
--- a/src/auth.js
+++ b/src/auth.js
@@ -10,7 +10,7 @@
- function login(username, password) {
+ async function login(username, password) {
    const user = await db.findUser(username);
-   if (user.password === hash(password)) {
+   if (await bcrypt.compare(password, user.password)) {
      return createSession(user);
    }
    throw new Error('Invalid credentials');
```

#### 内联编辑

在审查界面中，你可以：

1. 点击 **"Edit"** 按钮进入编辑模式
2. 直接修改文件内容
3. 点击 **"Save"** 保存更改

### 分支操作

#### Rebase

将任务分支变基到最新的主分支：

1. 打开任务卡片
2. 点击 **"Rebase"** 按钮
3. 确认操作

**注意事项：**
- Rebase 会重写任务分支历史
- 如果有冲突，需要手动解决

#### Merge

将任务分支合并到主分支：

方式一：在审查界面中点击 **"Merge"**

方式二：在任务卡片中点击 **"Merge"**

**Merge 策略：**

| 策略 | 说明 | 使用场景 |
|------|------|----------|
| **Merge Commit** | 创建合并提交 | 保留完整历史 |
| **Squash Merge** | 压缩为单个提交 | 清晰的历史 |
| **Rebase Merge** | 变基后合并 | 线性历史 |

### 提交管理

#### 查看提交

在 **Commits** 标签中查看：
- 提交信息
- 提交者
- 提交时间
- 变更文件

#### 修改提交

1. 选择要修改的提交
2. 点击 **"Edit"**
3. 修改提交信息或内容
4. 保存更改

#### 放弃提交

1. 选择要放弃的提交
2. 点击 **"Revert"**
3. 确认操作

---

## 🔧 高级功能

### MCP (Model Context Protocol) 配置

MCP 允许 AI 代理访问外部工具和服务。

#### 配置 MCP 服务器

1. 进入 **Settings → MCP**
2. 点击 **"Add Server"**
3. 填写配置：

```json
{
  "name": "file-system",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
}
```

4. 点击 **"Save"** 保存

#### 内置 MCP 服务器

Vibe Kanban 内置了以下 MCP 服务器：

| 服务器 | 功能 |
|--------|------|
| **file-system** | 文件系统访问 |
| **git** | Git 操作 |
| **github** | GitHub API |
| **database** | 数据库查询 |

### 远程部署

#### 在远程服务器上运行

1. **克隆仓库到服务器：**

```bash
git clone https://github.com/BloopAI/vibe-kanban.git
cd vibe-kanban
pnpm install
pnpm run build
```

2. **配置环境变量：**

```bash
# 设置允许的源
export VK_ALLOWED_ORIGINS=https://your-domain.com

# 设置端口
export PORT=3000
export HOST=0.0.0.0
```

3. **启动服务：**

```bash
# 开发模式
pnpm run dev

# 生产模式
pnpm run start
```

#### 配置反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### 配置远程 SSH

1. **在本地机器上配置 SSH：**

```bash
# 生成 SSH 密钥（如果没有）
ssh-keygen -t ed25519

# 复制公钥到服务器
ssh-copy-id user@your-server.com
```

2. **在 Vibe Kanban 中配置：**

   - 进入 **Settings → Editor Integration**
   - 设置 **Remote SSH Host**: `your-server.com`
   - 设置 **Remote SSH User**: `your-username`

3. **使用远程编辑：**

   点击 **"Open in VSCode"** 会自动生成类似 `vscode://vscode-remote/ssh-remote+user@host/path` 的 URL

### 开发服务器管理

#### 启动开发服务器

1. 打开项目卡片
2. 点击 **"Dev Server"** 按钮
3. 选择要启动的脚本
4. 点击 **"Start"**

#### 服务器配置

在项目设置中配置：

```json
{
  "devServers": [
    {
      "name": "Frontend",
      "command": "npm run dev",
      "port": 5173,
      "url": "http://localhost:5173"
    },
    {
      "name": "Backend",
      "command": "cargo run",
      "port": 8080,
      "url": "http://localhost:8080"
    }
  ]
}
```

#### 预览变更

1. 确保开发服务器正在运行
2. 在审查界面中点击 **"Preview"**
3. 浏览器将打开预览页面

---

## ⚙️ 配置与定制

### 全局设置

进入 **Settings → Global**

#### 编辑器集成

- **Default Editor**: 选择默认编辑器
  - VS Code
  - Cursor
  - Windsurf
  - IntelliJ IDEA
  - Zed

- **Remote SSH Host**: 远程服务器地址
- **Remote SSH User**: SSH 用户名

#### 主题

- **Light**: 浅色主题
- **Dark**: 深色主题
- **Auto**: 跟随系统

#### 通知

- **Sound Effects**: 音效开关
- **Desktop Notifications**: 桌面通知
- **Task Completion**: 任务完成通知

### 项目设置

打开项目卡片 → 点击 **Settings**

#### 基本信息

- **Project Name**: 项目名称
- **Repository Path**: 仓库路径
- **Default Branch**: 默认分支（通常 `main` 或 `master`）

#### Git 配置

- **Branch Pattern**: 分支命名模式
  ```
  task/{task_id}-{short_description}
  feature/{feature_name}
  bugfix/{bug_id}
  ```

- **Auto Cleanup**: 自动清理过期的 worktree

#### 脚本配置

**Setup Script**（项目初始化）：

```bash
#!/bin/bash
npm install
npm run setup
cp .env.example .env
```

**Dev Script**（开发服务器）：

```bash
#!/bin/bash
npm run dev
```

**Test Script**（运行测试）：

```bash
#!/bin/bash
npm test
```

### 任务模板

创建常用任务模板以提高效率：

#### 模板 1：Bug 修复

```markdown
Title: {bug_title}
Description: |
  # Bug 描述
  {bug_description}

  # 复现步骤
  1. {step_1}
  2. {step_2}

  # 预期行为
  {expected_behavior}

  # 实际行为
  {actual_behavior}

Agent: Claude Code
Branch: bugfix/{bug_id}
```

#### 模板 2：新功能

```markdown
Title: {feature_name}
Description: |
  # 功能需求
  {feature_requirements}

  # 验收标准
  - {criterion_1}
  - {criterion_2}
  - {criterion_3}

  # 技术方案
  {technical_approach}

Agent: Claude Code
Branch: feature/{feature_name}
```

#### 模板 3：重构

```markdown
Title: Refactor {module_name}
Description: |
  # 重构目标
  {refactor_goals}

  # 当前问题
  {current_issues}

  # 改进方案
  {improvement_plan}

  # 测试计划
  {test_plan}

Agent: Claude Code
Branch: refactor/{module_name}
```

---

## 🔍 故障排除

### 常见问题

#### 1. 无法启动 Vibe Kanban

**症状：** 运行 `npx vibe-kanban` 后没有反应

**解决方案：**

```bash
# 检查 Node.js 版本
node --version  # 应该 >= 18

# 清除 npm 缓存
npm cache clean --force

# 重新安装
npx vibe-kanban
```

#### 2. 无法添加项目

**症状：** 点击 "Add Project" 后没有反应或报错

**可能原因：**
- 路径不正确
- 没有 Git 仓库
- 权限不足

**解决方案：**

```bash
# 检查路径是否正确
ls -la /path/to/repo

# 检查是否是 Git 仓库
cd /path/to/repo
git status

# 检查权限
chmod +x /path/to/repo
```

#### 3. AI 代理无法执行

**症状：** 点击 "Play" 后任务一直处于运行状态

**可能原因：**
- API Key 未配置
- 代理命令未找到
- 项目配置错误

**解决方案：**

```bash
# 检查 Claude Code 配置
claude --version

# 检查 API Key
echo $ANTHROPIC_API_KEY

# 测试代理命令
claude --help
```

#### 4. Git 操作失败

**症状：** Rebase/Merge 时报错

**解决方案：**

```bash
# 检查 Git 状态
git status

# 解决冲突
git mergetool

# 继续操作
git rebase --continue
```

#### 5. 开发服务器无法启动

**症状：** 点击 "Start Dev Server" 后没有反应

**解决方案：**

1. 检查项目配置中的脚本是否正确
2. 确保端口未被占用
3. 查看日志输出

```bash
# 检查端口占用
lsof -i :3000

# 手动启动测试
cd /path/to/project
npm run dev
```

#### 6. 远程 SSH 连接失败

**症状：** 点击 "Open in VSCode" 后无法打开

**解决方案：**

```bash
# 测试 SSH 连接
ssh user@server

# 检查 SSH 配置
cat ~/.ssh/config

# 检查 VSCode Remote SSH 扩展
code list-extensions | grep remote
```

### 日志查看

#### 查看应用日志

```bash
# 开发模式
pnpm run dev 2>&1 | tee vibe-kanban.log

# 生产模式
pnpm run start 2>&1 | tee vibe-kanban.log
```

#### 查看任务日志

1. 打开任务卡片
2. 点击 **"Logs"** 标签
3. 查看实时日志输出

### 调试模式

启用详细日志：

```bash
# 启用调试日志
export DEBUG=vibe-kanban:*
export RUST_LOG=debug

# 启动应用
npx vibe-kanban
```

禁用 worktree 清理（调试用）：

```bash
export DISABLE_WORKTREE_CLEANUP=1
npx vibe-kanban
```

---

## 💡 最佳实践

### 项目组织

#### 1. 单一仓库 vs 多仓库

**单一仓库（Monorepo）：**

```
company-project/
├── packages/
│   ├── frontend/
│   ├── backend/
│   └── shared/
├── services/
└── docs/
```

**优点：**
- 统一的依赖管理
- 简化的协作
- 原子性提交

**多仓库：**

```
frontend-repo/
backend-repo/
shared-lib-repo/
```

**优点：**
- 独立的部署
- 清晰的权限
- 灵活的工具链

#### 2. 项目结构建议

推荐的项目结构：

```
my-project/
├── docs/              # 文档
├── examples/          # 示例
├── packages/          # 子包
├── scripts/           # 工具脚本
├── .github/           # GitHub 配置
├── .gitignore
├── package.json
├── pnpm-workspace.yaml
└── README.md
```

### 任务管理

#### 1. 任务命名规范

**清晰的任务标题：**

```
✅ 好的命名：
- "Fix: User authentication fails on Safari"
- "Feature: Add dark mode support"
- "Refactor: Migrate to TypeScript"

❌ 不好的命名：
- "Fix bug"
- "Add feature"
- "Update code"
```

#### 2. 任务描述模板

**完整的任务描述：**

```markdown
# 目标
{what_are_you_trying_to_achieve}

# 背景
{why_is_this_needed}

# 实现方案
{how_will_you_do_it}

# 验收标准
- [ ] {criterion_1}
- [ ] {criterion_2}
- [ ] {criterion_3}

# 注意事项
{potential_gotchas}

# 相关资源
- {link_1}
- {link_2}
```

#### 3. 任务拆分策略

**大任务拆分：**

将大任务拆分为多个小任务：

```
大任务：重构用户认证系统

拆分为：
1. 任务 A：设计新的认证架构
2. 任务 B：实现后端 API
3. 任务 C：实现前端 UI
4. 任务 D：编写单元测试
5. 任务 E：更新文档
```

**任务依赖关系：**

```
任务 A → 任务 B → 任务 C
         ↓
        任务 D
```

### Git 工作流

#### 1. 分支策略

**Git Flow：**

```
main (生产环境)
  ↓
develop (开发环境)
  ↓
feature/* (功能分支)
hotfix/* (紧急修复)
release/* (发布准备)
```

**GitHub Flow：**

```
main (默认分支)
  ↓
feature/* (功能分支)
```

#### 2. Commit 规范

**Conventional Commits：**

```
feat: add user authentication
fix: resolve login bug
docs: update README
refactor: simplify auth logic
test: add unit tests for auth
chore: update dependencies
```

#### 3. 代码审查清单

**审查要点：**

- [ ] 代码逻辑是否正确
- [ ] 是否有充分的错误处理
- [ ] 是否有必要的注释
- [ ] 是否符合代码规范
- [ ] 测试是否充分
- [ ] 文档是否更新
- [ ] 性能是否可接受
- [ ] 安全性是否考虑

### AI 代理使用技巧

#### 1. 选择合适的代理

| 场景 | 推荐代理 |
|------|----------|
| 复杂重构 | Claude Code |
| 快速原型 | Amp |
| 简单任务 | Echo |
| 代码生成 | Gemini CLI |

#### 2. 编写有效的提示词

**好的提示词：**

```
❌ 不好的提示词：
"修复登录bug"

✅ 好的提示词：
"修复用户登录问题：
1. 当前问题：用户输入错误密码后看不到错误提示
2. 期望行为：显示'用户名或密码错误'提示
3. 技术要求：使用 bcrypt 验证密码
4. 测试：添加错误场景的单元测试"
```

#### 3. 迭代式开发

**迭代流程：**

```
第 1 轮：实现基本功能
  ↓
第 2 轮：添加错误处理
  ↓
第 3 轮：优化性能
  ↓
第 4 轮：添加测试和文档
```

### 性能优化

#### 1. 并行执行

**同时运行多个任务：**

```
任务 1 (后端 API) ──┐
                   ├──→ 并行执行
任务 2 (前端 UI) ───┘
```

**注意事项：**
- 确保任务之间没有依赖
- 监控系统资源使用
- 使用独立的 worktree

#### 2. 缓存策略

**利用 Git 缓存：**

- 使用 `.gitignore` 排除临时文件
- 避免频繁的相同操作
- 利用 worktree 隔离环境影响

#### 3. 资源管理

**监控系统资源：**

```bash
# 查看进程
ps aux | grep vibe-kanban

# 查看端口占用
lsof -i :3000

# 查看磁盘使用
df -h

# 查看 worktree 数量
git worktree list
```

### 团队协作

#### 1. 权限管理

**团队角色：**

| 角色 | 权限 |
|------|------|
| **Owner** | 完全控制 |
| **Maintainer** | 项目和任务管理 |
| **Developer** | 任务执行 |
| **Viewer** | 只读访问 |

#### 2. 代码审查流程

**审查流程：**

```
1. 开发者创建任务
2. AI 代理执行任务
3. 开发者审查代码
4. Maintainer 审查并合并
5. 删除 worktree
```

#### 3. 沟通协作

**使用任务注释：**

在任务卡片中添加注释：

```markdown
<!-- @team 请注意这个改动会影响认证模块 -->
<!-- @reviewer 优先审查这个 PR -->
```

---

## 📚 附录

### A. 快捷键参考

| 快捷键 | 功能 |
|--------|------|
| `Ctrl/Cmd + N` | 新建任务 |
| `Ctrl/Cmd + P` | 搜索项目/任务 |
| `Ctrl/Cmd + /` | 打开命令面板 |
| `Ctrl/Cmd + K` | 快速切换项目 |
| `Escape` | 关闭面板 |

### B. 命令行参考

```bash
# 启动 Vibe Kanban
npx vibe-kanban

# 指定端口
PORT=8080 npx vibe-kanban

# 指定主机
HOST=0.0.0.0 npx vibe-kanban

# 允许的源
VK_ALLOWED_ORIGINS=https://example.com npx vibe-kanban

# 调试模式
DEBUG=vibe-kanban:* npx vibe-kanban
```

### C. 配置文件位置

| 平台 | 配置文件位置 |
|------|--------------|
| **macOS** | `~/Library/Application Support/vibe-kanban/` |
| **Linux** | `~/.config/vibe-kanban/` |
| **Windows** | `%APPDATA%/vibe-kanban/` |

### D. 相关资源

- **官方网站**: https://vibekanban.com
- **GitHub**: https://github.com/BloopAI/vibe-kanban
- **文档**: https://vibekanban.com/docs
- **Discord**: https://discord.gg/AC4nwVtJM3
- **讨论区**: https://github.com/BloopAI/vibe-kanban/discussions

### E. 贡献指南

如果你想为 Vibe Kanban 做贡献：

1. 加入 [Discord](https://discord.gg/AC4nwVtJM3) 社区
2. 在 [GitHub Discussions](https://github.com/BloopAI/vibe-kanban/discussions) 中讨论你的想法
3. 遵循代码规范
4. 编写测试
5. 提交 Pull Request

---

## 📖 版本历史

- **v0.1.18** (最新)
  - 支持多种 AI 代理
  - 优化性能和稳定性
  - 改进用户界面

- **v0.1.0**
  - 初始发布
  - 基础看板功能

---

## 📞 获取帮助

如果你遇到问题或有建议：

- 📖 查看[官方文档](https://vibekanban.com/docs)
- 💬 加入[Discord 社区](https://discord.gg/AC4nwVtJM3)
- 🐛 [提交 Issue](https://github.com/BloopAI/vibe-kanban/issues)
- 💡 [参与讨论](https://github.com/BloopAI/vibe-kanban/discussions)

---

**享受高效的 AI 编程体验！** 🚀
