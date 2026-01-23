---
name: e2e-docker-runner
description: |
  E2E Docker 执行器 - 在 Claude Code 中运行 Docker 化的 Playwright 测试。

  这个 skill 封装了 Docker 命令执行，将输出重定向到文件，解决 Bash tool 输出捕获问题。

  **适用场景**:
  - 需要在 Claude Code 对话中执行 E2E 测试
  - 需要获取完整的测试结果和报告
  - 需要 Docker 隔离环境

  **工作原理**:
  1. 调用 wrapper 脚本执行 Docker 命令
  2. 脚本将所有输出保存到文件
  3. Agent 读取结果文件获取测试状态

  **输出位置**: `output/test-result.txt`

model: inherit
color: cyan
tools:
  - Bash
  - Read
---

# E2E Docker Runner Skill

在 Claude Code 中执行 Docker 化的 E2E 测试。

## 核心原理

**问题**: Bash tool 执行 `docker run` 时无法捕获容器输出

**解决方案**:
1. 使用 wrapper 脚本执行 Docker 命令
2. 脚本将输出重定向到文件 (`output/test-output.raw`)
3. 脚本将结果摘要保存到 (`output/test-result.txt`)
4. Agent 读取文件获取测试结果

---

## 使用方法

### Windows 环境

```powershell
# 进入测试目录
cd E:\ai\ai-constitution\git\ai-marathon-coach-front\test-cases

# 执行测试（使用 PowerShell wrapper）
powershell -ExecutionPolicy Bypass -File "E:\ai\ai-constitution\ai-spec\specs\common\skills\e2e-runner\v1\scripts\run-e2e-docker.ps1"
```

### Linux/Mac 环境

```bash
# 进入测试目录
cd /path/to/test-cases

# 赋予执行权限
chmod +x ai-spec/specs/common/skills/e2e-runner/v1/scripts/run-e2e-docker.sh

# 执行测试
./ai-spec/specs/common/skills/e2e-runner/v1/scripts/run-e2e-docker.sh
```

---

## Agent 执行流程

当 Agent 调用此 skill 时：

### Step 1: 执行 wrapper 脚本

```bash
cd E:\ai\ai-constitution\git\ai-marathon-coach-front\test-cases
powershell -ExecutionPolicy Bypass -File "E:\ai\ai-constitution\ai-spec\specs\common\skills\e2e-runner\v1\scripts\run-e2e-docker.ps1"
```

### Step 2: 读取结果文件

```bash
# 读取结果摘要
cat output/test-result.txt

# 读取完整输出
cat output/test-output.raw

# 查看执行日志
cat output/docker-execution.log
```

### Step 3: 解析结果

结果文件格式 (`output/test-result.txt`):

```
E2E_TEST_EXIT_CODE=0
E2E_TEST_TIMESTAMP=2026-01-16T10:30:45Z
E2E_TEST_SPEC=e2e/quick-test.spec.ts
E2E_BASE_URL=http://localhost:3002
E2E_TEST_STATUS=PASS
```

### Step 4: 收集证据

```bash
# 检查失败的测试证据
ls -la output/test-results/

# 查看截图（如果有失败）
file output/test-results/*/*.png

# 查看 trace（用于调试）
file output/test-results/*/trace.zip
```

---

## 判定逻辑

```python
import os

# 读取结果文件
with open('output/test-result.txt', 'r') as f:
    result = dict(line.strip().split('=', 1) for line in f)

exit_code = int(result['E2E_TEST_EXIT_CODE'])
status = result['E2E_TEST_STATUS']

# 判定
if status == 'PASS':
    print('✅ 测试通过')
elif exit_code != 0:
    print(f'❌ 测试失败 (退出码: {exit_code})')
    # 读取详细输出
    with open('output/test-output.raw', 'r') as f:
        print(f.read())
```

---

## 环境变量

Wrapper 脚本支持以下环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WORK_DIR` | 当前目录 | 工作目录（测试套件位置）|
| `TEST_SPEC` | `e2e/quick-test.spec.ts` | 测试文件路径 |
| `BASE_URL` | `http://localhost:3002` | 被测应用 URL |
| `API_URL` | `http://localhost:8081/v1` | 后端 API URL |
| `DOCKER_IMAGE` | `e2e-runner:latest` | Docker 镜像名称 |

---

## 示例对话

### 用户: 运行首页的 E2E 测试

**Agent 执行**:

```bash
cd E:\ai\ai-constitution\git\ai-marathon-coach-front\test-cases
powershell -ExecutionPolicy Bypass -File "E:\ai\ai-constitution\ai-spec\specs\common\skills\e2e-runner\v1\scripts\run-e2e-docker.ps1"
```

**Agent 读取结果**:

```bash
cat output/test-result.txt
```

**Agent 输出**:

```
✅ E2E 测试执行完成

状态: PASS
退出码: 0
测试用例: e2e/quick-test.spec.ts
执行时间: 2026-01-16T10:30:45Z

报告:
- HTML: output/playwright-report/index.html
- 原始输出: output/test-output.raw
- 执行日志: output/docker-execution.log
```

---

## 错误处理

### 错误 1: Docker 镜像不存在

**症状**: `ERROR: Docker image not found`

**解决方案**:

```bash
cd ai-spec/specs/common/skills/e2e-runner/v1/docker
docker build -t e2e-runner:latest .
```

### 错误 2: 测试文件不存在

**症状**: `ERROR: Test file not found`

**解决方案**:

```bash
# 检查测试文件路径
ls e2e/quick-test.spec.ts

# 或指定正确的测试文件
TEST_SPEC=e2e/demo/example.spec.ts ./run-e2e-docker.sh
```

### 错误 3: 网络连接失败

**症状**: 测试超时或无法访问应用

**解决方案**:

```bash
# 验证应用是否运行
curl http://localhost:3002

# 检查 Docker 容器
docker ps | grep marathon

# 使用 host.docker.internal（Mac/Windows）
BASE_URL=http://host.docker.internal:3002 ./run-e2e-docker.sh
```

---

## 优势

✅ **完整输出捕获** - 所有测试输出都保存到文件
✅ **结果可追溯** - 保留原始日志和结果文件
✅ **Agent 可读** - 结构化的结果文件便于解析
✅ **Docker 隔离** - 使用容器化测试环境
✅ **证据收集** - 自动收集截图、视频、trace

---

## 相比直接执行的优势

| 方式 | 输出捕获 | 结果解析 | Agent 集成 |
|------|---------|---------|-----------|
| 直接 `docker run` | ❌ 不可靠 | ❌ 需手动 | ❌ 困难 |
| Wrapper 脚本 | ✅ 完整 | ✅ 自动化 | ✅ 容易 |

---

## 相关文档

- **Agent 规范**: `ai-spec/cli/claude/agents/e2e-test-executor.md`
- **E2E Runner Skill**: `ai-spec/cli/claude/skills/e2e-runner.md`
- **Docker 镜像**: `ai-spec/specs/common/skills/e2e-runner/v1/docker/`
