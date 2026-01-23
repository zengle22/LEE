# E2E Runner - 知识库 Pitfalls

## 常见坑点（必读）

### 1. 选择器不稳定

**症状**: 测试随机失败，提示 "selector not found"

**原因**: 使用了脆弱的 CSS 选择器（如 `.MuiButton-root.css-xyz`）

**解决方案**:
```typescript
// ❌ 错误
await page.click('.MuiButton-root');

// ✅ 正确
await page.getByTestId('btn-login').click();
```

**强制要求**: 所有测试必须使用 `data-testid` 选择器

---

### 2. 异步等待不充分

**症状**: 测试失败，提示 "element not visible"

**原因**: 使用 `waitForTimeout()` 固定延迟，网络慢时不够

**解决方案**:
```typescript
// ❌ 错误
await page.waitForTimeout(3000);

// ✅ 正确
await expect(page.getByTestId('loading-spinner')).toBeVisible();
await expect(page.getByTestId('loading-spinner')).toBeHidden();
```

**强制要求**: 禁止使用 `waitForTimeout()`，必须使用显式等待

---

### 3. 测试数据污染

**症状**: 测试在单独运行时通过，批量运行时失败

**原因**: 测试之间共享状态（localStorage/sessionStorage/cookies）

**解决方案**:
```typescript
test.beforeEach(async ({ page }) => {
  // 每次测试前清理状态
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
});
```

---

### 4. 时区/语言差异

**症状**: 本地通过，CI 失败（日期/文本不匹配）

**原因**: CI 环境时区/语言与本地不同

**解决方案**:
```typescript
// playwright.config.ts
use: {
  timezoneId: 'Asia/Shanghai',
  locale: 'zh-CN',
}
```

---

### 5. 网络请求未 Mock

**症状**: 测试不稳定，依赖外部 API

**原因**: 真实 API 可能慢/失败

**解决方案**:
```typescript
await page.route('/api/**', route => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({ data: [] }),
  });
});
```

---

### 6. 忽略控制台错误

**症状**: 测试通过但应用有 JS 错误

**解决方案**:
```typescript
page.on('console', msg => {
  if (msg.type() === 'error') {
    throw new Error(`Console error: ${msg.text()}`);
  }
});
```

---

### 7. 失败时缺失证据

**症状**: 测试失败但不知道为什么

**解决方案**: 确保配置正确

```typescript
// playwright.config.ts
use: {
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
  trace: 'retain-on-failure',
}
```

**检查**: 失败后必须有 screenshot/video/trace

---

## 更新记录

- 2026-01-16: 初始版本
