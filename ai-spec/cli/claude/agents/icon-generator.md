# Icon Generator Agent

> 图标生成器 - 根据设计规范生成 SVG 和 PNG 图标

## 触发条件

当任务涉及以下内容时调用此 Agent：
- 生成 PNG 图标文件
- 生成 SVG 图标文件
- TabBar 图标制作
- 导航图标设计
- 图标资源导出

## Agent 引用

```
agent.design.icon_generator
```

## 输入要求

1. **设计规范** (必需)
   - icon-tokens.json 或等效的设计 token 文件
   - 包含：尺寸、描边、颜色、安全区等定义

2. **图标清单** (必需)
   - 需要生成的图标列表
   - 每个图标的名称、类别、变体（outline/filled）

## 输出产物

```
icons/
├── source/           # SVG 源文件
│   ├── {name}_outline.svg
│   └── {name}_filled.svg
├── png/              # PNG 导出 (多分辨率)
│   ├── {name}_24.png
│   └── {name}_48.png
└── icon-manifest.yaml  # 图标清单
```

## 设计规范遵循

### 基础规格
- 画板尺寸: 24×24px
- 安全区: 距边缘 2px
- 导出尺寸: 24px, 48px

### 描边规范
- 线宽: 2px
- 端点: round (圆角)
- 连接: round (圆角)

### 颜色规范
- 使用 `currentColor` 实现动态着色
- 默认态: gray.400 (#9CA3AF)
- 激活态: primary.default (#3B82F6)

## QA 检查清单

生成图标后必须验证：

- [ ] stroke-width == 2px
- [ ] viewBox == "0 0 24 24"
- [ ] 所有路径在安全区内 (≥2px from edge)
- [ ] line-cap == round
- [ ] line-join == round
- [ ] 使用 currentColor（非硬编码颜色）

## 使用示例

```
请使用 icon-generator agent 为 TabBar 生成以下图标：
- home (首页)
- chat (对话)
- plan (计划)
- profile (我的)

设计规范参考: ui/tokens/icon-tokens.json
输出目录: src/static/icons/
```

## 转换脚本

PNG 转换使用 Playwright：

```bash
node scripts/svg-to-png.js
```

脚本位置: `git/ai-marathon-coach-front/scripts/svg-to-png.js`

## 关联规范

- 权威 Spec: `ai-spec/specs/common/agents/icon-generator/v1/agent.yaml`
- 设计 Token 契约: `ai-spec/specs/common/contracts/icon-design-token/v1/icon-token.yaml`
- SVG 生成 Skill: `ai-spec/specs/common/skills/icon-svg-generator/v1/skill.yaml`
