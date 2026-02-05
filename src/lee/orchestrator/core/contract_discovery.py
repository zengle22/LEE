"""
契约发现服务 - 自动发现和注册项目中的契约文件

支持自动扫描项目目录，发现符合规范的契约文件，
并建立契约索引以便工作流引用。
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from datetime import datetime


class ContractType(Enum):
    """契约类型枚举"""
    PRD = "prd"
    ARCHITECTURE = "architecture"
    UI_PROTOTYPE = "ui_prototype"
    UI_PAGE = "ui_page"
    UI_COMPONENT = "ui_component"
    TEST_CASE = "test_case"
    TEST_CASE_DESIGN = "test_case_design"
    BRANCH_COVERAGE = "branch_coverage"
    SPECIALIZED_TEST = "specialized_test"
    PLAYWRIGHT_SCRIPT = "playwright_script"
    FEATURE_CALIBRATION = "feature_calibration"
    REQUIREMENT_ALIGNMENT = "requirement_alignment"


class ContractStatus(Enum):
    """契约状态枚举"""
    DRAFT = "draft"
    FROZEN = "frozen"
    PENDING_CONFIRMATION = "pending_confirmation"


@dataclass
class ContractInfo:
    """契约信息"""
    contract_id: str
    contract_type: ContractType
    version: str
    status: ContractStatus
    is_frozen: bool
    file_path: str
    schema_path: str
    product_name: Optional[str] = None
    created_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "contract_id": self.contract_id,
            "contract_type": self.contract_type.value,
            "version": self.version,
            "status": self.status.value,
            "is_frozen": self.is_frozen,
            "file_path": self.file_path,
            "schema_path": self.schema_path,
            "product_name": self.product_name,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "metadata": self.metadata
        }


@dataclass
class ContractIndex:
    """契约索引"""
    contracts: Dict[str, ContractInfo] = field(default_factory=dict)
    contracts_by_type: Dict[ContractType, List[str]] = field(default_factory=dict)
    contracts_by_product: Dict[str, List[str]] = field(default_factory=dict)
    frozen_contracts: List[str] = field(default_factory=list)
    last_scan_time: Optional[datetime] = None
    scan_errors: List[str] = field(default_factory=dict)


class ContractDiscovery:
    """契约发现服务"""

    # 标准契约存储位置
    STANDARD_CONTRACT_DIRS = [
        "contracts",
        "spec/contracts",
        "spec-global/departments/*/contracts",
        "output/contracts",
    ]

    # 契约文件模式
    CONTRACT_PATTERNS = {
        ContractType.PRD: [
            "**/frozen-detailed-prd-contract/**/*.json",
            "**/prd/**/*.json",
            "**/frozen_prd*.json",
        ],
        ContractType.ARCHITECTURE: [
            "**/frozen-technical-architecture-contract/**/*.json",
            "**/architecture/**/*.json",
            "**/frozen_arch*.json",
        ],
        ContractType.UI_PROTOTYPE: [
            "**/frozen-ui-prototype-contract/**/*.json",
            "**/ui-prototype/**/*.json",
            "**/frozen_ui*.json",
        ],
        ContractType.UI_PAGE: [
            "**/ui-page-contract/**/*.yaml",
            "**/ui-page-contract/**/*.json",
            "**/spec/ui/pages/**/*.yaml",
        ],
        ContractType.UI_COMPONENT: [
            "**/ui-component-contract/**/*.yaml",
            "**/spec/ui/components/**/*.yaml",
        ],
        ContractType.TEST_CASE: [
            "**/test-case-contract/**/*.yaml",
            "**/test-case/**/*.yaml",
            "**/spec/qa/test-cases/**/*.yaml",
        ],
        ContractType.TEST_CASE_DESIGN: [
            "**/test-case-design-contract/**/*.yaml",
            "**/test-case-design/**/*.yaml",
        ],
        ContractType.BRANCH_COVERAGE: [
            "**/branch-coverage/**/*.json",
            "**/branch-coverage-report/**/*.json",
        ],
        ContractType.SPECIALIZED_TEST: [
            "**/specialized-test/**/*.json",
            "**/specialized-test-contract/**/*.json",
        ],
        ContractType.PLAYWRIGHT_SCRIPT: [
            "**/playwright-script-output/**/*.json",
            "**/e2e-scripts/**/*.json",
        ],
        ContractType.FEATURE_CALIBRATION: [
            "**/feature-calibration/**/*.json",
            "**/feature-calibration-report/**/*.json",
        ],
        ContractType.REQUIREMENT_ALIGNMENT: [
            "**/requirement-alignment/**/*.json",
            "**/requirement-alignment-report/**/*.json",
        ],
    }

    # 契约 ID 正则模式
    CONTRACT_ID_PATTERNS = {
        ContractType.PRD: r"^FDPRD-\d{8}-\d{3}$",
        ContractType.ARCHITECTURE: r"^FTA-\d{8}-\d{3}$",
        ContractType.UI_PROTOTYPE: r"^FUIPRO-\d{8}-\d{3}$",
        ContractType.UI_PAGE: r"^page\.[a-z_]+$",
    }

    def __init__(self, project_root: str = "."):
        """
        初始化契约发现服务

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self.index = ContractIndex()
        self.spec_global_root = self.project_root / "spec-global"

    def discover_all(self, force_refresh: bool = False) -> ContractIndex:
        """
        发现所有契约文件

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            契约索引
        """
        if not force_refresh and self.index.last_scan_time:
            return self.index

        self.index = ContractIndex()
        self.index.last_scan_time = datetime.now()

        # 扫描标准契约目录
        for contract_dir in self.STANDARD_CONTRACT_DIRS:
            expanded_dir = self._expand_path(contract_dir)
            if expanded_dir.exists():
                self._scan_directory(expanded_dir)

        # 扫描 spec-global 目录
        if self.spec_global_root.exists():
            self._scan_spec_global()

        return self.index

    def _expand_path(self, path_pattern: str) -> Path:
        """展开路径模式中的通配符"""
        if "*" in path_pattern:
            # 返回第一个匹配的目录
            matches = list(self.project_root.glob(path_pattern))
            return matches[0] if matches else Path(path_pattern)
        return self.project_root / path_pattern

    def _scan_directory(self, directory: Path) -> None:
        """扫描目录中的契约文件"""
        if not directory.is_dir():
            return

        for file_path in directory.rglob("*"):
            if file_path.is_file() and self._is_contract_file(file_path):
                try:
                    contract_info = self._parse_contract_file(file_path)
                    if contract_info:
                        self._add_to_index(contract_info)
                except Exception as e:
                    self.index.scan_errors.append(
                        f"Error parsing {file_path}: {str(e)}"
                    )

    def _scan_spec_global(self) -> None:
        """扫描 spec-global 目录中的契约"""
        departments_dir = self.spec_global_root / "departments"
        if not departments_dir.exists():
            return

        for dept_dir in departments_dir.iterdir():
            if not dept_dir.is_dir():
                continue

            contracts_dir = dept_dir / "contracts"
            if contracts_dir.exists():
                self._scan_directory(contracts_dir)

    def _is_contract_file(self, file_path: Path) -> bool:
        """判断文件是否为契约文件"""
        # 检查文件扩展名
        if file_path.suffix not in [".json", ".yaml", ".yml"]:
            return False

        # 检查文件名是否包含契约关键词
        contract_keywords = [
            "contract", "prd", "architecture", "ui-prototype",
            "test-case", "test-case-design", "branch-coverage",
            "feature-calibration", "requirement-alignment"
        ]
        file_name_lower = file_path.name.lower()
        return any(keyword in file_name_lower for keyword in contract_keywords)

    def _parse_contract_file(self, file_path: Path) -> Optional[ContractInfo]:
        """解析契约文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == ".json":
                    data = json.load(f)
                else:  # yaml
                    data = yaml.safe_load(f)

            # 识别契约类型
            contract_type = self._identify_contract_type(data, file_path)
            if not contract_type:
                return None

            # 提取契约信息
            metadata = data.get("metadata", {})
            contract_info = ContractInfo(
                contract_id=metadata.get("contract_id", self._generate_contract_id(file_path, contract_type)),
                contract_type=contract_type,
                version=data.get("contract_version", "1.0.0"),
                status=ContractStatus(metadata.get("status", "draft")),
                is_frozen=metadata.get("is_frozen", False),
                file_path=str(file_path.relative_to(self.project_root)),
                schema_path=str(file_path),
                product_name=metadata.get("product_name") or data.get("product_overview", {}).get("product_name"),
                created_date=self._parse_date(metadata.get("created_date")),
                metadata={
                    "contract_type": data.get("contract_type"),
                    "features_count": len(data.get("functional_details", {}).get("features", [])),
                }
            )

            return contract_info

        except Exception as e:
            self.index.scan_errors.append(f"Error parsing {file_path}: {str(e)}")
            return None

    def _identify_contract_type(self, data: Dict[str, Any], file_path: Path) -> Optional[ContractType]:
        """识别契约类型"""
        contract_type = data.get("contract_type", "")

        # 根据 contract_type 字段识别
        type_mapping = {
            "frozen-detailed-prd": ContractType.PRD,
            "frozen-technical-architecture": ContractType.ARCHITECTURE,
            "frozen-ui-prototype": ContractType.UI_PROTOTYPE,
        }

        if contract_type in type_mapping:
            return type_mapping[contract_type]

        # 根据文件路径识别
        path_str = str(file_path).lower()
        if "prd" in path_str:
            return ContractType.PRD
        elif "architecture" in path_str or "arch" in path_str:
            return ContractType.ARCHITECTURE
        elif "ui-page" in path_str or "page.contract" in path_str:
            return ContractType.UI_PAGE
        elif "ui-component" in path_str:
            return ContractType.UI_COMPONENT
        elif "test-case-design" in path_str:
            return ContractType.TEST_CASE_DESIGN
        elif "branch-coverage" in path_str:
            return ContractType.BRANCH_COVERAGE
        elif "specialized-test" in path_str:
            return ContractType.SPECIALIZED_TEST
        elif "playwright" in path_str:
            return ContractType.PLAYWRIGHT_SCRIPT
        elif "feature-calibration" in path_str:
            return ContractType.FEATURE_CALIBRATION
        elif "requirement-alignment" in path_str:
            return ContractType.REQUIREMENT_ALIGNMENT

        return None

    def _generate_contract_id(self, file_path: Path, contract_type: ContractType) -> str:
        """生成契约 ID"""
        # 基于文件路径生成 ID
        path_parts = file_path.relative_to(self.project_root).parts
        return f"contract-{'-'.join(path_parts[-2:])}"

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None

    def _add_to_index(self, contract_info: ContractInfo) -> None:
        """添加契约到索引"""
        # 添加到主索引
        self.index.contracts[contract_info.contract_id] = contract_info

        # 按类型索引
        if contract_info.contract_type not in self.index.contracts_by_type:
            self.index.contracts_by_type[contract_info.contract_type] = []
        self.index.contracts_by_type[contract_info.contract_type].append(contract_info.contract_id)

        # 按产品索引
        if contract_info.product_name:
            if contract_info.product_name not in self.index.contracts_by_product:
                self.index.contracts_by_product[contract_info.product_name] = []
            self.index.contracts_by_product[contract_info.product_name].append(contract_info.contract_id)

        # 冻结契约索引
        if contract_info.is_frozen:
            self.index.frozen_contracts.append(contract_info.contract_id)

    def find_contract(self, contract_id: str) -> Optional[ContractInfo]:
        """查找契约"""
        return self.index.contracts.get(contract_id)

    def find_contracts_by_type(self, contract_type: ContractType) -> List[ContractInfo]:
        """按类型查找契约"""
        contract_ids = self.index.contracts_by_type.get(contract_type, [])
        return [
            self.index.contracts[cid]
            for cid in contract_ids
            if cid in self.index.contracts
        ]

    def find_contracts_by_product(self, product_name: str) -> List[ContractInfo]:
        """按产品查找契约"""
        contract_ids = self.index.contracts_by_product.get(product_name, [])
        return [
            self.index.contracts[cid]
            for cid in contract_ids
            if cid in self.index.contracts
        ]

    def find_frozen_contracts(self) -> List[ContractInfo]:
        """查找所有冻结的契约"""
        return [
            self.index.contracts[cid]
            for cid in self.index.frozen_contracts
            if cid in self.index.contracts
        ]

    def get_workflow_inputs(self, workflow_id: str) -> Dict[str, str]:
        """
        获取工作流所需的输入契约

        Args:
            workflow_id: 工作流 ID

        Returns:
            契约类型到文件路径的映射
        """
        # 定义工作流到所需契约类型的映射
        workflow_requirements = {
            "workflow.qa.test_case_design_pipeline": {
                "prd": ContractType.PRD,
                "technical_architecture": ContractType.ARCHITECTURE,
                "ui_prototype": ContractType.UI_PROTOTYPE,
                "ui_page": ContractType.UI_PAGE,
            }
        }

        requirements = workflow_requirements.get(workflow_id, {})
        result = {}

        for input_name, contract_type in requirements.items():
            frozen_contracts = [
                c for c in self.find_contracts_by_type(contract_type)
                if c.is_frozen
            ]
            if frozen_contracts:
                # 优先选择最新的冻结契约
                result[input_name] = max(
                    frozen_contracts,
                    key=lambda c: c.created_date or datetime.min
                ).file_path

        return result

    def validate_workflow_inputs(self, workflow_id: str) -> Tuple[bool, List[str]]:
        """
        验证工作流输入是否完整

        Args:
            workflow_id: 工作流 ID

        Returns:
            (是否完整, 缺失的契约列表)
        """
        inputs = self.get_workflow_inputs(workflow_id)
        workflow_requirements = {
            "workflow.qa.test_case_design_pipeline": ["prd", "technical_architecture", "ui_prototype", "ui_page"]
        }

        required = workflow_requirements.get(workflow_id, [])
        missing = [r for r in required if r not in inputs]

        return len(missing) == 0, missing


# 单例实例
_discovery_instance: Optional[ContractDiscovery] = None


def get_discovery_service(project_root: str = ".") -> ContractDiscovery:
    """获取契约发现服务单例"""
    global _discovery_instance
    if _discovery_instance is None or _discovery_instance.project_root != Path(project_root).resolve():
        _discovery_instance = ContractDiscovery(project_root)
    return _discovery_instance
