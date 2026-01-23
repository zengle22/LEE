# Generate Icon Skill

> **Skill ID**: skill.design.generate_icon
> **触发命令**: `/generate-icon <icon_name> [options]`

## 概述

基于 Icon Design Token 规范生成 SVG 图标，并导出为多格式资产。

## 使用方法

```bash
/generate-icon home --category nav --description "首页导航图标，房屋形状"
/generate-icon running --category running --variants outline,filled
/generate-icon goal --category object --description "目标靶心图标" --sizes 24,48,1024
```

## 参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `icon_name` | 是 | - | 图标名称 (小写+下划线) |
| `--category` | 是 | - | 分类: nav/action/status/object/running |
| `--description` | 是 | - | 图标语义描述 |
| `--variants` | 否 | outline,filled | 样式变体 |
| `--sizes` | 否 | 24,48,1024 | 导出尺寸 |
| `--output` | 否 | ./icons | 输出目录 |

## 工作流程

```
1. 读取 Icon Design Token 规范
   ↓
2. 解析图标需求
   ↓
3. 生成 SVG 代码 (按变体)
   ↓
4. 运行 QA Gate 验证
   ├── 线宽一致性检查
   ├── 颜色合规检查
   ├── 安全区域检查
   ├── 网格对齐检查
   └── 禁止元素检查
   ↓
5. 导出 PNG (多尺寸)
   ↓
6. 更新 icon-manifest.yaml
   ↓
7. 输出资产包
```

## 输出结构

```
icons/
├── source/
│   ├── nav_home_outline.svg
│   └── nav_home_filled.svg
├── png/
│   ├── nav_home_outline_24.png
│   ├── nav_home_outline_48.png
│   ├── nav_home_outline_1024.png
│   ├── nav_home_filled_24.png
│   ├── nav_home_filled_48.png
│   └── nav_home_filled_1024.png
├── export/
│   ├── android/
│   │   └── drawable-*dpi/
│   ├── ios/
│   │   └── *.imageset/
│   └── web/
│       └── sprite.svg
└── icon-manifest.yaml
```

## Design Token 规范摘要

### 画板尺寸
| 尺寸 | 用途 | 网格 | 安全区 |
|------|------|------|--------|
| 24px | TabBar/列表 | 1px | 2px |
| 48px | 功能按钮 | 2px | 4px |
| 96px | 空状态 | 4px | 8px |
| 1024px | 导出源 | 32px | 64px |

### 线宽规范
- Outline 样式: 2px (24px 画板)
- Stroke cap/join: round
- 线宽按尺寸等比缩放

### 颜色调色板
| Token | 色值 | 用途 |
|-------|------|------|
| primary | #FF6B00 | 激活状态 |
| secondary | #1A73E8 | AI 相关 |
| default | #5F6368 | 默认状态 |
| inactive | #9AA0A6 | 禁用状态 |
| success | #34A853 | 成功 |
| warning | #FBBC05 | 警告 |
| error | #EA4335 | 错误 |

### 禁止事项
- ❌ 渐变填充
- ❌ 投影/阴影
- ❌ 文字标签
- ❌ 小于 1px 细节
- ❌ 超出安全区
- ❌ 多于 2 种颜色

## QA Gate 验证规则

| ID | 规则 | 严重性 |
|----|------|--------|
| QA001 | 线宽一致性 | Error |
| QA002 | 颜色合规 | Error |
| QA003 | 安全区域 | Error |
| QA004 | 网格对齐 | Warning |
| QA005 | 无禁止元素 | Error |
| QA006 | viewBox 正确 | Error |

## 示例

### 生成首页图标

```bash
/generate-icon home \
  --category nav \
  --description "首页导航图标，简洁的房屋形状，一个三角形屋顶加矩形主体"
```

输出:
```
✅ Icon generated: nav_home

Files created:
  - icons/source/nav_home_outline.svg
  - icons/source/nav_home_filled.svg
  - icons/png/nav_home_*_24.png
  - icons/png/nav_home_*_48.png
  - icons/png/nav_home_*_1024.png

QA Validation: ✅ PASSED (6/6 checks)

Manifest updated: icons/icon-manifest.yaml
```

### 生成跑步图标

```bash
/generate-icon running \
  --category running \
  --description "跑步者图标，表示运动中的人，动态姿态" \
  --variants outline,filled,duotone
```

## 批量生成

对于多个图标，可以使用清单文件:

```yaml
# icons-to-generate.yaml
icons:
  - name: home
    category: nav
    description: 首页导航图标
  - name: plan
    category: nav
    description: 计划/日历图标
  - name: profile
    category: nav
    description: 用户个人图标
  - name: running
    category: running
    description: 跑步者图标
  - name: goal
    category: running
    description: 比赛目标/靶心
  - name: trophy
    category: running
    description: 奖杯/成就图标
```

```bash
/generate-icon --from icons-to-generate.yaml
```

## 相关规范

- Icon Design Token: `ai-spec/specs/common/contracts/icon-design-token/v1/icon-token.yaml`
- Icon Generator Agent: `ai-spec/specs/common/agents/icon-generator/v1/agent.yaml`
- Icon SVG Generator Skill: `ai-spec/specs/common/skills/icon-svg-generator/v1/skill.yaml`
