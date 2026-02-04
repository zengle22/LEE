---
description: Format articles with WeChat-safe styling and color emphasis
---

# LEE Layout Command

文章排版命令 - 将原始文章转换为格式化的平台就绪内容。

## 功能

- 自动抽取文章结构
- 应用主题样式（红色/蓝色/极简）
- 生成微信公众号安全格式（无 div 标签）
- 自动校对并修复暗色文字
- 输出 Markdown 和 HTML 格式

## 用法

```bash
# 基本用法 - 使用默认的公众号红色主题
/lee-layout <文件路径>

# 指定主题
/lee-layout <文件路径> --theme <blue|minimal|wechat_red_safe>

# 指定平台
/lee-layout <文件路径> --platform <wechat|xhs|notion|feishu|generic>

# 指定输出格式
/lee-layout <文件路径> --format <md|html|both>

# 完整配置
/lee-layout <文件路径> --theme blue --platform xhs --format html
```

## 参数说明

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `--theme` | 排版主题 | `wechat_red_safe`, `blue`, `minimal` | `wechat_red_safe` |
| `--platform` | 目标平台 | `wechat`, `xhs`, `notion`, `feishu`, `generic` | `wechat` |
| `--format` | 输出格式 | `md`, `html`, `both` | `both` |
| `--no-proofread` | 跳过校对 | - | `false` |

## 主题说明

### wechat_red_safe（默认）
- 红色强调，重点突出
- 微信公众号安全格式
- 只使用 6 种颜色：#ff4d4f, #cf1322, #fff1f0, #4a4a4a, #555555, #666666
- 引用块使用深色 #4a4a4a 确保对比度

### blue
- 蓝色主题，专业稳重
- 适合技术文章

### minimal
- 极简主题，清爽干净
- 最少颜色使用

## 输出位置

```
articles/my-post.md
→ articles/output/my-post_final.md    # Markdown 格式
→ articles/output/my-post_final.html  # HTML 格式
→ articles/output/my-post_report.json # 处理报告
```

## 执行步骤

1. **验证输入** - 检查文件是否存在且格式正确
2. **加载主题** - 读取主题配置（colors, templates）
3. **应用排版** - 转换标题、引用块、列表等样式
4. **自动校对** - 检测并修复暗色文字（默认启用）
5. **生成输出** - 保存 MD 和 HTML 文件
6. **生成报告** - 记录处理过程和问题

## 快捷方式

- `/lee-fmt` - 简写形式
- `/format` - 别名

## 示例

```bash
# 排版当前文章
/lee-layout ./drafts/article.md

# 使用蓝色主题
/lee-layout ./drafts/article.md --theme blue

# 生成小红书格式
/lee-layout ./drafts/article.md --platform xhs

# 仅输出 HTML
/lee-layout ./drafts/article.md --format html
```

## 相关文档

- 主题配置: `spec-global/departments/media/themes/`
- 工作流定义: `spec-global/departments/media/workflows/content-layout-pipeline/`
- 执行脚本: `spec-global/departments/media/commands/article-layout/v1/executor.py`
