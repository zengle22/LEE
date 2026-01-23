# Reporting & Artifact Skill v1.0
# 报告与证据管理技能

## 概述

定义 E2E 测试报告的生成策略，包括机器可读和人类可读格式。
负责证据管理、错误归因分类、失败自动创建 Bug 契约。

## 技能标识

- **ID**: skill.test.reporting_artifact
- **名称**: Reporting & Artifact
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.e2e_test_executor
- agent.test.test_report_generator

---

## 1. 报告类型

### 1.1 JSON 报告 (机器可读)

```yaml
json_report:
  purpose: "给 Gate 和自动化工具使用"
  schema: "../contracts/e2e-report/v1/schema.json"
  path: "output/e2e/reports/{run_id}.json"

  required_fields:
    - report_id
    - run_id
    - manifest_id
    - summary (total, passed, failed, pass_rate)
    - verdict (PASS | FAIL | CONDITIONAL_PASS)
    - gate_checks

  example: |
    {
      "report_id": "E2E-RPT-20260113-ABC123",
      "run_id": "E2E-RUN-20260113-ABC123",
      "manifest_id": "MAN-2026-0001",
      "version": "v1.0.0-rc2",
      "platform": "chrome",
      "summary": {
        "total": 20,
        "passed": 18,
        "failed": 2,
        "skipped": 0,
        "pass_rate": 90.0,
        "p0_pass_rate": 100.0,
        "p1_pass_rate": 85.7
      },
      "gate_checks": [
        { "check_id": "p0_100_pass", "result": "pass" },
        { "check_id": "p1_90_pass", "result": "fail" },
        { "check_id": "overall_80_pass", "result": "pass" }
      ],
      "verdict": "CONDITIONAL_PASS",
      "recommendation": "fix_and_retest"
    }
```

### 1.2 Markdown 报告 (人类可读)

```yaml
markdown_report:
  purpose: "给人类阅读和分享"
  path: "output/e2e/reports/{run_id}.md"

  template: |
    # E2E 测试报告

    **运行 ID**: {run_id}
    **版本**: {version}
    **平台**: {platform}
    **执行时间**: {started_at} - {ended_at}
    **总耗时**: {duration}

    ---

    ## 执行汇总

    | 指标 | 值 |
    |------|-----|
    | 总用例数 | {total} |
    | 通过 | {passed} ✅ |
    | 失败 | {failed} ❌ |
    | 跳过 | {skipped} ⏭️ |
    | 通过率 | {pass_rate}% |

    ### 按优先级统计

    | 优先级 | 总数 | 通过 | 失败 | 通过率 |
    |--------|------|------|------|--------|
    | P0 | {p0_total} | {p0_passed} | {p0_failed} | {p0_rate}% |
    | P1 | {p1_total} | {p1_passed} | {p1_failed} | {p1_rate}% |
    | P2 | {p2_total} | {p2_passed} | {p2_failed} | {p2_rate}% |

    ---

    ## 门禁检查

    | 检查项 | 要求 | 实际 | 结果 |
    |--------|------|------|------|
    | P0 用例 100% 通过 | 100% | {p0_rate}% | {p0_check} |
    | P1 用例 >= 90% 通过 | 90% | {p1_rate}% | {p1_check} |
    | 整体 >= 80% 通过 | 80% | {pass_rate}% | {overall_check} |

    **判定结果**: {verdict}

    ---

    ## 失败用例详情

    {#each failed_cases}
    ### ❌ {case_id}: {name}

    - **模块**: {module}
    - **优先级**: {priority}
    - **失败类型**: {failure_category}
    - **失败消息**: {failure_message}
    - **失败步骤**: 第 {failed_step} 步
    - **关联 Bug**: {bug_id}

    **截图**:
    ![失败截图]({screenshot})

    ---
    {/each}

    ## 不稳定用例 (Flaky)

    {#if flaky_cases.length > 0}
    | 用例 ID | 名称 | 重试次数 | 最终结果 |
    |---------|------|----------|----------|
    {#each flaky_cases}
    | {case_id} | {name} | {retry_count} | {final_status} |
    {/each}
    {/if}

    ---

    ## 自动创建的 Bug

    {#each bugs_auto_created}
    - **{bug_id}**: {title} ({severity})
    {/each}

    ---

    ## 产物归档

    - [JSON 报告]({json_report_path})
    - [截图目录]({screenshots_dir})
    - [视频目录]({videos_dir})
    - [Trace 目录]({traces_dir})

    ---

    *报告生成时间: {generated_at}*
```

### 1.3 HTML 报告 (可交互)

```yaml
html_report:
  purpose: "可视化、可交互的报告"
  path: "output/e2e/reports/{run_id}.html"

  features:
    - "用例列表可筛选"
    - "失败用例可展开详情"
    - "截图可放大查看"
    - "视频可直接播放"
    - "趋势图表展示"

  generator: "playwright-html-reporter"  # 或自定义模板
```

---

## 2. 证据管理

### 2.1 证据目录结构

```yaml
evidence_structure:
  root: "output/e2e/evidence/{run_id}/"

  directories:
    screenshots:
      path: "screenshots/"
      naming: "{case_id}-{step}-{timestamp}.png"

    videos:
      path: "videos/"
      naming: "{case_id}.webm"
      retention:
        on_pass: false
        on_failure: true

    traces:
      path: "traces/"
      naming: "{case_id}.zip"
      viewer: "npx playwright show-trace {path}"

    logs:
      path: "logs/"
      files:
        - "console/{case_id}.json"
        - "network/{case_id}.json"

    dom_snapshots:
      path: "dom/"
      naming: "{case_id}-{step}.html"
```

### 2.2 证据采集策略

```yaml
capture_strategy:
  screenshots:
    on_failure: true        # 必须
    on_assertion: true      # 推荐
    on_step_complete: false # 可选
    on_page_navigate: false # 可选

  video:
    always_record: true
    keep_on_pass: false
    keep_on_failure: true
    format: "webm"

  trace:
    enabled: true
    on_first_retry: true

  logs:
    console:
      levels: ["error", "warning", "log"]
    network:
      include_response_body: true
      max_body_size: 10240
```

### 2.3 证据归档

```yaml
archiving:
  # 运行结束后归档
  on_run_complete:
    compress: true
    format: "zip"
    path: "output/e2e/archives/{run_id}.zip"

  # 保留策略
  retention:
    pass_runs: "7d"      # 通过的运行保留 7 天
    fail_runs: "30d"     # 失败的运行保留 30 天
    flaky_runs: "14d"    # 不稳定的运行保留 14 天

  # 上传到存储
  upload:
    enabled: true
    destination: "s3://e2e-evidence/{project}/{date}/"
    on_failure_only: false
```

---

## 3. 错误归因分类

### 3.1 失败分类

```yaml
failure_classification:
  categories:
    assertion_failed:
      code: "ASSERT_FAIL"
      description: "断言失败，实际结果与预期不符"
      likely_cause: "功能 Bug 或需求变更"
      action: "创建 Bug"

    element_not_found:
      code: "ELEM_NOT_FOUND"
      description: "无法找到目标元素"
      likely_cause: "选择器变化或页面结构调整"
      action: "检查选择器，可能需要更新 Page Object"

    timeout:
      code: "TIMEOUT"
      description: "操作超时"
      likely_cause: "页面加载慢或条件未满足"
      action: "检查环境性能，可能需要调整超时"

    network_error:
      code: "NETWORK_ERR"
      description: "网络请求失败"
      likely_cause: "后端服务问题或网络不稳定"
      action: "检查后端日志"

    script_error:
      code: "SCRIPT_ERR"
      description: "页面 JavaScript 错误"
      likely_cause: "前端代码 Bug"
      action: "创建前端 Bug"

    environment_error:
      code: "ENV_ERR"
      description: "测试环境问题"
      likely_cause: "环境配置或服务不可用"
      action: "检查环境，不创建 Bug"

    test_code_error:
      code: "TEST_ERR"
      description: "测试代码本身的错误"
      likely_cause: "测试脚本 Bug"
      action: "修复测试代码"

  auto_classification:
    rules:
      - pattern: "TimeoutError: waiting for"
        category: "timeout"

      - pattern: "Element not found"
        category: "element_not_found"

      - pattern: "net::ERR_"
        category: "network_error"

      - pattern: "Uncaught Error:"
        category: "script_error"

      - pattern: "Expected.*Received"
        category: "assertion_failed"
```

---

## 4. 失败自动创建 Bug

### 4.1 Bug 契约自动生成

```yaml
auto_bug_creation:
  enabled: true

  conditions:
    - "failure.category in ['assertion_failed', 'element_not_found', 'script_error']"
    - "failure.category != 'environment_error'"
    - "failure.category != 'test_code_error'"

  bug_template:
    bug_id: "BUG-{timestamp}"
    title: "[E2E] {case_name} - {failure_summary}"
    severity: "{mapped_from_priority}"  # P0→P0, P1→P1, P2→P2
    type: "functional"
    status: "new"

    detected_in:
      version: "{test_version}"
      environment: "test"
      test_case_id: "{case_id}"
      e2e_run_id: "{run_id}"

    repro:
      preconditions: "{from_case_preconditions}"
      steps: "{from_case_steps_until_failure}"
      expected: "{from_assertion_expected}"
      actual: "{captured_actual}"
      reproducible: "once"  # E2E 失败默认标记 once

    evidence:
      screenshots: ["{failure_screenshot}"]
      video: "{case_video}"
      logs:
        - trace_id: "{trace_id}"
          log_snippet: "{console_errors}"
      network: "{network_log_path}"

    ownership:
      reporter_agent: "agent.test.e2e_test_executor"

  output:
    path: "bugs/BUG-{timestamp}.yaml"
    link_to_report: true

  severity_mapping:
    P0: "P0"  # 核心链路失败
    P1: "P1"  # 重要功能失败
    P2: "P2"  # 次要功能失败
```

---

## 5. 趋势报告

```yaml
trend_reporting:
  metrics:
    - pass_rate_over_time
    - failure_by_category
    - flaky_test_rate
    - avg_execution_time

  aggregation:
    daily:
      path: "output/e2e/trends/daily-{date}.json"
    weekly:
      path: "output/e2e/trends/weekly-{week}.json"

  alerts:
    - condition: "pass_rate < 80"
      severity: "warning"
      notify: ["qa-team"]

    - condition: "p0_failures > 0"
      severity: "critical"
      notify: ["qa-team", "dev-team"]

    - condition: "flaky_rate > 10"
      severity: "warning"
      notify: ["qa-team"]
```

---

## 6. 最佳实践

```yaml
best_practices:
  reporting:
    - "JSON 报告用于自动化集成"
    - "Markdown 报告用于 PR 评论"
    - "HTML 报告用于详细分析"

  evidence:
    - "失败必须有截图"
    - "失败必须有视频"
    - "保留足够的日志上下文"

  bug_creation:
    - "自动创建但人工确认"
    - "包含完整复现信息"
    - "附带所有相关证据"

  retention:
    - "定期清理旧的证据"
    - "失败证据保留更长"
    - "归档重要的历史记录"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
