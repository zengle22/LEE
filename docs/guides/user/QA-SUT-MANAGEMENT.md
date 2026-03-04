# QA 测试环境管理方案

## 概述

本文档描述 LEE 框架中 QA 测试环境（SUT - System Under Test）的管理方案，包括环境配置、URL 解析、运行时管理等核心功能。

---

## 背景

在 QA 测试执行过程中，需要针对不同的测试环境（local、test、staging、prod）运行测试用例。每个环境有不同的 URL、认证信息等配置。原有实现存在以下问题：

1. **URL 硬编码**：环境 URL 分散在代码和配置中，难以统一管理
2. **优先级不明确**：CLI 参数、配置文件、环境默认值的关系不清晰
3. **扩展性不足**：只支持 Web 类型，不支持 API、移动端等不同类型的被测系统

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        QA 测试环境管理架构                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐                                                 │
│   │  CLI Commands   │  qa sut init/show/list/set/url                  │
│   └────────┬────────┘                                                 │
│            │                                                            │
│            ▼                                                            │
│   ┌─────────────────────────────────────────────────────────────────┐ │
│   │                    SUTConfigLoader                               │ │
│   │  - 从 .project/dirs.yaml 读取 tests_dir                         │ │
│   │  - 配置持久化到 tests/runtime/{env}/sut.yaml                    │ │
│   └─────────────────────────────────────────────────────────────────┘ │
│            │                                                            │
│            ▼                                                            │
│   ┌─────────────────┐    ┌─────────────────┐                         │
│   │   SUTConfig     │    │   URLResolver   │                         │
│   │  - sut_type     │    │  - resolve()    │                         │
│   │  - base_url    │    │  - priority     │                         │
│   │  - auth_type   │    └─────────────────┘                         │
│   │  - extras      │                                                 │
│   └─────────────────┘                                                 │
│            │                                                            │
│            ▼                                                            │
│   ┌─────────────────────────────────────────────────────────────────┐ │
│   │                     运行时目录                                    │ │
│   │  {tests_dir}/runtime/{env}/sut.yaml                            │ │
│   └─────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `SUTType` | sut.py | 被测系统类型枚举 |
| `SUTConfig` | sut.py | 统一配置模型 |
| `URLResolver` | sut.py | URL 解析器 |
| `SUTConfigLoader` | sut.py | 配置加载/持久化 |
| `qa sut` CLI | sut.py | 命令行管理工具 |

---

## 被测系统类型

当前支持以下 SUT 类型：

```python
class SUTType(Enum):
    WEB = "web"           # Web 应用
    API = "api"           # REST API
    MOBILE = "mobile"     # 移动应用
    DESKTOP = "desktop"   # 桌面应用
    MICROSERVICE = "microservice"  # 微服务
    UNKNOWN = "unknown"
```

每种类型可以有不同的配置项，通过 `extras` 字段存储类型特定的扩展配置。

---

## URL 解析优先级

URL 解析遵循以下优先级（从高到低）：

```
1. CLI --base-url 参数（显式指定）
        │
        ▼
2. tests/runtime/{env}/sut.yaml 配置文件
        │
        ▼
3. 环境默认值
        │
        ▼
   local  → http://localhost:3000
   test   → http://localhost:3000
   staging → https://app-staging.example.com
   prod   → https://app.example.com
```

---

## 目录结构

### 项目配置

项目目录结构在 `.project/dirs.yaml` 中定义：

```yaml
# .project/dirs.yaml
version: '1.0'
project_name: calorie-tracker
directories:
  tests_dir:
    path: tests
    description: Generated test files
```

### 运行时配置

测试运行时配置存储在：

```
{project_root}/
└── {project_name}/           # 来自 dirs.yaml 的 project_name
    └── tests/
        └── runtime/
            ├── local/
            │   └── sut.yaml
            ├── test/
            │   └── sut.yaml
            ├── staging/
            │   └── sut.yaml
            └── prod/
                └── sut.yaml
```

### SUT 配置文件格式

```yaml
# tests/runtime/staging/sut.yaml
sut_type: web
name: staging-default
base_url: https://app-staging.example.com
base_path: ""
protocol: https
auth_type: null
enabled: true
extras: {}
metadata:
  owner: qa-team
  last_updated: "2026-03-04"
```

---

## 使用指南

### CLI 命令

#### 1. 初始化环境配置

```bash
# 初始化 staging 环境，使用自定义 URL
python -m lee qa sut init staging --base-url "https://myapp-staging.example.com"

# 初始化 API 类型环境
python -m lee qa sut init staging --sut-type api
```

#### 2. 查看环境配置

```bash
# 查看指定环境配置
python -m lee qa sut show staging

# 查看默认 URL（无配置文件时）
python -m lee qa sut show prod
```

#### 3. 解析 URL

```bash
# 解析环境 URL（优先配置文件 > 默认值）
python -m lee qa sut url staging    # https://app-staging.example.com

# 解析并显示（带显式覆盖）
python -m lee qa sut url prod --explicit-url "https://custom.example.com"
```

#### 4. 列出所有配置

```bash
# 列出所有已配置的环境
python -m lee qa sut list
```

#### 5. 设置环境配置

```bash
# 设置或更新环境配置
python -m lee qa sut set staging \
    --base-url "https://custom-staging.example.com" \
    --base-path "/app" \
    --protocol "https"
```

---

### 代码中使用

#### 1. 便捷函数

```python
from lee.qa.runner import resolve_sut_url

# 简单解析
url = resolve_sut_url("staging")
# 结果: https://app-staging.example.com

# 显式覆盖
url = resolve_sut_url("staging", explicit_url="https://custom.com")
# 结果: https://custom.com
```

#### 2. 配置加载器

```python
from pathlib import Path
from lee.qa.runner import SUTConfigLoader, SUTType

project_root = Path("E:/ai/LEE")
loader = SUTConfigLoader(project_root)

# 加载配置（不存在则返回 None）
config = loader.load("staging")
if config:
    print(config.base_url)

# 加载或创建默认配置
config = loader.load_or_create("staging", base_url="https://example.com")

# 保存配置
loader.save("staging", config)
```

#### 3. TestConfig 集成

```python
from lee.qa.runner import TestConfig, SUTType

# 不指定 base_url 时，自动从环境获取
config = TestConfig(
    scripts=[],
    environment="staging"
)
print(config.base_url)  # 自动解析为 https://app-staging.example.com

# 指定 base_url 时优先使用
config = TestConfig(
    scripts=[],
    environment="staging",
    base_url="https://custom.example.com"
)
print(config.base_url)  # https://custom.example.com

# 使用 SUTConfig 对象
from lee.qa.runner import SUTConfig
sut = SUTConfig(sut_type=SUTType.WEB, base_url="https://example.com")
config = TestConfig(scripts=[], sut_config=sut)
```

---

## test_runner 集成

`test_runner` CLI 已集成 SUT 配置，使用方式：

```bash
# 方式1：使用环境默认值
python -m lee test-runner run-e2e \
    --suite smoke \
    --env staging \
    --test-set ./test-cases.yaml \
    --out-dir ./output

# 方式2：显式指定 URL（覆盖环境配置）
python -m lee test-runner run-e2e \
    --suite smoke \
    --env staging \
    --base-url "https://custom.example.com" \
    --test-set ./test-cases.yaml \
    --out-dir ./output

# 方式3：使用配置文件
# 先创建配置
python -m lee qa sut init staging --base-url "https://app-staging.example.com"
# 然后运行测试（会自动读取配置）
python -m lee test-runner run-e2e \
    --suite smoke \
    --env staging \
    --test-set ./test-cases.yaml \
    --out-dir ./output
```

---

## 扩展指南

### 添加新的 SUT 类型

如需支持新的 SUT 类型（如 gRPC 服务），可以：

1. 在 `SUTType` 枚举中添加新类型
2. 在 `SUTConfig.extras` 字段中添加类型特定配置
3. 在 `URLResolver.resolve_with_config()` 中添加解析逻辑

示例：

```python
# 添加 gRPC 类型支持
class SUTType(Enum):
    GRPC = "grpc"

# 使用 extras 存储 gRPC 特定配置
config = SUTConfig(
    sut_type=SUTType.GRPC,
    base_url="localhost:50051",
    extras={
        "proto_file": "service.proto",
        "service_name": "UserService",
    }
)
```

### 添加新的环境

修改 `URLResolver.DEFAULT_URLS` 字典：

```python
class URLResolver:
    DEFAULT_URLS = {
        "local": "http://localhost:3000",
        "test": "http://localhost:3000",
        "staging": "https://app-staging.example.com",
        "prod": "https://app.example.com",
        # 添加新环境
        "demo": "https://demo.example.com",
    }
```

---

## 常见问题

### Q: 配置文件和默认值的优先级？

A: 配置文件优先级高于默认值。CLI `--base-url` 参数优先级最高。

### Q: 如何在 CI/CD 中使用？

A: 可以通过环境变量或配置文件预设：

```bash
# 使用环境变量（如果在 test_runner 中实现）
export STAGING_URL="https://ci-staging.example.com"
python -m lee qa sut set staging --base-url "$STAGING_URL"
```

### Q: 配置文件可以提交到 Git 吗？

A: 建议将 `tests/runtime/` 目录加入 `.gitignore`，因为这是运行时生成的配置。不同环境的配置应该通过环境变量或配置管理工具注入。

---

## 变更历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-03-04 | 初始版本：SUT 配置模块和 CLI 命令 |
