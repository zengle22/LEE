---
name: analyze-supply
description: 分析市场现有解决方案，回答"已有解决方案哪里不够好"，输出 Existing Solutions + Gaps
arguments:
  - name: report_path
    description: 关键词分析报告路径（可选，不填则自动查找）
    required: false
---

# 竞品供给分析

回答一个核心问题：**已有解决方案哪里不够好？**

## 契约驱动流程

```
输入: contracts/google-keyword-contract.md
  ↓
处理: supply-analyzer Agent
  ↓
输出: contracts/supply-analysis-contract.md
  ↓
下游: business-opportunity-analyzer Agent
```

## 输入处理

{{#if report_path}}
指定报告路径：**{{report_path}}**
{{else}}
自动查找 `output/keywords/` 目录下的关键词分析报告。
{{/if}}

## 输出结构

```markdown
## Existing Solutions

### Category A: {类别名}
| 产品 | 描述 | 定价 | 优势 | 不足 |
|------|------|------|------|------|

### Category B: {类别名}
...

## Gaps

### Unserved Segment (被忽视的细分)
| 细分市场 | 证据 | 机会 |

### Poor UX (用户体验差)
| 问题 | 受影响产品 | 用户抱怨 |

### High Cost (成本过高)
| 问题 | 当前定价 | 被排斥用户 |

### Poor Integration (集成差)
| 问题 | 缺失集成 | 用户影响 |
```

## 使用示例

```bash
/analyze-supply
/analyze-supply ./output/keywords/2026-01-03_跑步AI产品_关键词分析.md
```
