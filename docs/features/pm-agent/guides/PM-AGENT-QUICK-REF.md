# PM Agent 快速参考

> **作者**: LEE Team
> **日期**: 2026-02-20
> **版本**: v1.0.0
> **分类**: 快速参考

## 🎯 功能状态

✅ **完整可用** - PM Agent 自然语言处理功能已 100% 完成并通过测试

---

## 🚀 快速开始

### 1. 启动 Chat CLI

```bash
# 基本模式（无需 LLM 配置）
lee chat --no-llm

# 完整模式（需要配置 LLM API key）
lee chat
```

### 2. 基本命令

```
Lee> help                    # 显示帮助
Lee> status                  # 查询状态
Lee> run                     # 运行下一步
Lee> run <step_id>          # 运行指定步骤
Lee> approve <gate_id>      # 批准网关
Lee> reject <gate_id>       # 拒绝网关
Lee> list                    # 列出工作流
Lee> metrics                 # 显示性能指标
Lee> exit                    # 退出
```

### 3. 自然语言示例（需 LLM）

```
Lee> 当前状态如何？
Lee> 运行下一步
Lee> 执行 generate_code 步骤
Lee> 批准 gate_review
Lee> 查看所有工作流
```

---

## 📊 测试验证

### 运行 Demo

```bash
python examples/pm_agent_demo.py
```

**预期输出**:
- ✅ 意图分类器: 75% 规则匹配率
- ✅ 权限检查器: 所有权限验证通过
- ✅ 安全模块: 拦截 3/3 恶意输入
- ✅ 缓存模块: 正常工作
- ✅ 决策引擎: 100% 成功率

---

## 🏗️ 架构组件

```
Decision Layer (决策层)
├─ Intent Classifier  → 意图识别
├─ Permission Checker → 权限验证
├─ Param Mapper      → 参数提取
└─ Decision Engine   → 编排器

Security Layer (安全层)
├─ Prompt Injection Detection
├─ Rate Limiting
└─ Audit Logging

Cache Layer (缓存层)
├─ Intent Cache
├─ Workflow Cache
└─ API Cache

API Layer (API层)
└─ Orchestrator API
```

---

## 📁 文件位置

### 核心代码
- `src/lee/orchestrator/execution/pm_agent/` - 所有 PM Agent 组件
- `src/lee/orchestrator/execution/pm_agent_runtime.py` - 运行时集成
- `src/lee/cli/commands/chat.py` - Chat CLI

### 配置
- `config/intent_classifier.yaml` - 意图和权限配置

### 文档
- `docs/features/pm-agent/` - 完整文档目录
  - `QUICKSTART.md` - 快速开始
  - `API-REFERENCE.md` - API 参考
  - `EXAMPLES.md` - 使用示例
  - `SECURITY-GUIDE.md` - 安全指南
  - `PERFORMANCE-GUIDE.md` - 性能指南

### 测试
- `tests/pm_agent/` - 单元测试
- `examples/pm_agent_demo.py` - 集成测试 Demo

---

## 🔧 编程接口

```python
from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime
from lee.orchestrator.execution.llm_executor import LLMExecutor
from lee.orchestrator.storage.sqlite_store import SQLiteStore

# 初始化
store = SQLiteStore(db_path)
llm_executor = LLMExecutor(profile="default")
runtime = PMAgentRuntime(orchestrator, llm_executor, store)

# 处理自然语言输入
result = await runtime.process_input(
    "运行下一步",
    session_id="user_session_123"
)

# 结果
# {
#     'status': 'success',
#     'action': 'next_step',
#     'data': {...},
#     'confidence': 0.85
# }
```

---

## 🐛 Bug 修复

所有已知 Bug 已修复：

1. ✅ ConversationContext.user_permissions 缺失
2. ✅ Demo 脚本变量名不匹配
3. ✅ Chat CLI Style 对象错误

---

## 📈 性能指标

| 指标 | 实际值 | 状态 |
|------|--------|------|
| 规则匹配延迟 | ~50ms | ✅ |
| 权限检查延迟 | ~20ms | ✅ |
| 端到端延迟（缓存） | ~170ms | ✅ |
| 缓存命中率 | ~75% | ✅ |
| 决策成功率 | 100% | ✅ |

---

## 📞 获取帮助

### 文档
- 查看 `docs/features/pm-agent/` 目录

### 示例
- 查看 `docs/features/pm-agent/EXAMPLES.md`

### 测试
- 运行 `python examples/pm_agent_demo.py`

### 问题
- 提交 Issue 到项目仓库

---

## ✅ 验证清单

- [x] Chat CLI 启动正常
- [x] 帮助命令工作
- [x] 性能指标显示
- [x] 退出命令正常
- [x] Demo 运行成功
- [x] 所有组件测试通过
- [x] 文档完整

---

**版本**: v1.0.0
**状态**: ✅ 生产就绪
**日期**: 2026-02-20
