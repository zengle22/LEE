import { defineConfig, devices } from '@playwright/test';

/**
 * E2E Runner - Playwright 配置
 *
 * 生产级配置，支持：
 * - 失败截图/视频/trace
 * - 并行执行
 * - 重试机制
 * - 多报告格式
 */

export default defineConfig({
  // 测试目录
  testDir: './tests',

  // 全局超时
  timeout: 30 * 1000, // 30 秒

  // 断言超时
  expect: {
    timeout: 5 * 1000, // 5 秒
  },

  // 失败处理
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : undefined,

  // 报告器
  reporter: [
    ['html', { outputFolder: 'output/playwright-report', open: 'never' }],
    ['json', { outputFile: 'output/e2e-report.json' }],
    ['junit', { outputFile: 'output/junit-report.xml' }],
    ['list'],
  ],

  // 全局配置
  use: {
    // 基础 URL（从环境变量读取）
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // 失败时截图
    screenshot: 'only-on-failure',

    // 失败时录屏
    video: 'retain-on-failure',

    // 失败时保存 trace
    trace: 'retain-on-failure',

    // 浏览器上下文
    viewport: { width: 1280, height: 720 },

    // 忽略 HTTPS 错误（测试环境常见）
    ignoreHTTPSErrors: true,

    // 时区
    timezoneId: 'Asia/Shanghai',

    // 语言
    locale: 'zh-CN',
  },

  // 项目配置（多浏览器）
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // 可选：Firefox
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    // 可选：WebKit (Safari)
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    // 可选：移动端
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
  ],

  // 本地开发服务器（可选）
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },

  // 输出目录
  outputDir: 'output/test-results',
});
