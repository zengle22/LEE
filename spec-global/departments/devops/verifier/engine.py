#!/usr/bin/env python3
"""
Verifier Engine - LEE Orchestrator 质量验证系统

负责执行验证契约（Contract），包括程序型检查和 AI 型检查。
"""

import os
import sys
import json
import yaml
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class VerificationStatus(Enum):
    """验证状态枚举"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class CheckType(Enum):
    """检查类型枚举"""
    PROGRAM = "program"
    AI = "ai"


class Severity(Enum):
    """严重程度枚举"""
    ERROR = "error"
    WARNING = "warning"


@dataclass
class CheckResult:
    """单个检查结果"""
    check_id: str
    check_name: str
    check_type: CheckType
    status: VerificationStatus
    severity: Severity
    detail: str
    score: Optional[float] = None
    suggestions: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class VerificationResult:
    """验证结果"""
    contract_id: str
    verification_time: str
    overall_status: VerificationStatus
    check_results: List[CheckResult]
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    summary: str = ""

    def __post_init__(self):
        """计算统计信息"""
        self.total_checks = len(self.check_results)
        self.passed_checks = sum(1 for c in self.check_results if c.status == VerificationStatus.PASS)
        self.failed_checks = sum(1 for c in self.check_results if c.status == VerificationStatus.FAIL)
        self.warning_checks = sum(1 for c in self.check_results if c.status == VerificationStatus.WARNING)
        self.summary = self._generate_summary()

    def _generate_summary(self) -> str:
        """生成摘要"""
        return (
            f"Verifier status={self.overall_status.value}, "
            f"checks={self.total_checks} "
            f"(passed={self.passed_checks}, failed={self.failed_checks}, warning={self.warning_checks})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "contract_id": self.contract_id,
            "verification_time": self.verification_time,
            "overall_status": self.overall_status.value,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "summary": self.summary,
            "check_results": [
                {
                    "check_id": c.check_id,
                    "check_name": c.check_name,
                    "check_type": c.check_type.value,
                    "status": c.status.value,
                    "severity": c.severity.value,
                    "detail": c.detail,
                    "score": c.score,
                    "suggestions": c.suggestions,
                    "execution_time": c.execution_time,
                }
                for c in self.check_results
            ],
        }


class VerifierEngine:
    """验证引擎"""

    def __init__(self, config_path: str = "verifier/config.yaml"):
        """初始化验证引擎"""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        # 契约文件在 contracts/ 目录下
        self.contracts_dir = Path("contracts")
        self.rules_dir = Path("verifier/rules")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            return self._default_config()

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "engine": {
                "default_ai_model": "claude-3.5-sonnet",
                "timeouts": {
                    "program_check_timeout": 30,
                    "ai_check_timeout": 120,
                },
            },
            "logging": {
                "level": "INFO",
                "path": "logs/verifier/",
            },
        }

    def load_contract(self, contract_id: str) -> Dict[str, Any]:
        """加载验证契约"""
        # 从 contract_id 提取文件名
        # 例如: devops.phase1.architecture.v1 -> phase1.architecture.v1.yaml
        # 移除部门名称（第一部分），保留其余部分并添加 .yaml
        parts = contract_id.split(".")
        contract_name = ".".join(parts[1:]) + ".yaml"
        contract_path = self.contracts_dir / contract_name

        if not contract_path.exists():
            raise FileNotFoundError(f"Contract not found: {contract_path}")

        with open(contract_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def verify(self, contract_id: str, artifacts: Dict[str, str], base_dir: str = ".") -> VerificationResult:
        """
        执行验证

        Args:
            contract_id: 契约 ID（例如：devops.phase1.architecture.v1）
            artifacts: 产物字典 {artifact_id: file_path}
            base_dir: 基础目录

        Returns:
            VerificationResult: 验证结果
        """
        start_time = datetime.now()

        # 加载契约
        contract = self.load_contract(contract_id)
        checks = contract.get("checks", [])

        # 执行检查
        check_results = []

        for check in checks:
            result = self._run_check(check, artifacts, base_dir)
            check_results.append(result)

            # 快速失败：如果是 error 级别失败且配置了 fail_fast
            if (result.status == VerificationStatus.FAIL and
                result.severity == Severity.ERROR and
                contract.get("validation_strategy", {}).get("fail_fast", True)):
                break

        # 聚合结果
        overall_status = self._aggregate_status(check_results)

        verification_time = datetime.now().isoformat()
        result = VerificationResult(
            contract_id=contract_id,
            verification_time=verification_time,
            overall_status=overall_status,
            check_results=check_results,
        )

        # 保存结果
        self._save_result(result, contract, base_dir)

        return result

    def _run_check(self, check: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> CheckResult:
        """运行单个检查"""
        import time
        start = time.time()

        check_type = CheckType(check["type"])

        if check_type == CheckType.PROGRAM:
            result = self._run_program_check(check, artifacts, base_dir)
        elif check_type == CheckType.AI:
            result = self._run_ai_check(check, artifacts, base_dir)
        else:
            result = CheckResult(
                check_id=check["id"],
                check_name=check["name"],
                check_type=check_type,
                status=VerificationStatus.WARNING,
                severity=Severity.WARNING,
                detail=f"Unknown check type: {check_type}",
            )

        result.execution_time = time.time() - start
        return result

    def _run_program_check(self, check: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> CheckResult:
        """运行程序型检查"""
        script = check.get("script", "")
        params = check.get("params", {})

        try:
            # 动态加载规则模块
            # 注意：脚本路径是相对于项目根目录的，不是相对于 base_dir
            module_path = script.replace("/", ".").replace(".py", "")
            script_path = Path.cwd() / script  # 使用当前工作目录而不是 base_dir

            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")

            spec = importlib.util.spec_from_file_location(module_path, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 调用验证函数
            if hasattr(module, 'verify'):
                result = module.verify(params, artifacts, base_dir)
            elif hasattr(module, 'check'):
                result = module.check(params, artifacts, base_dir)
            else:
                raise AttributeError(f"No verify() or check() function found in {script}")

            # 解析结果
            status = VerificationStatus.PASS if result.get("status") == "pass" else VerificationStatus.FAIL
            severity = Severity(check.get("severity", "error"))

            return CheckResult(
                check_id=check["id"],
                check_name=check["name"],
                check_type=CheckType.PROGRAM,
                status=status,
                severity=severity,
                detail=result.get("detail", ""),
                suggestions=result.get("suggestions", []),
            )

        except Exception as e:
            return CheckResult(
                check_id=check["id"],
                check_name=check["name"],
                check_type=CheckType.PROGRAM,
                status=VerificationStatus.FAIL,
                severity=Severity.ERROR,
                detail=f"程序检查执行失败: {str(e)}",
            )

    def _run_ai_check(self, check: Dict[str, Any], artifacts: Dict[str, str], base_dir: str) -> CheckResult:
        """运行 AI 型检查"""
        # 注意：这里是伪实现，实际需要调用 orchestrator 的 agent 系统
        agent_name = check.get("agent", "")
        spec_path = check.get("spec", "")
        params = check.get("params", {})

        # 伪代码：模拟 AI 验证结果
        # 实际实现需要通过 orchestrator API 调用 agent
        mock_result = {
            "score": 0.85,
            "status": "pass",
            "detail": "架构设计合理，包含所有必需组件",
            "suggestions": [
                "建议添加更多监控指标",
                "考虑增加容错机制"
            ]
        }

        # 根据评分判断状态
        min_score = params.get("min_score", 0.8)
        status = VerificationStatus.PASS if mock_result["score"] >= min_score else VerificationStatus.FAIL
        severity = Severity(check.get("severity", "error"))

        return CheckResult(
            check_id=check["id"],
            check_name=check["name"],
            check_type=CheckType.AI,
            status=status,
            severity=severity,
            detail=mock_result["detail"],
            score=mock_result["score"],
            suggestions=mock_result.get("suggestions", []),
        )

    def _aggregate_status(self, check_results: List[CheckResult]) -> VerificationStatus:
        """聚合验证状态"""
        has_error_fail = any(
            c.status == VerificationStatus.FAIL and c.severity == Severity.ERROR
            for c in check_results
        )
        has_warning_fail = any(
            c.status == VerificationStatus.FAIL and c.severity == Severity.WARNING
            for c in check_results
        )

        if has_error_fail:
            return VerificationStatus.FAIL
        elif has_warning_fail:
            return VerificationStatus.WARNING
        else:
            return VerificationStatus.PASS

    def _save_result(self, result: VerificationResult, contract: Dict[str, Any], base_dir: str):
        """保存验证结果"""
        # 创建输出目录
        output_format = contract.get("output_format", {})
        result_file = output_format.get("result_file", "verification-result.yaml")
        report_file = output_format.get("report_file", "verification-report.md")

        result_path = Path(base_dir) / result_file
        report_path = Path(base_dir) / report_file

        # 确保目录存在
        result_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存 YAML 结果
        with open(result_path, 'w', encoding='utf-8') as f:
            yaml.dump(result.to_dict(), f, default_flow_style=False, allow_unicode=True)

        # 生成 Markdown 报告
        self._generate_markdown_report(result, report_path)

    def _generate_markdown_report(self, result: VerificationResult, report_path: Path):
        """生成 Markdown 报告"""
        lines = [
            f"# 验证报告",
            f"",
            f"**契约 ID**: {result.contract_id}",
            f"**验证时间**: {result.verification_time}",
            f"**总体状态**: {result.overall_status.value.upper()}",
            f"",
            f"## 摘要",
            f"",
            f"{result.summary}",
            f"",
            f"## 检查结果详情",
            f"",
            f"| 检查 ID | 检查名称 | 类型 | 状态 | 严重程度 | 详情 |",
            f"|---------|----------|------|------|----------|------|",
        ]

        for c in result.check_results:
            status_icon = "✅" if c.status == VerificationStatus.PASS else "❌" if c.status == VerificationStatus.FAIL else "⚠️"
            lines.append(
                f"| {c.check_id} | {c.check_name} | {c.check_type.value} | {status_icon} {c.status.value} | {c.severity.value} | {c.detail} |"
            )

        # 添加建议
        suggestions = [s for c in result.check_results for s in c.suggestions]
        if suggestions:
            lines.extend([
                f"",
                f"## 建议",
                f"",
            ])
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"{i}. {suggestion}")

        lines.extend([
            f"",
            f"---",
            f"",
            f"*由 LEE Verifier Engine 生成*",
        ])

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="LEE Verifier Engine")
    parser.add_argument("contract_id", help="契约 ID（例如：devops.phase1.architecture.v1）")
    parser.add_argument("--artifacts", help="产物文件（JSON 格式）")
    parser.add_argument("--base-dir", default=".", help="基础目录")
    parser.add_argument("--config", default="verifier/config.yaml", help="配置文件路径")

    args = parser.parse_args()

    # 加载产物
    if args.artifacts:
        with open(args.artifacts, 'r', encoding='utf-8') as f:
            artifacts = json.load(f)
    else:
        artifacts = {}

    # 创建验证引擎
    engine = VerifierEngine(config_path=args.config)

    # 执行验证
    result = engine.verify(args.contract_id, artifacts, args.base_dir)

    # 输出结果
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    # 返回退出码
    if result.overall_status == VerificationStatus.PASS:
        sys.exit(0)
    elif result.overall_status == VerificationStatus.WARNING:
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
