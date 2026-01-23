# E2E Runner - 更新日志

所有重要变更都会记录在这个文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [1.0.0] - 2026-01-16

### 新增

#### 核心能力
- ✅ **Docker 镜像**: 基于官方 Playwright v1.41.0
- ✅ **Skill 规范**: skill.yaml (符合 v1.0 模板)
- ✅ **Agent 规范**: e2e-test-executor agent.yaml (v1.1)
- ✅ **输入契约**: e2e-test-input/v1/input.schema.json
- ✅ **输出契约**: e2e-test-result/v1/output.schema.json

#### 示例测试
- ✅ `login.spec.ts` - 登录流程（5 个用例）
- ✅ `home.spec.ts` - 首页功能（6 个用例）
- ✅ `accessibility.spec.ts` - 可访问性（6 个用例）

#### 知识库
- ✅ `pitfalls.md` - 7 个常见坑点
- ✅ `patterns.md` - 8 个可复用模式

#### 工具脚本
- ✅ `build.sh` - Linux/Mac 构建脚本
- ✅ `build.bat` - Windows 构建脚本
- ✅ `playwright.config.ts` - 生产级配置

#### 文档
- ✅ `README.md` - 完整使用指南
- ✅ `QUICKSTART.md` - 5 分钟快速开始
- ✅ `CHANGELOG.md` - 本更新日志

#### Claude Code 适配
- ✅ `cli/claude/skills/e2e-runner.md` - Skill MD 版本
- ✅ `cli/claude/agents/e2e-test-executor.md` - Agent MD 版本

### 技术规格

- **浏览器支持**: Chromium, Firefox, WebKit
- **并行能力**: 最多 16 workers
- **重试机制**: 可配置 0-5 次
- **超时控制**: 5s - 120s
- **报告格式**: HTML, JSON, JUnit
- **证据采集**: 截图、视频、trace

### 门禁标准

| 优先级 | 通过率要求 | 失败处理 |
|--------|-----------|---------|
| P0 | 100% | 立即 FAIL |
| P1 | ≥ 90% | CONDITIONAL_PASS |
| P2 | ≥ 80% | PASS（记录风险） |

### 已知限制

- 微信小程序需要单独的 miniprogram-automator（不在此镜像）
- 视频录制会增加 20-30% 的执行时间
- Trace 文件可能较大（每个失败用例 5-10 MB）

---

## 路线图

### v1.1.0 (计划中)
- [ ] 支持 Visual Regression Testing
- [ ] 集成 Lighthouse 性能测试
- [ ] 支持 Playwright Component Testing
- [ ] 增加更多示例测试（表单、上传、支付等）

### v1.2.0 (计划中)
- [ ] 支持多环境配置（dev/test/staging）
- [ ] 集成 Allure 报告
- [ ] 支持测试数据生成器
- [ ] 增加 API Mock 模板

### v2.0.0 (未来)
- [ ] 支持微信小程序（miniprogram-automator）
- [ ] 支持 React Native（Detox）
- [ ] 支持跨平台移动端（Appium）

---

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 贡献类型

- 🐛 Bug 修复
- ✨ 新功能
- 📝 文档改进
- ⚡ 性能优化
- 🧪 测试用例
- 🎨 代码风格

---

## 许可证

版权所有 © 2026 AI Constitution Project

---

## 致谢

- [Playwright](https://playwright.dev) - 强大的浏览器自动化框架
- [Docker](https://www.docker.com) - 容器化平台
- [axe-core](https://github.com/dequelabs/axe-core) - 可访问性测试引擎
