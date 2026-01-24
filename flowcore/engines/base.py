"""
Engine 执行器基类和注册机制
"""

from abc import ABC, abstractmethod
from typing import Dict, Callable, Optional, List
from pathlib import Path

from .protocol import StepExecutionRequest, StepExecutionResult, BaseExecutor


class EngineRegistry:
    """
    Engine 注册表 - 管理所有可用的执行引擎

    使用方式：
        @EngineRegistry.register("metagpt")
        def create_metagpt_executor(agent_spec, project_dir):
            return MetaGPTExecutor(project_dir, agent_spec)

        # 使用
        executor = EngineRegistry.create(agent_spec, project_dir)
    """

    # 注册表：engine_type -> factory_function
    _registry: Dict[str, Callable[[Dict, str], BaseExecutor]] = {}

    @classmethod
    def register(cls, engine_type: str):
        """
        装饰器：注册 Engine 工厂函数

        Args:
            engine_type: Engine 类型标识（如 "metagpt", "llm"）

        Example:
            @EngineRegistry.register("metagpt")
            def create_metagpt_executor(agent_spec, project_dir):
                return MetaGPTExecutor(project_dir, agent_spec)
        """
        def decorator(factory: Callable[[Dict, str], BaseExecutor]):
            cls._registry[engine_type] = factory
            return factory
        return decorator

    @classmethod
    def create(cls, agent_spec: Dict, project_dir: str) -> BaseExecutor:
        """
        创建 Executor 实例

        Args:
            agent_spec: Agent 规范（包含 engine 配置）
            project_dir: 项目目录

        Returns:
            Executor 实例

        Raises:
            ValueError: 如果 engine_type 未注册
        """
        engine_config = agent_spec.get("engine", {})
        engine_type = engine_config.get("type", "llm")  # 默认使用 llm

        factory = cls._registry.get(engine_type)

        if not factory:
            # 尝试动态导入
            factory = cls._try_dynamic_import(engine_type)

        if not factory:
            raise ValueError(
                f"Unknown engine type: '{engine_type}'. "
                f"Available engines: {list(cls._registry.keys())}"
            )

        return factory(agent_spec, project_dir)

    @classmethod
    def _try_dynamic_import(cls, engine_type: str) -> Optional[Callable]:
        """
        尝试动态导入 Engine 模块

        支持的导入路径：
        - flowcore.engines.{engine_type}.executor
        - flowcore.engines.{engine_type}

        Args:
            engine_type: Engine 类型

        Returns:
            工厂函数或 None
        """
        import importlib

        # 尝试 1: flowcore.engines.{engine_type}.executor
        try:
            module = importlib.import_module(f"flowcore.engines.{engine_type}.executor")
            if hasattr(module, "create_executor"):
                return module.create_executor
        except ImportError:
            pass

        # 尝试 2: flowcore.engines.{engine_type}
        try:
            module = importlib.import_module(f"flowcore.engines.{engine_type}")
            if hasattr(module, "create_executor"):
                return module.create_executor
        except ImportError:
            pass

        return None

    @classmethod
    def list_engines(cls) -> List[str]:
        """列出所有已注册的 Engine 类型"""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, engine_type: str) -> bool:
        """检查 Engine 是否已注册"""
        return engine_type in cls._registry


class AbstractExecutor(ABC):
    """
    Executor 抽象基类

    所有 Engine Executor 都应该继承此类并实现 execute 方法。
    """

    def __init__(self, project_dir: str, agent_spec: Dict):
        """
        初始化 Executor

        Args:
            project_dir: 项目目录
            agent_spec: Agent 规范
        """
        self.project_dir = Path(project_dir).resolve()
        self.agent_spec = agent_spec
        self.engine_config = agent_spec.get("engine", {})

    @abstractmethod
    async def execute(self, request: StepExecutionRequest) -> StepExecutionResult:
        """
        执行步骤 - 子类必须实现

        Args:
            request: 执行请求

        Returns:
            执行结果
        """
        pass

    def get_engine_type(self) -> str:
        """获取 Engine 类型标识"""
        return self.engine_config.get("type", "unknown")

    def validate_request(self, request: StepExecutionRequest) -> tuple[bool, Optional[str]]:
        """
        验证请求是否有效

        子类可以重写此方法以添加自定义验证逻辑。

        Args:
            request: 执行请求

        Returns:
            (是否有效, 错误信息)
        """
        # 基本验证
        if not request.step_id:
            return False, "step_id is required"

        if not request.project_dir:
            return False, "project_dir is required"

        # 检查超时设置
        if request.timeout_seconds <= 0:
            return False, "timeout_seconds must be positive"

        return True, None

    def _build_system_prompt(self, request: StepExecutionRequest) -> str:
        """
        构建 System Prompt

        子类可以重写此方法以自定义 Prompt 构建逻辑。

        Args:
            request: 执行请求

        Returns:
            System Prompt 字符串
        """
        # 从 agent_spec 获取 system_prompt
        system_prompt = request.get_system_prompt()

        # 如果没有定义，使用默认值
        if not system_prompt:
            system_prompt = f"You are a helpful AI assistant executing step '{request.step_id}'."

        # 添加上下文信息
        context = request.context

        # 添加项目信息
        project_meta = context.get("project_meta", {})
        if project_meta:
            system_prompt += f"\n\nProject: {project_meta.get('name', 'Unknown')}"

        # 添加输入产物信息
        inputs = request.get_inputs()
        if inputs:
            system_prompt += "\n\n## Upstream Outputs (Inputs):\n"
            for inp in inputs:
                system_prompt += f"\n### {inp.id}"
                if inp.path:
                    system_prompt += f"\nPath: {inp.path}"
                # 添加文件内容
                if hasattr(inp, 'content') and inp.content:
                    # 限制内容长度避免 prompt 过长
                    max_content_length = 8000
                    content = inp.content
                    if len(content) > max_content_length:
                        content = content[:max_content_length] + "\n...[content truncated]"
                    system_prompt += f"\nContent:\n```\n{content}\n```"
                elif inp.summary:
                    system_prompt += f"\n{inp.summary}"

        return system_prompt

    def _build_user_message(self, request: StepExecutionRequest) -> str:
        """
        构建 User Message

        子类可以重写此方法以自定义 Message 构建逻辑。

        Args:
            request: 执行请求

        Returns:
            User Message 字符串
        """
        # 从 context 获取 step_description
        step_description = request.context.get("step_description", "")

        # 如果没有定义，使用默认值
        if not step_description:
            step_description = f"Execute step '{request.step_id}'"

        # 添加输出要求
        contracts = request.get_contracts()
        if contracts:
            output_contract = contracts.get("output_schema")
            if output_contract:
                step_description += "\n\nOutput requirements:"
                step_description += f"\n{output_contract.schema}"

        return step_description

    def _extract_outputs_from_workspace(
        self,
        workspace_dir: Path,
        expected_outputs: Optional[List[str]] = None
    ) -> List[str]:
        """
        从工作目录提取输出文件

        Args:
            workspace_dir: 工作目录
            expected_outputs: 期望的输出文件列表（相对路径）

        Returns:
            输出文件路径列表（相对路径）
        """
        outputs = []

        # 如果有期望的输出列表，优先检查这些文件
        if expected_outputs:
            for out_path in expected_outputs:
                full_path = workspace_dir / out_path
                if full_path.exists():
                    outputs.append(out_path)

        # 如果没有期望列表，或期望列表的文件都不存在，扫描目录
        if not outputs:
            for file in workspace_dir.rglob("*"):
                if file.is_file():
                    # 跳过隐藏文件和临时文件
                    if file.name.startswith("."):
                        continue
                    if file.suffix in [".tmp", ".bak"]:
                        continue

                    # 返回相对路径
                    rel_path = file.relative_to(workspace_dir)
                    outputs.append(str(rel_path))

        return outputs
