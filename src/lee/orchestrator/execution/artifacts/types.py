"""
Artifact System Type Definitions

定义产出物管理系统的核心类型枚举。
"""

from enum import Enum
from typing import Dict, List, Set


class ArtifactType(str, Enum):
    """产出物主类型"""

    CONTRACT = "CONTRACT"  # 契约类：需求、API、测试等
    DOCUMENT = "DOCUMENT"  # 文档类：说明、记录、总结等
    CODE_REF = "CODE_REF"  # 代码引用类：git SHA 引用
    PATCH = "PATCH"  # 补丁类：git patch 文件
    TEST = "TEST"  # 测试类：测试报告、用例等
    HANDOVER = "HANDOVER"  # 移交类：部门/阶段间移交
    LOG = "LOG"  # 日志类
    INTERMEDIATE = "INTERMEDIATE"  # 中间产物


class ArtifactStatus(str, Enum):
    """产出物状态"""

    DRAFT = "DRAFT"  # 草稿状态，可编辑
    ACTIVE = "ACTIVE"  # 活跃状态，正在使用
    FROZEN = "FROZEN"  # 冻结状态，不可变
    ARCHIVED = "ARCHIVED"  # 归档状态
    DEPRECATED = "DEPRECATED"  # 废弃状态


class AdoptMode(str, Enum):
    """Adopt 模式"""

    COPY = "copy_mode"  # 复制文件内容
    REFERENCE = "reference_mode"  # 仅保存 git 引用


class GovernanceKind(str, Enum):
    """
    治理类别 (v1.0 新增)

    正交于 type/category 的维度，用于文件治理策略：
    - EVIDENCE: 过程证据 (测试报告、运行日志、Context Bundle)
    - TRANSFER: 中间产物 (PRD/API 契约、设计文档、测试计划)
    - DELIVERABLE: 制成品 (实现代码、可发布包)
    - KNOWLEDGE: 知识沉淀 (陷阱指南、规范文档)
    - STATE: 系统状态 (保留接口，暂不使用)
    """

    EVIDENCE = "evidence"
    TRANSFER = "transfer"
    DELIVERABLE = "deliverable"
    KNOWLEDGE = "knowledge"
    STATE = "state"  # 暂不使用，预留接口


class ArtifactCategoryRegistry:
    """
    产出物类别注册表

    从配置文件生成强类型类别枚举，实现配置驱动的类型系统。
    """

    _categories: Dict[str, Set[str]] = {
        "CONTRACT": {
            "frozen_prd",
            "api_contract",
            "test_plan",
            "design_doc",
        },
        "DOCUMENT": {
            "readme",
            "usage_guide",
            "investigation_report",
            "handover_doc",
        },
        "CODE_REF": {
            "implementation",
            "config",
            "script",
        },
        "PATCH": {
            "feature_patch",
            "bugfix_patch",
            "refactor_patch",
        },
        "TEST": {
            "test_report",
            "test_case",
            "coverage_report",
        },
        "HANDOVER": {
            "to_qa",
            "to_backend",
            "to_frontend",
            "to_devops",
        },
        "LOG": {
            "execution_log",
            "error_log",
            "debug_log",
        },
        "INTERMEDIATE": {
            "draft",
            "temp",
            "scratch",
        },
    }

    @classmethod
    def load_from_config(cls, config_path: str = "spec-global/artifacts/config.yaml") -> None:
        """从配置文件加载类别定义"""
        import yaml
        from pathlib import Path

        config_file = Path(config_path)
        if not config_file.exists():
            return

        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if "artifact_types" in config:
            categories = {}
            for type_name, type_config in config["artifact_types"].items():
                categories[type_name] = set(type_config.get("categories", []))
            cls._categories = categories

    @classmethod
    def get_categories(cls, artifact_type: str) -> Set[str]:
        """获取指定类型的所有类别"""
        return cls._categories.get(artifact_type, set())

    @classmethod
    def is_valid_category(cls, artifact_type: str, category: str) -> bool:
        """验证类别是否属于指定类型"""
        return category in cls._categories.get(artifact_type, set())

    @classmethod
    def all_categories(cls) -> Set[str]:
        """获取所有类别"""
        all_cats = set()
        for categories in cls._categories.values():
            all_cats.update(categories)
        return all_cats


# 预加载配置
ArtifactCategoryRegistry.load_from_config()


# 动态创建 ArtifactCategory 类
class ArtifactCategory(str, Enum):
    """产出物类别 (动态生成)"""

    # 类别值会在运行时从配置加载
    # 这里提供基础验证方法

    @classmethod
    def values(cls) -> List[str]:
        """获取所有有效类别值"""
        return list(ArtifactCategoryRegistry.all_categories())

    @classmethod
    def for_type(cls, artifact_type: ArtifactType) -> List[str]:
        """获取指定类型的类别列表"""
        return list(ArtifactCategoryRegistry.get_categories(artifact_type.value))


# 部门枚举
class Department(str, Enum):
    """部门定义 (用于 active/ 目录组织)"""

    PM = "pm"
    BACKEND = "backend"
    FRONTEND = "frontend"
    QA = "qa"
    DEVOPS = "devops"
    DATA = "data"
    DESIGN = "design"
