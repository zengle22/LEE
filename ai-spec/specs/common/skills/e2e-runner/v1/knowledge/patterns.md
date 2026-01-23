# E2E Runner - 技术模式

## 可复用模式

### 模式 1: Page Object Model (POM)

**场景**: 多个测试需要操作同一个页面

**实现**:

```typescript
// pages/LoginPage.ts
export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(username: string, password: string) {
    await this.page.getByTestId('input-username').fill(username);
    await this.page.getByTestId('input-password').fill(password);
    await this.page.getByTestId('btn-login').click();
  }

  async expectError(message: string) {
    await expect(this.page.getByTestId('login-error')).toContainText(message);
  }
}

// tests/login.spec.ts
import { LoginPage } from '../pages/LoginPage';

test('正常登录', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('test_user', 'Test@1234');
  await expect(page).toHaveURL('/home');
});
```

---

### 模式 2: Fixture 封装认证状态

**场景**: 多个测试需要已登录状态

**实现**:

```typescript
// fixtures/auth.ts
import { test as base } from '@playwright/test';

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    // 设置认证状态
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'test_token_12345');
      localStorage.setItem('user_id', 'test_user');
    });
    await page.goto('/home');
    await use(page);
  },
});

// tests/home.spec.ts
import { test } from '../fixtures/auth';

test('首页加载', async ({ authenticatedPage }) => {
  await expect(authenticatedPage.getByTestId('home-page')).toBeVisible();
});
```

---

### 模式 3: API Mock 统一管理

**场景**: 多个测试需要相同的 Mock 数据

**实现**:

```typescript
// mocks/api-mocks.ts
export const mockEmptyTrainings = (page: Page) => {
  return page.route('/api/trainings', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [] }),
    });
  });
};

export const mockLoadingError = (page: Page) => {
  return page.route('/api/trainings', route => {
    route.abort('failed');
  });
};

// tests/home.spec.ts
import { mockEmptyTrainings } from '../mocks/api-mocks';

test('空数据', async ({ page }) => {
  await mockEmptyTrainings(page);
  await page.goto('/home');
  await expect(page.getByTestId('empty-state')).toBeVisible();
});
```

---

### 模式 4: 自定义断言

**场景**: 复杂的验证逻辑重复出现

**实现**:

```typescript
// utils/custom-assertions.ts
export async function expectTrainingCard(
  page: Page,
  training: { name: string; date: string }
) {
  const card = page.getByTestId(`training-card-${training.name}`);
  await expect(card).toBeVisible();
  await expect(card.getByTestId('training-name')).toHaveText(training.name);
  await expect(card.getByTestId('training-date')).toHaveText(training.date);
}

// tests/home.spec.ts
test('训练卡片渲染', async ({ page }) => {
  await page.goto('/home');
  await expectTrainingCard(page, { name: '5公里轻松跑', date: '2024-01-08' });
});
```

---

### 模式 5: 并行测试隔离

**场景**: 多个测试并行运行，避免冲突

**实现**:

```typescript
// playwright.config.ts
export default defineConfig({
  fullyParallel: true,
  workers: 4,

  // 每个测试使用独立的浏览器上下文
  use: {
    contextOptions: {
      storageState: undefined, // 每次重新开始
    },
  },
});
```

---

### 模式 6: 测试优先级标记

**场景**: 区分 P0/P1/P2 测试

**实现**:

```typescript
// tests/login.spec.ts
test('P0 - 正常登录', async ({ page }) => {
  // P0 核心功能
});

test('P1 - 错误提示', async ({ page }) => {
  // P1 重要功能
});

test('P2 - 记住密码', async ({ page }) => {
  // P2 次要功能
});

// 只运行 P0
// npx playwright test --grep "P0"
```

---

### 模式 7: Visual Regression Testing

**场景**: 检测 UI 视觉变化

**实现**:

```typescript
test('首页截图对比', async ({ page }) => {
  await page.goto('/home');

  // 等待加载完成
  await expect(page.getByTestId('home-page')).toBeVisible();

  // 截图对比
  await expect(page).toHaveScreenshot('home-page.png', {
    maxDiffPixels: 100, // 允许最多 100 像素差异
  });
});
```

---

### 模式 8: 条件跳过测试

**场景**: 某些测试只在特定环境运行

**实现**:

```typescript
test('微信登录', async ({ page }) => {
  test.skip(process.env.PLATFORM !== 'wechat', '只在微信环境运行');

  // 微信特有的测试逻辑
});
```

---

## 更新记录

- 2026-01-16: 初始版本，8 种核心模式
