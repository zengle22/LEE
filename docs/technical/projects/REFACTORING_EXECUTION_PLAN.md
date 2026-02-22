> **作者**: LEE Team
> **日期**: 2026-02-22
> **版本**: v1.0.0
> **分类**: 重构实施方案

# LEE 项目重构实施方案

**架构师评审**: 已完成
**文档版本**: 1.0
**制定日期**: 2026-02-22
**执行周期**: 12周（3个月）
**风险等级**: 中等

---

## 📋 架构师评审意见

### 对原分析方案的评估

**优点**:
- ✅ 问题识别全面准确（41个具体问题）
- ✅ 优先级划分合理（P0-P3）
- ✅ 改进方向正确
- ✅ 提供了具体的代码示例

**需要改进的地方**:
- ⚠️ **缺乏详细的依赖分析** - 某些改动会影响哪些模块
- ⚠️ **缺少回滚计划** - 如果重构失败如何恢复
- ⚠️ **工作量估算偏乐观** - 实际执行需要考虑测试、调试、文档更新
- ⚠️ **缺少分支策略** - 如何在持续开发的同时进行重构
- ⚠️ **未考虑业务影响** - 重构期间如何保证业务连续性

---

## 🎯 架构设计原则

本次重构遵循以下原则：

1. **Strangler Fig Pattern** (绞杀者模式)
   - 逐步用新实现替换旧实现
   - 保持系统始终可用
   - 通过适配器层隔离新旧代码

2. **Branch by Abstraction** (抽象分支)
   - 先创建抽象接口
   - 新旧实现都实现该接口
   - 通过配置切换实现
   - 完全稳定后删除旧实现

3. **Incremental Migration** (增量迁移)
   - 每个阶段独立可发布
   - 每个阶段都有完整的测试覆盖
   - 每个阶段都可以安全回滚

---

## 📊 影响范围分析

### 依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
│  (main.py, commands/)                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      API Layer                              │
│  (api/__init__.py - 全局状态问题所在)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Orchestrator Layer                        │
│  (orchestrator.py - 上帝类问题所在)                          │
│  ├─ StepRunnerMixin                                         │
│  ├─ GateOperationsMixin                                     │
│  └─ SubworkflowMixin                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Service Layer                              │
│  ├─ TemplateManager (重复实现)                              │
│  ├─ Executors (包装器问题)                                  │
│  ├─ StateMachine (TODO未完成)                               │
│  └─ VariableResolver (表达式求值未完成)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Storage Layer                             │
│  (sqlite_store.py, migrations/)                             │
└─────────────────────────────────────────────────────────────┘
```

### 改动影响矩阵

| 改动项 | 影响模块 | 影响程度 | 风险等级 | 优先级 |
|--------|----------|----------|----------|--------|
| CLI命令去重 | main.py, commands/ | 低 | 低 | P0 |
| TemplateManager统一 | 全项目(11处导入) | 中 | 中 | P0 |
| 迁移shim删除 | tests/ | 低 | 低 | P0 |
| 门禁命令统一 | commands/, 用户 | 中 | 中 | P1 |
| 表达式求值实现 | variable_resolver.py | 中 | 中 | P1 |
| 状态机TODO完成 | state_machine.py | 低 | 低 | P1 |
| Orchestrator重构 | 全项目 | 高 | 高 | P2 |
| 全局状态移除 | api/, orchestrator/ | 高 | 高 | P2 |
| 执行器包装删除 | execution/ | 中 | 中 | P2 |

---

## 🗓️ 详细执行计划 (12周)

### 第一阶段：快速清理 (第1-2周)

**目标**: 移除明显的重复和错误，降低技术债务
**风险**: 低
**可回滚**: 是

#### Sprint 1.1: CLI命令去重 (2天)

```bash
# 任务清单
- [ ] 删除 main.py:190-201 的重复注册
- [ ] 添加 pre-commit hook 检测重复注册
- [ ] 运行测试套件验证
- [ ] 更新 CHANGELOG.md

# 验收标准
✓ 所有CLI命令仍然正常工作
✓ 测试套件 100% 通过
✓ pre-commit hook 阻止未来重复
```

**详细步骤**:

```python
# 文件: src/lee/cli/main.py
# 操作: 删除行 190-201

# Before:
cli.add_command(qa)
cli.add_command(test_runner, "test-runner")
cli.add_command(check_env, "check-env")
cli.add_command(behavior_compliance_checker, "behavior-check")
cli.add_command(diagram_gen, "diagram-gen")
cli.add_command(diagram_insert, "diagram-insert")
cli.add_command(md_to_wechat, "md-to-wechat")
cli.add_command(wf, "workflow")
cli.add_command(repo)
cli.add_command(verify)
cli.add_command(chat)
cli.add_command(watch)

# After: (完全删除上述行)

# 验证命令
pytest tests/test_cli.py -v
```

#### Sprint 1.2: 迁移shim删除 (1天)

```bash
# 任务清单
- [ ] 更新 tests/test_migration_002.py 导入
- [ ] 删除 migration_002_gate_actions_v1_1.py
- [ ] 运行迁移测试
- [ ] 更新文档

# 修改文件
tests/test_migration_002.py:11
# Before:
from lee.orchestrator.storage.migrations import migration_002_gate_actions_v1_1 as migration

# After:
from lee.orchestrator.storage.migrations.migration_002_gate_actions import Migration002
```

#### Sprint 1.3: TemplateManager统一 (3天)

```bash
# 影响范围分析
# 需要修改的文件：
tests/orchestrator/test_execution.py:24-25  (2处导入)
docs/architecture/Spec_Global_v3.1_Adaptation_Plan.md:299

# 实施步骤
Day 1: 准备工作
- [ ] 创建测试套件验证当前行为
- [ ] 分析 core/template_manager.py 的实际使用场景
- [ ] 确认是否可以直接删除

Day 2: 执行迁移
- [ ] 更新所有导入语句
- [ ] 删除 core/template_manager.py
- [ ] 运行完整测试套件

Day 3: 验证和文档
- [ ] 运行集成测试
- [ ] 更新相关文档
- [ ] Code review

# 回滚计划
如果测试失败：
1. 恢复 core/template_manager.py
2. 回滚导入语句
3. 分析失败原因，调整方案
```

**详细操作**:

```python
# 文件: tests/orchestrator/test_execution.py
# 操作: 更新导入

# Before:
from lee.orchestrator.core.template_manager import TemplateManager
from lee.orchestrator.core.template_manager import TemplateManager

# After:
from lee.orchestrator.execution.template_manager import TemplateManager
```

---

### 第二阶段：功能完善 (第3-5周)

**目标**: 完成未实现的核心功能
**风险**: 中
**可回滚**: 是

#### Sprint 2.1: 表达式求值实现 (1.5周)

```python
# 设计方案

# 1. 创建独立的表达式求值模块
# 文件: src/lee/orchestrator/execution/expression_evaluator.py

"""
表达式求值器

支持的语法:
- 算术运算: +, -, *, /, %, **
- 比较运算: ==, !=, <, >, <=, >=
- 逻辑运算: and, or, not
- 成员运算: in, not in
- 字符串: 'hello', "world"
- 数字: 42, 3.14
- 变量: variable_name
- 数组/字典访问: arr[0], dict['key']

安全性:
- 使用 ast 模块解析，限制可用的节点类型
- 禁止函数调用和导入
- 限制递归深度
"""

import ast
import operator
from typing import Any, Dict, Set

class ExpressionEvaluator:
    """安全的表达式求值器"""

    # 允许的运算符映射
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
        ast.And: lambda x, y: x and y,
        ast.Or: lambda x, y: x or y,
        ast.Not: operator.not_,
        ast.USub: operator.neg,
    }

    # 允许的AST节点类型
    ALLOWED_NODES = {
        ast.Expression, ast.BinOp, ast.UnaryOp,
        ast.Compare, ast.BoolOp, ast.Name,
        ast.Constant, ast.Num, ast.Str, ast.NameConstant,
        ast.List, ast.Tuple, ast.Dict, ast.Subscript,
        ast.Index,
    }

    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth

    def evaluate(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        求值表达式

        Args:
            expr: 表达式字符串，如 "x > 0 and y < 10"
            context: 变量上下文，如 {"x": 5, "y": 3}

        Returns:
            求值结果

        Raises:
            ValueError: 表达式语法错误或不安全
            KeyError: 变量不存在
        """
        try:
            tree = ast.parse(expr, mode='eval')
            self._validate_tree(tree, depth=0)
            return self._eval_node(tree.body, context)
        except (SyntaxError, ValueError) as e:
            raise ValueError(f"Invalid expression: {expr}") from e

    def _validate_tree(self, node: ast.AST, depth: int) -> None:
        """验证AST树安全性和深度"""
        if depth > self.max_depth:
            raise ValueError("Expression too complex")

        if type(node) not in self.ALLOWED_NODES:
            raise ValueError(f"Disallowed node type: {type(node).__name__}")

        for child in ast.walk(node):
            if child is node:
                continue
            if type(child) not in self.ALLOWED_NODES:
                raise ValueError(f"Disallowed node type: {type(child).__name__}")

    def _eval_node(self, node: ast.AST, context: Dict[str, Any]) -> Any:
        """递归求值AST节点"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        elif isinstance(node, ast.NameConstant):  # Python < 3.8
            return node.value
        elif isinstance(node, ast.Name):
            if node.id not in context:
                raise KeyError(f"Variable not found: {node.id}")
            return context[node.id]
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            return self.OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            return self.OPERATORS[op_type](operand)
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                op_type = type(op)
                if op_type not in self.OPERATORS:
                    raise ValueError(f"Unsupported operator: {op_type.__name__}")
                result = self.OPERATORS[op_type](left, right)
                if not result:
                    break
                left = right
            return result
        elif isinstance(node, ast.BoolOp):
            values = [self._eval_node(v, context) for v in node.values]
            op_type = type(node.op)
            if op_type == ast.And:
                return all(values)
            elif op_type == ast.Or:
                return any(values)
        elif isinstance(node, ast.List):
            return [self._eval_node(e, context) for e in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(e, context) for e in node.elts)
        elif isinstance(node, ast.Dict):
            keys = [self._eval_node(k, context) for k in node.keys]
            values = [self._eval_node(v, context) for v in node.values]
            return dict(zip(keys, values))
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value, context)
            slice_val = self._eval_slice(node.slice, context)
            return value[slice_val]
        else:
            raise ValueError(f"Unsupported node type: {type(node).__name__}")

    def _eval_slice(self, slice_node: ast.AST, context: Dict[str, Any]) -> Any:
        """求值切片/索引"""
        if isinstance(slice_node, ast.Index):  # Python < 3.9
            return self._eval_node(slice_node.value, context)
        elif isinstance(slice_node, ast.Constant):
            return slice_node.value
        else:
            return self._eval_node(slice_node, context)


# 2. 集成到 VariableResolver
# 文件: src/lee/orchestrator/execution/variable_resolver.py

from lee.orchestrator.execution.expression_evaluator import ExpressionEvaluator

class VariableResolver:
    def __init__(self):
        self.expr_evaluator = ExpressionEvaluator()
        # ... 其他初始化

    def resolve_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        解析并求值表达式

        示例:
            resolve_expression("x > 0", {"x": 5}) -> True
            resolve_expression("status == 'done'", {"status": "done"}) -> True
            resolve_expression("x > 0 and y < 10", {"x": 5, "y": 3}) -> True
        """
        try:
            return self.expr_evaluator.evaluate(expr, context)
        except (ValueError, KeyError) as e:
            # 记录错误并返回默认值
            logging.warning(f"Expression evaluation failed: {expr}, error: {e}")
            return False
```

**测试计划**:

```python
# 文件: tests/test_expression_evaluator.py

import pytest
from lee.orchestrator.execution.expression_evaluator import ExpressionEvaluator

class TestExpressionEvaluator:
    def test_arithmetic_operations(self):
        evaluator = ExpressionEvaluator()
        assert evaluator.evaluate("1 + 2", {}) == 3
        assert evaluator.evaluate("10 - 3", {}) == 7
        assert evaluator.evaluate("2 * 3", {}) == 6
        assert evaluator.evaluate("10 / 2", {}) == 5.0
        assert evaluator.evaluate("10 % 3", {}) == 1
        assert evaluator.evaluate("2 ** 3", {}) == 8

    def test_comparison_operations(self):
        evaluator = ExpressionEvaluator()
        ctx = {"x": 5, "y": 10}
        assert evaluator.evaluate("x > 0", ctx) is True
        assert evaluator.evaluate("x < y", ctx) is True
        assert evaluator.evaluate("x == 5", ctx) is True
        assert evaluator.evaluate("y != 5", ctx) is True
        assert evaluator.evaluate("x >= 5", ctx) is True
        assert evaluator.evaluate("y <= 10", ctx) is True

    def test_logical_operations(self):
        evaluator = ExpressionEvaluator()
        ctx = {"x": 5, "y": 3}
        assert evaluator.evaluate("x > 0 and y < 10", ctx) is True
        assert evaluator.evaluate("x > 10 or y > 0", ctx) is True
        assert evaluator.evaluate("not (x > 10)", ctx) is True

    def test_string_operations(self):
        evaluator = ExpressionEvaluator()
        ctx = {"status": "done", "list": ["a", "b", "c"]}
        assert evaluator.evaluate("status == 'done'", ctx) is True
        assert evaluator.evaluate("'a' in list", ctx) is True
        assert evaluator.evaluate("'d' not in list", ctx) is True

    def test_complex_expressions(self):
        evaluator = ExpressionEvaluator()
        ctx = {"x": 5, "y": 3, "status": "running", "states": ["pending", "running"]}
        assert evaluator.evaluate("(x > 0 and y < 10) or status == 'done'", ctx) is True
        assert evaluator.evaluate("status in states", ctx) is True
        assert evaluator.evaluate("x + y > 5", ctx) is True

    def test_variable_not_found(self):
        evaluator = ExpressionEvaluator()
        with pytest.raises(KeyError):
            evaluator.evaluate("undefined_var > 0", {})

    def test_invalid_syntax(self):
        evaluator = ExpressionEvaluator()
        with pytest.raises(ValueError):
            evaluator.evaluate("x > 0 and", {})

    def test_disallowed_operations(self):
        evaluator = ExpressionEvaluator()
        # 函数调用应该被阻止
        with pytest.raises(ValueError):
            evaluator.evaluate("print('hello'))", {})

        # 导入应该被阻止
        with pytest.raises(ValueError):
            evaluator.evaluate("__import__('os')", {})

    def test_max_depth_limit(self):
        evaluator = ExpressionEvaluator(max_depth=3)
        # 深度嵌套应该被阻止
        with pytest.raises(ValueError):
            evaluator.evaluate("(((1)))", {})
```

#### Sprint 2.2: 状态机TODO完成 (3天)

```python
# 文件: src/lee/orchestrator/execution/state_machine.py

class WorkflowStateMachine:
    async def invalidate_workflow(
        self,
        workflow_id: str,
        reason: str,
        invalidated_by: Optional[str] = None,
    ) -> None:
        """
        使工作流失效，标记所有相关任务和门禁为失效状态

        Args:
            workflow_id: 工作流ID
            reason: 失效原因
            invalidated_by: 失效操作人（可选）

        Raises:
            WorkflowNotFoundError: 工作流不存在
            InvalidStateError: 工作流状态不允许失效
        """
        # 1. 验证工作流状态
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")

        if instance.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.INVALIDATED,
        ]:
            raise InvalidStateError(
                f"Cannot invalidate workflow in state: {instance.status}"
            )

        # 2. 更新工作流状态
        await self.store.update_workflow_status(
            workflow_id,
            WorkflowStatus.INVALIDATED,
        )

        # 3. 批量更新任务状态
        task_update_sql = """
            UPDATE task_executions
            SET status = 'invalidated',
                invalidated_at = ?,
                invalidated_reason = ?,
                invalidated_by = ?
            WHERE workflow_id = ?
              AND status IN ('pending', 'running')
        """
        await self.store.execute(
            task_update_sql,
            (datetime.utcnow(), reason, invalidated_by, workflow_id)
        )

        # 4. 批量更新门禁状态
        gate_update_sql = """
            UPDATE gate_approvals
            SET status = 'invalidated',
                invalidated_at = ?,
                invalidated_reason = ?,
                invalidated_by = ?
            WHERE workflow_id = ?
              AND status = 'pending'
        """
        await self.store.execute(
            gate_update_sql,
            (datetime.utcnow(), reason, invalidated_by, workflow_id)
        )

        # 5. 记录事件日志
        await self.store.log_event(
            workflow_id=workflow_id,
            event_type="workflow_invalidated",
            event_data={
                "reason": reason,
                "invalidated_by": invalidated_by,
                "previous_status": instance.status,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # 6. 如果是子工作流，级联失效父工作流的相关步骤
        if instance.level == WorkflowLevel.SUB:
            await self._invalidate_parent_step(workflow_id, reason)

    async def _invalidate_parent_step(self, sub_workflow_id: str, reason: str) -> None:
        """使父工作流中触发子工作流的步骤失效"""
        # 查找父工作流
        parent_info = await self.store.get_parent_workflow(sub_workflow_id)
        if parent_info:
            parent_workflow_id, parent_step_id = parent_info
            # 使父步骤失效
            await self.store.update_task_status(
                parent_workflow_id,
                parent_step_id,
                "invalidated",
                invalidated_reason=reason,
            )
```

**测试**:

```python
# 文件: tests/test_state_machine_invalidation.py

import pytest
from lee.orchestrator.execution.state_machine import WorkflowStateMachine

@pytest.mark.asyncio
async def test_invalidate_running_workflow(store):
    """测试使运行中的工作流失效"""
    sm = WorkflowStateMachine(store)

    # 创建运行中的工作流
    workflow_id = await sm.create_workflow("test_template")
    await sm.start_step(workflow_id, "step1")

    # 使工作流失效
    await sm.invalidate_workflow(
        workflow_id,
        reason="User cancelled",
        invalidated_by="test_user",
    )

    # 验证状态
    instance = await store.get_workflow(workflow_id)
    assert instance.status == WorkflowStatus.INVALIDATED

    # 验证任务状态
    tasks = await store.get_tasks(workflow_id)
    assert all(t.status == "invalidated" for t in tasks)

@pytest.mark.asyncio
async def test_cannot_invalidate_completed_workflow(store):
    """测试不能使已完成的工作流失效"""
    sm = WorkflowStateMachine(store)

    # 创建已完成的工作流
    workflow_id = await sm.create_workflow("test_template")
    await sm.complete_workflow(workflow_id)

    # 应该抛出异常
    with pytest.raises(InvalidStateError):
        await sm.invalidate_workflow(workflow_id, "test reason")
```

#### Sprint 2.3: 通知系统实现 (1周)

```python
# 文件: src/lee/orchestrator/notifications/__init__.py

"""
通知系统

支持的通知渠道:
- 邮件 (SMTP)
- Slack (Webhook)
- 钉钉 (Webhook)
- 企业微信 (Webhook)
- 日志 (开发/测试环境)
"""

# 文件: src/lee/orchestrator/notifications/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    body: str
    level: str = "info"  # info, warning, error
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class NotificationRecipient:
    """通知接收者"""
    id: str  # 用户ID
    channels: Dict[str, str]  # {"email": "user@example.com", "slack": "@username"}

class NotificationChannel(ABC):
    """通知渠道抽象接口"""

    @abstractmethod
    async def send(
        self,
        recipient: NotificationRecipient,
        message: NotificationMessage,
    ) -> bool:
        """
        发送通知

        Returns:
            bool: 是否发送成功
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查渠道是否可用"""
        pass


# 文件: src/lee/orchestrator/notifications/email_channel.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.use_tls = use_tls

    async def send(
        self,
        recipient: NotificationRecipient,
        message: NotificationMessage,
    ) -> bool:
        """发送邮件通知"""
        try:
            email_addr = recipient.channels.get("email")
            if not email_addr:
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.title
            msg["From"] = self.from_addr
            msg["To"] = email_addr

            # 纯文本版本
            text_part = MIMEText(message.body, "plain", "utf-8")
            msg.attach(text_part)

            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
            return False

    def is_available(self) -> bool:
        """检查SMTP配置是否完整"""
        return all([
            self.smtp_host,
            self.smtp_port,
            self.username,
            self.password,
            self.from_addr,
        ])


# 文件: src/lee/orchestrator/notifications/slack_channel.py

import httpx

class SlackNotificationChannel(NotificationChannel):
    """Slack通知渠道"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(
        self,
        recipient: NotificationRecipient,
        message: NotificationMessage,
    ) -> bool:
        """发送Slack通知"""
        try:
            slack_id = recipient.channels.get("slack")
            if not slack_id:
                return False

            # 根据级别选择颜色
            color = {
                "info": "good",
                "warning": "warning",
                "error": "danger",
            }.get(message.level, "good")

            payload = {
                "channel": slack_id,
                "attachments": [{
                    "color": color,
                    "title": message.title,
                    "text": message.body,
                    "footer": "LEE Workflow System",
                }]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0,
                )
                return response.status_code == 200

        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")
            return False

    def is_available(self) -> bool:
        """检查Webhook URL是否配置"""
        return bool(self.webhook_url)


# 文件: src/lee/orchestrator/notifications/service.py

class NotificationService:
    """通知服务"""

    def __init__(self, channels: List[NotificationChannel]):
        self.channels = channels

    async def notify(
        self,
        recipients: List[NotificationRecipient],
        message: NotificationMessage,
    ) -> Dict[str, int]:
        """
        发送通知给多个接收者

        Returns:
            {"success": 成功数, "failed": 失败数}
        """
        results = {"success": 0, "failed": 0}

        for recipient in recipients:
            for channel in self.channels:
                if not channel.is_available():
                    continue

                if await channel.send(recipient, message):
                    results["success"] += 1
                else:
                    results["failed"] += 1

        return results

    async def notify_gate_pending(
        self,
        workflow_id: str,
        gate_id: str,
        approvers: List[NotificationRecipient],
    ) -> None:
        """通知门禁待审批"""
        message = NotificationMessage(
            title=f"门禁待审批: {gate_id}",
            body=f"工作流 {workflow_id} 中的门禁 {gate_id} 等待您的审批。\n\n"
                 f"请使用以下命令进行审批:\n"
                 f"  lee gates approve {workflow_id} {gate_id} --approver YOUR_NAME\n"
                 f"  lee gates reject {workflow_id} {gate_id} --approver YOUR_NAME",
            level="info",
            metadata={
                "workflow_id": workflow_id,
                "gate_id": gate_id,
                "event": "gate_pending",
            },
        )

        await self.notify(approvers, message)

    async def notify_gate_approved(
        self,
        workflow_id: str,
        gate_id: str,
        approver: str,
        recipients: List[NotificationRecipient],
    ) -> None:
        """通知门禁已批准"""
        message = NotificationMessage(
            title=f"门禁已批准: {gate_id}",
            body=f"门禁 {gate_id} 已被 {approver} 批准。\n"
                 f"工作流 {workflow_id} 将继续执行。",
            level="info",
        )

        await self.notify(recipients, message)

    async def notify_workflow_failed(
        self,
        workflow_id: str,
        error: str,
        recipients: List[NotificationRecipient],
    ) -> None:
        """通知工作流失败"""
        message = NotificationMessage(
            title=f"工作流失败: {workflow_id}",
            body=f"工作流 {workflow_id} 执行失败。\n\n错误: {error}",
            level="error",
        )

        await self.notify(recipients, message)


# 文件: config/notifications.yaml

notifications:
  enabled: true

  channels:
    email:
      enabled: false
      smtp_host: smtp.example.com
      smtp_port: 587
      username: noreply@example.com
      password: ${SMTP_PASSWORD}
      from_addr: "LEE Workflow <noreply@example.com>"
      use_tls: true

    slack:
      enabled: false
      webhook_url: ${SLACK_WEBHOOK_URL}

    dingtalk:
      enabled: false
      webhook_url: ${DINGTALK_WEBHOOK_URL}

    wechat_work:
      enabled: false
      webhook_url: ${WECHAT_WORK_WEBHOOK_URL}

  # 用户通知配置
  users:
    user1:
      email: user1@example.com
      slack: "@user1"
    user2:
      email: user2@example.com
      dingtalk: "user2_phone"
```

---

### 第三阶段：架构重构 (第6-10周)

**目标**: 解决核心架构问题
**风险**: 高
**可回滚**: 通过feature flag

#### Sprint 3.1: Orchestrator服务化 (3周)

采用 **Branch by Abstraction** 模式：

**Week 1: 创建抽象层**

```python
# 文件: src/lee/orchestrator/services/interfaces.py

"""
Orchestrator服务接口定义

通过抽象接口，将现有的Mixin实现逐步替换为独立服务
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

# ========================================================================
# 步骤运行服务接口
# ========================================================================

class IStepRunnerService(ABC):
    """步骤运行服务接口"""

    @abstractmethod
    async def run_agent_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """运行Agent步骤"""
        pass

    @abstractmethod
    async def run_skill_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """运行Skill步骤"""
        pass

    @abstractmethod
    async def run_cli_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """运行CLI步骤"""
        pass

    @abstractmethod
    async def run_gate_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """运行门禁步骤"""
        pass

# ========================================================================
# 门禁操作服务接口
# ========================================================================

class IGateOperationsService(ABC):
    """门禁操作服务接口"""

    @abstractmethod
    async def approve_gate(
        self,
        workflow_id: str,
        gate_ref: str,
        approver: str,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """批准门禁"""
        pass

    @abstractmethod
    async def reject_gate(
        self,
        workflow_id: str,
        gate_ref: str,
        rejector: str,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """拒绝门禁"""
        pass

    @abstractmethod
    async def get_pending_gates(
        self,
        workflow_id: str,
    ) -> List[Dict[str, Any]]:
        """获取待审批门禁"""
        pass

    @abstractmethod
    async def request_gate_review(
        self,
        workflow_id: str,
        gate_id: str,
        reviewers: List[str],
    ) -> None:
        """请求门禁审批"""
        pass

# ========================================================================
# 子工作流服务接口
# ========================================================================

class ISubworkflowService(ABC):
    """子工作流服务接口"""

    @abstractmethod
    async def spawn_subworkflow(
        self,
        parent_workflow_id: str,
        parent_step_id: str,
        template_id: str,
        inputs: Dict[str, Any],
    ) -> str:
        """创建子工作流"""
        pass

    @abstractmethod
    async def backfill_subworkflow_result(
        self,
        parent_workflow_id: str,
        parent_step_id: str,
        sub_workflow_id: str,
    ) -> None:
        """回填子工作流结果到父工作流"""
        pass

    @abstractmethod
    async def get_subworkflow_status(
        self,
        sub_workflow_id: str,
    ) -> Dict[str, Any]:
        """获取子工作流状态"""
        pass
```

**Week 2: 实现适配器层**

```python
# 文件: src/lee/orchestrator/services/adapters.py

"""
适配器层：将Mixin实现适配到服务接口

这是临时过渡方案，待新实现稳定后可以删除
"""

from lee.orchestrator.execution.step_runners import StepRunnerMixin
from lee.orchestrator.execution.gate_operations import GateOperationsMixin
from lee.orchestrator.execution.subworkflow_ops import SubworkflowMixin
from lee.orchestrator.services.interfaces import (
    IStepRunnerService,
    IGateOperationsService,
    ISubworkflowService,
)

class StepRunnerServiceAdapter(IStepRunnerService):
    """步骤运行服务适配器"""

    def __init__(self, orchestrator):
        """
        Args:
            orchestrator: 具有StepRunnerMixin的Orchestrator实例
        """
        self._orchestrator = orchestrator

    async def run_agent_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """委托给Mixin实现"""
        return await self._orchestrator._run_agent_step(
            workflow_id,
            step,
            context,
        )

    async def run_skill_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """委托给Mixin实现"""
        return await self._orchestrator._run_skill_step(
            workflow_id,
            step,
            context,
        )

    async def run_cli_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """委托给Mixin实现"""
        return await self._orchestrator._run_cli_step(
            workflow_id,
            step,
            context,
        )

    async def run_gate_step(
        self,
        workflow_id: str,
        step: Step,
        context: RunnerContext,
    ) -> StepResult:
        """委托给Mixin实现"""
        return await self._orchestrator._run_gate_step(
            workflow_id,
            step,
            context,
        )


class GateOperationsServiceAdapter(IGateOperationsService):
    """门禁操作服务适配器"""

    def __init__(self, orchestrator):
        self._orchestrator = orchestrator

    async def approve_gate(
        self,
        workflow_id: str,
        gate_ref: str,
        approver: str,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """委托给Mixin实现"""
        return await self._orchestrator.approve_gate(
            workflow_id,
            gate_ref,
            approver,
            comments,
        )

    # ... 其他方法类似


class SubworkflowServiceAdapter(ISubworkflowService):
    """子工作流服务适配器"""

    def __init__(self, orchestrator):
        self._orchestrator = orchestrator

    async def spawn_subworkflow(
        self,
        parent_workflow_id: str,
        parent_step_id: str,
        template_id: str,
        inputs: Dict[str, Any],
    ) -> str:
        """委托给Mixin实现"""
        return await self._orchestrator._spawn_subworkflow(
            parent_workflow_id,
            parent_step_id,
            template_id,
            inputs,
        )

    # ... 其他方法类似
```

**Week 3: 重构Orchestrator使用服务接口**

```python
# 文件: src/lee/orchestrator/execution/orchestrator_v4.py

"""
Orchestrator v4.0 - 使用依赖注入的新架构

通过feature flag控制是否启用新架构:
- LEE_ORCHESTRATOR_V4_ENABLED=true 使用新架构
- LEE_ORCHESTRATOR_V4_ENABLED=false 使用旧架构
"""

import os
from typing import Optional

from lee.orchestrator.services.interfaces import (
    IStepRunnerService,
    IGateOperationsService,
    ISubworkflowService,
)
from lee.orchestrator.services.adapters import (
    StepRunnerServiceAdapter,
    GateOperationsServiceAdapter,
    SubworkflowServiceAdapter,
)

class OrchestratorV4:
    """
    新版Orchestrator - 使用依赖注入

    对比v3的变化:
    - 不再使用多重继承
    - 通过构造函数注入服务依赖
    - 更清晰的职责分离
    - 更容易测试
    """

    def __init__(
        self,
        store: SQLiteStore,
        template_manager: TemplateManager,
        step_runner: IStepRunnerService,
        gate_ops: IGateOperationsService,
        subworkflow: ISubworkflowService,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            store: 存储层
            template_manager: 模板管理器
            step_runner: 步骤运行服务
            gate_ops: 门禁操作服务
            subworkflow: 子工作流服务
            config: 配置字典
        """
        self.store = store
        self.template_manager = template_manager
        self.step_runner = step_runner
        self.gate_ops = gate_ops
        self.subworkflow = subworkflow
        self.config = config or {}

        # 其他组件
        self.state_machine = WorkflowStateMachine(store)
        self.evidence_collector = EvidenceCollector(store)
        # ... 其他组件

    # ========================================================================
    # 核心调度方法
    # ========================================================================

    async def create_workflow(
        self,
        template_id: str,
        inputs: Dict[str, Any],
        level: WorkflowLevel = WorkflowLevel.MAIN,
    ) -> str:
        """创建工作流实例"""
        # 验证模板
        template = await self.template_manager.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # 验证输入
        self._validate_inputs(template, inputs)

        # 创建实例
        workflow_id = str(uuid.uuid4())
        instance = WorkflowInstance(
            id=workflow_id,
            template_id=template_id,
            status=WorkflowStatus.PENDING,
            level=level,
            inputs=inputs,
        )

        await self.store.create_workflow(instance)

        # 记录事件
        await self.store.log_event(
            workflow_id=workflow_id,
            event_type="workflow_created",
            event_data={"template_id": template_id},
        )

        return workflow_id

    async def run_step(self, workflow_id: str) -> StepResult:
        """执行一个步骤"""
        # 获取工作流实例
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # 计算ready step
        ready_step = self._find_ready_step(instance)
        if not ready_step:
            # 没有ready step，工作流可能完成
            await self._check_workflow_completion(workflow_id)
            return StepResult(status="no_ready_step")

        # 构建运行上下文
        context = await self._build_runner_context(workflow_id, ready_step)

        # 根据步骤类型分发到对应服务
        if ready_step.type == "agent":
            result = await self.step_runner.run_agent_step(
                workflow_id, ready_step, context
            )
        elif ready_step.type == "skill":
            result = await self.step_runner.run_skill_step(
                workflow_id, ready_step, context
            )
        elif ready_step.type == "cli":
            result = await self.step_runner.run_cli_step(
                workflow_id, ready_step, context
            )
        elif ready_step.type == "gate":
            result = await self.step_runner.run_gate_step(
                workflow_id, ready_step, context
            )
        else:
            result = StepResult(
                status="failed",
                error=f"Unknown step type: {ready_step.type}",
            )

        # 更新状态机
        await self.state_machine.complete_step(
            workflow_id,
            ready_step.id,
            result,
        )

        return result

    # ========================================================================
    # 门禁操作（委托给服务）
    # ========================================================================

    async def approve_gate(
        self,
        workflow_id: str,
        gate_ref: str,
        approver: str,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """批准门禁"""
        return await self.gate_ops.approve_gate(
            workflow_id, gate_ref, approver, comments
        )

    async def reject_gate(
        self,
        workflow_id: str,
        gate_ref: str,
        rejector: str,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """拒绝门禁"""
        return await self.gate_ops.reject_gate(
            workflow_id, gate_ref, rejector, comments
        )

    # ========================================================================
    # 子工作流操作（委托给服务）
    # ========================================================================

    async def spawn_subworkflow(
        self,
        parent_workflow_id: str,
        parent_step_id: str,
        template_id: str,
        inputs: Dict[str, Any],
    ) -> str:
        """创建子工作流"""
        return await self.subworkflow.spawn_subworkflow(
            parent_workflow_id,
            parent_step_id,
            template_id,
            inputs,
        )


# ========================================================================
# 工厂函数：根据feature flag创建Orchestrator
# ========================================================================

def create_orchestrator(
    store: SQLiteStore,
    template_manager: TemplateManager,
    config: Optional[Dict[str, Any]] = None,
) -> Orchestrator:
    """
    根据feature flag创建Orchestrator实例

    Args:
        store: 存储层
        template_manager: 模板管理器
        config: 配置字典

    Returns:
        Orchestrator实例（v3或v4）
    """
    use_v4 = os.getenv("LEE_ORCHESTRATOR_V4_ENABLED", "false").lower() == "true"

    if use_v4:
        # 创建v4架构（依赖注入）
        # 首先创建v3实例作为适配器的目标
        v3_orchestrator = Orchestrator(
            store=store,
            template_manager=template_manager,
            config=config,
        )

        # 创建适配器
        step_runner = StepRunnerServiceAdapter(v3_orchestrator)
        gate_ops = GateOperationsServiceAdapter(v3_orchestrator)
        subworkflow = SubworkflowServiceAdapter(v3_orchestrator)

        # 创建v4实例
        return OrchestratorV4(
            store=store,
            template_manager=template_manager,
            step_runner=step_runner,
            gate_ops=gate_ops,
            subworkflow=subworkflow,
            config=config,
        )
    else:
        # 使用v3架构（Mixin）
        return Orchestrator(
            store=store,
            template_manager=template_manager,
            config=config,
        )
```

**Week 3: 添加feature flag和测试**

```python
# 文件: tests/test_orchestrator_v4.py

import pytest
import os
from lee.orchestrator.execution.orchestrator_v4 import create_orchestrator

@pytest.mark.asyncio
async def test_v3_orchestrator_still_works(store, template_manager):
    """确保v3架构仍然正常工作"""
    os.environ["LEE_ORCHESTRATOR_V4_ENABLED"] = "false"

    orchestrator = create_orchestrator(store, template_manager)

    # 验证是v3实例
    assert isinstance(orchestrator, Orchestrator)
    assert not isinstance(orchestrator, OrchestratorV4)

@pytest.mark.asyncio
async def test_v4_orchestrator_works(store, template_manager):
    """测试v4架构可以工作"""
    os.environ["LEE_ORCHESTRATOR_V4_ENABLED"] = "true"

    orchestrator = create_orchestrator(store, template_manager)

    # 验证是v4实例
    assert isinstance(orchestrator, OrchestratorV4)

    # 验证功能
    workflow_id = await orchestrator.create_workflow(
        "test_template",
        inputs={},
    )
    assert workflow_id is not None
```

#### Sprint 3.2: 全局状态移除 (2周)

```python
# 文件: src/lee/orchestrator/api/container.py

"""
依赖注入容器

使用容器模式管理Orchestrator实例的生命周期
"""

from typing import Optional, Dict
from weakref import WeakValueDictionary
from dataclasses import dataclass

@dataclass
class OrchestratorConfig:
    """Orchestrator配置"""
    project_dir: str
    port: int
    llm_profile: str = "default"
    log_level: str = "INFO"


class OrchestratorContainer:
    """
    Orchestrator容器

    职责:
    - 管理Orchestrator实例的生命周期
    - 提供实例的获取和释放
    - 使用weakref自动清理不再使用的实例
    """

    def __init__(self):
        # 使用弱引用字典，当外部不再引用时自动清理
        self._instances: WeakValueDictionary[
            tuple[str, int],  # (project_dir, port)
            Orchestrator,
        ] = WeakValueDictionary()

    def get_orchestrator(
        self,
        config: OrchestratorConfig,
    ) -> Orchestrator:
        """
        获取Orchestrator实例

        如果不存在则创建新实例，如果存在则返回已有实例

        Args:
            config: Orchestrator配置

        Returns:
            Orchestrator实例
        """
        key = (config.project_dir, config.port)

        if key not in self._instances:
            # 创建新实例
            store = SQLiteStore(config.project_dir)
            template_manager = TemplateManager()

            orchestrator = create_orchestrator(
                store=store,
                template_manager=template_manager,
                config={
                    "project_dir": config.project_dir,
                    "port": config.port,
                    "llm_profile": config.llm_profile,
                },
            )

            self._instances[key] = orchestrator

        return self._instances[key]

    def remove_orchestrator(
        self,
        project_dir: str,
        port: int,
    ) -> None:
        """
        手动移除Orchestrator实例

        Args:
            project_dir: 项目目录
            port: 端口
        """
        key = (project_dir, port)
        if key in self._instances:
            del self._instances[key]

    def clear(self) -> None:
        """清空所有实例"""
        self._instances.clear()


# 全局容器实例（单例）
_container: Optional[OrchestratorContainer] = None

def get_container() -> OrchestratorContainer:
    """获取全局容器实例（单例模式）"""
    global _container
    if _container is None:
        _container = OrchestratorContainer()
    return _container


# 文件: src/lee/orchestrator/api/__init__.py (重构后)

"""
LEE Orchestrator API

重构说明:
- 使用容器模式管理Orchestrator实例
- 不再直接操作全局字典
- 更容易测试和mock
"""

from lee.orchestrator.api.container import (
    OrchestratorContainer,
    OrchestratorConfig,
    get_container,
)

async def get_orchestrator(
    project_dir: str,
    port: int = 8000,
) -> Orchestrator:
    """
    获取Orchestrator实例

    Args:
        project_dir: 项目目录
        port: API服务端口

    Returns:
        Orchestrator实例
    """
    container = get_container()
    config = OrchestratorConfig(
        project_dir=project_dir,
        port=port,
    )
    return container.get_orchestrator(config)


async def release_orchestrator(
    project_dir: str,
    port: int = 8000,
) -> None:
    """
    释放Orchestrator实例

    Args:
        project_dir: 项目目录
        port: API服务端口
    """
    container = get_container()
    container.remove_orchestrator(project_dir, port)


# 用于测试的mock函数
def reset_container():
    """重置容器（仅用于测试）"""
    global _container
    _container = None
```

---

### 第四阶段：质量提升 (第11-12周)

**目标**: 建立长期质量保障机制

#### Sprint 4.1: 类型提示完善 (1周)

```bash
# 任务清单
- [ ] 为所有公共API添加完整的类型提示
- [ ] 配置mypy进行类型检查
- [ ] 修复所有类型错误
- [ ] 在CI/CD中集成类型检查

# 详细步骤
Day 1-2: 为核心模块添加类型提示
- src/lee/orchestrator/execution/orchestrator.py
- src/lee/orchestrator/storage/sqlite_store.py
- src/lee/orchestrator/api/__init__.py

Day 3-4: 为服务层添加类型提示
- src/lee/orchestrator/services/
- src/lee/orchestrator/execution/

Day 5: 配置mypy和CI集成
```

**mypy配置**:

```ini
# 文件: pyproject.toml

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
follow_imports = normal
strict_optional = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = [
    "click.*",
    "yaml.*",
    "toml.*",
]
ignore_missing_imports = true
```

#### Sprint 4.2: 错误处理统一 (1周)

```python
# 文件: src/lee/orchestrator/exceptions.py

"""
LEE Orchestrator 异常定义

统一的异常层次结构
"""

class LeeError(Exception):
    """LEE基础异常"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# ========================================================================
# 工作流相关异常
# ========================================================================

class WorkflowError(LeeError):
    """工作流异常基类"""
    pass


class WorkflowNotFoundError(WorkflowError):
    """工作流不存在"""
    pass


class WorkflowInvalidStateError(WorkflowError):
    """工作流状态无效"""
    pass


class WorkflowValidationError(WorkflowError):
    """工作流验证失败"""
    pass


# ========================================================================
# 模板相关异常
# ========================================================================

class TemplateError(LeeError):
    """模板异常基类"""
    pass


class TemplateNotFoundError(TemplateError):
    """模板不存在"""
    pass


class TemplateValidationError(TemplateError):
    """模板验证失败"""
    pass


# ========================================================================
# 步骤相关异常
# ========================================================================

class StepError(LeeError):
    """步骤异常基类"""
    pass


class StepExecutionError(StepError):
    """步骤执行失败"""
    pass


class StepNotFoundError(StepError):
    """步骤不存在"""
    pass


# ========================================================================
# 门禁相关异常
# ========================================================================

class GateError(LeeError):
    """门禁异常基类"""
    pass


class GateNotFoundError(GateError):
    """门禁不存在"""
    pass


class GateApprovalError(GateError):
    """门禁审批失败"""
    pass


# ========================================================================
# 存储相关异常
# ========================================================================

class StorageError(LeeError):
    """存储异常基类"""
    pass


class StorageConnectionError(StorageError):
    """存储连接失败"""
    pass


class StorageQueryError(StorageError):
    """存储查询失败"""
    pass


# ========================================================================
# 表达式相关异常
# ========================================================================

class ExpressionError(LeeError):
    """表达式异常基类"""
    pass


class ExpressionSyntaxError(ExpressionError):
    """表达式语法错误"""
    pass


class ExpressionEvaluationError(ExpressionError):
    """表达式求值错误"""
    pass
```

---

## 🔄 分支策略与发布计划

### Git工作流

```
main (生产)
  ↑
  ├─ release/v3.6 (重构发布分支)
  │    ↑
  │    ├─ refactor/remove-cli-duplication
  │    ├─ refactor/unify-template-manager
  │    ├─ feature/expression-evaluator
  │    ├─ refactor/orchestrator-v4
  │    └─ quality/add-type-hints
  │
  └─ feature/* (新功能分支)
```

### 发布计划

| 版本 | 时间 | 内容 | 风险 |
|------|------|------|------|
| v3.5.1 | 第2周 | 快速清理：CLI去重、迁移shim、TemplateManager统一 | 低 |
| v3.6.0 | 第5周 | 功能完善：表达式求值、状态机TODO、通知系统 | 中 |
| v3.7.0 | 第10周 | 架构重构：Orchestrator服务化、全局状态移除 | 高 |
| v3.8.0 | 第12周 | 质量提升：类型提示、错误处理统一 | 低 |

---

## 🧪 测试策略

### 测试金字塔

```
        /\
       /E2E\      ← 端到端测试 (10%)
      /------\
     /  集成  \    ← 集成测试 (30%)
    /----------\
   /    单元    \  ← 单元测试 (60%)
  /--------------\
```

### 关键测试场景

```python
# 文件: tests/refactoring/test_refactoring_suites.py

"""
重构期间的测试套件

确保重构不破坏现有功能
"""

class TestRefactoringSuites:
    """重构测试套件"""

    @pytest.mark.asyncio
    async def test_workflow_creation_unchanged(self):
        """测试工作流创建接口未改变"""
        # v3和v4应该表现一致
        pass

    @pytest.mark.asyncio
    async def test_gate_approval_unchanged(self):
        """测试门禁审批接口未改变"""
        pass

    @pytest.mark.asyncio
    async def test_subworkflow_spawn_unchanged(self):
        """测试子工作流创建接口未改变"""
        pass

    @pytest.mark.asyncio
    async def test_api_backward_compatibility(self):
        """测试API向后兼容性"""
        pass

    @pytest.mark.asyncio
    async def test_v3_v4_parity(self):
        """测试v3和v4功能等价性"""
        # 使用相同输入分别调用v3和v4
        # 验证输出一致
        pass
```

---

## 📈 进度追踪

### 每周检查项

- [ ] 代码变更量统计
- [ ] 测试覆盖率趋势
- [ ] 技术债务指标变化
- [ ] 性能基准测试
- [ ] 用户反馈收集

### 关键指标

| 指标 | 当前 | 第2周 | 第5周 | 第10周 | 第12周 |
|------|------|-------|-------|--------|--------|
| TODO数量 | 8 | 5 | 2 | 0 | 0 |
| 代码重复 | 8处 | 5处 | 2处 | 0 | 0 |
| 类型覆盖率 | 30% | 40% | 60% | 80% | 90% |
| 测试覆盖率 | 未知 | 50% | 65% | 75% | 80% |
| 代码健康评分 | C+ (65) | B (70) | B+ (75) | A- (85) | A (90) |

---

## ⚠️ 风险管理

### 风险识别与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 重构破坏现有功能 | 中 | 高 | 完整的测试套件、feature flag |
| 进度延误 | 中 | 中 | 每周回顾、优先级动态调整 |
| 团队知识断层 | 低 | 中 | 文档同步、代码审查 |
| 性能下降 | 低 | 中 | 性能基准测试、持续监控 |
| 用户不适应 | 低 | 低 | 渐进式发布、文档更新 |

### 回滚计划

每个阶段都设计了回滚机制：

1. **代码级别**: 使用Git分支，可以快速回退
2. **功能级别**: 使用feature flag，可以即时切换
3. **数据级别**: 数据库迁移保持向后兼容
4. **API级别**: 保持接口兼容性

---

## 📚 文档更新

### 需要更新的文档

- [ ] `README.md` - 更新项目结构说明
- [ ] `docs/architecture/` - 更新架构图
- [ ] `docs/api/` - 更新API文档
- [ ] `CHANGELOG.md` - 记录所有变更
- [ ] `docs/migration/` - 添加迁移指南
- [ ] `docs/adr/` - 创建架构决策记录

### ADR列表

```
docs/adr/
├── 001-orchestrator-refactoring-v3-to-v4.md
├── 002-expression-evaluator-implementation.md
├── 003-notification-system-design.md
├── 004-removal-of-global-state.md
├── 005-template-manager-unification.md
└── 006-error-handling-standardization.md
```

---

## ✅ 验收标准

### 每个阶段的验收标准

**第一阶段 (第2周)**:
- ✅ 所有P0问题已解决
- ✅ 测试套件100%通过
- ✅ 无新增技术债务

**第二阶段 (第5周)**:
- ✅ 所有P1功能已完成
- ✅ 集成测试通过
- ✅ 性能无明显下降

**第三阶段 (第10周)**:
- ✅ 架构重构完成
- ✅ 向后兼容性保证
- ✅ 文档完整更新

**第四阶段 (第12周)**:
- ✅ 代码健康评分达到A级
- ✅ 类型覆盖率>80%
- ✅ 测试覆盖率>70%

---

## 🎓 团队协作

### 角色与职责

| 角色 | 职责 |
|------|------|
| 架构师 | 设计方案、代码审查、决策 |
| 开发者 | 实施重构、编写测试 |
| QA | 编写测试用例、验证功能 |
| DevOps | CI/CD配置、环境管理 |

### 沟通机制

- **每日站会**: 同步进度、识别阻塞
- **每周回顾**: 检查指标、调整计划
- **代码审查**: 所有代码必须经过审查
- **架构评审**: 重大决策需要团队讨论

---

## 📞 联系方式

**项目负责人**: [待定]
**架构师**: [待定]
**问题反馈**: GitHub Issues

---

**文档版本**: 1.0
**制定人**: 架构师
**审批人**: [待定]
**生效日期**: 2026-02-22
