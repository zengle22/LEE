"""
test_runner v0.1 单元测试

测试覆盖：
- test_runner CLI: 参数解析、exit code 映射、Playwright 报告转换
- check_env CLI: 各检查项通过/失败场景
- behavior_compliance_checker CLI: 合规/不合规 report 校验
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from lee.cli.commands.test_runner import (
    test_runner,
    _classify_error,
    _transform_playwright_report,
    EXIT_SUCCESS,
    EXIT_TEST_FAILURE,
    EXIT_INFRA_ERROR,
    EXIT_INVALID_ARGS,
)
from lee.cli.commands.check_env import check_env
from lee.cli.commands.behavior_compliance_checker import behavior_compliance_checker

_WORKSPACE_TMP_ROOT = Path(__file__).resolve().parent.parent / ".test-temp-test-runner"
_WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_case_dir(prefix: str) -> Path:
    path = _WORKSPACE_TMP_ROOT / f"{prefix}-{uuid.uuid4().hex}"
    if path.exists():
        __import__('shutil').rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path



# ══════════════════════════════════════════════════════════
# test_runner 测试
# ══════════════════════════════════════════════════════════

class TestClassifyError:
    """测试错误分类逻辑。"""

    def test_infra_error_econnrefused(self):
        assert _classify_error("ECONNREFUSED 127.0.0.1:3000", "failed") == "infra_error"

    def test_infra_error_dns(self):
        assert _classify_error("getaddrinfo ENOTFOUND example.com", "failed") == "infra_error"

    def test_infra_error_network(self):
        assert _classify_error("net::ERR_CONNECTION_REFUSED", "failed") == "infra_error"

    def test_script_error_timeout(self):
        assert _classify_error("Timeout 30000ms exceeded", "failed") == "script_error"

    def test_script_error_locator(self):
        assert _classify_error("Locator('#btn') not found", "failed") == "script_error"

    def test_assertion_failed_expect(self):
        assert _classify_error("expect(received).toBe(expected)", "failed") == "assertion_failed"

    def test_assertion_failed_default(self):
        assert _classify_error("some unknown error", "failed") == "assertion_failed"

    def test_empty_error_msg(self):
        assert _classify_error("", "failed") == "script_error"


class TestTransformPlaywrightReport:
    """测试 Playwright JSON → 标准报告转换。"""

    def _make_pw_report(self, specs):
        """构造一个最小 Playwright JSON reporter 格式。"""
        return {
            "suites": [{
                "title": "test suite",
                "specs": specs,
            }],
        }

    def test_all_passed(self):
        pw = self._make_pw_report([
            {
                "title": "TC_001",
                "tests": [{"results": [{"status": "passed", "duration": 500}]}],
            },
            {
                "title": "TC_002",
                "tests": [{"results": [{"status": "passed", "duration": 300}]}],
            },
        ])
        case_dir = _make_case_dir("empty-report")
        result = _transform_playwright_report(pw, "smoke", "test", case_dir)
        assert result["total"] == 2
        assert result["passed"] == 2
        assert result["failed"] == 0
        assert len(result["cases"]) == 2
        assert all(c["status"] == "passed" for c in result["cases"])

    def test_some_failed(self):
        pw = self._make_pw_report([
            {
                "title": "TC_001",
                "tests": [{"results": [{"status": "passed", "duration": 500}]}],
            },
            {
                "title": "TC_FAIL_001",
                "tests": [{
                    "results": [{
                        "status": "failed",
                        "duration": 1200,
                        "error": {"message": "expect(page).toHaveURL(/dashboard/)"},
                        "attachments": [],
                    }],
                }],
            },
        ])
        case_dir = _make_case_dir("empty-report")
        result = _transform_playwright_report(pw, "smoke", "test", case_dir)
        assert result["total"] == 2
        assert result["passed"] == 1
        assert result["failed"] == 1

        failed_case = [c for c in result["cases"] if c["status"] == "failed"][0]
        assert failed_case["error_type"] == "assertion_failed"
        assert "toHaveURL" in failed_case["error_message"]

    def test_empty_report(self):
        pw = {"suites": []}
        case_dir = _make_case_dir("empty-report")
        result = _transform_playwright_report(pw, "smoke", "test", case_dir)
        assert result["total"] == 0
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["cases"] == []

    def test_suite_and_env_preserved(self):
        pw = {"suites": []}
        case_dir = _make_case_dir("suite-env")
        result = _transform_playwright_report(pw, "regression", "staging", case_dir)
        assert result["suite"] == "regression"
        assert result["env"] == "staging"


class TestTestRunnerCLI:
    """测试 test_runner CLI 参数解析和 exit code。"""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(test_runner, ["run-e2e", "--help"])
        assert result.exit_code == 0
        assert "--suite" in result.output
        assert "--env" in result.output

    def test_missing_required_args(self):
        runner = CliRunner()
        result = runner.invoke(test_runner, ["run-e2e"])
        assert result.exit_code != 0  # Click 参数缺失

    def test_nonexistent_test_set(self):
        runner = CliRunner()
        result = runner.invoke(test_runner, [
            "run-e2e",
            "--suite", "smoke",
            "--env", "test",
            "--test-set", "/nonexistent/file.yaml",
            "--out-dir", "/tmp/test_out",
            "--report-json", "/tmp/test_out/report.json",
        ])
        assert result.exit_code != 0  # Click 的 exists=True 校验


# ══════════════════════════════════════════════════════════
# check_env 测试
# ══════════════════════════════════════════════════════════

class TestCheckEnvCLI:
    """测试 check_env CLI。"""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(check_env, ["qa-e2e", "--help"])
        assert result.exit_code == 0
        assert "--require-docker" in result.output

    @patch("lee.cli.commands.check_env.shutil.which")
    @patch("lee.cli.commands.check_env.subprocess.run")
    def test_docker_not_found(self, mock_run, mock_which):
        mock_which.return_value = None  # docker not found

        runner = CliRunner()
        result = runner.invoke(check_env, [
            "qa-e2e",
            "--no-require-docker",  # 跳过 docker 检查
            "--require-script", "/nonexistent/script.sh",
        ])
        # 脚本不存在应该导致 checks 中有失败
        output = json.loads(result.output)
        assert output["ok"] is False
        assert any(c["name"] == "run_e2e_script" and not c["ok"]
                    for c in output["checks"])

    @patch("lee.cli.commands.check_env._check_docker")
    @patch("lee.cli.commands.check_env._check_script")
    @patch("lee.cli.commands.check_env._check_docker_image")
    def test_all_pass(self, mock_image, mock_script, mock_docker):
        mock_docker.return_value = {"name": "docker", "ok": True}
        mock_script.return_value = {"name": "run_e2e_script", "ok": True}
        mock_image.return_value = {"name": "docker_image", "ok": True}

        runner = CliRunner()
        result = runner.invoke(check_env, ["qa-e2e"])
        output = json.loads(result.output)
        assert output["ok"] is True
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════
# behavior_compliance_checker 测试
# ══════════════════════════════════════════════════════════

class TestBehaviorComplianceChecker:
    """测试行为合规检查器。"""

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(behavior_compliance_checker, ["verify", "--help"])
        assert result.exit_code == 0
        assert "--report-json" in result.output

    def test_report_not_found(self):
        runner = CliRunner()
        result = runner.invoke(behavior_compliance_checker, [
            "verify",
            "--report-json", str(_make_case_dir("report-not-found") / "nonexistent.json"),
        ])
        output = json.loads(result.output)
        assert output["compliant"] is False
        assert any(v["rule"] == "report_exists" for v in output["violations"])

    def test_valid_report(self):
        report = {
            "suite": "smoke",
            "env": "test",
            "total": 2,
            "passed": 1,
            "failed": 1,
            "cases": [
                {
                    "id": "TC_001",
                    "status": "passed",
                    "error_type": None,
                    "duration_ms": 500,
                    "error_message": None,
                    "screenshot": None,
                    "trace": None,
                    "logs": None,
                },
                {
                    "id": "TC_002",
                    "status": "failed",
                    "error_type": "assertion_failed",
                    "duration_ms": 1200,
                    "error_message": "Expected /dashboard",
                    "screenshot": None,
                    "trace": None,
                    "logs": None,
                },
            ],
        }
        case_dir = _make_case_dir("bad-totals")
        report_path = case_dir / "e2e-report.json"
        with open(report_path, "w") as f:
            json.dump(report, f)

        runner = CliRunner()
        result = runner.invoke(behavior_compliance_checker, [
            "verify",
            "--report-json", str(report_path),
        ])
        output = json.loads(result.output)
        assert output["compliant"] is True
        assert output["violations"] == []

    def test_missing_case_fields(self):
        report = {
            "suite": "smoke",
            "env": "test",
            "total": 1,
            "passed": 0,
            "failed": 1,
            "cases": [
                {"status": "failed"},  # 缺少 id 和 error_type
            ],
        }
        case_dir = _make_case_dir("bad-totals")
        report_path = case_dir / "e2e-report.json"
        with open(report_path, "w") as f:
            json.dump(report, f)

        runner = CliRunner()
        result = runner.invoke(behavior_compliance_checker, [
            "verify",
            "--report-json", str(report_path),
        ])
        output = json.loads(result.output)
        assert output["compliant"] is False
        rules = [v["rule"] for v in output["violations"]]
        assert "case_required_field" in rules
        assert "failed_case_error_type" in rules

    def test_inconsistent_totals(self):
        report = {
            "suite": "smoke",
            "env": "test",
            "total": 5,  # 声称 5 个，实际只有 1 个
            "passed": 1,
            "failed": 0,
            "cases": [
                {"id": "TC_001", "status": "passed"},
            ],
        }
        case_dir = _make_case_dir("bad-totals")
        report_path = case_dir / "e2e-report.json"
        with open(report_path, "w") as f:
            json.dump(report, f)

        runner = CliRunner()
        result = runner.invoke(behavior_compliance_checker, [
            "verify",
            "--report-json", str(report_path),
        ])
        output = json.loads(result.output)
        assert output["compliant"] is False
        rules = [v["rule"] for v in output["violations"]]
        assert "total_consistency" in rules

    def test_invalid_json(self):
        case_dir = _make_case_dir("invalid-json")
        report_path = case_dir / "bad.json"
        with open(report_path, "w") as f:
            f.write("{invalid json")

        runner = CliRunner()
        result = runner.invoke(behavior_compliance_checker, [
            "verify",
            "--report-json", str(report_path),
        ])
        output = json.loads(result.output)
        assert output["compliant"] is False
        assert any(v["rule"] == "report_parseable" for v in output["violations"])
