# Frontend Testing Data-Testid Specification
# 前端测试 data-testid 规范

> **规范编号**: STD-DEV-FE-TEST-001  
> **版本**: v1.0  
> **生效日期**: 2026-02-06  
> **强制级别**: MUST (必须遵守)  
> **适用范围**: 所有 UniApp/Vue 前端项目  
> **制定者**: Tech Architect  
> **审批状态**: ✅ 已批准并强制执行

---

## 1. 规范目标

### 1.1 目的
- 统一前端代码中的测试标识属性
- 支持自动化测试的元素定位
- 确保测试属性不影响生产环境

### 1.2 预期效果
- 测试通过率提升 40%+
- 元素定位稳定性达到 99%+
- 零生产环境性能影响

---

## 2. 技术实现规范

### 2.1 实现方式 (强制)

**唯一允许的方式**: 辅助函数方式

```javascript
// src/utils/testHelper.js
/**
 * 生成 data-testid 属性对象
 * 仅在测试环境返回实际属性
 * @param {string} id - testid 标识
 * @returns {Object} - 属性对象或空对象
 */
export function testId(id) {
  // #ifdef TEST
  return { 'data-testid': id }
  // #endif
  
  // #ifndef TEST
  return {}
  // #endif
}

/**
 * 简写版本 (推荐在模板中使用)
 */
export function tid(id) {
  return testId(id)
}
```

### 2.2 使用方式 (强制)

**Vue2 Options API**:
```vue
<template>
  <view v-bind="tid('page-card-training')" class="card">
    内容
  </view>
</template>

<script>
import { tid } from '@/utils/testHelper.js'

export default {
  methods: { tid }
}
</script>
```

**Vue3 Composition API**:
```vue
<template>
  <view v-bind="tid('page-card-training')" class="card">
    内容
  </view>
</template>

<script setup>
import { tid } from '@/utils/testHelper.js'
</script>
```

**动态 testid (列表场景)**:
```vue
<template>
  <view 
    v-for="(item, index) in list" 
    :key="item.id"
    v-bind="tid(`${item.type}-item-${index}`)"
  >
    {{ item.name }}
  </view>
</template>
```

### 2.3 ❌ 禁止的写法

```vue
<!-- 禁止 1: template 中使用注释形式的条件编译 -->
<view 
  class="card"
  <!-- #ifdef TEST -->        ← 错误！不支持
  data-testid="xxx"
  <!-- #endif -->
>

<!-- 禁止 2: 直接硬编码 data-testid -->
<view data-testid="xxx">     ← 错误！会出现在生产环境

<!-- 禁止 3: 使用 v-if 控制 (运行时判断) -->
<view :data-testid="isTest ? 'xxx' : null">  ← 错误！增加运行时开销
```

---

## 3. 命名规范 (强制)

### 3.1 命名格式

```
格式: {scope}-{type}-{identifier}

全部小写，使用连字符(-)分隔
```

### 3.2 Scope (作用域) - 必填

| 值 | 含义 | 示例 |
|----|------|------|
| `page` | 页面级元素 | `page-card-training` |
| `comp` | 组件级元素 | `comp-modal-body` |
| `global` | 全局共享元素 | `global-nav-header` |

### 3.3 Type (类型) - 必填

| 值 | 含义 | 示例 |
|----|------|------|
| `btn` | 按钮 | `page-btn-send` |
| `input` | 输入框 | `page-input-search` |
| `card` | 卡片 | `page-card-training` |
| `list` | 列表容器 | `page-list-messages` |
| `item` | 列表项 | `page-item-message` |
| `modal` | 弹窗 | `comp-modal-status` |
| `nav` | 导航 | `global-nav-tabbar` |
| `text` | 文本 | `page-text-title` |
| `slider` | 滑块 | `comp-slider-fatigue` |
| `selector` | 选择器 | `comp-selector-quality` |
| `icon` | 图标 | `page-icon-avatar` |
| `image` | 图片 | `page-image-banner` |

### 3.4 Identifier (标识) - 必填

- 使用小写字母和连字符
- 描述元素的功能或内容
- 列表项需添加索引: `{identifier}-{index}`

**良好示例**:
```
page-card-training-today
page-btn-chat-send
page-input-message
comp-modal-body-status
comp-slider-fatigue-level
page-list-training-items
page-item-training-0
page-item-training-1
global-nav-tabbar-home
global-nav-tabbar-profile
```

**错误示例**:
```
todayTrainingCard      ← 错误: 驼峰命名
today-training-card    ← 错误: 缺少 scope
page-card              ← 错误: 缺少 identifier
Page-Card-Training     ← 错误: 大写字母
page_card_training     ← 错误: 下划线
```

---

## 4. 覆盖率要求 (强制)

### 4.1 必须添加 testid 的元素

| 优先级 | 元素类型 | 说明 |
|--------|----------|------|
| P0 | 主要交互元素 | 按钮、输入框、可点击卡片 |
| P0 | 页面核心区域 | 主要内容区、导航栏 |
| P0 | 动态内容容器 | 列表、消息容器 |
| P1 | 辅助信息 | 标题、状态文本 |
| P1 | 次要交互 | 切换按钮、展开/收起 |
| P2 | 静态装饰 | 图标、分割线 (可选) |

### 4.2 覆盖率标准

| 级别 | 要求 | 检查方式 |
|------|------|----------|
| MUST | P0 元素 100% 覆盖 | CI 自动检查 |
| SHOULD | P1 元素 80% 覆盖 | Code Review |
| MAY | P2 元素 50% 覆盖 | 自愿 |

---

## 5. 环境配置 (强制)

### 5.1 测试环境构建

**package.json**:
```json
{
  "scripts": {
    "build:test": "cross-env NODE_ENV=test uni build --mode test",
    "dev:test": "cross-env NODE_ENV=test uni dev --mode test"
  }
}
```

**vue.config.js**:
```javascript
module.exports = {
  configureWebpack: {
    // 测试环境配置
    mode: process.env.NODE_ENV === 'test' ? 'development' : 'production'
  }
}
```

### 5.2 条件编译配置

**manifest.json**:
```json
{
  "mp-weixin": {
    "appid": "your-app-id"
  },
  "uniStatistics": {
    "enable": false
  }
}
```

---

## 6. 验证机制 (强制)

### 6.1 本地验证

**脚本**: `scripts/verify-testids.js`
```javascript
const fs = require('fs')
const path = require('path')

// 递归获取所有 .vue 文件
function getVueFiles(dir, files = []) {
  const items = fs.readdirSync(dir)
  items.forEach(item => {
    const fullPath = path.join(dir, item)
    if (fs.statSync(fullPath).isDirectory()) {
      getVueFiles(fullPath, files)
    } else if (fullPath.endsWith('.vue')) {
      files.push(fullPath)
    }
  })
  return files
}

// 检查 testid 规范
function verifyTestIds() {
  const vueFiles = getVueFiles('src')
  const errors = []
  
  const namingPattern = /^(page|comp|global)-(btn|input|card|list|item|modal|nav|text|slider|selector|icon|image)-[a-z0-9-]+$/
  
  vueFiles.forEach(file => {
    const content = fs.readFileSync(file, 'utf-8')
    
    // 检查禁止的写法
    if (content.includes('data-testid=') && !content.includes('tid(') && !content.includes('testId(')) {
      errors.push(`${file}: 发现硬编码 data-testid，必须使用 tid() 辅助函数`)
    }
    
    // 提取所有 testid
    const matches = content.match(/tid\(['"`]([^'"`]+)['"`]\)/g)
    if (matches) {
      matches.forEach(match => {
        const id = match.match(/tid\(['"`]([^'"`]+)['"`]\)/)[1]
        if (!namingPattern.test(id)) {
          errors.push(`${file}: testid "${id}" 不符合命名规范`)
        }
      })
    }
  })
  
  if (errors.length > 0) {
    console.error('❌ TestId 规范检查失败:\n')
    errors.forEach(e => console.error(`  - ${e}`))
    process.exit(1)
  } else {
    console.log('✅ TestId 规范检查通过')
  }
}

verifyTestIds()
```

### 6.2 CI/CD 验证

**.github/workflows/ci.yml**:
```yaml
name: CI

on: [push, pull_request]

jobs:
  testid-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Verify testid naming convention
        run: node scripts/verify-testids.js
      
      - name: Build for test environment
        run: npm run build:test
      
      - name: Verify no testid in production build
        run: |
          npm run build
          if grep -r "data-testid" dist/; then
            echo "❌ ERROR: data-testid found in production build!"
            exit 1
          else
            echo "✅ No data-testid in production build"
          fi
```

---

## 7. Code Review 检查单 (强制)

### 7.1 Reviewer 必须检查

```markdown
## PR Code Review 检查单

### TestId 规范检查
- [ ] 所有 P0 元素都有 testid
- [ ] testid 命名符合 `{scope}-{type}-{identifier}` 规范
- [ ] 使用 `tid()` 辅助函数，无硬编码
- [ ] 无 `<!-- #ifdef -->` 注释形式在 template 中
- [ ] 列表项 testid 包含索引

### 运行验证
- [ ] `node scripts/verify-testids.js` 通过
- [ ] 测试环境构建成功
- [ ] 生产构建无 data-testid
```

---

## 8. 违规处理 (强制)

### 8.1 违规级别

| 级别 | 违规情况 | 处理方式 |
|------|----------|----------|
| CRITICAL | 生产环境出现 data-testid | 立即回滚，记大过 |
| HIGH | 硬编码 data-testid | PR 必须拒绝 |
| MEDIUM | 命名不规范 | PR 建议修改 |
| LOW | P0 元素遗漏 testid | 必须补充后合并 |

### 8.2 自动拦截

CI 流程会自动拦截以下情况：
1. 命名不规范
2. 硬编码 data-testid
3. 生产构建包含 data-testid

---

## 9. 实施路线图

### Phase 0: 规范准备 (0.5天)
- [ ] 创建 testHelper.js
- [ ] 配置 package.json 脚本
- [ ] 设置 CI 检查

### Phase 1: 试点验证 (1天)
- [ ] 选择 1-2 个页面试点
- [ ] 验证方案可行性
- [ ] 收集反馈

### Phase 2: 全面推广 (5天)
- [ ] 按优先级批量实施
- [ ] Code Review 强制检查
- [ ] 覆盖率达标

### Phase 3: 固化 (持续)
- [ ] 监控合规率
- [ ] 定期审计
- [ ] 持续改进

---

## 10. 相关文档

| 文档 | 路径 |
|------|------|
| 实施方案 | `output/frontend-test-infrastructure-implementation-plan.md` |
| 架构师评审 | `output/architecture-review-frontend-test-infrastructure.md` |
| 需求文档 | `qa/testing/docs/frontend-cooperation-requirements.md` |

---

## 11. 修订历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-02-06 | 初始版本，强制实施 | Tech Architect |

---

**批准状态**: ✅ 已批准并强制执行  
**生效日期**: 2026-02-06  
**下次评审**: 2026-03-06

*本规范为 LEE Framework Dev Department 强制执行标准，所有前端项目必须遵守。*
