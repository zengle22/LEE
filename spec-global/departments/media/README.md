# Media Department Specification System (v1.0)
# 媒体部门规范体系

本目录包含了媒体部门在内容生产、排版优化、发布管理等阶段的核心规范、Agent 定义及工作流。遵循 **结构优先、样式可配置、结果稳定** 的原则，通过标准化的契约（Contract）实现 Agent 间的高效协作与批量生产。

## 🌟 核心理念

1. **结构优先**：所有内容必须先结构化，再应用样式
2. **样式可配置**：排版规则通过主题文件定义，而非 LLM 自由发挥
3. **结果稳定**：同一内容重复执行，输出结构完全一致
4. **平台安全**：输出的 HTML/CSS 必须符合目标平台的安全规范
5. **就近输出**：所有输出文件放置在输入文件所在目录的 `output` 子目录
6. **公众号友好**：不使用 `<div>` 等公众号编辑器不支持的标签，确保复制粘贴不崩

## 🏗️ 目录结构

```text
departments/media/
├── agents/                    # 媒体相关 Agent 定义
│   ├── article-structure-extractor/v1/    # 文章结构抽取 Agent
│   ├── readable-color-layout/v1/          # 可读性排版 Agent
│   ├── media-publisher/v1/                # 媒体发布 Agent
│   └── media-reviewer/v1/                 # 媒体审核 Agent
├── commands/                  # Splash Commands（快速命令）
│   └── article-layout/v1/                 # 文章排版命令 /layout
├── contracts/                 # 媒体阶段特有的契约定义
│   ├── article-structure-contract/v1/     # 文章结构契约
│   ├── layout-theme-contract/v1/          # 排版主题契约
│   ├── formatted-content-contract/v1/     # 格式化内容契约
│   └── media-publish-contract/v1/         # 发布契约
├── skills/                    # 媒体技能规范
│   ├── readable-color-layout/v1/          # 可读性排版技能
│   ├── structure-extraction/v1/           # 结构抽取技能
│   ├── platform-safe-rendering/v1/        # 平台安全渲染技能
│   ├── md-to-wechat-richtext/v1/          # Markdown 转 公众号富文本
│   └── content-proofreading/v1/            # 内容校对技能
├── themes/                    # 排版主题定义
│   ├── wechat-red-theme/v1/               # 公众号安全红色主题
│   ├── blue-theme/v1/                     # 蓝色主题
│   └── minimal-theme/v1/                  # 极简主题
├── workflows/                  # 媒体流水线定义
│   └── content-layout-pipeline/v1/        # 内容排版流水线
└── README.md                  # 本说明文件
```

## 🔄 内容排版流水线 (Content Layout Pipeline)

该流水线串联了从原始文章到平台就绪内容的完整过程。

### 阶段 1：结构抽取 (Structure Extraction)
* **Agent**: `agent.media.structure_extractor`
* **Skill**: `skill.media.structure_extraction`
* **输入**: 原始文章 (Markdown / 纯文本)
* **输出**: 文章结构 (Article Structure) - 中间表示
* **关键**: 不做任何样式判断，只识别层级和重要性

### 阶段 2：可读性排版 (Readable Layout)
* **Agent**: `agent.media.readable_color_layout`
* **Skill**: `skill.media.readable_color_layout`
* **输入**: 文章结构 + 主题配置
* **输出**: 格式化内容 (Formatted Content)
* **关键**: 根据主题规则应用稳定的样式

### 阶段 3：平台安全渲染 (Platform Safe Render)
* **Skill**: `skill.media.md_to_wechat_richtext`
* **输入**: 格式化 Markdown
* **输出**: 公众号安全 HTML
* **关键**: 不使用 `<div>` 等不支持的标签，全部使用内联样式

### 阶段 4：内容校对 (Content Proofreading)
* **Skill**: `skill.media.content_proofreading`
* **输入**: 格式化内容
* **输出**: 校对后内容 + 校对报告
* **关键**: 自动发现并修复暗色字体、对比度不足等问题

### 阶段 5：媒体审核 (Media Review)
* **Agent**: `agent.media.media_reviewer`
* **输入**: 校对后的内容
* **输出**: 审核报告

### 阶段 6：最终冻结 (Final Freeze)
* **Agent**: `agent.governance.approval_reviewer`
* **输入**: 审核报告
* **输出**: 冻结确认
* **🔒 冻结点**: **最终冻结** - 人类确认后可发布

### 阶段 7：平台发布 (Platform Publish)
* **Agent**: `agent.media.media_publisher`
* **输入**: 冻结的内容
* **输出**: 发布状态

## 🎨 排版主题系统

所有排版样式通过主题文件定义，确保：

- **颜色可配置**: 所有颜色值从主题文件读取
- **结构稳定**: 同一主题下，排版结构完全一致
- **多平台支持**: 针对不同平台的 HTML 安全级别
- **公众号友好**: 红色主题已优化为公众号安全版

### 公众号安全标签

| 允许的标签 | 用途 |
|-----------|------|
| `p` | 段落 |
| `span` | 内联容器（强调色关键） |
| `h1, h2, h3` | 标题 |
| `strong, b` | 加粗 |
| `em, i` | 斜体 |
| `blockquote` | 引用块 |
| `pre, code` | 代码块 |
| `ul, ol, li` | 列表 |
| `br` | 换行 |

| 禁止的标签 | 原因 |
|-----------|------|
| `div` | ❌ 公众号编辑器不支持 |
| `section` | ❌ 公众号编辑器不支持 |
| `article` | ❌ 公众号编辑器不支持 |
| `script, style, link` | ❌ 安全风险 |

### 主题文件结构

```yaml
themes/{theme_name}/v1/theme.yaml:
  name: "红色强调主题（公众号安全版）"
  description: "专为公众号优化，不使用 div 等不支持的标签"

  html_tags:
    allowed: [p, span, h1, h2, h3, strong, blockquote, pre, code, ul, ol, li]
    forbidden: [div, section, script, style, link]

  colors:
    primary: "#ff4d4f"
    emphasis_high: "#fa541c"
    text: "#262626"

  templates:
    highlight_section: |
      # 使用 p + span 组合，不使用 div
      <p style="color:#cf1322;font-weight:bold">标题</p>
      <p style="color:#fa541c">● <span style="color:#262626">内容</span></p>
```

## 🛠️ 维护与扩展

- **新增 Agent**: 遵循现有 YAML 规范，放置于 `agents/` 目录下
- **新增主题**: 在 `themes/` 目录下创建新的主题文件
- **修改契约**: 修改 `contracts/` 下的 schema，并同步更新相关 Agent
- **更新流程**: 修改 `workflows/content-layout-pipeline/v1/workflow.yaml`

## 📂 输出目录规则

**工作规则**：所有输出文件应放置在输入文件所在目录的 `output` 子目录中。

### 示例

```
输入文件: /path/to/article.md
输出目录: /path/to/output/

输出文件:
  - /path/to/output/{article_id}_structure.json    # 结构抽取结果
  - /path/to/output/{article_id}_formatted.md      # 格式化内容
  - /path/to/output/{article_id}_review.json       # 审核报告
```

### 优点

- **项目关联**：输出文件与输入文件在同一个项目中，便于管理
- **版本控制**：输出文件可以与源文件一起纳入版本控制
- **易于查找**：输出文件就在输入文件旁边，无需切换目录
- **独立整洁**：使用 `output` 子目录避免与源文件混合

## 📦 核心技能

### ReadableColorLayoutSkill

**输入**: 一篇「已经成稿」的文章（Markdown / 纯文本）

**输出**:
- 清晰层级
- 重点有颜色
- 模块化块状结构
- 直接可粘贴到公众号 / 小红书 / Notion / 飞书

**特点**:
- 排版规则稳定、可配置
- 可放进流水线批量处理
- 同一篇文章重复跑 5 次，排版结构一致

---

## 🚀 Splash Commands（快速命令）

媒体部门提供了 **Splash Command**，让你在 Claude Code 中一键完成文章排版。

### /lee-layout - 文章排版命令

**基本用法**:
```
/lee-layout <文件路径>
```

**完整参数**:
```
/lee-layout <文件路径> [--theme <主题>] [--platform <平台>] [--format <格式>]
```

**参数说明**:
| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `--theme` | 排版主题 | `wechat_red_safe`, `blue`, `minimal` | `wechat_red_safe` |
| `--platform` | 目标平台 | `wechat`, `xhs`, `notion`, `feishu`, `generic` | `wechat` |
| `--format` | 输出格式 | `md`, `html`, `both` | `both` |
| `--proofread` | 自动校对 | `true`, `false` | `true` |

**使用示例**:

```bash
# 基本用法 - 使用默认的公众号红色主题
/lee-layout articles/my-post.md

# 指定平台
/lee-layout articles/my-post.md --platform xhs

# 指定主题
/lee-layout articles/my-post.md --theme blue

# 仅输出 HTML
/lee-layout articles/my-post.md --format html

# 完整配置
/lee-layout articles/my-post.md --theme minimal --platform notion --format both
```

**输出位置**:
```
articles/my-post.md
→ articles/output/my-post_final.md    # Markdown 格式
→ articles/output/my-post_final.html  # HTML 格式
→ articles/output/my-post_report.json # 处理报告
```

**快捷别名**:
- `/lee-fmt` - 简写形式
- `/format` - 通用别名
- `/fmt` - 最短别名

**错误处理**:
- 文件不存在：提示检查路径
- 不支持的格式：提示支持 `.md` 和 `.txt`
- 主题/平台不存在：提示可用选项

---
*Generated by LEE Spec Maintainer*
*Version: 1.1.0*
