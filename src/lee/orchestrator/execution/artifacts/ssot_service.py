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


def _normalize_versioned_refs(values) -> List[Dict[str, Optional[str]]]:
    refs: List[Dict[str, Optional[str]]] = []
    for value in values or []:
        if isinstance(value, dict):
            ref_id = value.get("id")
            version = value.get("version")
            if ref_id and version:
                refs.append(value)
        elif isinstance(value, str):
            refs.append({"id": value, "version": None})
    return refs


def _extract_upstream_refs(artifact: ArtifactMetadata) -> List[Tuple[str, str]]:
    properties = getattr(artifact, "properties", {}) or {}
    refs: List[Tuple[str, str]] = []
    if artifact.derived_from:
        refs.append(("derived_from", artifact.derived_from))
    for ref in _normalize_versioned_refs(properties.get("derived_from_ids", [])):
        ref_id = ref.get("id")
        if ref_id:
            refs.append((f"derived_from_ids@{ref.get('version')}", ref_id))
    for source_ref in properties.get("source_refs", []):
        ref_id = str(source_ref).split("#", 1)[0]
        if ref_id:
            refs.append(("source_ref", ref_id))
    for ref_id in artifact.implements or []:
        refs.append(("implements", ref_id))
    for ref_id in artifact.verifies or []:
        refs.append(("verifies", ref_id))

    seen: Set[Tuple[str, str]] = set()
    ordered: List[Tuple[str, str]] = []
    for item in refs:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


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
            upstream_refs = _extract_upstream_refs(current)
            if upstream_refs:
                rel_kind, rel_target = upstream_refs[0]
                chain_entry["relation"] = f"{rel_kind} -> {rel_target}"

            chain.append(chain_entry)

            # 移动到上游
            current = self.manager.get(upstream_refs[0][1]) if upstream_refs else None

        # 反转，从 root 到当前
        chain.reverse()
        return chain

    def release_check(self, release_id: str) -> Dict[str, object]:
        """
        执行 release 级聚合校验。
        """
        release = self.manager.get(release_id)
        errors: List[str] = []
        warnings: List[str] = []

        if not release:
            return {"passed": False, "errors": [f"Release {release_id} not found"], "warnings": []}

        props = getattr(release, "properties", {}) or {}
        versioned_refs = _normalize_versioned_refs(props.get("derived_from_ids", []))
        if not versioned_refs:
            errors.append(f"{release_id} missing derived_from_ids")

        children = self.manager.registry.get_by_parent(release_id)
        devplans = [a for a in children if a.properties.get("ssot_type") == "devplan"]
        testplans = [a for a in children if a.properties.get("ssot_type") == "testplan"]
        reports = [a for a in children if a.properties.get("ssot_type") == "report"]

        feat_ids = {ref["id"] for ref in versioned_refs if str(ref.get("id", "")).startswith("FEAT-")}
        devplan_feat_ids = {
            ref.get("id")
            for plan in devplans
            for ref in _normalize_versioned_refs((plan.properties or {}).get("derived_from_ids", []))
            if ref.get("id")
        }
        testplan_feat_ids = {
            ref.get("id")
            for plan in testplans
            for ref in _normalize_versioned_refs((plan.properties or {}).get("derived_from_ids", []))
            if ref.get("id")
        }

        for feat_id in sorted(feat_ids - devplan_feat_ids):
            errors.append(f"{release_id} feat {feat_id} not covered by any DEVPLAN")
        for feat_id in sorted(feat_ids - testplan_feat_ids):
            errors.append(f"{release_id} feat {feat_id} not covered by any TESTPLAN")

        report_kinds = {
            (report.properties or {}).get("report_kind")
            for report in reports
        }
        required_report_kinds = {"release", "test_execution", "go_no_go"}
        for kind in sorted(required_report_kinds - report_kinds):
            errors.append(f"{release_id} missing report_kind={kind}")

        all_artifacts = self.manager.registry.list_all()
        for artifact in all_artifacts:
            if artifact.properties.get("ssot_type") != "bug":
                continue
            bug_props = artifact.properties or {}
            if bug_props.get("found_in_release") != release_id:
                continue
            if bug_props.get("severity") == "blocker" and bug_props.get("bug_state") not in ("closed", "waived"):
                errors.append(f"{release_id} has blocker bug {artifact.id} not closed")
            if bug_props.get("bug_state") == "waived":
                if not bug_props.get("waiver_reason") or not bug_props.get("waiver_approved_by"):
                    errors.append(f"{artifact.id} waived bug missing waiver metadata")

        if not props.get("rollback_plan"):
            warnings.append(f"{release_id} missing rollback_plan")

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "release_id": release_id,
            "devplans": [item.id for item in devplans],
            "testplans": [item.id for item in testplans],
        }

    def derive_plans(self, release_id: str) -> Dict[str, str]:
        """
        Derive DEVPLAN/TESTPLAN skeletons from a RELEASE scope.
        """
        release = self.manager.get(release_id)
        if not release:
            raise ValueError(f"Release {release_id} not found")

        release_props = getattr(release, "properties", {}) or {}
        release_refs = _normalize_versioned_refs(release_props.get("derived_from_ids", []))
        if not release_refs:
            raise ValueError(f"Release {release_id} has no derived_from_ids")

        existing_children = self.manager.registry.get_by_parent(release_id)
        existing_devplan = next((a for a in existing_children if a.properties.get("ssot_type") == "devplan"), None)
        existing_testplan = next((a for a in existing_children if a.properties.get("ssot_type") == "testplan"), None)

        feat_refs = [ref for ref in release_refs if str(ref.get("id", "")).startswith("FEAT-")]
        slices = []
        testplan_refs: List[Dict[str, object]] = list(feat_refs)

        for ref in feat_refs:
            feat_id = ref["id"]
            feat_version = ref["version"]
            slice_key = ref.get("slice_key") or f"{feat_id.lower().replace('-', '_')}_{feat_version.lower()}"
            slices.append(
                {
                    "slice_key": slice_key,
                    "feat_id": feat_id,
                    "feat_version": feat_version,
                    "required": bool(ref.get("required", True)),
                    "dependencies": [],
                }
            )

            testsets = [
                artifact for artifact in self.manager.registry.get_by_parent(feat_id)
                if artifact.properties.get("ssot_type") == "testset"
            ]
            for testset in testsets:
                testplan_refs.append(
                    {
                        "id": testset.id,
                        "version": testset.properties.get("version", "v1"),
                        "required": bool(ref.get("required", True)),
                        "slice_key": slice_key,
                    }
                )

        result: Dict[str, str] = {}

        if existing_devplan:
            result["devplan_id"] = existing_devplan.id
        else:
            devplan = self.manager.create_ssot(
                ssot_type=SSOTType.DEVPLAN,
                title=f"Dev plan for {release_id}",
                content=f"# Dev plan for {release_id}\n",
                run_id=release.run_id or "plan-derive",
                parent_id=release_id,
                derived_from=feat_refs,
                owner=release_props.get("owner", "delivery"),
                tags=release.tags,
                properties={
                    "coverage_summary": f"Derived from {release_id}",
                    "slices": slices,
                },
            )
            result["devplan_id"] = devplan.id

        if existing_testplan:
            result["testplan_id"] = existing_testplan.id
        else:
            testplan = self.manager.create_ssot(
                ssot_type=SSOTType.TESTPLAN,
                title=f"Test plan for {release_id}",
                content=f"# Test plan for {release_id}\n",
                run_id=release.run_id or "plan-derive",
                parent_id=release_id,
                derived_from=testplan_refs,
                owner="qa",
                tags=release.tags,
                properties={
                    "coverage_summary": f"Derived from {release_id}",
                    "environment_matrix": [release_props.get("target_env", "staging")],
                    "slices": slices,
                },
            )
            result["testplan_id"] = testplan.id

        return result

    def render_view(self, view_name: str, release_id: Optional[str] = None) -> Dict[str, object]:
        """
        Render human-facing derived SSOT views.
        """
        if view_name not in {"release-dashboard", "feat-delivery-matrix", "test-coverage-summary"}:
            raise ValueError(f"Unsupported view: {view_name}")

        if not release_id:
            raise ValueError("render_view requires release_id")

        release = self.manager.get(release_id)
        if not release:
            raise ValueError(f"Release {release_id} not found")

        release_props = getattr(release, "properties", {}) or {}
        release_refs = _normalize_versioned_refs(release_props.get("derived_from_ids", []))
        children = self.manager.registry.get_by_parent(release_id)
        devplans = [a for a in children if a.properties.get("ssot_type") == "devplan"]
        testplans = [a for a in children if a.properties.get("ssot_type") == "testplan"]
        reports = [a for a in children if a.properties.get("ssot_type") == "report"]

        feature_rows = []
        for ref in release_refs:
            feat_id = ref.get("id")
            if not feat_id or not str(feat_id).startswith("FEAT-"):
                continue
            slice_key = ref.get("slice_key")
            feature_rows.append(
                {
                    "feat_id": feat_id,
                    "version": ref.get("version"),
                    "slice_key": slice_key,
                    "covered_by_devplan": any(
                        feat_id in {item.get("id") for item in _normalize_versioned_refs((plan.properties or {}).get("derived_from_ids", []))}
                        for plan in devplans
                    ),
                    "covered_by_testplan": any(
                        feat_id in {item.get("id") for item in _normalize_versioned_refs((plan.properties or {}).get("derived_from_ids", []))}
                        for plan in testplans
                    ),
                    "test_reports": [
                        report.id
                        for report in reports
                        if (report.properties or {}).get("report_kind") == "test_execution"
                        and (
                            not slice_key
                            or (report.properties or {}).get("slice_key") in (None, slice_key)
                        )
                    ],
                }
            )

        if view_name == "release-dashboard":
            release_check = self.release_check(release_id)
            return {
                "view": view_name,
                "release_id": release_id,
                "status": release.status.value,
                "release_scope_size": len(feature_rows),
                "devplan_ids": [item.id for item in devplans],
                "testplan_ids": [item.id for item in testplans],
                "report_ids": [item.id for item in reports],
                "gate_passed": release_check["passed"],
                "gate_errors": release_check["errors"],
                "gate_warnings": release_check["warnings"],
            }

        if view_name == "feat-delivery-matrix":
            return {
                "view": view_name,
                "release_id": release_id,
                "features": feature_rows,
            }

        return {
            "view": view_name,
            "release_id": release_id,
            "coverage": [
                {
                    "feat_id": row["feat_id"],
                    "slice_key": row["slice_key"],
                    "test_report_count": len(row["test_reports"]),
                    "covered_by_testplan": row["covered_by_testplan"],
                }
                for row in feature_rows
            ],
        }


# ============================================================================
# SSOT v1.3 新增：P0/P1 校验规则
# ============================================================================

from .id_parser import (
    parse_parent,
    parse_scope,
    resolve_scope,
    parse_id,
    validate_id_format,
    validate_parent_consistency,
)
from .types import SSOTType, ObjectCategory


class ValidationResult:
    """校验结果"""

    def __init__(self):
        self.errors: List[str] = []  # P0 错误
        self.warnings: List[str] = []  # P1 警告

    @property
    def is_valid(self) -> bool:
        """是否通过 P0 校验"""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """是否有 P1 警告"""
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """添加 P0 错误"""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """添加 P1 警告"""
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult") -> None:
        """合并另一个校验结果"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


class SSOTValidator:
    """
    SSOT P0/P1 校验器

    SSOT v1.3 新增的校验器，提供 11 条 P0 规则和 3 条 P1 规则。
    """

    def __init__(self, registry):
        """
        初始化校验器

        Args:
            registry: ArtifactRegistry 实例
        """
        self.registry = registry

    def validate_p0(self, artifact_id: str) -> ValidationResult:
        """
        执行 P0 Blocking 校验

        P0 规则:
        1. ID 唯一性
        2. 路径唯一性 (active)
        3. Metadata 完整性
        4. 类型合法性
        5. 引用存在性
        6. 文件名与 ID 一致性
        7. ID 格式合法且可解析
        8. parse_parent(id) == parent_id
        9. parse_scope(id) == resolve_scope(parent_id)
        10. parent_id 必填检查
        11. TC.parent_id 必须为 TESTSET
        """
        result = ValidationResult()
        artifact = self.registry.get(artifact_id)

        if not artifact:
            result.add_error(f"Artifact {artifact_id} not found in registry")
            return result

        # 规则 1: ID 唯一性 (已在 registry 中保证)
        # 规则 2: 路径唯一性 (active)
        self._validate_path_uniqueness(artifact, result)

        # 规则 3: Metadata 完整性
        self._validate_metadata_completeness(artifact, result)

        # 规则 4: 类型合法性
        self._validate_type_legality(artifact, result)

        # 规则 5: 引用存在性
        self._validate_reference_existence(artifact, result)

        # 规则 6: 文件名与 ID 一致性
        self._validate_filename_id_match(artifact, result)

        # 规则 7: ID 格式合法且可解析
        self._validate_id_format(artifact, result)

        # 规则 8-9: parent_id 一致性
        self._validate_parent_consistency(artifact, result)

        # 规则 10: parent_id 必填检查
        self._validate_parent_required(artifact, result)

        # 规则 11: TC.parent_id 必须为 TESTSET
        self._validate_tc_parent(artifact, result)

        # 规则 12+: 交付链专用规则
        self._validate_delivery_rules(artifact, result)

        return result

    def validate_p1(self, artifact_id: str) -> ValidationResult:
        """
        执行 P1 Warning 校验

        P1 规则:
        12. 父子类型推荐关系检查
        13. 孤儿对象检查
        14. slug 规范检查
        """
        result = ValidationResult()
        artifact = self.registry.get(artifact_id)

        if not artifact:
            return result

        # 规则 12: 父子类型推荐关系
        self._validate_parent_type_recommendation(artifact, result)

        # 规则 13: 孤儿对象检查
        self._validate_orphan_object(artifact, result)

        # 规则 14: slug 规范检查
        self._validate_slug_spec(artifact, result)

        return result

    def validate_all(self, artifact_id: str) -> ValidationResult:
        """
        执行完整校验 (P0 + P1)
        """
        result = ValidationResult()
        result.merge(self.validate_p0(artifact_id))
        result.merge(self.validate_p1(artifact_id))
        return result

    def _validate_path_uniqueness(self, artifact, result: ValidationResult) -> None:
        """规则 2: 路径唯一性 (active)"""
        if artifact.status.value == "ACTIVE":
            # 检查是否有其他 active 对象使用相同路径
            existing = self.registry.get_by_path(artifact.path)
            if existing and existing.id != artifact.id:
                result.add_error(f"路径 '{artifact.path}' 已被其他 active 对象 {existing.id} 占用")

    def _validate_metadata_completeness(self, artifact, result: ValidationResult) -> None:
        """规则 3: Metadata 完整性"""
        # 检查必填字段
        if not artifact.id:
            result.add_error("Missing required field: id")
        if not artifact.type:
            result.add_error("Missing required field: type")
        if not hasattr(artifact, 'title') or not artifact.title:
            result.add_error("Missing required field: title")
        if not artifact.status:
            result.add_error("Missing required field: status")

    def _validate_type_legality(self, artifact, result: ValidationResult) -> None:
        """规则 4: 类型合法性"""
        valid_types = {t.value for t in ArtifactType}
        if artifact.type.value not in valid_types:
            result.add_error(f"Invalid type: {artifact.type.value}")

    def _validate_reference_existence(self, artifact, result: ValidationResult) -> None:
        """规则 5: 引用存在性"""
        properties = getattr(artifact, "properties", {}) or {}

        # 检查 derived_from
        if artifact.derived_from:
            if not self.registry.exists(artifact.derived_from):
                result.add_error(f"derived_from '{artifact.derived_from}' does not exist")

        # 检查 related_ids (如果存在)
        for ref_id in properties.get("related_ids", []):
            if not self.registry.exists(ref_id):
                result.add_error(f"related_ids '{ref_id}' does not exist")

        # 检查 source_refs 中显式引用的对象
        for source_ref in properties.get("source_refs", []):
            ref_id = source_ref.split("#", 1)[0]
            if ref_id and not self.registry.exists(ref_id):
                result.add_error(f"source_refs '{source_ref}' does not exist")

        # 检查 derived_from_ids
        for ref in properties.get("derived_from_ids", []):
            if isinstance(ref, dict):
                ref_id = ref.get("id")
                version = ref.get("version")
                if not ref_id or not version:
                    result.add_error("derived_from_ids entry must include id and version")
                    continue
                if not self.registry.exists(ref_id):
                    result.add_error(f"derived_from_ids '{ref_id}' does not exist")
            elif isinstance(ref, str):
                if not self.registry.exists(ref):
                    result.add_error(f"derived_from_ids '{ref}' does not exist")
            else:
                result.add_error(f"derived_from_ids entry has unsupported type: {type(ref).__name__}")

        # 兼容旧 metadata 字段
        if hasattr(artifact, 'related_ids') and artifact.related_ids:
            for ref_id in artifact.related_ids:
                if not self.registry.exists(ref_id):
                    result.add_error(f"related_ids '{ref_id}' does not exist")

        # 检查 verifies
        if artifact.verifies:
            for ref_id in artifact.verifies:
                if not self.registry.exists(ref_id):
                    result.add_error(f"verifies '{ref_id}' does not exist")

        # 检查 implements
        if artifact.implements:
            for ref_id in artifact.implements:
                if not self.registry.exists(ref_id):
                    result.add_error(f"implements '{ref_id}' does not exist")

    def _validate_filename_id_match(self, artifact, result: ValidationResult) -> None:
        """规则 6: 文件名与 ID 一致性"""
        # 从 path 中提取文件名
        filename = Path(artifact.path).name
        # 左侧 ID 应该与 artifact.id 匹配
        file_id = filename.split("__")[0]
        if file_id != artifact.id:
            result.add_error(f"Filename ID '{file_id}' does not match artifact id '{artifact.id}'")

    def _validate_id_format(self, artifact, result: ValidationResult) -> None:
        """规则 7: ID 格式合法且可解析"""
        if not validate_id_format(artifact.id):
            result.add_error(f"ID format is invalid: {artifact.id}")

    def _validate_parent_consistency(self, artifact, result: ValidationResult) -> None:
        """规则 8-9: parent_id 一致性"""
        # 只有 SSOT 对象才有 parent_id 概念
        if not self.registry.is_ssot_id(artifact.id):
            return

        # 获取 parent_id (如果存在)
        parent_id = (getattr(artifact, "properties", {}) or {}).get("parent_id")

        # 推断 SSOT 类型 (从 ID 前缀)
        id_prefix = artifact.id.split("-")[0].upper()
        try:
            ssot_type = SSOTType(id_prefix.lower())
        except ValueError:
            return

        # 使用 id_parser 进行校验
        error = validate_parent_consistency(artifact.id, parent_id, ssot_type)
        if error:
            result.add_error(error)

    def _validate_parent_required(self, artifact, result: ValidationResult) -> None:
        """规则 10: parent_id 必填检查"""
        if not self.registry.is_ssot_id(artifact.id):
            return

        # 获取 parent_id
        parent_id = (getattr(artifact, "properties", {}) or {}).get("parent_id")

        # 推断 SSOT 类型
        id_prefix = artifact.id.split("-")[0].upper()
        try:
            ssot_type = SSOTType(id_prefix.lower())
        except ValueError:
            return

        # 检查是否需要 parent_id
        if SSOTType.requires_parent(ssot_type) and not parent_id:
            result.add_error(f"类型 {ssot_type.value} 需要 parent_id，但未提供")

        expected = ObjectCategory.get_parent_requirement(ssot_type)
        if expected and parent_id:
            parent_prefix = parent_id.split("-", 1)[0].upper()
            if expected == "RELEASE" and parent_prefix != "REL":
                result.add_error(f"类型 {ssot_type.value} 的 parent_id 必须是 RELEASE，当前为 {parent_prefix}")
            elif expected == "RELEASE|DEVPLAN|TESTPLAN|TASK|FEAT" and parent_prefix not in ("REL", "DEVPLAN", "TESTPLAN", "TASK", "FEAT"):
                result.add_error(f"REPORT 对象的 parent_id 类型不合法，当前为 {parent_prefix}")
            elif expected not in ("RELEASE", "RELEASE|DEVPLAN|TESTPLAN|TASK|FEAT") and parent_prefix != expected:
                result.add_error(f"类型 {ssot_type.value} 的 parent_id 必须是 {expected}，当前为 {parent_prefix}")

    def _validate_tc_parent(self, artifact, result: ValidationResult) -> None:
        """规则 11: TC.parent_id 必须为 TESTSET"""
        if not self.registry.is_ssot_id(artifact.id):
            return

        id_prefix = artifact.id.split("-")[0].upper()
        if id_prefix != "TC":
            return

        parent_id = (getattr(artifact, "properties", {}) or {}).get("parent_id")
        if parent_id:
            # 解析 parent_id 确认是 TESTSET
            parent_prefix = parent_id.split("-")[0].upper()
            if parent_prefix != "TESTSET":
                result.add_error(f"TC 对象的 parent_id 必须为 TESTSET 类型，当前为 {parent_prefix}")

    def _validate_delivery_rules(self, artifact, result: ValidationResult) -> None:
        """新增 release/devplan/testplan/task/report/bug 规则。"""
        if not self.registry.is_ssot_id(artifact.id):
            return

        properties = getattr(artifact, "properties", {}) or {}
        try:
            ssot_type = SSOTType(artifact.properties.get("ssot_type", artifact.id.split("-", 1)[0].lower()))
        except ValueError:
            return

        refs = _normalize_versioned_refs(properties.get("derived_from_ids", []))

        if ssot_type == SSOTType.RELEASE:
            if not refs:
                result.add_error("RELEASE 必须声明 derived_from_ids")
            if artifact.status.value in ("ACTIVE", "FROZEN") and not properties.get("scope_frozen_at"):
                result.add_warning("RELEASE 缺少 scope_frozen_at")
            for ref in refs:
                if not str(ref.get("id", "")).startswith("FEAT-"):
                    result.add_error(f"RELEASE derived_from_ids 只能 pin FEAT，当前为 {ref.get('id')}")
            for recut in properties.get("recuts", []):
                if not isinstance(recut, dict):
                    result.add_error("RELEASE.properties.recuts[] 必须是对象")
                    continue
                required_recut_fields = {"recut_id", "reason", "old_refs", "new_refs", "approved_by", "changed_at"}
                missing = required_recut_fields - set(recut.keys())
                if missing:
                    result.add_error(f"RELEASE recut 缺少字段: {', '.join(sorted(missing))}")

        if ssot_type == SSOTType.DEVPLAN:
            if not any(str(ref.get("id", "")).startswith("FEAT-") for ref in refs):
                result.add_error("DEVPLAN.derived_from_ids 至少包含一个 FEAT")
            slices = properties.get("slices")
            if "slices" not in properties:
                result.add_warning("DEVPLAN 缺少 properties.slices")
            elif not isinstance(slices, list):
                result.add_error("DEVPLAN.properties.slices 必须是列表")

        if ssot_type == SSOTType.TESTPLAN:
            has_feat = any(str(ref.get("id", "")).startswith("FEAT-") for ref in refs)
            has_testset = any(str(ref.get("id", "")).startswith("TESTSET-") for ref in refs)
            if not has_feat or not has_testset:
                result.add_error("TESTPLAN.derived_from_ids 必须同时包含 FEAT 和 TESTSET")
            if not properties.get("environment_matrix"):
                result.add_warning("TESTPLAN 缺少 environment_matrix")
            if "slices" in properties and not isinstance(properties.get("slices"), list):
                result.add_error("TESTPLAN.properties.slices 必须是列表")

        if ssot_type == SSOTType.TASK:
            if not properties.get("slice_key"):
                result.add_warning("TASK 缺少 slice_key")

        if ssot_type == SSOTType.BUG:
            if not properties.get("severity"):
                result.add_error("BUG 缺少 severity")
            if not properties.get("source_report_id"):
                result.add_error("BUG 缺少 source_report_id")
            if properties.get("bug_state") == "waived":
                if not properties.get("waiver_reason") or not properties.get("waiver_approved_by"):
                    result.add_error("BUG waived 时必须包含 waiver_reason 和 waiver_approved_by")

        if ssot_type == SSOTType.REPORT:
            required_fields = ("report_kind", "subject_id", "result")
            for field in required_fields:
                if not properties.get(field):
                    result.add_error(f"REPORT 缺少 properties.{field}")
            if "evidence_refs" not in properties:
                result.add_error("REPORT 缺少 properties.evidence_refs")

    def _validate_parent_type_recommendation(self, artifact, result: ValidationResult) -> None:
        """规则 12: 父子类型推荐关系"""
        # 这是一个 P1 警告，不是 blocking 错误
        pass

    def _validate_orphan_object(self, artifact, result: ValidationResult) -> None:
        """规则 13: 孤儿对象检查"""
        # 检查是否有任何引用指向此对象
        related = self.registry.get_related(artifact.id)
        if not related:
            # 检查是否有下游对象
            has_downstream = False
            for other in self.registry.list_all():
                derived_from = getattr(other, "derived_from", None)
                derived_from_ids = (getattr(other, "properties", {}) or {}).get("derived_from_ids", [])
                normalized_ids = {
                    ref.get("id") if isinstance(ref, dict) else ref
                    for ref in derived_from_ids
                }
                if derived_from == artifact.id or artifact.id in normalized_ids:
                    has_downstream = True
                    break
            if not has_downstream:
                result.add_warning(f"对象 {artifact.id} 可能是孤儿对象 (无上游也无下游)")

    def _validate_slug_spec(self, artifact, result: ValidationResult) -> None:
        """规则 14: slug 规范检查"""
        # 从文件名提取 slug
        filename = Path(artifact.path).name
        if "__" not in filename:
            result.add_warning(f"文件名缺少 slug 部分: {filename}")
            return

        _, slug_ext = filename.split("__", 1)
        slug = Path(slug_ext).stem

        # 检查 slug 长度
        if len(slug) > 50:
            result.add_warning(f"slug 长度超过 50 字符: {slug}")

        # 检查 slug 字符
        import re
        if not re.match(r"^[a-z0-9-]*$", slug):
            result.add_warning(f"slug 包含非标准字符: {slug}")
