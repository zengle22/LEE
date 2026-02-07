# Frontend Testing Standards
# 前端测试规范 (强制执行)

> **标准编号**: STD-DEV-FE-TEST-001  
> **版本**: v1.0  
> **生效日期**: 2026-02-06  
> **强制级别**: MUST  
> **适用范围**: 所有 UniApp/Vue 前端项目

---

## 📋 快速参考

### 1. 三步开始

```bash
# Step 1: 创建辅助函数
# src/utils/testHelper.js
export function tid(id) {
  // #ifdef TEST
  return { 'data-testid': id }
  // #endif
  return {}
}

# Step 2: 在组件中使用
# pages/home/index.vue
<template>
  <view v-bind="tid('page-card-training')" class="card">
    内容
  </view>
</template>

<script>
import { tid } from '@/utils/testHelper.js'
export default { methods: { tid } }
</script>

# Step 3: 配置构建脚本
# package.json
{
  "scripts": {
    "build:test": "cross-env NODE_ENV=test uni build --mode test"
  }
}
```

### 2. 命名速查

```
格式: {scope}-{type}-{identifier}

Scope    Type       Identifier
─────────────────────────────────────
page     btn        send-message
page     input      search-keyword
page     card       training-today
page     list       messages
page     item       training-0
comp     modal      body-status
comp     slider     fatigue-level
global   nav        tabbar-home
```

**示例**:
- `page-btn-chat-send` - 对话页面的发送按钮
- `comp-modal-body-status` - 身体状态弹窗
- `page-item-message-0` - 消息列表第1项

### 3. 禁止清单 ❌

```vue
<!-- 禁止 1: 硬编码 -->
<view data-testid="xxx">

<!-- 禁止 2: 注释条件编译 (template中) -->
<view <!-- #ifdef TEST -->data-testid="xxx"<!-- #endif -->>

<!-- 禁止 3: 运行时判断 -->
<view :data-testid="isTest ? 'xxx' : null">

<!-- 禁止 4: 命名不规范 -->
<view v-bind="tid('todayTrainingCard')">  ← 驼峰命名
<view v-bind="tid('today_training_card')">  ← 下划线
<view v-bind="tid('card')">  ← 缺少 scope 和 identifier
```

### 4. 必须遵守 ✅

```vue
<!-- 正确: 使用 tid() 辅助函数 -->
<view v-bind="tid('page-card-training-today')">

<!-- 正确: 动态 testid (列表) -->
<view v-for="(item, i) in list" v-bind="tid(`page-item-${i}`)">

<!-- 正确: 符合命名规范 -->
<view v-bind="tid('page-btn-chat-send')">
<view v-bind="tid('comp-modal-body-status')">
<view v-bind="tid('global-nav-tabbar-home')">
```

---

## 📚 完整文档

| 文档 | 说明 |
|------|------|
| [testid-spec.md](./testid-spec.md) | 完整规范文档 |
| [enforcement.yaml](./enforcement.yaml) | 强制执行配置 |

---

## 🔍 验证命令

```bash
# 本地验证
node scripts/verify-testids.js

# 测试环境构建
npm run build:test

# 生产构建检查
npm run build && ! grep -r "data-testid" dist/
```

---

## ⚠️ 违规后果

| 违规 | 后果 |
|------|------|
| 生产环境出现 data-testid | 立即回滚，记大过 |
| 硬编码 data-testid | PR 被拒绝 |
| 命名不规范 | 必须修改 |

---

## 👥 相关 Agent

| Agent | 职责 |
|-------|------|
| Frontend Architect | 确保架构设计符合本规范 |
| UniApp Frontend Engineer | 确保实现代码符合本规范 |
| Code Reviewer | Review 时强制检查本规范 |

---

**本规范为 LEE Framework Dev Department 强制执行标准**

*最后更新: 2026-02-06*
