import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * 可访问性测试 - 冒烟测试
 *
 * 优先级: P1
 * 覆盖: WCAG 2.1 AA 标准
 */

test.describe('可访问性测试', () => {
  test('P1 - 登录页应该通过 axe-core 检查', async ({ page }) => {
    await page.goto('/login');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('P1 - 首页应该通过 axe-core 检查', async ({ page }) => {
    // 模拟已登录
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock_token_12345');
    });
    await page.goto('/home');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('P1 - 键盘导航应该正常工作', async ({ page }) => {
    await page.goto('/home');

    // Tab 导航到第一个训练卡片
    await page.keyboard.press('Tab');
    const firstCard = page.getByTestId('training-card').first();
    await expect(firstCard).toBeFocused();

    // Enter 应该触发点击
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/training\/.+/);
  });

  test('P2 - 所有交互元素应该有正确的 ARIA 标签', async ({ page }) => {
    await page.goto('/login');

    // 检查登录表单
    const form = page.getByRole('form');
    await expect(form).toHaveAttribute('aria-label', '登录表单');

    // 检查输入框
    const usernameInput = page.getByRole('textbox', { name: '用户名' });
    await expect(usernameInput).toBeVisible();

    const passwordInput = page.getByLabelText('密码');
    await expect(passwordInput).toBeVisible();

    // 检查按钮
    const loginButton = page.getByRole('button', { name: '登录' });
    await expect(loginButton).toBeVisible();
  });

  test('P2 - 焦点管理应该正确', async ({ page }) => {
    await page.goto('/login');

    // 页面加载后焦点应该在第一个输入框
    await expect(page.getByTestId('input-username')).toBeFocused();

    // Tab 导航应该按照逻辑顺序
    await page.keyboard.press('Tab');
    await expect(page.getByTestId('input-password')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('checkbox-remember')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('btn-login')).toBeFocused();
  });

  test('P1 - 颜色对比度应该符合 WCAG AA', async ({ page }) => {
    await page.goto('/home');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .include(['color-contrast'])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});
