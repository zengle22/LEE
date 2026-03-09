# P0 级别问题技术方案（重写版）：统一表达式求值接入

**重写日期**: 2026-03-06  
**优先级**: P0  
**状态**: 待评审  
**目标**: 修复 IR 层条件/规则恒真问题，并与现有执行引擎语义统一

---

## 1. 问题定义

当前 `IR` 层存在两个占位实现：

1. `GateRuleIR.evaluate()`  
   位置：`src/lee/orchestrator/ir/models.py:121`  
   当前行为：固定返回 `(True, None)`

2. `StepIR._evaluate_condition()`  
   位置：`src/lee/orchestrator/ir/models.py:413`  
   当前行为：固定返回 `True`

这会导致：

- Gate 规则无法真正拦截失败条件
- 带 `condition` 的步骤无法被跳过
- 跨工作流循环和条件分支出现“表达式失效但流程继续”的假阳性

---

## 2. 设计结论

**不新增第三套表达式引擎。**

仓库里已经存在两套相关能力：

- `ConditionEngine`：负责条件表达式解析与求值  
  `src/lee/orchestrator/execution/condition_engine.py`
- `GateEngine`：负责门禁规则评估与 `validation_method` 分发  
  `src/lee/orchestrator/execution/gate_engine.py`

本次 P0 修复应当：

1. 复用现有引擎，而不是新增 `expression_engine.py`
2. 在 `IR` 层增加一个轻量适配层，统一语法和上下文访问
3. 明确错误策略，避免继续使用隐式 `fail-open`

---

## 3. 现状约束

### 3.1 仓库内已出现的表达式语法

现有文档和测试里已经使用了多种表达式风格：

- Python 风格：`qa_test.exit_decision == 'fail'`
- `$` 变量风格：`$convergence_decision.action == 'continue_to_dev'`
- 大写逻辑运算：`A AND B`、`A OR B`
- 扩展操作：`CONTAINS`

因此本次不能只支持单一 Python 语法，否则会造成“修复后仍有大量条件不可执行”。

### 3.2 现有引擎的能力边界

`ConditionEngine` 当前已支持：

- `== != < > <= >=`
- `and/or/not`
- `&& ||`
- 基于 AST 的属性访问，如 `foo.bar`
- `$foo.bar` 风格变量

当前仍缺少：

- 大写 `AND/OR/NOT` 的预处理
- `true/false/null` 与 Python 字面量的统一
- `CONTAINS` 这类扩展语法的统一入口
- 点访问与字典对象混用时的上下文适配

### 3.3 错误策略要求

P0 修复不能继续默认“表达式解析失败也返回 True”。  
至少对以下场景要收敛为可控行为：

- Mandatory gate 规则求值失败
- Conditional step 求值失败
- 关键循环收敛条件求值失败

---

## 4. 目标方案

### 4.1 新增模块

新增一个 **适配层**，而不是新增求值引擎：

```text
src/lee/orchestrator/ir/
├── models.py
└── expression_adapter.py
```

职责：

1. 对输入表达式做语法标准化
2. 对上下文做只读适配
3. 调用 `ConditionEngine` / `GateEngine`
4. 统一抛出 `ExpressionAdapterError`

---

## 5. 详细设计

### 5.1 `ExpressionAdapter`

```python
from dataclasses import dataclass
from typing import Any, Dict, Optional

from lee.orchestrator.execution.condition_engine import ConditionEngine
from lee.orchestrator.execution.gate_engine import GateEngine


class ExpressionAdapterError(Exception):
    pass


@dataclass
class EvaluationResult:
    passed: bool
    error_message: Optional[str] = None


class ExpressionAdapter:
    def __init__(self) -> None:
        self._condition_engine = ConditionEngine()
        self._gate_engine = GateEngine()

    def evaluate_condition(self, expression: str, context: Dict[str, Any]) -> bool:
        normalized = self._normalize_expression(expression)
        normalized_context = self._normalize_context(context)
        try:
            return self._condition_engine.evaluate(normalized, normalized_context)
        except Exception as exc:
            raise ExpressionAdapterError(str(exc)) from exc

    def evaluate_gate_rule(
        self,
        expression: str,
        context: Dict[str, Any],
        validation_method: Optional[str],
    ) -> EvaluationResult:
        normalized = self._normalize_expression(expression)
        normalized_context = self._normalize_context(context)
        try:
            evaluator = self._gate_engine._evaluators.get(
                validation_method or "default",
                self._gate_engine._evaluators["default"],
            )
            passed, _actual, _expected, error = evaluator(normalized, normalized_context)
            return EvaluationResult(passed=passed, error_message=error)
        except Exception as exc:
            raise ExpressionAdapterError(str(exc)) from exc
```

### 5.2 表达式标准化规则

新增 `_normalize_expression()`，最小范围支持以下转换：

1. 大写逻辑运算符统一为小写
   - `AND` -> `and`
   - `OR` -> `or`
   - `NOT` -> `not`

2. 小写布尔字面量统一为 Python 风格
   - `true` -> `True`
   - `false` -> `False`
   - `null` -> `None`

3. 对已有 `$foo.bar` 表达式保持兼容

4. `CONTAINS` 暂定转换为 `in`
   - `analysis.risk_area CONTAINS 'irreversible'`
   - 转为 `'irreversible' in analysis.risk_area`

说明：

- 这里只做语法归一化，不实现任意脚本能力
- 不支持函数调用、索引写入、lambda、列表推导式等动态语法

### 5.3 上下文适配

新增 `_normalize_context()`，目标是让以下场景都能一致读取：

- `foo.bar` 访问对象属性
- `foo.bar` 访问字典键
- 嵌套字典、dataclass、普通对象混用

建议实现：

- 保持原始 `dict` 结构不变
- 为需要点访问的字典节点包装只读代理对象
- 不在适配阶段修改业务对象本身

如果实现成本过高，P0 可先限定：

- 条件求值统一使用 `ConditionEngine` 当前的 `$a.b` / `a.b` 访问路径
- 对纯字典上下文使用递归对象视图包装

### 5.4 `GateRuleIR.evaluate()` 改造

目标：

- 保留 `validation_method`
- 对默认表达式求值走适配层
- 对求值异常返回 `False + 错误信息`

伪代码：

```python
def evaluate(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    adapter = get_expression_adapter()
    try:
        result = adapter.evaluate_gate_rule(
            expression=self.rule_expression,
            context=context,
            validation_method=self.validation_method,
        )
    except ExpressionAdapterError as exc:
        return False, f"规则 '{self.rule_id}' 表达式求值失败: {exc}"

    if result.passed:
        return True, None

    return False, self.error_message or result.error_message or (
        f"规则 '{self.rule_id}' 未通过: {self.name}"
    )
```

### 5.5 `StepIR._evaluate_condition()` 改造

目标：

- 空条件仍返回 `True`
- 非空条件统一走 `ExpressionAdapter.evaluate_condition()`
- 默认不再静默 `return True`

建议策略：

- 默认返回 `False`
- 同时记录可观察错误信息

原因：

- 这类条件控制的是“是否执行”，解析失败时继续执行属于危险默认值
- 对 P0 缺陷，宁可阻止可疑步骤继续，也不应无条件放行

伪代码：

```python
def _evaluate_condition(self, context: Dict[str, Any]) -> bool:
    if not self.condition:
        return True

    adapter = get_expression_adapter()
    try:
        return adapter.evaluate_condition(self.condition, context)
    except ExpressionAdapterError:
        return False
```

如需兼容历史行为，可追加：

- 记录日志
- 在高层调用方收集条件错误
- 仅对明确标记为 `legacy_condition_mode` 的工作流保留 fail-open

P0 默认不建议继续 fail-open。

### 5.6 `GateIR.evaluate()` 的阻塞语义修正

当前 `GateIR.evaluate()` 只会因为 `BLOCKER` 级别问题返回失败。  
但注释写的是“强制标准 0 容忍”，语义并不完全一致。

建议修正为：

- 只要 `mandatory_criteria` 中存在失败，就返回 `False`
- `severity` 仅用于展示等级，不决定 mandatory 是否阻塞

即：

```python
mandatory_failures = [rule for rule in self.mandatory_criteria if not rule.evaluate(context)[0]]
if mandatory_failures:
    return False, issues
```

这是本次修复应一并处理的逻辑缺陷。

### 5.7 跨工作流循环条件

`subworkflow_ops.py` 里目前还有 `_evaluate_phase_condition()` 的简化实现。  
本次 P0 至少应确认两件事：

1. `StepIR._evaluate_condition()` 修复后，主执行链路的 conditional step 生效
2. `CrossWorkflowLoop` 内部条件是否仍走独立简化逻辑

若当前运行路径仍依赖 `_evaluate_phase_condition()`，则需要同步改为复用 `ExpressionAdapter`。  
否则会出现“Step 修好了，phase condition 仍是半残实现”的不一致。

---

## 6. 测试方案

测试文件建议：

```text
tests/test_ir_expression_adapter.py
tests/test_ir_gate_rule_evaluation.py
tests/test_ir_step_condition_evaluation.py
```

### 6.1 适配层单元测试

覆盖：

- `a > 1`
- `a > 1 and b == 'x'`
- `A AND B` 归一化
- `true/false/null` 归一化
- `$foo.bar == 'x'`
- `foo.bar == 'x'`
- `CONTAINS` 归一化
- 未定义变量
- 非法表达式

### 6.2 `GateRuleIR` 集成测试

覆盖：

- 默认规则通过
- 默认规则失败
- `validation_method="numeric_compare"` 仍然可用
- 表达式异常时返回 `False` 和错误信息
- `error_message` 覆盖默认错误文案

### 6.3 `StepIR` 集成测试

覆盖：

- 条件为真
- 条件为假
- 空条件
- 大写 `AND/OR`
- `$` 路径引用
- 表达式错误时返回 `False`

### 6.4 回归测试

至少补以下现有场景：

- `tests/test_cross_workflow_loop.py`
- `tests/test_gate_integration.py`
- `tests/test_p1_integrations.py`

重点验证：

- 原有 `GateEngine` 行为未被破坏
- 跨工作流循环条件不会再静默放行

---

## 7. 依赖与实现策略

### 7.1 依赖策略

**本次不引入 `simpleeval`。**

理由：

- 仓库已经有可复用引擎
- 新增第三方库不能解决现有语法兼容问题
- 会增加两套语义并存和维护成本

### 7.2 项目配置

如确需新增依赖，应修改 `pyproject.toml`，不是 `requirements.txt`。  
但本方案默认无需新增依赖。

---

## 8. 实施计划

### Phase 1: 统一适配层

- [ ] 新增 `expression_adapter.py`
- [ ] 实现表达式标准化
- [ ] 实现上下文只读适配
- [ ] 补适配层单元测试

### Phase 2: 接入 IR

- [ ] 改造 `GateRuleIR.evaluate()`
- [ ] 改造 `StepIR._evaluate_condition()`
- [ ] 修正 `GateIR.evaluate()` 的 mandatory 阻塞逻辑

### Phase 3: 收敛循环补齐

- [ ] 评估 `subworkflow_ops.py` 的 phase condition 路径
- [ ] 如命中主链路，改为复用适配层
- [ ] 补跨工作流回归测试

### Phase 4: 验证

- [ ] 运行新增单测
- [ ] 运行相关集成测试
- [ ] 验证现有 gate 与 loop 场景不回归

**预估工期**: 1.5 到 2.5 天

---

## 9. 风险与决策

### 风险 1: 旧语法分散

仓库内已经同时存在 Python 风格、`$` 风格和文档 DSL 风格。  
处理方式：

- P0 先支持已知高频语法
- 归一化逻辑集中在适配层
- 后续再考虑完整 DSL 收敛

### 风险 2: fail-open 改为 fail-close 可能影响老流程

处理方式：

- 默认对条件执行采用 fail-close
- 通过日志和测试识别受影响流程
- 如有必要，用显式开关保留 legacy 行为，而不是全局静默放行

### 风险 3: `GateEngine` 与 `IR` 层接口耦合

处理方式：

- 适配层只调用公开行为和受控入口
- 如后续需要，补一个 `GateEngine.evaluate_expression()` 明确接口，替代直接取 `_evaluators`

---

## 10. 验收标准

满足以下条件才算完成：

1. `GateRuleIR.evaluate()` 不再恒真
2. `StepIR._evaluate_condition()` 不再恒真
3. `mandatory_criteria` 任一失败时 Gate 返回失败
4. 支持 `and/or/not`、`AND/OR/NOT`、`true/false/null`
5. 支持 `foo.bar` 与 `$foo.bar` 的常见访问方式
6. 相关单测与回归测试通过
7. 不引入第三套独立表达式求值实现

---

## 11. 建议的后续增强

不属于本次 P0 必做，但建议进入后续迭代：

- 为 `ConditionEngine` 增加公开的标准化入口
- 为 `GateEngine` 增加公开表达式评估接口
- 统一文档中的表达式语法规范
- 为条件求值失败增加结构化日志和诊断信息

---

**审批状态**: 待审批  
**技术负责人**: 待填写  
**预计完成日期**: 待填写
