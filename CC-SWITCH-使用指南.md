# CC Switch 完整使用指南

## 目录
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [详细配置](#详细配置)
- [高级功能](#高级功能)
- [常见问题](#常见问题)

---

## 快速开始

### 第一步：添加供应商

1. **打开 CC Switch**（安装完成后从开始菜单启动）

2. **点击"添加供应商"按钮**

3. **选择供应商类型**：

   **预设供应商（推荐新手）**：
   - **PackyCode** - API 中转服务，稳定可靠
   - **智谱 GLM** - 国产大模型，价格优惠
   - **AIGoCode** - 一站式 AI 编程平台
   - **DMXAPI** - 多模型聚合服务

   **官方登录**：
   - **Claude 官方登录** - 使用 Anthropic 官方 API
   - **Codex 官方登录** - 使用 OpenAI 官方 API

   **自定义**：
   - 使用自己的 API 端点（如自建代理、其他中转服务）

4. **填写配置信息**：

   如果选择自定义或预设供应商，通常需要填写：
   - **API Key**：必填，从供应商处获取
   - **Base URL**：API 端点地址（某些预设会自动填充）
   - **模型名称**：可选，默认使用推荐的模型

5. **点击"保存"**

### 第二步：启用供应商

1. 在供应商列表中找到刚添加的供应商
2. 点击右侧的"启用"按钮
3. 供应商卡片会显示为激活状态（通常有绿色标识）

### 第三步：应用配置

**重要**：配置生效需要重启 AI 编程工具：

- **Claude Code**：重启终端或重新运行 `claude` 命令
- **Codex**：重启终端或重新运行 `codex` 命令
- **Gemini CLI**：托盘切换会自动重写 `.env` 文件，无需重启

---

## 核心功能

### 1. 供应商管理

#### 切换供应商
- **主界面切换**：点击供应商卡片 → 点击"启用"
- **托盘快速切换**：右键点击系统托盘图标 → 选择供应商

#### 编辑供应商
1. 点击供应商卡片上的编辑图标
2. 修改配置信息
3. 点击"保存"
4. 重新启用供应商

#### 删除供应商
1. 点击供应商卡片上的删除图标
2. 确认删除

#### 复制供应商
1. 点击供应商卡片上的复制图标
2. 基于现有配置快速创建新供应商
3. 修改需要更改的字段（如 API Key）

#### 拖拽排序
- 直接拖拽供应商卡片调整顺序
- 排序后托盘菜单中的顺序也会相应调整

### 2. 速度测试

测试 API 端点的响应速度和质量：

1. 在供应商卡片上找到速度测试按钮（通常是闪电图标⚡）
2. 点击开始测试
3. 等待测试完成（几秒钟）
4. 查看结果：
   - **延迟**：响应时间（毫秒）
   - **状态**：✅ 可用 / ❌ 不可用
   - **建议**：根据测试结果给出优化建议

**最佳实践**：
- 定期测试不同供应商，选择响应最快的
- 如果某个供应商频繁超时，考虑更换
- 测试结果可作为选择供应商的参考依据

### 3. 导入导出配置

#### 导出配置（备份）
1. 点击右上角的设置图标⚙️
2. 找到"导入/导出"部分
3. 点击"导出配置"
4. 选择保存位置
5. 配置文件会自动保存（JSON 格式）

#### 导入配置（恢复）
1. 点击"导入配置"
2. 选择之前导出的配置文件
3. 确认导入

**自动备份**：
- CC Switch 会在 `~/.cc-switch/backups/` 目录自动保留最近 10 个备份
- 每次更改配置时自动创建备份

---

## 详细配置

### Claude Code 配置

#### 配置文件位置
```
~/.claude/settings.json     # 主配置文件
~/.claude.json              # MCP 服务器配置
~/.claude/CLAUDE.md         # 系统提示词
~/.claude/skills/           # Skills 目录
```

#### API Key 字段
CC Switch 会自动配置以下字段之一：
- `env.ANTHROPIC_AUTH_TOKEN`
- `env.ANTHROPIC_API_KEY`

#### 模型配置（细粒度）
可以配置不同层级的模型：
- **Haiku**：快速、经济（用于简单任务）
- **Sonnet**：平衡性能和速度（推荐日常使用）
- **Opus**：最强性能（用于复杂任务）
- **自定义模型**：指定特定模型名称

### Codex 配置

#### 配置文件位置
```
~/.codex/auth.json         # API 认证（必需）
~/.codex/config.toml       # 配置文件（可选）
~/.codex/AGENTS.md         # 系统提示词
```

#### API Key 字段
CC Switch 会配置 `auth.json` 中的：
- `OPENAI_API_KEY`

#### 特殊配置
- **自定义配置目录**：支持云同步
- **WSL 支持**：自动同步 WSL 环境配置

### Gemini CLI 配置

#### 配置文件位置
```
~/.gemini/.env              # 环境变量（API Key）
~/.gemini/settings.json     # 配置文件
~/.gemini/GEMINI.md         # 系统提示词
```

#### API Key 字段
CC Switch 会配置 `.env` 中的：
- `GEMINI_API_KEY`
- `GOOGLE_GEMINI_API_KEY`

#### 环境变量
支持配置：
- `GOOGLE_GEMINI_BASE_URL` - 自定义端点
- `GEMINI_MODEL` - 默认模型
- 其他自定义环境变量

#### 托盘实时切换
Gemini CLI 的配置更改会自动重写 `.env` 文件，**无需重启** CLI

---

## 高级功能

### 1. MCP 服务器管理

**什么是 MCP？**
MCP (Model Context Protocol) 是 Claude Code 和其他 AI CLI 的扩展协议，允许连接外部工具和服务。

#### 访问 MCP 面板
点击主界面右上角的 **"MCP"** 按钮

#### 添加 MCP 服务器

1. **点击"添加服务器"**

2. **选择传输类型**：
   - **stdio**：标准输入输出（本地进程）
   - **http**：HTTP 端点（网络服务）
   - **sse**：Server-Sent Events（实时流）

3. **使用内置模板**（推荐）：
   - **mcp-fetch**：网页抓取工具
   - **mcp-filesystem**：文件系统操作
   - **mcp-git**：Git 仓库操作
   - **mcp-postgres**：PostgreSQL 数据库
   - 更多模板...

4. **或手动配置**：
   - **服务器名称**：自定义标识
   - **命令**：启动命令（stdio 模式）
   - **URL**：服务地址（http/sse 模式）
   - **参数**：命令行参数或环境变量

5. **选择要应用到的应用**：
   - ☑️ Claude Code
   - ☑️ Codex
   - ☑️ Gemini CLI

6. **点击"保存"**

#### 启用/禁用 MCP 服务器
- 切换服务器右侧的开关
- 启用的服务器会自动同步到各应用的 live 配置

#### 导入现有 MCP 配置
1. 点击"导入"按钮
2. 选择要导入的应用（Claude/Codex/Gemini）
3. CC Switch 会自动读取并添加现有 MCP 服务器

#### MCP 配置文件位置
- **Claude Code**：`~/.claude.json` → `mcpServers`
- **Codex**：`~/.codex/config.toml` → `[mcp_servers]`
- **Gemini CLI**：`~/.gemini/settings.json` → `mcpServers`

### 2. Skills 管理（Claude Code）

**什么是 Skills？**
Skills 是 Claude Code 的可重用代码片段和命令，可以从 GitHub 仓库安装。

#### 访问 Skills 面板
点击主界面右上角的 **"Skills"** 按钮

#### 内置仓库
CC Switch 预配置了以下精选仓库：
- **Anthropic 官方**：官方维护的技能集合
- **ComposioHQ**：社区热门技能
- **其他社区仓库**

#### 安装 Skill

1. **浏览可用技能**
   - 在列表中查看所有仓库的技能
   - 每个技能显示名称、描述、来源仓库

2. **点击"安装"按钮**
   - Skill 会被下载到 `~/.claude/skills/`
   - 自动安装所有依赖

3. **验证安装**
   - 安装成功后，按钮变为"已安装"
   - 可以在 Claude Code 中直接使用

#### 添加自定义仓库

1. 点击"添加仓库"
2. 输入 GitHub 仓库地址（如：`https://github.com/user/repo`）
3. 可选：指定子目录（如果仓库包含多个项目）
4. 点击"扫描"
5. CC Switch 会自动发现并显示仓库中的所有技能

#### 卸载 Skill
1. 找到已安装的技能
2. 点击"卸载"
3. 确认卸载

#### 更新 Skills
- Skills 不会自动更新
- 需要手动卸载后重新安装以获取最新版本

### 3. Prompts 管理

**什么是 Prompts？**
系统提示词（System Prompts）是预设的指令，定义 AI 助手的行为和角色。

#### 访问 Prompts 面板
点击主界面右上角的 **"Prompts"** 按钮

#### 创建提示词预设

1. **点击"添加预设"**

2. **填写信息**：
   - **名称**：预设标识（如"代码审查员"、"技术作家"）
   - **描述**：预设用途说明
   - **提示词内容**：使用 Markdown 编辑器编写

3. **使用 Markdown 编辑器**：
   - 左侧：编写模式（支持语法高亮）
   - 右侧：实时预览
   - 工具栏：加粗、斜体、列表、代码块等

4. **点击"保存"**

#### 激活提示词预设

1. 在预设列表中选择要激活的提示词
2. 点击"激活"按钮
3. CC Switch 会自动将提示词写入对应应用的配置文件：
   - **Claude Code**：`~/.claude/CLAUDE.md`
   - **Codex**：`~/.codex/AGENTS.md`
   - **Gemini CLI**：`~/.gemini/GEMINI.md`

#### 提示词保护机制
- 切换预设前，CC Switch 会自动保存当前提示词内容
- 如果您手动修改了提示词文件，切换时会保留修改
- 可以随时恢复到之前的版本

### 4. 环境变量冲突检测

CC Switch 会自动检测配置冲突：

#### 检测范围
- Claude Code、Codex、Gemini CLI 之间的环境变量
- MCP 服务器配置冲突
- 自定义环境变量冲突

#### 冲突指示器
- **黄色警告**⚠️：存在潜在冲突
- **红色错误**❌：严重冲突，可能导致配置无效

#### 解决冲突
1. 点击冲突指示器查看详情
2. 查看冲突的环境变量和来源
3. 根据建议进行修改：
   - 禁用冲突的配置
   - 修改变量名称
   - 删除不需要的配置

### 5. 云同步配置

支持将配置目录设置到云同步文件夹，实现多设备同步。

#### 设置云同步

1. 打开设置⚙️
2. 找到"自定义配置目录"
3. 点击"浏览"选择云同步文件夹：
   - **Windows**：OneDrive、Dropbox
   - **macOS**：iCloud Drive
   - **Linux**：坚果云 WebDAV
4. 重启 CC Switch

#### 多设备同步
1. 在设备 A 上设置云同步目录
2. 在设备 B 上设置相同的云同步目录
3. 配置会自动在设备间同步

**注意**：
- 不要同时在不同设备上修改配置，可能导致冲突
- 建议使用设备的配置目录，而非共享目录

### 6. 深度链接导入

通过分享链接快速导入供应商配置。

#### 使用深度链接

1. 接收分享链接（格式：`ccswitch://import?data=...`）
2. 在浏览器中点击链接
3. CC Switch 会自动打开并显示导入对话框
4. 查看配置详情
5. 点击"导入"添加配置

#### 创建分享链接
1. 编辑供应商配置
2. 点击"分享"或"导出链接"
3. 复制生成的链接
4. 分享给他人

**安全提示**：
- 深度链接包含 API Key 等敏感信息
- 仅分享给可信的人员
- 建议分享前移除 API Key，让接收者自行填写

---

## 高级技巧

### 1. 托盘快速操作

右键点击系统托盘的 CC Switch 图标可以：
- 快速切换供应商（无需打开主界面）
- 查看当前激活的供应商
- 打开主界面
- 退出应用

**Gemini CLI 特别优势**：
- 托盘切换会立即重写 `.env` 文件
- **无需重启** Gemini CLI 即可生效

### 2. 键盘快捷键

- **Ctrl/Cmd + N**：添加新供应商
- **Ctrl/Cmd + ,**：打开设置
- **Ctrl/Cmd + Q**：退出应用（如果支持）
- **Escape**：关闭对话框

### 3. 多应用配置管理

可以同时为三个应用配置不同的供应商：

**场景示例**：
- **Claude Code** 使用 PackyCode（稳定）
- **Codex** 使用智谱 GLM（经济）
- **Gemini CLI** 使用 AIGoCode（快速）

每个应用的配置相互独立，互不影响。

### 4. 配置备份策略

#### 自动备份
- 位置：`~/.cc-switch/backups/`
- 保留：最近 10 个备份
- 触发：每次配置更改时自动创建

#### 手动备份
1. 导出配置到安全位置
2. 定期备份到外部存储或云服务

#### 恢复备份
1. 点击"导入配置"
2. 选择备份文件
3. 确认恢复

### 5. 性能优化

#### 供应商选择建议
- **日常开发**：使用响应时间 < 500ms 的供应商
- **复杂任务**：使用 Opus 级别模型
- **简单任务**：使用 Haiku 级别模型（节省成本）

#### 速度测试最佳实践
- 定期测试（每周一次）
- 测试多个供应商进行比较
- 根据测试结果调整供应商优先级

#### MCP 服务器优化
- 禁用不常用的 MCP 服务器（提升启动速度）
- 本地服务器优先使用 stdio 模式
- 远程服务器使用 http/sse 模式

---

## 常见问题

### Q1: 更换供应商后配置不生效？
**A**: 需要重启 AI 编程工具：
- **Windows**: 关闭终端，重新打开
- **macOS/Linux**: 执行 `exec $SHELL` 或重启终端
- **Gemini CLI 特例**: 托盘切换自动生效，无需重启

### Q2: 提示"无法连接到 API"？
**A**: 检查以下项目：
1. API Key 是否正确
2. Base URL 是否可访问（使用速度测试功能）
3. 网络连接是否正常
4. 是否需要配置代理

### Q3: MCP 服务器不工作？
**A**: 排查步骤：
1. 检查 MCP 服务器的启动命令是否正确
2. 查看 CLI 的错误日志
3. 确认服务器已在"启用"状态
4. 尝试手动运行命令测试

### Q4: 如何重置到官方登录？
**A**:
1. 添加"官方登录"预设供应商
2. 启用该预设
3. 重启 AI 编程工具
4. 按照官方流程登录（通常是 OAuth）

### Q5: 配置文件损坏怎么办？
**A**:
1. 使用自动备份恢复：`~/.cc-switch/backups/`
2. 或导出之前的手动备份
3. 如果都没有，重新添加供应商即可

### Q6: 开机自启如何设置？
**A**:
1. 打开设置⚙️
2. 找到"开机自启"
3. 切换开关
4. 重启计算机后生效

**平台差异**：
- **Windows**: 注册表启动项
- **macOS**: LaunchAgent
- **Linux**: XDG autostart

### Q7: 如何卸载 CC Switch？
**A**:
- **Windows**: 控制面板 → 程序和功能 → CC Switch → 卸载
- **macOS**: 删除应用程序中的 CC Switch
- **Linux**: 使用包管理器卸载（如 `apt remove cc-switch`）

**卸载后配置文件保留**：
- `~/.cc-switch/` 配置目录不会被删除
- 如需完全清理，手动删除该目录

### Q8: 支持哪些代理配置？
**A**:
CC Switch 支持在供应商配置中设置代理：
- **HTTP Proxy**: `http://proxy.example.com:8080`
- **SOCKS5 Proxy**: `socks5://proxy.example.com:1080`
- **带认证**: `http://user:pass@proxy.example.com:8080`

### Q9: 如何获取 API Key？
**A**:
- **官方 API**: 访问 Anthropic/OpenAI 官网注册
- **中转服务**:
  - PackyCode: https://www.packyapi.com/register?aff=cc-switch
  - 智谱 GLM: https://www.bigmodel.cn/claude-code?ic=RRVJPB5SII
  - AIGoCode: https://aigocode.com/invite/CC-SWITCH
  - DMXAPI: https://www.dmxapi.cn/register?aff=bUHu

### Q10: 数据库升级问题？
**A**（v3.8.0+）:
从 v3.7.x 升级到 v3.8.0+ 时，配置会自动迁移到 SQLite 数据库：
- 迁移过程自动进行
- 原有 JSON 配置会保留作为备份
- 如果迁移失败，可以手动恢复备份

---

## 参考资源

### 官方文档
- [GitHub 仓库](https://github.com/farion1231/cc-switch)
- [更新日志](https://github.com/farion1231/cc-switch/blob/main/CHANGELOG.md)
- [v3.9.0 发布说明](https://github.com/farion1231/cc-switch/blob/main/docs/release-note-v3.9.0-zh.md)

### 教程和指南
- [PackyCode 使用教程](https://docs.packyapi.com/docs/ccswitch/)
- [知乎快速上手指南](https://zhuanlan.zhihu.com/p/1972328772964446521)

### 合作服务商
- [智谱 GLM Coding Plan](https://www.bigmodel.cn/claude-code?ic=RRVJPB5SII) - 特别优惠 9 折
- [PackyCode](https://www.packyapi.com/register?aff=cc-switch) - 优惠码: cc-switch
- [AIGoCode](https://aigocode.com/invite/CC-SWITCH) - 首充奖励 10%
- [DMXAPI](https://www.dmxapi.cn/register?aff=bUHu) - Claude 专属 3.4 折
- [Cubence](https://cubence.com/signup?code=CCSWITCH&source=ccs) - 优惠码: CCSWITCH

---

## 版本信息

- **当前版本**: v3.10.1
- **发布日期**: 2025-01-20
- **系统要求**:
  - Windows 10+
  - macOS 10.15 (Catalina)+
  - Linux (Ubuntu 22.04+, Debian 11+, Fedora 34+)

---

## 技术支持

如遇到问题：
1. 查看本文档的"常见问题"部分
2. 在 [GitHub Issues](https://github.com/farion1231/cc-switch/issues) 搜索相似问题
3. 提交新的 Issue，包含：
   - CC Switch 版本号
   - 操作系统版本
   - 详细的问题描述和复现步骤
   - 错误日志（如果有）

---

**享受 AI 编程带来的高效体验！** 🚀
