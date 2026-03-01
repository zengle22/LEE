# Test Runner 日志采集指南

## 概述

test_runner v0.3 新增了详细的调试日志功能，帮助 QA 团队诊断路径相关问题（如 BUG-2026-0049）。

## 日志级别

| 级别 | 说明 | 输出内容 |
|------|------|----------|
| INFO | 基本信息 | 启动信息、参数、找到的脚本数量 |
| PATH-DEBUG | 路径调试 | 路径查找过程、每次尝试的结果 |
| ERROR | 错误信息 | 错误详情、堆栈跟踪 |

## 使用方法

### 1. 控制台输出详细日志

```bash
# 使用 --verbose 或 -v 选项
test-runner run-e2e \
  --mode local \
  --verbose \
  --suite smoke \
  --env test \
  --test-set qa/test-runs/TR-xxx/tse-xxx/cases.yaml \
  --out-dir qa/test-runs/TR-xxx/tse-xxx/evidence/ \
  --report-json qa/test-runs/TR-xxx/report.json
```

### 2. 保存日志到文件

```bash
# 使用 --log-file 选项
test-runner run-e2e \
  --mode local \
  --log-file qa/test-runs/logs/test-runner.log \
  --suite smoke \
  --env test \
  --test-set qa/test-runs/TR-xxx/tse-xxx/cases.yaml \
  --out-dir qa/test-runs/TR-xxx/tse-xxx/evidence/ \
  --report-json qa/test-runs/TR-xxx/report.json
```

### 3. 同时使用详细日志和文件保存

```bash
# 同时使用 --verbose 和 --log-file
test-runner run-e2e \
  --mode local \
  --verbose \
  --log-file qa/test-runs/logs/debug-$(date +%Y%m%d-%H%M%S).log \
  --suite smoke \
  --env test \
  --test-set qa/test-runs/TR-xxx/tse-xxx/cases.yaml \
  --out-dir qa/test-runs/TR-xxx/tse-xxx/evidence/ \
  --report-json qa/test-runs/TR-xxx/report.json
```

## 日志输出示例

### INFO 级别

```
[INFO] test_runner 启动 - 模式：local
[INFO] 参数：suite=smoke, env=test, test_set=qa/test-runs/TR-xxx/tse-xxx/cases.yaml
[INFO] test_set_id: TS-V1.2-ONBOARDING
[INFO] 加载测试用例：开发者测试登录流程
[INFO] 找到 4 个测试脚本
```

### PATH-DEBUG 级别（--verbose 时输出）

```
[PATH-DEBUG] test_set_id: TS-V1.2-ONBOARDING
[PATH-DEBUG] out_dir: qa/test-runs/TR-xxx/tse-xxx/evidence
[PATH-DEBUG] test_data.paths: {'scripts': 'qa/test-runs/TR-xxx/tse-xxx/scripts/'}
[PATH-DEBUG] 使用 paths.scripts 配置：qa/test-runs/TR-xxx/tse-xxx/scripts
[PATH-DEBUG] 目录存在，找到脚本
[PATH-DEBUG] 最终脚本目录：qa/test-runs/TR-xxx/tse-xxx/scripts
[PATH-DEBUG] 目录存在：True
[PATH-DEBUG] 找到的脚本数量：4
[PATH-DEBUG]   - qa/test-runs/TR-xxx/tse-xxx/scripts/test_e2e_positive.spec.ts
[PATH-DEBUG]   - qa/test-runs/TR-xxx/tse-xxx/scripts/test_e2e_negative.spec.ts
[PATH-DEBUG]   - qa/test-runs/TR-xxx/tse-xxx/scripts/test_e2e_boundary.spec.ts
[PATH-DEBUG]   - qa/test-runs/TR-xxx/tse-xxx/scripts/test_e2e_exception.spec.ts
```

### 路径查找失败时的日志

```
[PATH-DEBUG] test_set_id: TS-V1.2-ONBOARDING
[PATH-DEBUG] out_dir: qa/test-runs/TR-xxx/tse-xxx/evidence
[PATH-DEBUG] test_data.paths: {}
[PATH-DEBUG] 回退到 out_dir.parent: qa/test-runs/TR-xxx/tse-xxx/scripts
[PATH-DEBUG] 尝试原始 test_set_id 路径：qa/test-runs/TR-xxx/tse-TS-V1.2-ONBOARDING/scripts
[PATH-DEBUG] 找到原始路径目录
[PATH-DEBUG] 最终脚本目录：qa/test-runs/TR-xxx/tse-TS-V1.2-ONBOARDING/scripts
[PATH-DEBUG] 目录存在：True
[PATH-DEBUG] 找到的脚本数量：4
```

## 日志分析流程

### 步骤 1：确认 test_set_id

查看日志中的 test_set_id 值：
```
[INFO] test_set_id: TS-V1.2-ONBOARDING
```

### 步骤 2：检查路径查找优先级

日志会按优先级顺序显示每次尝试：
```
[PATH-DEBUG] 使用 paths.scripts 配置：...         ← 优先级 1
[PATH-DEBUG] 回退到 out_dir.parent: ...            ← 优先级 2
[PATH-DEBUG] 尝试原始 test_set_id 路径：...         ← 优先级 3
[PATH-DEBUG] 尝试 slugified 路径：...              ← 优先级 4
```

### 步骤 3：确认最终选择的目录

```
[PATH-DEBUG] 最终脚本目录：qa/test-runs/TR-xxx/tse-xxx/scripts
[PATH-DEBUG] 目录存在：True
```

### 步骤 4：检查找到的脚本

```
[PATH-DEBUG] 找到的脚本数量：4
[PATH-DEBUG]   - .../test_e2e_positive.spec.ts
[PATH-DEBUG]   - .../test_e2e_negative.spec.ts
...
```

## 常见问题诊断

### 问题 1：找不到脚本

**日志表现**：
```
[PATH-DEBUG] 脚本目录不存在：qa/test-runs/TR-xxx/tse-xxx/scripts
[PATH-DEBUG] 父目录内容：[...]
[WARNING] 脚本目录不存在：qa/test-runs/TR-xxx/tse-xxx/scripts
```

**可能原因**：
- 脚本生成步骤失败
- 路径配置不正确
- test_set_id 与实际目录名不匹配

**解决方案**：
1. 检查 S4 步骤（s4_1_translate_scripts）是否成功
2. 检查 workflow.yaml 中的路径模板
3. 对比实际目录结构和 test_set_id

### 问题 2：路径不匹配

**日志表现**：
```
[PATH-DEBUG] 尝试原始 test_set_id 路径：qa/test-runs/TR-xxx/tse-TS-V1.2-ONBOARDING/scripts
[PATH-DEBUG] 找到原始路径目录
```

**说明**：双路径兼容策略生效，自动找到了正确的目录。

**后续行动**：
1. 记录此情况并报告给开发团队
2. 检查工作流模板一致性
3. 考虑统一路径命名规则

## 日志文件位置推荐

```bash
# 按测试运行组织日志
qa/test-runs/
└── TR-2026-03-01-XXX/
    ├── logs/
    │   ├── test-runner.log          # 主日志
    │   ├── path-debug.log           # 路径调试日志
    │   └── error-classification.log # 错误分类日志
    ├── tse-XXX/
    │   ├── scripts/
    │   ├── evidence/
    │   └── cases.yaml
    └── report.json
```

## 自动化日志采集

可以在 CI/CD 流程中自动添加日志采集：

```yaml
# GitHub Actions 示例
- name: Run E2E Tests
  run: |
    test-runner run-e2e \
      --mode local \
      --verbose \
      --log-file qa/test-runs/logs/test-runner-${{ github.run_id }}.log \
      --suite ${{ matrix.suite }} \
      --env test \
      --test-set qa/test-runs/test-set.yaml \
      --out-dir qa/test-runs/output/ \
      --report-json qa/test-runs/report.json

- name: Upload Logs
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-logs
    path: qa/test-runs/logs/
```

## 相关 Bug

- BUG-2026-0049: workflow 路径模板与实际目录不匹配
- BUG-2026-0048: test_runner 回退到错误的 scripts 路径
- BUG-2026-0047: 脚本翻译器没收到测试用例数据

## 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.3 | 2026-03-01 | 新增 --log-file 和 --verbose 选项 |
| v0.2 | 2026-02-28 | 新增错误分类功能 |
| v0.1 | 2026-02-25 | 初始版本 |
