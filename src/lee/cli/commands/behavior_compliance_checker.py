"""
behavior_compliance_checker CLI — 行为合规检查器 v0.1

检查 test_runner 输出的 e2e-report.json 是否符合基本规范。

v0.1 极简版，只做:
  - report_json 文件存在且可解析
  - 每条 case 有 id / status / error_type
  - 可选：artifacts 路径存在检查

Exit Code 约定:
  0 — 合规
  1 — 不合规（有 violations）
  3 — 参数错误
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import click


@click.group()
def behavior_compliance_checker():
    """行为合规检查器 (v0.1)"""
    pass


@behavior_compliance_checker.command("verify")
@click.option("--report-json", required=True,
              type=click.Path(), help="e2e-report.json 文件路径")
@click.option("--check-artifacts/--no-check-artifacts", default=False,
              help="是否检查 artifacts 路径存在")
@click.option("--artifacts-base-dir", default=None,
              help="artifacts 基准目录（用于路径拼接）")
def verify(
    report_json: str,
    check_artifacts: bool,
    artifacts_base_dir: str,
) -> None:
    """验证 e2e-report.json 是否符合规范。"""

    report_path = Path(report_json)
    violations: List[Dict[str, Any]] = []

    # 1. 文件存在性
    if not report_path.exists():
        violations.append({
            "rule": "report_exists",
            "message": f"报告文件不存在: {report_path}",
        })
        _output_result(False, violations)
        sys.exit(1)

    # 2. JSON 可解析
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as exc:
        violations.append({
            "rule": "report_parseable",
            "message": f"JSON 解析失败: {exc}",
        })
        _output_result(False, violations)
        sys.exit(1)

    # 3. 顶层字段检查
    required_top_fields = ["suite", "env", "total", "passed", "failed", "cases"]
    for field in required_top_fields:
        if field not in report:
            violations.append({
                "rule": "top_level_field",
                "message": f"缺少顶层字段: {field}",
            })

    # 4. cases 数组检查
    cases = report.get("cases", [])
    if not isinstance(cases, list):
        violations.append({
            "rule": "cases_is_array",
            "message": "cases 字段不是数组",
        })
        cases = []

    # 5. 每条 case 字段检查
    required_case_fields = ["id", "status"]
    recommended_case_fields = ["error_type", "duration_ms"]

    for idx, case in enumerate(cases):
        if not isinstance(case, dict):
            violations.append({
                "rule": "case_is_object",
                "message": f"cases[{idx}] 不是对象",
            })
            continue

        for field in required_case_fields:
            if field not in case:
                violations.append({
                    "rule": "case_required_field",
                    "message": f"cases[{idx}] 缺少必填字段: {field}",
                    "case_index": idx,
                })

        # status 值域检查
        valid_statuses = {"passed", "failed", "skipped"}
        status = case.get("status")
        if status and status not in valid_statuses:
            violations.append({
                "rule": "case_status_value",
                "message": f"cases[{idx}] status 值无效: {status}（期望: {valid_statuses}）",
                "case_index": idx,
            })

        # 失败用例必须有 error_type
        if status == "failed" and not case.get("error_type"):
            violations.append({
                "rule": "failed_case_error_type",
                "message": f"cases[{idx}] 失败用例缺少 error_type",
                "case_index": idx,
            })

        # error_type 值域检查
        valid_error_types = {"assertion_failed", "script_error", "infra_error", None}
        error_type = case.get("error_type")
        if error_type and error_type not in valid_error_types:
            violations.append({
                "rule": "case_error_type_value",
                "message": f"cases[{idx}] error_type 值无效: {error_type}",
                "case_index": idx,
            })

    # 6. 可选：artifacts 路径检查
    if check_artifacts and cases:
        base = Path(artifacts_base_dir) if artifacts_base_dir else report_path.parent
        for idx, case in enumerate(cases):
            if not isinstance(case, dict):
                continue
            for art_field in ("screenshot", "trace", "logs"):
                art_path = case.get(art_field)
                if art_path:
                    full = base / art_path
                    if not full.exists():
                        violations.append({
                            "rule": "artifact_exists",
                            "message": f"cases[{idx}].{art_field} 路径不存在: {full}",
                            "case_index": idx,
                        })

    # 7. total/passed/failed 一致性检查
    total = report.get("total", 0)
    passed_count = report.get("passed", 0)
    failed_count = report.get("failed", 0)
    actual_total = len(cases)

    if total != actual_total:
        violations.append({
            "rule": "total_consistency",
            "message": f"total ({total}) != len(cases) ({actual_total})",
        })

    actual_passed = sum(1 for c in cases if isinstance(c, dict) and c.get("status") == "passed")
    actual_failed = sum(1 for c in cases if isinstance(c, dict) and c.get("status") == "failed")

    if passed_count != actual_passed:
        violations.append({
            "rule": "passed_consistency",
            "message": f"passed ({passed_count}) != 实际 passed ({actual_passed})",
        })

    if failed_count != actual_failed:
        violations.append({
            "rule": "failed_consistency",
            "message": f"failed ({failed_count}) != 实际 failed ({actual_failed})",
        })

    # 输出
    compliant = len(violations) == 0
    _output_result(compliant, violations)
    sys.exit(0 if compliant else 1)


def _output_result(compliant: bool, violations: List[Dict[str, Any]]) -> None:
    """输出合规检查结果到 stdout。"""
    result = {
        "compliant": compliant,
        "violations": violations,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))
