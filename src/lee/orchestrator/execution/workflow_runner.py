"""
Workflow Runner - Plan → Instance → Execute 流程控制器

负责：
1. 加载和渲染模板
2. 调用 Plan Agent 生成 Plan
3. 处理 Review Gate
4. 生成 Instance 文件
5. 触发 Orchestrator 执行
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

from lee.orchestrator.core.template_engine import TemplateEngine
from lee.orchestrator.core.template_resolver import TemplateResolver
from lee.orchestrator.core.instance_generator import InstanceGenerator
from lee.orchestrator.execution.plan_agent import PlanAgent, PlanConfig, create_plan
from lee.orchestrator.execution.llm_executor import LLMExecutor
from lee.orchestrator.execution.review_gate import ReviewGate, check_review_gate
from lee.orchestrator.execution.concurrency_scope import derive_concurrency_scope


def _get_pm_workflow():
    """Lazy import to avoid circular import"""
    from lee.orchestrator.api import pm_workflow
    return pm_workflow


@dataclass
class WorkflowRunConfig:
    """工作流运行配置"""
    workflow_key: str
    template_path: Path
    params: Dict[str, Any]
    project_root: Path
    plan_mode: str = "simple"  # simple/suggest/force
    skip_plan: bool = False
    instance_id: Optional[str] = None  # 指定从 Instance 运行
    auto_approve: bool = False  # 自动批准（测试用，生产环境应为 False）
    ssot_root_id: Optional[str] = None  # SSOT Root ID (任务立项 ID)


@dataclass
class WorkflowRunResult:
    """工作流运行结果"""
    workflow_id: str
    instance_path: Optional[Path]
    plan_summary: Optional[str]
    success: bool
    error: Optional[str] = None


class WorkflowRunner:
    """
    Workflow Runner - 统一执行入口

    支持两种模式：
    1. Plan 模式：Template → Plan → Instance → Execute
    2. Instance 模式：直接加载 Instance 执行
    """

    def __init__(self, config: WorkflowRunConfig):
        self.config = config
        self.plan_agent: Optional[PlanAgent] = None
        self.instance_generator: Optional[InstanceGenerator] = None

    async def run(self) -> WorkflowRunResult:
        """
        执行工作流

        Returns:
            WorkflowRunResult
        """
        try:
            # 1. 确定执行模式
            if self.config.instance_id:
                return await self._run_from_instance()
            elif self.config.skip_plan:
                return await self._run_direct()
            else:
                return await self._run_with_plan()
        except Exception as e:
            logger.error(f"Workflow run failed: {e}", exc_info=True)
            return WorkflowRunResult(
                workflow_id="",
                instance_path=None,
                plan_summary=None,
                success=False,
                error=str(e)
            )

    async def _run_with_plan(self) -> WorkflowRunResult:
        """使用 Plan 模式执行"""
        # 1. 加载和渲染模板
        template = await self._load_template()

        # 2. 调用 Plan Agent
        plan_config = PlanConfig(
            mode=self.config.plan_mode,
            skip_conditions=["steps.length <= 3"],
            review_criteria=["complexity == high", "gate_count > 0"]
        )

        llm = LLMExecutor()
        plan_result = await create_plan(
            template=template,
            params=self.config.params,
            llm_executor=llm,
            config=plan_config
        )

        # 3. 检查 Review Gate
        plan_mode = plan_result.instance.get("plan", {}).get("mode", "simple")
        needs_review = plan_result.instance.get("plan", {}).get("needs_review", False)

        # 检查是否需要审批
        gate = ReviewGate(auto_approve=self.config.auto_approve)
        decision = await gate.check(plan_result, plan_mode)

        if not decision.approved:
            # 需要人类审批
            user_decision = await gate.request_approval(
                plan_result.summary,
                self.config.workflow_key
            )
            if not user_decision.approved:
                return WorkflowRunResult(
                    workflow_id="",
                    instance_path=None,
                    plan_summary=plan_result.summary,
                    success=False,
                    error=f"Plan rejected: {user_decision.reason}"
                )

        # 4. 生成 Instance
        self.instance_generator = InstanceGenerator(self.config.project_root)
        instance_meta = self.instance_generator.generate(
            plan_result=plan_result,
            phase_id=self.config.params.get("phase_id", ""),
            tier="l2"
        )

        # 5. 创建工作流实例
        workflow_id = await self._create_workflow(instance_meta.instance_path)

        return WorkflowRunResult(
            workflow_id=workflow_id,
            instance_path=instance_meta.instance_path,
            plan_summary=plan_result.summary,
            success=True
        )

    async def _run_from_instance(self) -> WorkflowRunResult:
        """从 Instance 文件执行"""
        self.instance_generator = InstanceGenerator(self.config.project_root)

        # 加载 Instance
        instance = self.instance_generator.load_latest(
            workflow_id=self.config.instance_id,
            tier="l2"
        )

        if not instance:
            return WorkflowRunResult(
                workflow_id="",
                instance_path=None,
                plan_summary=None,
                success=False,
                error=f"Instance not found: {self.config.instance_id}"
            )

        # 直接创建工作流，传递 instance_path
        instance_path = self.instance_generator.instances_dir / "l2" / f"{self.config.instance_id}-v{instance.get('version', 1)}.yaml"
        workflow_id = await self._create_workflow(instance_path)

        return WorkflowRunResult(
            workflow_id=workflow_id,
            instance_path=instance_path,
            plan_summary=None,
            success=True
        )

    async def _run_direct(self) -> WorkflowRunResult:
        """直接执行（跳过 Plan）"""
        # 渲染模板
        template = await self._load_template()

        # 直接创建工作流
        workflow_id = await self._create_workflow(self.config.template_path)

        return WorkflowRunResult(
            workflow_id=workflow_id,
            instance_path=None,
            plan_summary=None,
            success=True
        )

    async def _load_template(self) -> Dict[str, Any]:
        """加载和渲染模板"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 读取模板文件
        with open(self.config.template_path, encoding="utf-8") as f:
            template_content = f.read()

        # 构建目录上下文
        dir_context = self._build_dir_context()
        logger.info(f"Directory context: {dir_context}")

        # 渲染模板
        engine = TemplateEngine()
        from datetime import datetime
        render_context = {
            "params": self.config.params,
            **self.config.params,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
            "now": datetime.now(),
            **dir_context,  # 注入目录变量
        }
        logger.info(f"Render context keys: {list(render_context.keys())}")
        
        rendered = engine.render_string(template_content, render_context)
        
        # 检查渲染后的路径变量
        if "{{ tests_dir }}" in rendered:
            logger.warning("WARNING: {{ tests_dir }} was NOT rendered!")
        if "{{ qa_specs_dir }}" in rendered:
            logger.warning("WARNING: {{ qa_specs_dir }} was NOT rendered!")
        
        # 解析为 Dict
        return yaml.safe_load(rendered)

    def _build_dir_context(self) -> Dict[str, str]:
        """Build directory context for template rendering.

        Returns a dict mapping variable names to directory paths.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 尝试从 .project/dirs.yaml 加载
        dirs_yaml_path = self.config.project_root / ".project" / "dirs.yaml"
        context = {}
        
        if dirs_yaml_path.exists():
            with open(dirs_yaml_path, 'r', encoding='utf-8') as f:
                dirs_config = yaml.safe_load(f) or {}

            directories = dirs_config.get("directories", {})
            logger.info(f"Loaded directories: {list(directories.keys())}")

            # 直接映射目录配置到模板变量
            # 注意：spec_dir 和 specs_dir 是同一个东西的不同命名
            if "specs_dir" in directories:
                context["specs_dir"] = directories["specs_dir"].get("path", "spec")
            elif "spec_dir" in directories:
                context["specs_dir"] = directories["spec_dir"].get("path", "spec")
            else:
                context["specs_dir"] = "spec"
            
            if "qa_specs_dir" in directories:
                context["qa_specs_dir"] = directories["qa_specs_dir"].get("path", "spec/qa")
            else:
                context["qa_specs_dir"] = "spec/qa"
            
            # 其他目录直接映射
            for dir_name in ["src_dir", "docs_dir", "knowledge_dir", "tests_dir", "artifacts_dir",
                            "config_dir", "workflow_dir", "tools_dir", 
                            "deploy_dir", "legacy_dir"]:
                if dir_name in directories:
                    context[dir_name] = directories[dir_name].get("path", dir_name.replace("_dir", ""))
                else:
                    # 默认值
                    defaults = {
                        "src_dir": "src",
                        "docs_dir": "docs",
                        "knowledge_dir": "knowledge",
                        "tests_dir": "tests",
                        "artifacts_dir": ".artifacts",
                        "config_dir": ".project",
                        "workflow_dir": ".workflow",
                        "tools_dir": "tools",
                        "deploy_dir": "deploy",
                        "legacy_dir": "legacy",
                    }
                    context[dir_name] = defaults.get(dir_name, dir_name.replace("_dir", ""))
            
            logger.info(f"Built context: {context}")
        else:
            # 使用默认值
            context = {
                "specs_dir": "spec",
                "qa_specs_dir": "spec/qa",
                "src_dir": "src",
                "docs_dir": "docs",
                "knowledge_dir": "knowledge",
                "tests_dir": "tests",
                "artifacts_dir": ".artifacts",
                "config_dir": ".project",
                "workflow_dir": ".workflow",
                "tools_dir": "tools",
                "deploy_dir": "deploy",
                "legacy_dir": "legacy",
            }
            logger.warning(f"dirs.yaml not found, using defaults: {context}")
        
        return context

    async def _create_workflow(self, instance_path: Path) -> str:
        """创建工作流实例"""
        pm_workflow = _get_pm_workflow()
        scope_info = derive_concurrency_scope(
            self.config.workflow_key,
            self.config.params,
            self.config.project_root,
        )
        result = pm_workflow(
            "create",
            project_dir=str(self.config.project_root),
            level="task",
            template_id=str(instance_path),
            data={
                "params": self.config.params,
                "workflow_key": self.config.workflow_key,
                "instance_path": str(instance_path),
                "concurrency_scope": scope_info.concurrency_scope,
                "concurrency_key": scope_info.concurrency_key,
                "scope_source": scope_info.scope_source,
            }
        )

        if "error" in result:
            raise Exception(result.get("error"))

        return result.get("workflow_id", "")


async def run_workflow(
    workflow_key: str,
    template_path: Path,
    params: Dict[str, Any],
    project_root: Path,
    plan_mode: str = "suggest",
    skip_plan: bool = False,
    instance_id: Optional[str] = None,
    ssot_root_id: Optional[str] = None
) -> WorkflowRunResult:
    """
    便捷函数：运行工作流

    Args:
        workflow_key: Workflow key
        template_path: 模板路径
        params: 参数
        project_root: 项目根目录
        plan_mode: Plan 模式
        skip_plan: 是否跳过 Plan
        instance_id: Instance ID（从 Instance 运行）
        ssot_root_id: SSOT Root ID（任务立项 ID）

    Returns:
        WorkflowRunResult
    """
    config = WorkflowRunConfig(
        workflow_key=workflow_key,
        template_path=template_path,
        params=params,
        project_root=project_root,
        plan_mode=plan_mode,
        skip_plan=skip_plan,
        instance_id=instance_id,
        ssot_root_id=ssot_root_id
    )

    runner = WorkflowRunner(config)
    return await runner.run()
