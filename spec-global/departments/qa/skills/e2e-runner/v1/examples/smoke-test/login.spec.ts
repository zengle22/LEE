import { test, expect } from '@playwright/test';

/**
 * 登录流程 - 冒烟测试
 *
 * 优先级: P0
 * 覆盖场景: 正常登录、错误提示、记住密码
 */

test.describe('登录流程', () => {
  test.beforeEach(async ({ page }) => {
    // 访问登录页
    await page.goto('/login');
  });

  test('P0 - 正常登录应该跳转到首页', async ({ page }) => {
    // 输入用户名
    await page.getByTestId('input-username').fill('test_user');

    // 输入密码
    await page.getByTestId('input-password').fill('Test@1234');

    // 点击登录
    await page.getByTestId('btn-login').click();

    // 断言：应该跳转到首页
    await expect(page).toHaveURL('/home');

    // 断言：应该看到用户名
    await expect(page.getByTestId('user-display-name')).toHaveText('test_user');
  });

  test('P1 - 错误的密码应该显示提示', async ({ page }) => {
    await page.getByTestId('input-username').fill('test_user');
    await page.getByTestId('input-password').fill('wrong_password');
    await page.getByTestId('btn-login').click();

    // 断言：应该显示错误提示
    await expect(page.getByTestId('login-error')).toBeVisible();
    await expect(page.getByTestId('login-error')).toContainText('用户名或密码错误');

    // 断言：不应该跳转
    await expect(page).toHaveURL('/login');
  });

  test('P1 - 空字段应该禁用登录按钮', async ({ page }) => {
    // 断言：初始状态登录按钮应该禁用
    await expect(page.getByTestId('btn-login')).toBeDisabled();

    // 输入用户名
    await page.getByTestId('input-username').fill('test_user');
    await expect(page.getByTestId('btn-login')).toBeDisabled();

    // 输入密码
    await page.getByTestId('input-password').fill('Test@1234');
    await expect(page.getByTestId('btn-login')).toBeEnabled();
  });

  test('P2 - 记住密码应该保存到本地', async ({ page, context }) => {
    await page.getByTestId('input-username').fill('test_user');
    await page.getByTestId('input-password').fill('Test@1234');

    // 勾选记住密码
    await page.getByTestId('checkbox-remember').check();
    await expect(page.getByTestId('checkbox-remember')).toBeChecked();

    await page.getByTestId('btn-login').click();
    await expect(page).toHaveURL('/home');

    // 验证 localStorage
    const rememberMe = await page.evaluate(() => localStorage.getItem('rememberMe'));
    expect(rememberMe).toBe('true');
  });

  test('P1 - 键盘操作应该正常工作', async ({ page }) => {
    // Tab 导航
    await page.keyboard.press('Tab');
    await expect(page.getByTestId('input-username')).toBeFocused();

    await page.keyboard.type('test_user');

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('input-password')).toBeFocused();

    await page.keyboard.type('Test@1234');

    // Enter 提交
    await page.keyboard.press('Enter');

    // 应该跳转
    await expect(page).toHaveURL('/home');
  });
});
