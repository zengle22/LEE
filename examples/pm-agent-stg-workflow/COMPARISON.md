# PM Agent 使用方式对比

本文档对比 PM Agent 的不同使用方式，帮助你选择最适合的方式。

---

## 📊 三种使用方式对比

### 1️⃣ 快速入门 (quick_start.py)

**特点**:
- ✅ 最简单，只有 50 行代码
- ✅ 适合初学者
- ✅ 易于理解和修改
- ⚠️  只执行单个步骤

**代码示例**:
```python
# 查看状态
state = api_get_state(project_dir)

# 列出就绪步骤
ready_steps = api_list_ready_steps(project_dir)

# 执行第一个步骤
result = api_run_step(project_dir, ready_steps[0]['id'])
```

**适用场景**:
- 学习 PM API
- 理解基本流程
- 快速测试功能

**运行方式**:
```bash
python examples/pm-agent-stg-workflow/quick_start.py
```

---

### 2️⃣ 完整示例 (run_stg_with_pm_agent.py)

**特点**:
- ✅ 完整的决策逻辑
- ✅ 自动处理门控
- ✅ 记录决策历史
- ✅ 错误处理
- ✅ 执行整个工作流

**代码示例**:
```python
class STGWorkflowPM:
    def analyze_state(self, state):
        # 分析状态，生成建议
        if failed_steps > 0:
            return "handle_failure"
        elif pending_gates:
            return "check_gates"
        elif ready_steps:
            return "execute_next"

    async def run_workflow_interactive(self):
        # 主循环
        while not completed:
            # 1. 查看状态
            state = api_get_state(project_dir)

            # 2. 分析决策
            analysis = self.analyze_state(state)

            # 3. 执行决策
            if analysis == "execute_next":
                result = api_run_step(project_dir, step_id)
            elif analysis == "check_gates":
                # 处理门控
                ...
```

**适用场景**:
- 生产环境
- 完整工作流执行
- 需要 PM Agent 做决策

**运行方式**:
```bash
python examples/pm-agent-stg-workflow/run_stg_with_pm_agent.py
```

---

### 3️⃣ 直接使用 API (自定义集成)

**特点**:
- ✅ 最大灵活性
- ✅ 完全控制决策逻辑
- ✅ 可集成到任何系统
- ⚠️  需要自己编写所有逻辑

**代码示例**:
```python
# 自定义 PM Agent
class MyPMAgent:
    def __init__(self):
        self.strategy = "conservative"  # 保守策略

    def should_execute(self, step):
        # 自定义决策逻辑
        if step["risk_level"] == "high":
            return False  # 高风险步骤不自动执行
        return True

    def execute_with_approval(self, step_id):
        # 需要审批的执行
        print(f"请求审批: {step_id}")
        approval = input("是否批准? (y/n): ")
        if approval == 'y':
            return api_run_step(".", step_id)
```

**适用场景**:
- 集成到现有系统
- 自定义决策逻辑
- 复杂的审批流程

**运行方式**:
```python
# 作为模块导入
from my_pm_agent import MyPMAgent
agent = MyPMAgent()
agent.run()
```

---

## 🎯 选择指南

### 根据使用场景选择

| 场景 | 推荐方式 | 理由 |
|------|---------|------|
| **学习 PM API** | quick_start.py | 简单清晰 |
| **理解工作流程** | quick_start.py | 单步执行易理解 |
| **测试单个步骤** | quick_start.py | 快速验证 |
| **运行完整工作流** | run_stg_with_pm_agent.py | 自动化执行 |
| **生产环境部署** | run_stg_with_pm_agent.py | 完整错误处理 |
| **自定义决策逻辑** | 直接使用 API | 最大灵活性 |
| **集成到 Claude Code** | 直接使用 API | 工具集成 |
| **集成到 Web 应用** | 直接使用 API | API 调用 |

### 根据技能水平选择

| 技能水平 | 推荐方式 | 学习曲线 |
|---------|---------|---------|
| **初学者** | quick_start.py | ⭐ 简单 |
| **中级用户** | run_stg_with_pm_agent.py | ⭐⭐ 中等 |
| **高级用户** | 直接使用 API | ⭐⭐⭐ 复杂 |

---

## 📖 代码对比

### 相同功能：执行一个步骤

#### 快速入门方式
```python
# 简单直接
ready_steps = api_list_ready_steps(".")
result = api_run_step(".", ready_steps[0]['id'])
```

#### 完整示例方式
```python
# 有决策逻辑和错误处理
class PMAgent:
    async def execute_step(self):
        state = api_get_state(".")
        analysis = self.analyze_state(state)

        if analysis["recommendation"] == "execute_next":
            step_id = self.select_step(analysis["ready_steps"])
            result = await api_run_step(".", step_id)

            if result["status"] == "failed":
                await self.handle_failure(result)
            else:
                self.log_success(result)
```

#### 自定义方式
```python
# 完全自定义
class MyCustomPM:
    def execute_with_checks(self, step_id):
        # 执行前检查
        if not self.validate_preconditions(step_id):
            return self.skip_step(step_id)

        # 执行
        result = api_run_step(".", step_id)

        # 执行后处理
        if result["status"] == "completed":
            self.notify_stakeholders(result)
            self.update_dashboard(result)

        return result
```

---

## 🚀 迁移路径

### 从 quick_start 到 run_stg_with_pm_agent

```python
# 第 1 步：添加状态分析
def analyze_state(self, state):
    return {
        "progress": state['completed_steps'] / state['total_steps'],
        "ready": len(state['ready_steps']) > 0
    }

# 第 2 步：添加决策逻辑
if analysis["ready"]:
    execute_step()
else:
    check_gates()

# 第 3 步：添加循环
while not completed:
    step = get_next_step()
    execute_step(step)
    update_state()

# 第 4 步：添加错误处理
try:
    result = api_run_step(".", step_id)
except Exception as e:
    handle_error(e)
```

### 从 quick_start 到自定义集成

```python
# 第 1 步：封装成类
class MyPM:
    def execute_step(self, step_id):
        return api_run_step(".", step_id)

# 第 2 步：添加配置
class MyPM:
    def __init__(self, config):
        self.project_dir = config["project_dir"]
        self.auto_retry = config["auto_retry"]

# 第 3 步：添加钩子
class MyPM:
    def before_execute(self, step_id):
        self.notify_start(step_id)

    def after_execute(self, result):
        self.log_result(result)

# 第 4 步：添加集成点
class MyPM:
    def integrate_with_web(self):
        # Flask 集成
        @app.route('/execute/<step_id>')
        def execute(step_id):
            return self.execute_step(step_id)
```

---

## 💡 最佳实践建议

### 1. 从简单开始
```python
# ✅ 推荐：先用 quick_start.py 理解流程
python quick_start.py

# ❌ 不推荐：直接写复杂的自定义逻辑
```

### 2. 逐步增加复杂度
```python
# 第 1 阶段：理解单步执行
quick_start.py

# 第 2 阶段：理解完整流程
run_stg_with_pm_agent.py

# 第 3 阶段：自定义需求
my_custom_pm.py
```

### 3. 保持代码清晰
```python
# ✅ 好：函数职责单一
def get_ready_steps():
    return api_list_ready_steps(".")

def execute_step(step_id):
    return api_run_step(".", step_id)

# ❌ 差：一个函数做太多事
def do_everything():
    state = api_get_state(".")
    if state:
        steps = api_list_ready_steps(".")
        if steps:
            result = api_run_step(".", steps[0]['id'])
            if result:
                # ... 嵌套太深
```

---

## 📚 相关资源

- **快速入门**: `examples/pm-agent-stg-workflow/quick_start.py`
- **完整示例**: `examples/pm-agent-stg-workflow/run_stg_with_pm_agent.py`
- **使用指南**: `examples/pm-agent-stg-workflow/README.md`
- **API 文档**: `docs/PM-AGENT-USER-GUIDE.md`
- **协议文档**: `docs/PM_AGENT_PROTOCOL.md`

---

**选择适合你的方式，开始使用 PM Agent！** 🚀
