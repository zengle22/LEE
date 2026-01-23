# E2E Runner - 目录结构

```
e2e-runner/v1/
├── skill.yaml                          # Skill 规范（权威来源）
├── README.md                           # 完整使用指南
├── QUICKSTART.md                       # 5 分钟快速开始
├── CHANGELOG.md                        # 版本更新日志
├── SUMMARY.md                          # 项目完成总结
│
├── docker/                             # Docker 镜像配置
│   ├── Dockerfile                      # 基于 Playwright v1.41.0
│   ├── package.json                    # Node.js 依赖
│   ├── playwright.config.ts            # Playwright 配置
│   ├── build.sh                        # Linux/Mac 构建脚本
│   ├── build.bat                       # Windows 构建脚本
│   └── .gitignore                      # Git 忽略规则
│
├── examples/                           # 示例测试
│   ├── EXAMPLES.md                     # 测试用例示例库（40+ 示例）
│   └── smoke-test/                     # 冒烟测试套件
│       ├── login.spec.ts               # 登录流程（5 个用例）
│       ├── home.spec.ts                # 首页功能（6 个用例）
│       └── accessibility.spec.ts       # 可访问性（6 个用例）
│
└── knowledge/                          # 知识库
    ├── pitfalls.md                     # 7 个常见坑点
    └── patterns.md                     # 8 个可复用模式
```

## 文件说明

### 核心配置（4 个文件）

1. **skill.yaml** - Skill 规范定义
   - 定义输入输出契约
   - 运行时配置
   - 约束声明
   - 测试钩子

2. **docker/Dockerfile** - Docker 镜像
   - 基于 `mcr.microsoft.com/playwright:v1.41.0-focal`
   - 预装 Node.js 18+ 和 Playwright
   - 健康检查
   - 生产优化

3. **docker/package.json** - Node.js 依赖
   - `@playwright/test` ^1.41.0
   - `@axe-core/playwright` ^4.8.3（可访问性）
   - 测试脚本

4. **docker/playwright.config.ts** - Playwright 配置
   - 并行执行（4 workers）
   - 失败重试（2 次）
   - 报告器（HTML + JSON + JUnit）
   - 截图/视频/trace 配置

### 文档（6 个文件）

1. **README.md** - 完整使用指南
   - 快速开始
   - 输入输出定义
   - 测试用例示例
   - 调试技巧
   - CI 集成
   - 常见问题

2. **QUICKSTART.md** - 5 分钟上手
   - 5 个步骤快速开始
   - 核心规则
   - CI 配置
   - FAQ

3. **CHANGELOG.md** - 版本更新日志
   - v1.0.0 新增内容
   - 路线图（v1.1/v1.2/v2.0）
   - 贡献指南

4. **SUMMARY.md** - 项目完成总结
   - 文件清单
   - 技术交付
   - 验收标准
   - 下一步行动

5. **examples/EXAMPLES.md** - 测试用例示例库
   - 40+ 真实场景示例
   - 登录、表单、列表、文件上传
   - API Mock、响应式、错误处理
   - 可访问性、WebSocket、Service Worker

6. **knowledge/pitfalls.md** - 常见坑点
   - 选择器不稳定
   - 异步等待不充分
   - 测试数据污染
   - 时区/语言差异
   - 网络请求未 Mock
   - 忽略控制台错误
   - 失败时缺失证据

7. **knowledge/patterns.md** - 可复用模式
   - Page Object Model
   - Fixture 封装认证
   - API Mock 统一管理
   - 自定义断言
   - 并行测试隔离
   - 测试优先级标记
   - Visual Regression Testing
   - 条件跳过测试

### 示例测试（3 个文件）

1. **examples/smoke-test/login.spec.ts**
   - 正常登录（P0）
   - 错误密码（P1）
   - 空字段验证（P1）
   - 记住密码（P2）
   - 键盘操作（P1）

2. **examples/smoke-test/home.spec.ts**
   - 页面加载（P0）
   - 点击跳转（P0）
   - 空数据（P1）
   - 加载失败（P1）
   - 骨架屏（P2）
   - 导航（P1）

3. **examples/smoke-test/accessibility.spec.ts**
   - WCAG 2.1 AA 检查（P1）
   - 键盘导航（P1）
   - ARIA 标签（P2）
   - 焦点管理（P2）
   - 颜色对比（P1）

### 工具脚本（2 个文件）

1. **docker/build.sh** - Linux/Mac 构建脚本
   - 检查 Docker
   - 构建镜像
   - 验证镜像
   - 显示使用方法

2. **docker/build.bat** - Windows 构建脚本
   - 检查 Docker
   - 构建镜像
   - 验证镜像
   - 显示使用方法

---

## 相关文件（项目其他位置）

### Agent 规范

```
ai-spec/specs/common/agents/e2e-test-executor/v1/
└── agent.yaml                          # Agent 规范
```

### 契约定义

```
ai-spec/specs/common/contracts/
├── e2e-test-input/v1/
│   └── input.schema.json               # 输入契约
└── e2e-test-result/v1/
    └── output.schema.json              # 输出契约
```

### Claude Code 适配

```
ai-spec/cli/claude/
├── skills/
│   └── e2e-runner.md                   # Skill MD 版本
└── agents/
    └── e2e-test-executor.md            # Agent MD 版本
```

---

## 文件统计

| 类型 | 数量 | 说明 |
|------|------|------|
| 配置文件 | 4 | skill.yaml, Dockerfile, package.json, playwright.config.ts |
| 文档文件 | 7 | README, QUICKSTART, CHANGELOG, SUMMARY, EXAMPLES, pitfalls, patterns |
| 测试文件 | 3 | login.spec.ts, home.spec.ts, accessibility.spec.ts |
| 脚本文件 | 2 | build.sh, build.bat |
| 契约文件 | 2 | input.schema.json, output.schema.json |
| Agent 文件 | 1 | agent.yaml |
| Claude MD | 2 | e2e-runner.md, e2e-test-executor.md |
| **总计** | **21** | |

---

## 代码行数统计（估算）

| 文件 | 行数 | 说明 |
|------|------|------|
| skill.yaml | ~150 | Skill 规范 |
| agent.yaml | ~180 | Agent 规范 |
| Dockerfile | ~30 | Docker 镜像 |
| playwright.config.ts | ~80 | Playwright 配置 |
| 示例测试（3 个） | ~300 | 17 个测试用例 |
| 文档（7 个） | ~2000 | 完整文档 |
| 契约（2 个） | ~300 | JSON Schema |
| Claude MD（2 个） | ~600 | MD 适配 |
| **总计** | **~3640** | |

---

## 目录大小（估算）

- Docker 镜像: ~1.5 GB（包含浏览器）
- 源代码: ~500 KB
- 文档: ~200 KB
- 示例测试: ~50 KB

---

✅ 完整的目录结构，所有文件已创建并组织完毕。
