"""
SSOT Service - SSOT 真理链服务层

提供 SSOT 真理链校验、影响分析等服务。
CLI 和 Gate 共用此服务层。
"""

from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

from .manager import ArtifactManager
from .models import ArtifactMetadata
from .types import ArtifactType


class SSOTService:
    """
    SSOT 真理链服务层

    提供：
    1. 真理链完整性校验
    2. 影响范围分析
    3. 真理链路径展示
    """

    def __init__(self, artifact_manager: ArtifactManager):
        """
        初始化 SSOT 服务

        Args:
            artifact_manager: ArtifactManager 实例
        """
        self.manager = artifact_manager

    def validate(
        self,
        run_id: Optional[str] = None,
        release: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        校验真理链完整性

        v1.0 规则:
        1. 所有 api_contract 必须有 derived_from 指向某个 prd_contract
        2. 所有 implementation (CODE_REF) 必须有 implements 指向至少一个 api_contract
        3. 所有 test_plan 必须有 verifies 指向至少一个 PRD 或 API

        Args:
            run_id: 按 run ID 校验
            release: 按 release tag 校验

        Returns:
            (是否通过，错误列表)
        """
        errors = []

        # 获取待校验的 artifacts
        artifacts = self._get_artifacts_for_validation(run_id, release)

        # 建立索引便于查找
        by_id: Dict[str, ArtifactMetadata] = {a.id: a for a in artifacts}
        prd_contracts = self._get_prd_contracts(artifacts)
        api_contracts = self._get_api_contracts(artifacts)

        # 规则 1: api_contract 必须有 derived_from 指向某个 prd_contract
        errors.extend(self._validate_api_contracts(api_contracts, prd_contracts, by_id))

        # 规则 2: implementation 必须有 implements
        errors.extend(self._validate_implementations(artifacts, api_contracts))

        # 规则 3: test_plan 必须有 verifies
        errors.extend(self._validate_test_plans(artifacts, prd_contracts, api_contracts))

        return len(errors) == 0, errors

    def _get_artifacts_for_validation(
        self,
        run_id: Optional[str],
        release: Optional[str]
    ) -> List[ArtifactMetadata]:
        """获取待校验的 artifacts"""
        if run_id:
            return self.manager.registry.get_by_run(run_id)

        all_artifacts = list(self.manager.registry._artifacts.values())

        if release:
            # 按 release tag 过滤
            return [
                a for a in all_artifacts
                if release in (a.tags or [])
            ]

        # 默认返回最近 100 个
        return all_artifacts[-100:]

    def _get_prd_contracts(
        self,
        artifacts: List[ArtifactMetadata]
    ) -> Set[str]:
        """获取所有 PRD contract 的 ID 集合"""
        return {
            a.id for a in artifacts
            if a.type == ArtifactType.CONTRACT and a.category == "prd_contract"
        }

    def _get_api_contracts(
        self,
        artifacts: List[ArtifactMetadata]
    ) -> Set[str]:
        """获取所有 API contract 的 ID 集合"""
        return {
            a.id for a in artifacts
            if a.type == ArtifactType.CONTRACT and a.category == "api_contract"
        }

    def _validate_api_contracts(
        self,
        api_contracts: Set[str],
        prd_contracts: Set[str],
        by_id: Dict[str, ArtifactMetadata]
    ) -> List[str]:
        """验证 API contracts"""
        errors = []
        for api_id in api_contracts:
            api = by_id.get(api_id)
            if not api:
                continue

            # 规则：api_contract 必须有 derived_from 指向某个 prd_contract
            if not api.derived_from:
                errors.append(f"{api_id} (api_contract) missing derived_from")
            elif api.derived_from not in prd_contracts:
                # 检查 derived_from 是否存在于 artifacts 中
                if api.derived_from not in by_id:
                    errors.append(
                        f"{api_id} (api_contract) derived_from '{api.derived_from}' not found"
                    )
                # 注意：如果 derived_from 存在但不是 prd_contract，这里不做强制错误
                # 因为 v1 允许 Task Card 作为 SSOT root

        return errors

    def _validate_implementations(
        self,
        artifacts: List[ArtifactMetadata],
        api_contracts: Set[str]
    ) -> List[str]:
        """验证 implementations"""
        errors = []

        implementations = [
            a for a in artifacts
            if a.type == ArtifactType.CODE_REF and a.category == "implementation"
        ]

        for impl in implementations:
            # 规则：implementation 必须有 implements 指向至少一个 api_contract
            if not impl.implements:
                errors.append(f"{impl.id} (implementation) missing implements")
            else:
                # 检查 implements 的 API 是否存在
                for api_id in impl.implements:
                    if api_id not in api_contracts:
                        errors.append(
                            f"{impl.id} (implementation) implements '{api_id}' not found"
                        )

        return errors

    def _validate_test_plans(
        self,
        artifacts: List[ArtifactMetadata],
        prd_contracts: Set[str],
        api_contracts: Set[str]
    ) -> List[str]:
        """验证 test plans"""
        errors = []

        test_plans = [
            a for a in artifacts
            if a.category in ("test_plan", "test_set")
        ]

        valid_targets = prd_contracts | api_contracts

        for test in test_plans:
            # 规则：test_plan 必须有 verifies 指向至少一个 PRD 或 API
            if not test.verifies:
                errors.append(f"{test.id} (test_plan) missing verifies")
            else:
                # 检查 verifies 的目标是否存在
                for target_id in test.verifies:
                    if target_id not in valid_targets:
                        errors.append(
                            f"{test.id} (test_plan) verifies '{target_id}' not found"
                        )

        return errors

    def impact(self, artifact_id: str) -> Dict[str, List[str]]:
        """
        分析某个 artifact 的影响范围

        Args:
            artifact_id: artifact ID

        Returns:
            影响范围字典：
            {
                "direct_dependents": [...],  # 直接依赖此 artifact 的
                "indirect_dependents": [...],  # 间接依赖此 artifact 的
                "verifiers": [...],  # 验证此 artifact 的测试
            }
        """
        artifact = self.manager.get(artifact_id)
        if not artifact:
            return {
                "direct_dependents": [],
                "indirect_dependents": [],
                "verifiers": [],
            }

        all_artifacts = list(self.manager.registry._artifacts.values())

        # 直接依赖：derived_from / implements / verifies 指向此 artifact
        direct_dependents = []
        verifiers = []

        for a in all_artifacts:
            if a.derived_from == artifact_id:
                direct_dependents.append(a.id)
            if artifact_id in a.implements:
                direct_dependents.append(a.id)
            if artifact_id in a.verifies:
                verifiers.append(a.id)

        # 间接依赖：递归查找
        indirect_dependents = self._find_indirect_dependents(
            artifact_id, all_artifacts, set(direct_dependents)
        )

        return {
            "direct_dependents": direct_dependents,
            "indirect_dependents": list(indirect_dependents),
            "verifiers": verifiers,
        }

    def _find_indirect_dependents(
        self,
        artifact_id: str,
        all_artifacts: List[ArtifactMetadata],
        direct: Set[str]
    ) -> Set[str]:
        """递归查找间接依赖"""
        by_id = {a.id: a for a in all_artifacts}
        indirect = set()
        visited = set(direct)

        queue = list(direct)
        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            current = by_id.get(current_id)
            if not current:
                continue

            # 查找依赖 current 的 artifacts
            for a in all_artifacts:
                if a.id in visited:
                    continue
                if a.derived_from == current_id:
                    indirect.add(a.id)
                    queue.append(a.id)
                if current_id in a.implements:
                    indirect.add(a.id)
                    queue.append(a.id)

        return indirect

    def show_chain(self, artifact_id: str) -> List[Dict[str, str]]:
        """
        显示某个 artifact 的真理链路径

        Args:
            artifact_id: artifact ID

        Returns:
            真理链路径列表，从 root 到当前 artifact
        """
        artifact = self.manager.get(artifact_id)
        if not artifact:
            return []

        chain = []
        visited = set()
        current = artifact

        while current and current.id not in visited:
            visited.add(current.id)

            chain_entry = {
                "id": current.id,
                "type": current.type.value,
                "category": current.category,
                "relation": "",
            }

            # 确定关系
            if current.derived_from:
                chain_entry["relation"] = f"derived_from -> {current.derived_from}"
            elif current.implements:
                chain_entry["relation"] = f"implements -> {', '.join(current.implements)}"
            elif current.verifies:
                chain_entry["relation"] = f"verifies -> {', '.join(current.verifies)}"

            chain.append(chain_entry)

            # 移动到上游
            if current.derived_from:
                current = self.manager.get(current.derived_from)
            elif current.implements:
                # 取第一个 implements
                current = self.manager.get(current.implements[0])
            else:
                current = None

        # 反转，从 root 到当前
        chain.reverse()
        return chain
