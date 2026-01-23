# UI Tokens Contract v1.0

设计 Token 契约规范 - 杜绝 magic number，让 UI 一致性可以门禁化。

## 核心理念

**Token 是设计系统的"常量定义"**：
- 颜色、字号、间距等都通过 token 引用
- 不允许出现裸的 `#1D4ED8` 或 `16px`
- 修改 token 即可全局生效

## Token 分类

| 类别 | 说明 | 示例 |
|------|------|------|
| `color` | 颜色系统 | primary, text, background |
| `font` | 字体系统 | family, size, weight, lineHeight |
| `space` | 间距系统 | 基于 4px 网格 |
| `radius` | 圆角系统 | sm, md, lg |
| `shadow` | 阴影系统 | 层次感定义 |
| `animation` | 动画系统 | duration, easing |
| `breakpoint` | 断点系统 | 响应式布局 |
| `zIndex` | 层级系统 | modal, tooltip |

## 完整示例

```json
{
  "$schema": "ui-tokens-contract/v1",
  "version": "1.0.0",

  "color": {
    "primary": "#1D4ED8",
    "primary.hover": "#1E40AF",
    "primary.active": "#1E3A8A",
    "secondary": "#6B7280",
    "success": "#059669",
    "warning": "#D97706",
    "danger": "#DC2626",
    "info": "#0284C7",

    "text": {
      "primary": "#111827",
      "secondary": "#6B7280",
      "disabled": "#9CA3AF",
      "inverse": "#FFFFFF"
    },

    "background": {
      "primary": "#FFFFFF",
      "secondary": "#F9FAFB",
      "elevated": "#FFFFFF",
      "overlay": "rgba(0, 0, 0, 0.5)"
    },

    "border": {
      "default": "#E5E7EB",
      "hover": "#D1D5DB",
      "focus": "#1D4ED8",
      "error": "#DC2626"
    }
  },

  "font": {
    "family": {
      "base": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      "heading": "inherit",
      "mono": "'Fira Code', 'Consolas', monospace"
    },
    "size": {
      "xs": 12,
      "sm": 14,
      "md": 16,
      "lg": 18,
      "xl": 20,
      "2xl": 24,
      "3xl": 30
    },
    "weight": {
      "regular": 400,
      "medium": 500,
      "semibold": 600,
      "bold": 700
    },
    "lineHeight": {
      "tight": 1.25,
      "base": 1.5,
      "relaxed": 1.75
    }
  },

  "space": {
    "0": 0,
    "1": 4,
    "2": 8,
    "3": 12,
    "4": 16,
    "5": 20,
    "6": 24,
    "8": 32,
    "10": 40,
    "12": 48,
    "16": 64,
    "20": 80,
    "24": 96
  },

  "radius": {
    "none": 0,
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "full": "9999px"
  },

  "shadow": {
    "none": "none",
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
  },

  "animation": {
    "duration": {
      "fast": "150ms",
      "normal": "300ms",
      "slow": "500ms"
    },
    "easing": {
      "linear": "linear",
      "easeIn": "cubic-bezier(0.4, 0, 1, 1)",
      "easeOut": "cubic-bezier(0, 0, 0.2, 1)",
      "easeInOut": "cubic-bezier(0.4, 0, 0.2, 1)"
    }
  },

  "breakpoint": {
    "sm": 640,
    "md": 768,
    "lg": 1024,
    "xl": 1280,
    "2xl": 1536
  },

  "zIndex": {
    "dropdown": 1000,
    "sticky": 1020,
    "fixed": 1030,
    "modal": 1040,
    "popover": 1050,
    "tooltip": 1060
  }
}
```

## 在组件中引用

```yaml
# component.yaml
tokens:
  - color.primary
  - color.primary.hover
  - font.size.md
  - space.3
  - radius.md
```

## 在样式中使用

```css
/* 使用 CSS 变量 */
.button {
  background-color: var(--color-primary);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
}

.button:hover {
  background-color: var(--color-primary-hover);
}
```

## 门禁规则

Token Gate 会检查：
- [ ] 代码中不允许出现裸的颜色值（如 `#1D4ED8`）
- [ ] 代码中不允许出现裸的尺寸值（如 `16px`）
- [ ] 所有使用的 token 必须在 tokens.json 中定义
- [ ] token 命名必须符合规范（小写 + 点分隔）

## 渐进式推进策略

| 阶段 | Token 化范围 | 门禁强度 |
|------|-------------|---------|
| Phase 1 | 颜色、字号、间距 | 警告 |
| Phase 2 | 圆角、阴影 | 警告 |
| Phase 3 | 所有 token | 错误（阻断） |

## 与 Figma 同步

tokens.json 可以从 Figma 导出：

```bash
# 使用 Figma Tokens 插件导出
figma-tokens export --output=spec/ui/tokens/tokens.json

# 或使用 Style Dictionary 转换
style-dictionary build
```
