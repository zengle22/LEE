# 详细执行日志方案

## 1. 需求目标

生成详细的 AI 工作日志，包含：
- 调用了哪些 agent
- 是否正确的 agent 在工作
- agent 的工作流程
- 读写了哪些文件
- 调用了哪些工具
- 主要的思考过程
- 用的哪个 model
- 消耗了多少 token

## 2. 数据来源

### 2.1 Claude Code 会话日志
**位置**: `~/.claude/projects/{project-hash}/{session-id}.jsonl`

**包含的关键数据**:

| 字段 | 说明 | 示例 |
|------|------|------|
| `type` | 消息类型 | "user", "assistant" |
| `message.model` | 使用的模型 | "claude-opus-4-5-20251101" |
| `message.content[].type` | 内容类型 | "thinking", "text", "tool_use" |
| `message.content[].thinking` | 思考过程 | "让我分析这个问题..." |
| `message.content[].name` | 工具名称 | "Task", "Read", "Write", "Edit", "Bash" |
| `message.content[].input` | 工具输入 | `{subagent_type: "Explore", prompt: "..."}` |
| `message.usage.input_tokens` | 输入 token | 10000 |
| `message.usage.output_tokens` | 输出 token | 2000 |
| `toolUseResult.agentId` | 子 agent ID | "af0038e" |
| `toolUseResult.totalTokens` | agent 总 token | 54170 |
| `toolUseResult.totalToolUseCount` | 工具调用次数 | 30 |
| `timestamp` | 时间戳 | "2026-01-09T09:45:05.042Z" |

### 2.2 Orchestrator 日志
**位置**: `.workflow/events.jsonl` 和 `.workflow/traces/`

**包含的关键数据**:
- step_started / step_completed 事件
- token 信息
- 输出文件列表

## 3. 实现方案

### 3.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code Session                      │
│  ~/.claude/projects/{hash}/{session}.jsonl                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Session Log Parser                         │
│  orchestrator/core/session_log_parser.py                     │
│                                                              │
│  - 解析 JSONL 格式                                           │
│  - 提取 tool_use / thinking / usage                         │
│  - 关联 orchestrator step                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Detailed Execution Report                    │
│  output/detailed-execution-log.md                            │
│                                                              │
│  - 按步骤组织                                                │
│  - 包含完整工作流程                                          │
│  - 人类可读的 Markdown 格式                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件

#### 3.2.1 SessionLogParser

```python
class SessionLogParser:
    """Claude Code 会话日志解析器"""

    def __init__(self, session_log_path: str):
        self.log_path = Path(session_log_path)

    def parse(self) -> List[LogEntry]:
        """解析整个会话日志"""
        entries = []
        with open(self.log_path) as f:
            for line in f:
                entry = json.loads(line)
                entries.append(self._parse_entry(entry))
        return entries

    def extract_step_activities(self, step_id: str,
                                 start_time: str,
                                 end_time: str) -> StepActivity:
        """提取某个步骤时间段内的所有活动"""
        return StepActivity(
            agents_called=[...],      # Task 工具调用的 agent
            tools_used=[...],         # Read, Write, Edit, Bash 等
            files_read=[...],         # 读取的文件列表
            files_written=[...],      # 写入的文件列表
            thinking_summary="...",   # 主要思考过程摘要
            model="claude-opus-4-5",  # 使用的模型
            token_usage={...},        # token 使用详情
        )
```

#### 3.2.2 DetailedReportGenerator

```python
class DetailedReportGenerator:
    """详细执行报告生成器"""

    def generate(self, phase_dir: str,
                 session_log_path: str) -> str:
        """生成详细执行报告"""

        # 1. 加载 orchestrator 状态
        sm = StateMachine(phase_dir)
        state = sm.load()

        # 2. 解析 Claude Code 日志
        parser = SessionLogParser(session_log_path)

        # 3. 按步骤生成报告
        report = self._generate_header(state)

        for step_id, step_data in state["steps"].items():
            activities = parser.extract_step_activities(
                step_id,
                step_data["started_at"],
                step_data["completed_at"]
            )
            report += self._generate_step_section(step_id, activities)

        return report
```

### 3.3 输出格式

```markdown
# Phase 8: UI 核心页面 - 详细执行日志

**Run ID**: RUN-20260111141036-20a9a78c
**Session**: 6afa9f19-55b9-488e-8a4b-7f2f347df530
**生成时间**: 2026-01-11T16:00:00

---

## 执行摘要

| 指标 | 值 |
|------|-----|
| 总步骤数 | 12 |
| 已完成 | 10 |
| 总 Token | 1,234,567 |
| 总耗时 | 2h 15m |
| Agent 调用 | 45 次 |
| 工具调用 | 320 次 |

---

## 步骤详情

### Step 1: p08_01_requirements (需求校准)

**执行信息**:
| 项目 | 值 |
|------|-----|
| 开始时间 | 2026-01-11 14:10:47 |
| 结束时间 | 2026-01-11 14:15:04 |
| 耗时 | 4m 17s |
| 模型 | claude-opus-4-5-20251101 |
| Token (输入) | 27,909 |
| Token (输出) | 3,500 |

**Agent 调用**:
| Agent | 调用次数 | Token | 描述 |
|-------|----------|-------|------|
| Explore | 2 | 15,000 | 探索 UI 规范文件 |
| Plan | 1 | 8,000 | 规划需求校准步骤 |

**工具调用统计**:
| 工具 | 次数 | 说明 |
|------|------|------|
| Read | 15 | 读取文件 |
| Glob | 8 | 搜索文件 |
| Grep | 5 | 搜索内容 |
| Write | 3 | 写入文件 |
| Bash | 2 | 执行命令 |

**读取的文件** (15):
- `project/AI跑步教练/ui/pages/home.page.yaml`
- `project/AI跑步教练/ui/pages/chat.page.yaml`
- ... (展开/折叠)

**写入的文件** (3):
- `openspec/01-requirements/calibrated-requirements.md` ✅
- `openspec/01-requirements/page-list.md` ✅
- `openspec/01-requirements/api-requirements.md` ✅

**主要思考过程**:
> 1. 分析 8 个页面的 UI 规范文件
> 2. 识别页面状态 (loading/empty/error) 需求
> 3. 确认 API 对接需求
> 4. 生成校准后的需求文档

---

### Step 2: p08_02_test_contracts (测试契约)
...

---

## Token 使用汇总

| 步骤 | 输入 Token | 输出 Token | 缓存命中 | 成本估算 |
|------|------------|------------|----------|----------|
| p08_01 | 27,909 | 3,500 | 85% | $0.15 |
| p08_02 | 35,000 | 4,200 | 90% | $0.18 |
| ... | ... | ... | ... | ... |
| **总计** | **450,000** | **85,000** | **88%** | **$2.50** |

---

## Agent 使用分析

| Agent 类型 | 调用次数 | 总 Token | 正确使用率 |
|------------|----------|----------|------------|
| Explore | 12 | 180,000 | 100% |
| Plan | 5 | 45,000 | 100% |
| code-reviewer | 3 | 35,000 | 100% |
| frontend-developer | 8 | 120,000 | 100% |

**Agent 调用时序图**:
```
p08_01: Explore → Explore → Plan
p08_02: Explore → Plan
p08_03: Plan → Explore
p08_04: frontend-developer × 8
p08_05: test-automator × 2
p08_06: code-reviewer × 3
...
```

---

*报告由 orchestrator detailed-log 命令生成*
```

### 3.4 CLI 命令

```bash
# 新增命令
python -m orchestrator detailed-log <phase-dir> \
    --session <session-id> \
    --output <output-path>

# 示例
python -m orchestrator detailed-log project/AI跑步教练/dev/phase8 \
    --session 6afa9f19-55b9-488e-8a4b-7f2f347df530 \
    --output output/detailed-execution-log.md
```

### 3.5 自动关联会话

为了自动关联 Claude Code 会话和 orchestrator 步骤，需要：

1. **在 orchestrator start 时记录 session_id**:
   ```python
   def start_step(self, step_id, session_id=None):
       # 记录当前 Claude Code session
       state["steps"][step_id]["session_id"] = session_id
   ```

2. **环境变量传递**:
   ```bash
   # Claude Code 设置环境变量
   export CLAUDE_SESSION_ID=6afa9f19-55b9-488e-8a4b-7f2f347df530

   # orchestrator 读取
   session_id = os.environ.get("CLAUDE_SESSION_ID")
   ```

3. **或通过项目路径自动查找最新会话**:
   ```python
   def find_latest_session(project_path):
       claude_projects = Path.home() / ".claude" / "projects"
       project_hash = project_path.replace("/", "-").replace("\\", "-")
       project_dir = claude_projects / project_hash
       sessions = sorted(project_dir.glob("*.jsonl"),
                        key=lambda p: p.stat().st_mtime)
       return sessions[-1] if sessions else None
   ```

## 4. 实现步骤

1. **Phase 1: SessionLogParser** (核心)
   - 解析 Claude Code JSONL 日志
   - 提取 tool_use, thinking, usage
   - 支持时间范围过滤

2. **Phase 2: DetailedReportGenerator**
   - 生成 Markdown 报告
   - 按步骤组织
   - 包含统计汇总

3. **Phase 3: CLI 集成**
   - 添加 `detailed-log` 命令
   - 支持自动会话发现
   - 支持输出路径指定

4. **Phase 4: Workflow 集成**
   - 在验收步骤要求生成详细日志
   - artifact gate 检查文件存在

## 5. 注意事项

1. **隐私考虑**: 日志可能包含敏感信息，需要过滤
2. **文件大小**: 会话日志可能很大 (50MB+)，需要流式解析
3. **跨会话**: 一个 Phase 可能跨多个会话，需要合并
4. **性能**: 大日志解析需要优化

## 6. 预期收益

- 完整的 AI 工作审计记录
- 验证 agent 是否正确执行
- Token 成本分析
- 问题排查依据
- 流程优化参考
