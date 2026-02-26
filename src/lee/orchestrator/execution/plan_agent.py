"""
Plan Agent - LLM 分析任务，生成执行计划

负责分析 workflow 模板和参数，生成：
1. Instance YAML - 机器执行用
2. Plan Summary - 人类决策用
"""

import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.llm_executor import LLMExecutor


@dataclass
class PlanResult:
    """Plan 执行结果"""
    instance: Dict[str, Any]  # Instance YAML 内容
    summary: str  # Plan Summary Markdown
    version: int = 1
    success: bool = True
    error: Optional[str] = None


@dataclass
class PlanConfig:
    """Plan 配置"""
    mode: str = "suggest"  # simple/suggest/force (使用 ReviewMode 枚举)
    skip_conditions: List[str] = field(default_factory=list)
    review_criteria: List[str] = field(default_factory=list)

    def get_mode(self) -> str:
        """获取模式字符串"""
        return self.mode


class PlanAgent:
    """
    Plan Agent - 分析任务并生成执行计划

    输入:
        - 渲染后的 workflow 模板
        - 用户参数

    输出:
        - Instance YAML
        - Plan Summary (Markdown)
    """

    def __init__(self, llm_executor: Optional[LLMExecutor] = None):
        self.llm = llm_executor

    async def plan(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any],
        config: Optional[PlanConfig] = None
    ) -> PlanResult:
        """
        执行 Plan

        Args:
            template: 渲染后的 workflow 模板
            params: 用户参数
            config: Plan 配置

        Returns:
            PlanResult - 包含 Instance 和 Summary
        """
        config = config or PlanConfig()

        # 1. 分析模板
        analysis = self._analyze_template(template)

        # 2. 检查是否跳过 (simple 模式)
        if config.mode == "simple" and self._check_skip_conditions(analysis, config):
            return self._create_simple_instance(template, params, analysis)

        # 3. LLM 生成 Plan
        return await self._llm_plan(template, params, analysis, config)

    def _analyze_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """分析模板复杂度"""
        steps = template.get("steps", [])
        human_gates = template.get("human_in_the_loop", [])
        quality_gates = []

        # 统计涉及的质量门禁
        for step in steps:
            if "quality_gate" in step:
                quality_gates.append(step.get("quality_gate"))

        return {
            "step_count": len(steps),
            "agent_count": sum(1 for s in steps if s.get("kind") == "agent"),
            "skill_count": sum(1 for s in steps if s.get("kind") == "skill"),
            "gate_count": len(human_gates),
            "quality_gate_count": len(quality_gates),
            "has_implementation": any("implementation" in s.get("id", "").lower() for s in steps),
            "estimated_duration": self._estimate_duration(len(steps)),
        }

    def _estimate_duration(self, step_count: int) -> str:
        """估算执行时间"""
        if step_count <= 3:
            return "30min"
        elif step_count <= 7:
            return "2h"
        elif step_count <= 13:
            return "8h"
        else:
            return "1d"

    def _check_skip_conditions(self, analysis: Dict[str, Any], config: PlanConfig) -> bool:
        """检查是否满足跳过条件"""
        for condition in config.skip_conditions:
            if "steps.length <=" in condition:
                threshold = int(condition.split("<=")[1].strip())
                if analysis.get("step_count", 0) <= threshold:
                    return True
            if "complexity ==" in condition:
                complexity = condition.split("==")[1].strip()
                if analysis.get("complexity") == complexity:
                    return True
        return False

    async def _llm_plan(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any],
        analysis: Dict[str, Any],
        config: PlanConfig
    ) -> PlanResult:
        """使用 LLM 生成 Plan"""

        # 构建 prompt
        prompt = self._build_plan_prompt(template, params, analysis)

        # 调用 LLM
        if self.llm:
            response = await self.llm.execute({
                "prompt": prompt,
                "response_format": "yaml"
            })
            llm_output = response.get("generated_text", "")
        else:
            # 降级：使用模板分析
            return self._create_fallback_instance(template, params, analysis, config)

        # 解析 LLM 输出
        try:
            plan_data = yaml.safe_load(llm_output)
        except:
            return self._create_fallback_instance(template, params, analysis, config)

        # 生成 Instance
        instance = self._build_instance(template, params, analysis, plan_data, config)

        # 生成 Summary
        summary = self._build_summary(template, params, analysis, plan_data, config)

        return PlanResult(
            instance=instance,
            summary=summary,
            version=1,
            success=True
        )

    def _build_plan_prompt(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> str:
        """构建 Plan prompt"""
        template_yaml = yaml.dump(template, allow_unicode=True, default_flow_style=False)

        return f"""你是一个 Workflow Plan Agent。你的任务分析以下 workflow 模板，生成执行计划。

## 模板信息
```yaml
{template_yaml}
```

## 参数
{params}

## 模板分析
- 步骤数: {analysis['step_count']}
- Agent 步骤: {analysis['agent_count']}
- Skill 步骤: {analysis['skill_count']}
- Human Gates: {analysis['gate_count']}
- 质量门禁: {analysis['quality_gate_count']}
- 涉及代码实现: {analysis['has_implementation']}
- 预计执行时间: {analysis['estimated_duration']}

## 输出要求

请以 YAML 格式输出执行计划，包含：

```yaml
plan:
  mode: force  # simple/suggest/force
  complexity: high/medium/low
  needs_l3_split: true/false
  needs_review: true/false
  estimated_duration: "如 8h"
  reason: "决策原因"

success_criteria:
  simple:
    - "简单条件1"
    - "简单条件2"
  expressions:
    - "表达式条件1"

failure_criteria:
  simple:
    - "简单失败条件1"
  expressions:
    - "表达式失败条件1"

retry:
  enabled: true/false
  max_attempts: 3
  strategy: exponential
  base_delay: 10
```

决策规则：
1. 如果步骤数 > 7 或涉及代码实现，mode 应该是 force
2. 如果有 Human Gates，needs_review 应该是 true
3. 如果步骤数 <= 3，mode 可以是 simple
"""

    def _build_instance(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any],
        analysis: Dict[str, Any],
        plan_data: Dict[str, Any],
        config: PlanConfig
    ) -> Dict[str, Any]:
        """构建 Instance"""
        plan = plan_data.get("plan", {})
        success_criteria = plan_data.get("success_criteria", {})
        failure_criteria = plan_data.get("failure_criteria", {})
        retry = plan_data.get("retry", {})

        # 生成 workflow ID
        wf_id = f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 构建步骤列表
        steps = []
        for step in template.get("steps", []):
            steps.append({
                "id": step.get("id"),
                "name": step.get("name", step.get("id")),
                "status": "pending",
                "mandatory": step.get("mandatory", True),
                "retry_count": 0,
                "kind": step.get("kind", "agent"),
                "agent_id": step.get("agent_id", ""),
                "skill_id": step.get("skill_id", ""),
            })

        return {
            "kind": "workflow-instance",
            "id": wf_id,
            "name": template.get("name", "Workflow"),
            "template_ref": template.get("id", ""),
            "template_version": template.get("version", "1.0"),
            "phase_id": params.get("phase_id", ""),
            "plan": plan,
            "instance_config": {
                "success_criteria": success_criteria,
                "failure_criteria": failure_criteria,
                "retry": retry
            },
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "version": 1,
            "steps": steps
        }

    def _build_summary(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any],
        analysis: Dict[str, Any],
        plan_data: Dict[str, Any],
        config: PlanConfig
    ) -> str:
        """构建 Plan Summary (Markdown)"""
        plan = plan_data.get("plan", {})
        success = plan_data.get("success_criteria", {}).get("simple", [])
        failure = plan_data.get("failure_criteria", {}).get("simple", [])
        retry = plan_data.get("retry", {})

        return f"""# Plan Summary - {template.get('name', 'Workflow')}

## 基本信息
- **Template**: {template.get('id')} v{template.get('version')}
- **Phase ID**: {params.get('phase_id', 'N/A')}
- **Plan 模式**: {plan.get('mode', 'suggest')}
- **生成时间**: {datetime.now().isoformat()}

## 复杂度评估

| 维度 | 评估 | 说明 |
|------|------|------|
| 步骤数量 | {analysis['step_count']} | {"高" if analysis['step_count'] > 7 else "中" if analysis['step_count'] > 3 else "低"} |
| Agent 步骤 | {analysis['agent_count']} | |
| Skill 步骤 | {analysis['skill_count']} | |
| Human Gates | {analysis['gate_count']} | |
| 质量门禁 | {analysis['quality_gate_count']} | |

## 拆分决策

**是否需要 L3 拆分**: {plan.get('needs_l3_split', False)}

**原因**: {plan.get('reason', '根据复杂度分析')}

## Review Gate 模式

**模式**: {plan.get('mode', 'suggest')} ({config.mode})

**触发条件**:
- simple: 自动跳过
- suggest: {config.review_criteria or 'LLM 判断'}
- force: 始终需要人类审批

## 成功标准

### 简单条件
{chr(10).join(f'- [ ] {s}' for s in success) or '- 无'}

### 表达式条件
{chr(10).join(f'- [ ] {s}' for s in plan_data.get('success_criteria', {}).get('expressions', [])) or '- 无'}

## 失败标准

### 简单条件
{chr(10).join(f'- [x] {s}' for s in failure) or '- 无'}

### 表达式条件
{chr(10).join(f'- [x] {s}' for s in plan_data.get('failure_criteria', {}).get('expressions', [])) or '- 无'}

## 重试配置

- 最大重试: {retry.get('max_attempts', 3)} 次
- 重试策略: {retry.get('strategy', 'exponential')}
- 基础延迟: {retry.get('base_delay', 10)} 秒
- 副作用分析: {"是" if retry.get('side_effects_analysis') else "否"}

---
*此文档由 Plan Agent 自动生成*
"""

    def _create_simple_instance(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> PlanResult:
        """创建简单的 Instance（跳过 LLM）"""
        wf_id = f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        steps = []
        for step in template.get("steps", []):
            steps.append({
                "id": step.get("id"),
                "name": step.get("name", step.get("id")),
                "status": "pending",
                "mandatory": step.get("mandatory", True),
                "retry_count": 0,
            })

        instance = {
            "kind": "workflow-instance",
            "version": "1.0",
            "id": wf_id,
            "name": template.get("name", "Workflow"),
            "template_ref": template.get("id", ""),
            "template_version": template.get("version", "1.0"),
            "phase_id": params.get("phase_id", ""),
            "plan": {
                "mode": "simple",
                "complexity": "low" if analysis["step_count"] <= 3 else "medium",
                "needs_l3_split": False,
                "needs_review": False,
                "estimated_duration": analysis["estimated_duration"],
                "reason": "步骤数 <= 3，自动跳过"
            },
            "instance_config": {
                "success_criteria": {
                    "simple": ["all_steps_completed"],
                    "expressions": []
                },
                "failure_criteria": {
                    "simple": ["any_step_failed"],
                    "expressions": []
                },
                "retry": {
                    "enabled": True,
                    "max_attempts": 3,
                    "strategy": "exponential",
                    "base_delay": 10
                }
            },
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "version": 1,
            "steps": steps
        }

        summary = f"""# Plan Summary - {template.get('name')}

## 简化模式 (simple)

由于步骤数 <= 3，自动跳过 LLM Plan。

- 步骤数: {analysis['step_count']}
- 预计时间: {analysis['estimated_duration']}
- Review: 跳过

"""

        return PlanResult(instance=instance, summary=summary, version=1, success=True)

    def _create_fallback_instance(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any],
        analysis: Dict[str, Any],
        config: PlanConfig
    ) -> PlanResult:
        """创建降级 Instance（LLM 失败时使用）"""
        # 与 _create_simple 类似，但使用模板分析结果
        return self._create_simple_instance(template, params, analysis)


async def create_plan(
    template: Dict[str, Any],
    params: Dict[str, Any],
    llm_executor: Optional[LLMExecutor] = None,
    config: Optional[PlanConfig] = None
) -> PlanResult:
    """
    便捷函数：创建 Plan

    Args:
        template: Workflow 模板
        params: 参数
        llm_executor: LLM 执行器
        config: Plan 配置

    Returns:
        PlanResult
    """
    agent = PlanAgent(llm_executor)
    return await agent.plan(template, params, config)
