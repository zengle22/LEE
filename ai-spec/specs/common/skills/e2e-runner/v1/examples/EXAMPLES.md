# E2E Runner - 测试用例示例库

> 真实场景的测试用例参考

---

## 目录

1. [登录与认证](#登录与认证)
2. [表单操作](#表单操作)
3. [列表与分页](#列表与分页)
4. [API Mock](#api-mock)
5. [文件上传](#文件上传)
6. [响应式布局](#响应式布局)
7. [错误处理](#错误处理)
8. [可访问性](#可访问性)

---

## 登录与认证

### 基础登录流程

```typescript
test('正常登录流程', async ({ page }) => {
  await page.goto('/login');

  await page.getByTestId('input-username').fill('test_user');
  await page.getByTestId('input-password').fill('Test@1234');
  await page.getByTestId('btn-login').click();

  await expect(page).toHaveURL('/home');
  await expect(page.getByTestId('user-display-name')).toHaveText('test_user');
});
```

### 使用 Fixture 复用登录状态

```typescript
// fixtures/auth.ts
import { test as base } from '@playwright/test';

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'test_token_12345');
    });
    await page.goto('/home');
    await use(page);
  },
});

// 使用
test('已登录状态访问首页', async ({ authenticatedPage }) => {
  await expect(authenticatedPage.getByTestId('home-page')).toBeVisible();
});
```

### 记住密码功能

```typescript
test('勾选记住密码应该保存到本地', async ({ page }) => {
  await page.goto('/login');

  await page.getByTestId('input-username').fill('test_user');
  await page.getByTestId('input-password').fill('Test@1234');
  await page.getByTestId('checkbox-remember').check();
  await page.getByTestId('btn-login').click();

  // 验证 localStorage
  const rememberMe = await page.evaluate(() => localStorage.getItem('rememberMe'));
  expect(rememberMe).toBe('true');
});
```

---

## 表单操作

### 表单验证

```typescript
test('空字段应该显示错误提示', async ({ page }) => {
  await page.goto('/contact');

  // 不填写任何字段，直接提交
  await page.getByTestId('btn-submit').click();

  // 断言：每个必填字段都有错误提示
  await expect(page.getByTestId('error-name')).toContainText('姓名不能为空');
  await expect(page.getByTestId('error-email')).toContainText('邮箱不能为空');
  await expect(page.getByTestId('error-message')).toContainText('消息不能为空');
});
```

### 实时验证

```typescript
test('邮箱格式错误应该实时提示', async ({ page }) => {
  await page.goto('/contact');

  await page.getByTestId('input-email').fill('invalid-email');
  await page.getByTestId('input-email').blur();

  await expect(page.getByTestId('error-email')).toContainText('请输入有效的邮箱地址');
});
```

### 复杂表单提交

```typescript
test('完整表单提交流程', async ({ page }) => {
  await page.goto('/contact');

  // 填写表单
  await page.getByTestId('input-name').fill('张三');
  await page.getByTestId('input-email').fill('zhangsan@example.com');
  await page.getByTestId('select-category').selectOption('feedback');
  await page.getByTestId('textarea-message').fill('这是一条反馈消息');

  // Mock 提交 API
  await page.route('/api/contact', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({ success: true, message: '提交成功' }),
    });
  });

  // 提交
  await page.getByTestId('btn-submit').click();

  // 断言：显示成功提示
  await expect(page.getByTestId('success-message')).toContainText('提交成功');
});
```

---

## 列表与分页

### 加载列表数据

```typescript
test('列表应该正确加载数据', async ({ page }) => {
  // Mock 列表 API
  await page.route('/api/items', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        data: [
          { id: 1, name: '项目 1', status: 'active' },
          { id: 2, name: '项目 2', status: 'inactive' },
        ],
      }),
    });
  });

  await page.goto('/items');

  // 断言：列表项渲染
  await expect(page.getByTestId('item-1')).toBeVisible();
  await expect(page.getByTestId('item-2')).toBeVisible();
  await expect(page.getByTestId('item-1-name')).toHaveText('项目 1');
});
```

### 分页功能

```typescript
test('点击下一页应该加载新数据', async ({ page }) => {
  let currentPage = 1;

  await page.route('/api/items*', route => {
    const url = new URL(route.request().url());
    const page = parseInt(url.searchParams.get('page') || '1');

    route.fulfill({
      status: 200,
      body: JSON.stringify({
        data: [
          { id: page * 10 + 1, name: `第 ${page} 页项目 1` },
          { id: page * 10 + 2, name: `第 ${page} 页项目 2` },
        ],
        pagination: { total: 100, page, pageSize: 10 },
      }),
    });
  });

  await page.goto('/items');

  // 断言：第 1 页
  await expect(page.getByTestId('item-11-name')).toHaveText('第 1 页项目 1');

  // 点击下一页
  await page.getByTestId('btn-next-page').click();

  // 断言：第 2 页
  await expect(page.getByTestId('item-21-name')).toHaveText('第 2 页项目 1');
});
```

### 无限滚动

```typescript
test('滚动到底部应该自动加载更多', async ({ page }) => {
  await page.goto('/feed');

  // 初始有 10 条
  await expect(page.getByTestId('feed-item')).toHaveCount(10);

  // 滚动到底部
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

  // 等待加载
  await page.waitForResponse('/api/feed?offset=10');

  // 应该有 20 条
  await expect(page.getByTestId('feed-item')).toHaveCount(20);
});
```

---

## API Mock

### 基础 Mock

```typescript
test('Mock API 返回空数据', async ({ page }) => {
  await page.route('/api/trainings', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [] }),
    });
  });

  await page.goto('/home');

  await expect(page.getByTestId('empty-state')).toBeVisible();
});
```

### Mock 延迟响应

```typescript
test('加载状态应该显示骨架屏', async ({ page }) => {
  await page.route('/api/trainings', async route => {
    // 延迟 2 秒
    await new Promise(resolve => setTimeout(resolve, 2000));
    route.fulfill({
      status: 200,
      body: JSON.stringify({ data: [] }),
    });
  });

  const reloadPromise = page.goto('/home');

  // 应该显示骨架屏
  await expect(page.getByTestId('training-card-skeleton')).toBeVisible();

  // 等待加载完成
  await reloadPromise;
  await expect(page.getByTestId('training-card-skeleton')).toBeHidden();
});
```

### Mock 错误响应

```typescript
test('API 失败应该显示错误状态', async ({ page }) => {
  await page.route('/api/trainings', route => {
    route.fulfill({
      status: 500,
      body: JSON.stringify({ error: 'Internal Server Error' }),
    });
  });

  await page.goto('/home');

  await expect(page.getByTestId('error-state')).toBeVisible();
  await expect(page.getByTestId('btn-retry')).toBeVisible();
});
```

### 条件 Mock

```typescript
test('根据参数返回不同数据', async ({ page }) => {
  await page.route('/api/items*', route => {
    const url = new URL(route.request().url());
    const filter = url.searchParams.get('filter');

    if (filter === 'active') {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ data: [{ id: 1, status: 'active' }] }),
      });
    } else {
      route.fulfill({
        status: 200,
        body: JSON.stringify({ data: [] }),
      });
    }
  });

  await page.goto('/items?filter=active');
  await expect(page.getByTestId('item-1')).toBeVisible();

  await page.goto('/items?filter=inactive');
  await expect(page.getByTestId('empty-state')).toBeVisible();
});
```

---

## 文件上传

### 单文件上传

```typescript
test('上传图片应该显示预览', async ({ page }) => {
  await page.goto('/upload');

  // 选择文件
  const fileInput = page.getByTestId('input-file');
  await fileInput.setInputFiles('test-fixtures/test-image.png');

  // 断言：显示预览
  await expect(page.getByTestId('image-preview')).toBeVisible();
  await expect(page.getByTestId('image-preview')).toHaveAttribute('src', /test-image/);
});
```

### 多文件上传

```typescript
test('多文件上传应该显示列表', async ({ page }) => {
  await page.goto('/upload');

  const fileInput = page.getByTestId('input-files');
  await fileInput.setInputFiles([
    'test-fixtures/file1.pdf',
    'test-fixtures/file2.pdf',
  ]);

  await expect(page.getByTestId('file-list-item')).toHaveCount(2);
  await expect(page.getByText('file1.pdf')).toBeVisible();
  await expect(page.getByText('file2.pdf')).toBeVisible();
});
```

---

## 响应式布局

### 移动端布局

```typescript
test('移动端应该显示汉堡菜单', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');

  // 桌面端导航应该隐藏
  await expect(page.getByTestId('desktop-nav')).toBeHidden();

  // 汉堡菜单应该可见
  await expect(page.getByTestId('hamburger-menu')).toBeVisible();

  // 点击汉堡菜单
  await page.getByTestId('hamburger-menu').click();
  await expect(page.getByTestId('mobile-nav')).toBeVisible();
});
```

### 平板布局

```typescript
test('平板应该使用中等尺寸布局', async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto('/');

  // 检查列数
  const columns = await page.getByTestId('grid-item').count();
  expect(columns).toBe(2); // 平板 2 列
});
```

---

## 错误处理

### 网络错误

```typescript
test('网络断开应该显示离线提示', async ({ page, context }) => {
  await page.goto('/home');

  // 模拟网络断开
  await context.setOffline(true);
  await page.reload();

  await expect(page.getByTestId('offline-banner')).toBeVisible();
});
```

### 超时处理

```typescript
test('请求超时应该显示重试按钮', async ({ page }) => {
  await page.route('/api/data', route => {
    // 永不响应（模拟超时）
  });

  await page.goto('/data');

  // 等待超时提示
  await expect(page.getByTestId('timeout-error')).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId('btn-retry')).toBeVisible();
});
```

---

## 可访问性

### WCAG 合规检查

```typescript
import AxeBuilder from '@axe-core/playwright';

test('页面应该通过 WCAG 2.1 AA', async ({ page }) => {
  await page.goto('/');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  expect(results.violations).toEqual([]);
});
```

### 键盘导航

```typescript
test('Tab 导航应该按逻辑顺序', async ({ page }) => {
  await page.goto('/form');

  await page.keyboard.press('Tab');
  await expect(page.getByTestId('input-name')).toBeFocused();

  await page.keyboard.press('Tab');
  await expect(page.getByTestId('input-email')).toBeFocused();

  await page.keyboard.press('Tab');
  await expect(page.getByTestId('btn-submit')).toBeFocused();
});
```

### 屏幕阅读器支持

```typescript
test('所有交互元素应该有 ARIA 标签', async ({ page }) => {
  await page.goto('/');

  const button = page.getByRole('button', { name: '登录' });
  await expect(button).toBeVisible();

  const form = page.getByRole('form', { name: '登录表单' });
  await expect(form).toBeVisible();
});
```

---

## 高级场景

### WebSocket 测试

```typescript
test('WebSocket 消息应该实时显示', async ({ page }) => {
  await page.goto('/chat');

  // 监听 WebSocket
  page.on('websocket', ws => {
    ws.on('framesent', event => {
      if (event.payload === 'ping') {
        // 模拟服务器响应
        ws.send('pong');
      }
    });
  });

  // 发送消息
  await page.getByTestId('input-message').fill('Hello');
  await page.getByTestId('btn-send').click();

  // 断言：消息显示
  await expect(page.getByText('Hello')).toBeVisible();
});
```

### Service Worker 测试

```typescript
test('Service Worker 应该缓存资源', async ({ page, context }) => {
  // 注册 Service Worker
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // 断开网络
  await context.setOffline(true);

  // 刷新页面（应该从缓存加载）
  await page.reload();
  await expect(page.getByTestId('home-page')).toBeVisible();
});
```

---

更多示例请参考 Playwright 官方文档: https://playwright.dev/docs/writing-tests
