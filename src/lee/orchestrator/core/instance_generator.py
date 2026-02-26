"""
Instance Generator - 根据 Plan 生成 Instance 文件

负责：
1. 根据 PlanResult 生成 Instance YAML
2. 版本管理（v1, v2, ...）
3. 保存到 instances/l2|l3/ 目录
"""

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class InstanceMetadata:
    """Instance 元数据"""
    workflow_id: str
    version: int
    phase_id: str
    template_ref: str
    template_version: str
    created_at: str


class InstanceGenerator:
    """
    Instance 生成器

    用法：
        generator = InstanceGenerator(workspace_root)
        metadata = generator.generate(plan_result, phase_id)
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        """
        初始化 Instance Generator

        Args:
            workspace_root: 工作空间根目录，默认当前目录
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.instances_dir = self.workspace_root / ".workflow" / "instances"

    def generate(
        self,
        plan_result: Any,
        phase_id: str,
        tier: str = "l2"
    ) -> InstanceMetadata:
        """
        生成 Instance 文件

        Args:
            plan_result: PlanAgent 返回的 PlanResult
            phase_id: Phase ID
            tier: l2 或 l3

        Returns:
            InstanceMetadata - 包含 workflow_id 和版本信息
        """
        # 获取 workflow_id 和版本
        workflow_id = plan_result.instance.get("id", f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        version = self._get_next_version(workflow_id, tier)

        # 构建 Instance 数据
        instance = self._build_instance(plan_result, phase_id, version)

        # 保存文件
        file_path = self._save_instance(instance, workflow_id, tier, version)

        return InstanceMetadata(
            workflow_id=workflow_id,
            version=version,
            phase_id=phase_id,
            template_ref=instance.get("template_ref", ""),
            template_version=instance.get("template_version", "1.0"),
            created_at=instance.get("created_at", "")
        )

    def _get_next_version(self, workflow_id: str, tier: str) -> int:
        """获取下一个版本号"""
        tier_dir = self.instances_dir / tier
        if not tier_dir.exists():
            return 1

        # 查找现有版本
        existing = list(tier_dir.glob(f"{workflow_id}-v*.yaml"))
        if not existing:
            return 1

        # 提取最大版本号
        max_version = 0
        for f in existing:
            try:
                v = int(f.stem.split("-v")[-1])
                max_version = max(max_version, v)
            except (ValueError, IndexError):
                continue

        return max_version + 1

    def _build_instance(
        self,
        plan_result: Any,
        phase_id: str,
        version: int
    ) -> Dict[str, Any]:
        """构建 Instance 数据"""
        instance = plan_result.instance.copy()

        # 更新版本信息
        instance["version"] = version
        instance["phase_id"] = phase_id
        instance["status"] = "pending"
        instance["updated_at"] = datetime.now().isoformat()

        return instance

    def _save_instance(
        self,
        instance: Dict[str, Any],
        workflow_id: str,
        tier: str,
        version: int
    ) -> Path:
        """保存 Instance 文件"""
        tier_dir = self.instances_dir / tier
        tier_dir.mkdir(parents=True, exist_ok=True)

        file_path = tier_dir / f"{workflow_id}-v{version}.yaml"

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(instance, f, allow_unicode=True, default_flow_style=False)

        return file_path

    def load_latest(self, workflow_id: str, tier: str = "l2") -> Optional[Dict[str, Any]]:
        """
        加载最新版本的 Instance

        Args:
            workflow_id: Workflow ID
            tier: l2 或 l3

        Returns:
            Instance 数据或 None
        """
        tier_dir = self.instances_dir / tier
        if not tier_dir.exists():
            return None

        # 查找所有版本
        versions = list(tier_dir.glob(f"{workflow_id}-v*.yaml"))
        if not versions:
            return None

        # 按版本号排序，取最新
        versions.sort(key=lambda f: int(f.stem.split("-v")[-1]))
        latest = versions[-1]

        with open(latest, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_version(
        self,
        workflow_id: str,
        version: int,
        tier: str = "l2"
    ) -> Optional[Dict[str, Any]]:
        """
        加载指定版本的 Instance

        Args:
            workflow_id: Workflow ID
            version: 版本号
            tier: l2 或 l3

        Returns:
            Instance 数据或 None
        """
        tier_dir = self.instances_dir / tier
        file_path = tier_dir / f"{workflow_id}-v{version}.yaml"

        if not file_path.exists():
            return None

        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def update_status(
        self,
        workflow_id: str,
        status: str,
        tier: str = "l2",
        version: Optional[int] = None
    ) -> bool:
        """
        更新 Instance 状态

        Args:
            workflow_id: Workflow ID
            status: 新状态
            tier: l2 或 l3
            version: 指定版本，默认最新

        Returns:
            是否成功
        """
        if version is None:
            instance = self.load_latest(workflow_id, tier)
        else:
            instance = self.load_version(workflow_id, version, tier)

        if not instance:
            return False

        instance["status"] = status
        instance["updated_at"] = datetime.now().isoformat()

        if version is None:
            version = instance.get("version", 1)

        file_path = self.instances_dir / tier / f"{workflow_id}-v{version}.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(instance, f, allow_unicode=True, default_flow_style=False)

        return True

    def update_step_status(
        self,
        workflow_id: str,
        step_id: str,
        status: str,
        output: Optional[Dict[str, Any]] = None,
        tier: str = "l2",
        version: Optional[int] = None
    ) -> bool:
        """
        更新步骤状态

        Args:
            workflow_id: Workflow ID
            step_id: 步骤 ID
            status: 新状态
            output: 步骤输出
            tier: l2 或 l3
            version: 指定版本，默认最新

        Returns:
            是否成功
        """
        if version is None:
            instance = self.load_latest(workflow_id, tier)
        else:
            instance = self.load_version(workflow_id, version, tier)

        if not instance:
            return False

        # 更新步骤状态
        steps = instance.get("steps", [])
        for step in steps:
            if step.get("id") == step_id:
                step["status"] = status
                step["updated_at"] = datetime.now().isoformat()
                if output:
                    step["output"] = output
                break

        instance["updated_at"] = datetime.now().isoformat()

        # 保存
        if version is None:
            version = instance.get("version", 1)

        file_path = self.instances_dir / tier / f"{workflow_id}-v{version}.yaml"
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(instance, f, allow_unicode=True, default_flow_style=False)

        return True

    def list_instances(self, tier: str = "l2") -> List[Dict[str, Any]]:
        """
        列出所有 Instance

        Args:
            tier: l2 或 l3

        Returns:
            Instance 列表（基本信息）
        """
        tier_dir = self.instances_dir / tier
        if not tier_dir.exists():
            return []

        instances = []
        for f in tier_dir.glob("*.yaml"):
            try:
                with open(f, encoding="utf-8") as fp:
                    data = yaml.safe_load(fp)
                    instances.append({
                        "id": data.get("id"),
                        "version": data.get("version"),
                        "name": data.get("name"),
                        "status": data.get("status"),
                        "template_ref": data.get("template_ref"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                    })
            except Exception:
                continue

        return sorted(instances, key=lambda x: x.get("created_at", ""), reverse=True)


async def generate_instance(
    plan_result: Any,
    phase_id: str,
    workspace_root: Optional[Path] = None,
    tier: str = "l2"
) -> InstanceMetadata:
    """
    便捷函数：生成 Instance

    Args:
        plan_result: PlanResult
        phase_id: Phase ID
        workspace_root: 工作空间根目录
        tier: l2 或 l3

    Returns:
        InstanceMetadata
    """
    generator = InstanceGenerator(workspace_root)
    return generator.generate(plan_result, phase_id, tier)
