# LEE 审计与日志使用指南

> v3.2 — 事件溯源日志 + LLM 元数据增强

## 概览

LEE 提供两层日志能力：

| 层级 | 存储 | 用途 |
|---|---|---|
| **SQLite `task_executions`** | `.workflow/lee.db` | 步骤级：input/output、状态、耗时 |
| **EventLog JSONL** | `.workflow/events.jsonl` | 事件级：完整时间线、审计报告 |

执行一次工作流后，两者自动产生，无需额外配置。

---

## 1. 事件日志文件（events.jsonl）

### 位置

```
{project_root}/.workflow/events.jsonl
```

### 事件类型

| 事件 | 触发点 | 含义 |
|---|---|---|
| `run_created` | `create_workflow` | 工作流实例被创建 |
| `run_started` | `run_until_blocked` 开始 | 开始批量执行步骤 |
| `run_completed` | `run_until_blocked` 结束 | 所有步骤完成 |
| `run_failed` | `run_until_blocked` 结束 | 执行失败 |
| `step_started` | `run_step` 内 | 某个步骤开始执行 |
| `step_completed` | Agent/Claude Code 步骤成功 | 步骤完成，含 outputs_hash |
| `step_failed` | 步骤异常 | 步骤失败，含 error 信息 |
| `gate_triggered` | Human Gate 暂停 | 工作流等待人工审批 |
| `gate_approved` | `approve_gate` | 门禁被批准 |
| `gate_rejected` | `reject_gate` | 门禁被拒绝 |

### 事件格式

每行一个 JSON 对象，追加写入：

```json
{
  "event_id": "EVT-20260213093045123456-0001",
  "event_type": "step_completed",
  "timestamp": "2026-02-13T09:30:45.123456",
  "run_id": "RUN-20260213-0930-abc1",
  "step_id": "implement_backend",
  "agent_id": "agent.dev.go-backend-engineer",
  "actor": "agent",
  "data": {"outputs": ["src/api/handler.go", "src/api/router.go"]},
  "outputs_hash": "a1b2c3d4e5f67890"
}
```

---

## 2. Python API 使用

### 查询事件

```python
from lee.orchestrator.storage.event_log import EventLog, EventType

# 指定项目目录和 run_id
el = EventLog("/path/to/project", run_id="RUN-xxx")

# 查询所有事件
all_events = el.get_events()

# 按类型过滤
failures = el.get_events(event_type=EventType.STEP_FAILED)

# 按步骤过滤
step_timeline = el.get_step_timeline("implement_backend")
# 返回该步骤的 started → completed/failed 时间线

# 按时间过滤
recent = el.get_events(since="2026-02-13T09:00:00")

# 限制数量
latest_5 = el.get_events(limit=5)
```

### 统计信息

```python
stats = el.get_statistics()
```

返回：

```python
{
    "total_events": 42,
    "event_counts": {
        "run_created": 1,
        "step_started": 8,
        "step_completed": 7,
        "step_failed": 1,
        "gate_triggered": 2,
        "gate_approved": 2
    },
    "step_durations": {
        "generate_prd": 12.5,        # 秒
        "implement_backend": 45.2,
        "code_review": 8.7
    },
    "gate_wait_times": {
        "prd_review_gate": 3600.0,   # 秒（等待人工审批）
        "code_review_gate": 1800.0
    },
    "error_count": 1,
    "retry_count": 0
}
```

### 导出审计报告

```python
report_path = el.export_audit_report()
# 默认输出到: {project}/.workflow/audit_report_{run_id}.json

# 或指定路径
report_path = el.export_audit_report("/tmp/audit.json")
```

审计报告包含完整的事件列表 + 统计信息，可直接用于合规审查。

---

## 3. LLM 元数据

每个 Agent 步骤完成后，`TaskExecution.output_data` 中包含 `llm_meta` 字段：

```python
# 从 SQLite 查询
executions = await store.get_task_executions(workflow_id)
for ex in executions:
    if ex.output_data and "llm_meta" in ex.output_data:
        meta = ex.output_data["llm_meta"]
        print(f"Model:    {meta['model']}")
        print(f"Tokens:   {meta['input_tokens']} in / {meta['output_tokens']} out")
        print(f"Duration: {meta['duration_seconds']}s")
        print(f"Stop:     {meta['stop_reason']}")
```

`llm_meta` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | str | 实际使用的模型（如 `gpt-4-turbo`） |
| `provider` | str | 提供商（`openai`、`zhipu`、`custom`） |
| `tokens_used` | int | 总 token 数（input + output） |
| `input_tokens` | int | Prompt token 消耗 |
| `output_tokens` | int | Completion token 消耗 |
| `duration_seconds` | float | API 调用耗时（秒） |
| `stop_reason` | str | 停止原因（`stop`、`length`、`content_filter`） |

---

## 4. 命令行快速查看

### 查看原始事件流

```bash
# 最近 20 条事件
tail -20 .workflow/events.jsonl | python -m json.tool --no-ensure-ascii

# 只看失败事件
grep '"step_failed"' .workflow/events.jsonl | python -m json.tool

# 只看门禁事件
grep '"gate_' .workflow/events.jsonl | python -m json.tool

# 统计各事件类型数量
cat .workflow/events.jsonl | python -c "
import sys, json, collections
c = collections.Counter()
for line in sys.stdin:
    if line.strip():
        c[json.loads(line)['event_type']] += 1
for k, v in c.most_common():
    print(f'  {k:25s} {v}')
"
```

### 导出审计报告

```bash
python -c "
from lee.orchestrator.storage.event_log import EventLog
el = EventLog('.', run_id='YOUR_RUN_ID')
path = el.export_audit_report()
print(f'Report exported to: {path}')
"
```

---

## 5. 数据流架构

```
Orchestrator.run_step()
    │
    ├── EventLog.log(STEP_STARTED)     ──→  .workflow/events.jsonl
    │
    ├── StepRunnerMixin._run_agent_step()
    │       │
    │       ├── LLMExecutor.execute()
    │       │       └── _call_llm()  ──→  返回 {content, model, tokens, stop_reason}
    │       │
    │       ├── output_data.llm_meta   ──→  SQLite task_executions.output_data
    │       │
    │       ├── EventLog.log(STEP_COMPLETED, outputs_hash)
    │       │
    │       └── EvidenceCollector      ──→  evidence/{run_id}/
    │
    └── EventLog.log(STEP_FAILED)      ──→  .workflow/events.jsonl (异常时)
```

---

## 6. 注意事项

- **events.jsonl 是追加写入的**，不会自动清理。长时间运行的项目应定期归档旧文件。
- **LLM 元数据依赖 API 提供商**：如果 API 响应中不包含 `usage` 字段，`input_tokens` / `output_tokens` 将为 `0`。
- **EventLog 不记录 prompt 全文**，只记录 `outputs_hash`（SHA-256 前 16 位）。完整的 prompt 存储在 SQLite `task_executions.input_data` 中。
- **审计报告是快照**：`export_audit_report()` 生成的 JSON 是调用时刻的快照，不会自动更新。
