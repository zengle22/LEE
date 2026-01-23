# /execution-report 命令

生成 Phase 执行报告 (人类可读的 Markdown 格式)

## 用途

将 AI 执行日志转换为人类可读的 Markdown 报告，包含：
- 执行摘要 (总耗时、步骤数、成功率)
- 执行时间线
- 错误信息高亮
- 各步骤状态

## 使用方式

```
/execution-report [phase-dir]
```

## 参数

| 参数 | 说明 | 必填 |
|------|------|------|
| phase-dir | Phase 目录路径 | 否 (默认当前目录) |

## 示例

```bash
# 生成当前 Phase 的执行报告
/execution-report

# 生成指定 Phase 的执行报告
/execution-report ./project/AI跑步教练/dev/phase7
```

## 底层命令

```bash
python -m orchestrator trace <phase-dir> --format markdown
```

## 输出

报告生成到: `<phase-dir>/.workflow/traces/report_{run_id}.md`

## 报告内容示例

```markdown
# Execution Trace Report

**Run ID**: RUN-20260111-113533
**Generated At**: 2026-01-11T14:05:18

---

## Summary

| Metric | Value |
|--------|-------|
| Total Spans | 13 |
| Total Duration | 3185840ms |
| Errors | 3 |

## Timeline

- ✅ **step.p07_04_implementation** - 377ms
- ❌ **step.p07_04_implementation** - 720143ms
  - Error: Output not found
- ✅ **step.p07_05_unit_tests** - 182152ms
```

## 相关命令

- `/acceptance` - 运行 Phase 验收
- `/status` - 查看工作流状态

## 技能引用

`skill.common.generate_execution_report`
