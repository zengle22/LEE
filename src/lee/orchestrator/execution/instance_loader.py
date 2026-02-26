"""
Instance Loader Mixin - 支持从 Instance 文件加载执行

提供从 Instance YAML 文件加载步骤和配置的能力，
使 Orchestrator 可以从 Plan 生成的 Instance 执行。
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.template_manager import Step


class InstanceLoaderMixin:
    """
    Instance Loader Mixin

    用法：
        class MyOrchestrator(InstanceLoaderMixin, OtherMixins):
            pass
    """

    def _is_instance_path(self, template_id: str) -> bool:
        """
        判断 template_id 是否是 Instance 文件路径

        Args:
            template_id: 模板 ID 或文件路径

        Returns:
            是否是 Instance 文件
        """
        path = Path(template_id)
        # 检查是否是 .yaml 文件
        if not path.suffix == ".yaml":
            return False
        # 检查路径中是否包含 instances
        if "instances" in str(path):
            return True
        # 检查文件名是否是 wf_*-v*.yaml 格式
        name = path.stem
        if "-v" in name:
            try:
                version = int(name.split("-v")[-1])
                return True
            except ValueError:
                pass
        return False

    def _load_instance_file(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        加载 Instance 文件

        Args:
            template_id: Instance 文件路径

        Returns:
            Instance 数据或 None
        """
        path = Path(template_id)
        if not path.exists():
            return None

        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return None

    def _get_steps_from_instance(
        self,
        instance: Dict[str, Any]
    ) -> List[Step]:
        """
        从 Instance 获取步骤列表

        Args:
            instance: Instance 数据

        Returns:
            Step 列表
        """
        steps = []
        for step_def in instance.get("steps", []):
            step = Step(
                id=step_def.get("id", ""),
                name=step_def.get("name", step_def.get("id", "")),
                kind=step_def.get("kind", "agent"),
                agent_id=step_def.get("agent_id"),
                skill_id=step_def.get("skill_id"),
                gate_id=step_def.get("gate_id"),
            )
            steps.append(step)
        return steps

    def _get_instance_config(
        self,
        instance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从 Instance 获取配置

        Args:
            instance: Instance 数据

        Returns:
            配置字典
        """
        return instance.get("instance_config", {})

    def _get_plan_info(
        self,
        instance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从 Instance 获取 Plan 信息

        Args:
            instance: Instance 数据

        Returns:
            Plan 信息
        """
        return instance.get("plan", {})


def get_steps_from_instance(template_id: str) -> Optional[List[Step]]:
    """
    便捷函数：从 Instance 文件获取步骤

    Args:
        template_id: Instance 文件路径

    Returns:
        Step 列表或 None
    """
    path = Path(template_id)
    if not path.exists() or path.suffix != ".yaml":
        return None

    # 检查是否是 Instance 格式
    try:
        with open(path, encoding="utf-8") as f:
            instance = yaml.safe_load(f)

        if instance.get("kind") != "workflow-instance":
            return None

        # 提取步骤
        steps = []
        for step_def in instance.get("steps", []):
            step = Step(
                id=step_def.get("id", ""),
                name=step_def.get("name", step_def.get("id", "")),
                kind=step_def.get("kind", "agent"),
                agent_id=step_def.get("agent_id"),
                skill_id=step_def.get("skill_id"),
                gate_id=step_def.get("gate_id"),
            )
            steps.append(step)
        return steps
    except Exception:
        return None
