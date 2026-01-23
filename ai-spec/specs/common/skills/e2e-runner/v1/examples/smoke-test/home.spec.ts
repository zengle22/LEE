import { test, expect } from '@playwright/test';

/**
 * 首页 - 冒烟测试
 *
 * 优先级: P0
 * 覆盖场景: 页面加载、核心功能、导航
 */

test.describe('首页', () => {
  test.beforeEach(async ({ page }) => {
    // 模拟已登录状态
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock_token_12345');
      localStorage.setItem('user_id', 'test_user');
    });
    await page.goto('/home');
  });

  test('P0 - 首页应该正确加载', async ({ page }) => {
    // 断言：页面标题
    await expect(page).toHaveTitle(/首页/);

    // 断言：主要区域可见
    await expect(page.getByTestId('home-page')).toBeVisible();
    await expect(page.getByTestId('today-training')).toBeVisible();
    await expect(page.getByTestId('training-list')).toBeVisible();
  });

  test('P0 - 点击训练卡片应该跳转到详情', async ({ page }) => {
    // 等待训练列表加载
    await expect(page.getByTestId('training-card').first()).toBeVisible();

    // 点击第一个训练卡片
    await page.getByTestId('training-card').first().click();

    // 断言：应该跳转到详情页
    await expect(page).toHaveURL(/\/training\/.+/);
    await expect(page.getByTestId('training-detail')).toBeVisible();
  });

  test('P1 - 空数据应该显示空状态', async ({ page }) => {
    // Mock API 返回空数据
    await page.route('/api/trainings', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [] }),
      });
    });

    // 刷新页面
    await page.reload();

    // 断言：应该显示空状态
    await expect(page.getByTestId('empty-state')).toBeVisible();
    await expect(page.getByTestId('empty-state')).toContainText('暂无训练计划');
  });

  test('P1 - 加载失败应该显示错误状态', async ({ page }) => {
    // Mock API 返回错误
    await page.route('/api/trainings', route => {
      route.abort('failed');
    });

    // 刷新页面
    await page.reload();

    // 断言：应该显示错误状态
    await expect(page.getByTestId('error-state')).toBeVisible();
    await expect(page.getByTestId('btn-retry')).toBeVisible();
  });

  test('P2 - 加载状态应该显示骨架屏', async ({ page }) => {
    // Mock API 延迟响应
    await page.route('/api/trainings', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [] }),
      });
    });

    // 刷新页面
    const reloadPromise = page.reload();

    // 断言：应该显示骨架屏
    await expect(page.getByTestId('training-card-skeleton')).toBeVisible();

    // 等待加载完成
    await reloadPromise;
  });

  test('P1 - 导航栏应该正常工作', async ({ page }) => {
    // 点击"我的"
    await page.getByTestId('nav-profile').click();
    await expect(page).toHaveURL('/profile');

    // 点击"首页"返回
    await page.getByTestId('nav-home').click();
    await expect(page).toHaveURL('/home');
  });
});
