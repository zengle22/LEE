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
│   ├── media-reviewer/v1/                 # 媒体审核 Agent
│   ├── diagram-analysis-agent/v1/         # 图表分析 Agent（新增）
│   └── diagram-planner-agent/v1/          # 图表规划 Agent（新增）
├── commands/                  # Splash Commands（快速命令）
│   └── article-layout/v1/                 # 文章排版命令 /layout
├── contracts/                 # 媒体阶段特有的契约定义
│   ├── article-structure-contract/v1/     # 文章结构契约
│   ├── layout-theme-contract/v1/          # 排版主题契约
│   ├── formatted-content-contract/v1/     # 格式化内容契约
│   ├── media-publish-contract/v1/         # 发布契约
│   ├── diagram-opportunity-contract/v1/   # 图表机会识别契约（新增）
│   ├── diagram-plan-contract/v1/          # 图表规划契约（新增）
│   └── diagram-asset-contract/v1/         # 图表资产契约（新增）
├── skills/                    # 媒体技能规范
│   ├── readable-color-layout/v1/          # 可读性排版技能
│   ├── structure-extraction/v1/           # 结构抽取技能
│   ├── platform-safe-rendering/v1/        # 平台安全渲染技能
│   ├── md-to-wechat-richtext/v1/          # Markdown 转 公众号富文本
│   ├── content-proofreading/v1/           # 内容校对技能
│   ├── diagram-generation/v1/             # 图表生成技能（新增）
│   └── diagram-insertion/v1/              # 图表插入技能（新增）
├── themes/                    # 排版主题定义
│   ├── wechat-red-theme/v1/               # 公众号安全红色主题
│   ├── blue-theme/v1/                     # 蓝色主题
│   └── minimal-theme/v1/                  # 极简主题
├── workflows/                  # 媒体流水线定义
│   ├── content-layout-pipeline/v1/        # 内容排版流水线
│   └── diagram-insertion-pipeline/v1/     # 图表插入流水线（新增）
├── tools/                      # MCP 工具
│   └── diagram-render-mcp/v1/             # Mermaid 渲染 MCP（新增）
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

## 📊 文章结构图插入流水线 (Diagram Insertion Pipeline)

**这是 Media 部门新增的生产线，用于为成稿在需要的地方配上结构图。**

### 设计理念

> **AI 决定"该不该有图 + 图的结构"，程序决定"图长什么样 + 怎么落地"。**

采用「媒体资产池」模式：
- 图片作为独立的媒体资产生成
- 文章中插入占位提示而非实际图片
- 人类在公众号后台手动上传并插入
- 完全遵守 LEE 三方协作哲学：人类/程序/AI 各司其职

### 为什么不用 Base64 或本地路径？

| 方案 | 问题 | 我们的选择 |
|------|------|-----------|
| Base64 | 体积大、公众号不稳定、无法人工修正 | ❌ 不使用 |
| 本地路径 `![图](path)` | 公众号不认、发布前必须手动处理 | ❌ 不作为最终格式 |
| Mermaid 源码 | 把渲染压力推回给人 | ❌ 仅作为溯源 |
| **媒体资产池** | 人类保留发布控制权 | ✅ **采用** |

### 流水线阶段

#### 阶段 1：结构分析 (Structure Analysis)
* **Agent**: `agent.media.diagram_analyzer`
* **职责**: 判断"哪里需要结构图"
* **输入**: 成稿文章 (MD)
* **输出**: 图表机会列表 (Diagram Opportunities)
* **关键**: 认知判断层，不输出视觉决策

#### 阶段 2：图表规划 (Diagram Planning)
* **Agent**: `agent.media.diagram_planner`
* **职责**: 规划"用什么类型的图"
* **输入**: 图表机会 + 文章内容
* **输出**: Structure DSL（节点、关系，无视觉描述）
* **关键**: 编辑能力层，只输出结构

#### 阶段 3：图表生成 (Diagram Generation)
* **Skill**: `skill.media.diagram_generation`
* **职责**: DSL → Mermaid 文本
* **关键**: 纯确定性转换，不调用 LLM

#### 阶段 4：图表渲染 (Diagram Rendering)
* **MCP**: `mcp.media.diagram_renderer`
* **职责**: Mermaid → PNG
* **关键**: 「去 AI 化」步骤，程序渲染，AI 不碰像素

#### 阶段 5：占位插入 (Placeholder Insertion)
* **Skill**: `skill.media.diagram_insertion`
* **职责**: 在文章中插入占位提示
* **输出示例**:
  ```markdown
  <!-- DIAGRAM:diagram_001 -->
  【结构图：治理闭环】
  
  > 📎 发布前操作：
  > 1. 打开文件：`images/diagram_001.png`
  > 2. 上传到公众号素材库
  > 3. 删除本占位提示，插入图片
  ```

#### 阶段 6：人工审核 (Human Gate)
* **检查点**:
  1. 这些图真的有必要吗？
  2. 结构有没有误导？
  3. 会不会抢了文字的风头？
* **注意**: 不需要改 Mermaid 语法，最多删除不需要的图

### 使用场景

```yaml
workflow: workflow.media.diagram_insertion_pipeline
input:
  article_md: "articles/my-article.md"
```

**适用情况**:
- 文章包含抽象概念密集段
- 需要展示流程、架构、层级关系
- 文字成本高，图能显著提升理解

**不适用情况**:
- 案例叙述/情绪段落
- 内容已经充分展开，无需辅助
- 过于简单的关系

### 输出文件结构

```
output/
├── article_with_diagrams.md      # 带占位提示的文章
├── diagram_report.json           # 处理报告
└── images/
    ├── diagram_001.png           # 高清 PNG（2x 缩放）
    ├── diagram_001.mmd           # Mermaid 源码（溯源）
    ├── diagram_002.png
    └── diagram_002.mmd
```

### 完整发布流程

1. **运行 Diagram Insertion Pipeline** → 生成带占位提示的文章和图片
2. **（可选）运行 Content Layout Pipeline** → 排版美化
3. **人工审核** → 确认图表必要性
4. **公众号发布** → 上传图片，替换占位提示，发布

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
