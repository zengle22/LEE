"""
QA Orchestrator Extensions 单元测试

测试内容：
1. Evidence Verifiers (evidence_exists, evidence_reference)
2. Behavior Compliance Verifier
3. check_env CLI 工具
4. GateEngine 新增评估器
5. Orchestrator 新增 step 类型
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime

from lee.orchestrator.verifiers.base import VerifyStatus
from lee.orchestrator.verifiers.evidence import EvidenceExistsVerifier, EvidenceReferenceVerifier
from lee.orchestrator.verifiers.behavior_compliance import BehaviorComplianceVerifier
from lee.orchestrator.verifier_engine import VerifierEngine
from lee.orchestrator.tools.check_env import EnvChecker, run_check_env
from lee.orchestrator.execution.gate_engine import GateEngine


# ============================================================================
# Evidence Verifiers 测试
# ============================================================================

class TestEvidenceExistsVerifier:
    """EvidenceExistsVerifier 单元测试"""

    def test_verifier_id(self):
        """测试 verifier_id"""
        verifier = EvidenceExistsVerifier()
        assert verifier.verifier_id == "evidence_exists"

    def test_missing_evidence_dir_config(self):
        """测试缺少 evidence_dir 配置"""
        verifier = EvidenceExistsVerifier()
        result = verifier.verify({"config": {}})

        assert result.status == VerifyStatus.FAILED
        assert "evidence_dir not configured" in result.message

    def test_evidence_dir_not_found(self):
        """测试证据目录不存在"""
        verifier = EvidenceExistsVerifier()
        result = verifier.verify({
            "project_root": "/tmp/nonexistent",
            "config": {
                "evidence_dir": "evidence/test",
                "error_status": "invalid_run",
            }
        })

        assert result.status == VerifyStatus.FAILED
        assert "not found" in result.message
        assert result.details["error_status"] == "invalid_run"

    def test_evidence_exists_pass(self):
        """测试证据存在时通过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建证据目录和文件
            evidence_dir = Path(tmpdir) / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "test.log").write_text("log content")
            (evidence_dir / "screenshot.png").write_text("fake png")

            verifier = EvidenceExistsVerifier()
            result = verifier.verify({
                "project_root": tmpdir,
                "config": {
                    "evidence_dir": "evidence",
                    "required_files": [
                        {"pattern": "*.log", "description": "执行日志"},
                        {"pattern": "*.png", "description": "截图"},
                    ],
                }
            })

            assert result.status == VerifyStatus.PASSED
            assert "All required evidence files exist" in result.message

    def test_evidence_missing_required_files(self):
        """测试缺少必需文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建证据目录但不创建文件
            evidence_dir = Path(tmpdir) / "evidence"
            evidence_dir.mkdir()

            verifier = EvidenceExistsVerifier()
            result = verifier.verify({
                "project_root": tmpdir,
                "config": {
                    "evidence_dir": "evidence",
                    "required_files": [
                        {"pattern": "*.log", "description": "执行日志"},
                    ],
                    "fail_on_missing": True,
                }
            })

            assert result.status == VerifyStatus.FAILED
            assert "执行日志" in result.message

    def test_optional_file_with_condition(self):
        """测试带条件的可选文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_dir = Path(tmpdir) / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "test.log").write_text("log")

            verifier = EvidenceExistsVerifier()
            result = verifier.verify({
                "project_root": tmpdir,
                "case": {"meta": {"headless": True}},
                "config": {
                    "evidence_dir": "evidence",
                    "required_files": [
                        {"pattern": "*.log", "description": "执行日志"},
                        {"pattern": "*.png", "description": "截图", "optional_if": "case.meta.headless == true"},
                    ],
                }
            })

            # 因为 headless=true，所以 png 是可选的
            assert result.status == VerifyStatus.PASSED


class TestEvidenceReferenceVerifier:
    """EvidenceReferenceVerifier 单元测试"""

    def test_verifier_id(self):
        """测试 verifier_id"""
        verifier = EvidenceReferenceVerifier()
        assert verifier.verifier_id == "evidence_reference"

    def test_no_cases_pass(self):
        """测试无用例时通过"""
        verifier = EvidenceReferenceVerifier()
        result = verifier.verify({
            "execution_results": {"cases": []},
            "config": {},
        })

        assert result.status == VerifyStatus.PASSED

    def test_all_cases_have_evidence(self):
        """测试所有用例都有证据"""
        verifier = EvidenceReferenceVerifier()
        result = verifier.verify({
            "execution_results": {
                "cases": [
                    {
                        "case_id": "TC001",
                        "evidence_bundle": {
                            "logs": "evidence/tc001.log",
                            "runner_result_ref": "runner-output.json#TC001",
                        }
                    },
                    {
                        "case_id": "TC002",
                        "evidence_bundle": {
                            "logs": "evidence/tc002.log",
                            "runner_result_ref": "runner-output.json#TC002",
                        }
                    },
                ]
            },
            "config": {},
        })

        assert result.status == VerifyStatus.PASSED

    def test_case_missing_evidence(self):
        """测试用例缺少证据"""
        verifier = EvidenceReferenceVerifier()
        result = verifier.verify({
            "execution_results": {
                "cases": [
                    {"case_id": "TC001", "evidence_bundle": None},
                    {"case_id": "TC002"},  # 完全没有 evidence_bundle
                ]
            },
            "config": {"fail_on_error": True},
        })

        assert result.status == VerifyStatus.FAILED
        assert "TC001" in result.message
        assert "TC002" in result.message

    def test_case_missing_logs(self):
        """测试用例缺少 logs 字段"""
        verifier = EvidenceReferenceVerifier()
        result = verifier.verify({
            "execution_results": {
                "cases": [
                    {
                        "case_id": "TC001",
                        "evidence_bundle": {
                            "runner_result_ref": "runner-output.json#TC001",
                            # 缺少 logs
                        }
                    },
                ]
            },
            "config": {"fail_on_error": True},
        })

        assert result.status == VerifyStatus.FAILED
        assert "missing logs" in result.message


# ============================================================================
# Behavior Compliance Verifier 测试
# ============================================================================

class TestBehaviorComplianceVerifier:
    """BehaviorComplianceVerifier 单元测试"""

    def test_verifier_id(self):
        """测试 verifier_id"""
        verifier = BehaviorComplianceVerifier()
        assert verifier.verifier_id == "behavior_compliance"

    def test_compliant_behavior(self):
        """测试合规行为"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "status": "pass",
                        "result_text": "Test passed successfully",
                        "evidence_bundle": {"logs": "test.log", "screenshots": ["s1.png"]},
                    }
                ]
            },
            "confirmed_env_errors": [],
            "config": {},
        })

        assert result.status == VerifyStatus.PASSED
        assert "AI behavior compliant" in result.message

    def test_mock_pattern_violation(self):
        """测试 mock 关键词违规"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "result_text": "使用 mock 数据模拟了接口返回",
                        "meta": {"allow_mock": False},
                    }
                ]
            },
            "confirmed_env_errors": [],
            "config": {},
        })

        assert result.status == VerifyStatus.FAILED
        violations = result.details["violations"]
        assert len(violations) > 0
        assert violations[0]["rule_id"] == "no_mock_without_flag"

    def test_mock_allowed_when_flagged(self):
        """测试允许 mock 时不违规"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "result_text": "使用 mock 数据",
                        "meta": {"allow_mock": True},  # 显式允许
                    }
                ]
            },
            "confirmed_env_errors": [],
            "config": {},
        })

        assert result.status == VerifyStatus.PASSED

    def test_network_error_without_source(self):
        """测试无来源的网络错误违规"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "claimed_network_error": True,
                        "runtime_errors": {"source": "ai_claimed"},  # 非法来源
                    }
                ]
            },
            "confirmed_env_errors": [],
            "config": {},
        })

        assert result.status == VerifyStatus.FAILED
        violations = result.details["violations"]
        rule_ids = [v["rule_id"] for v in violations]
        assert "no_network_error_without_runtime_error" in rule_ids

    def test_network_error_with_valid_source(self):
        """测试有合法来源的网络错误"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "claimed_network_error": True,
                        "runtime_errors": {"source": "runner_cli"},  # 合法来源
                    }
                ]
            },
            "confirmed_env_errors": [],
            "config": {},
        })

        assert result.status == VerifyStatus.PASSED

    def test_tool_missing_without_confirmation(self):
        """测试未确认的工具缺失违规"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "claimed_tool_missing": True,
                        "missing_tool": "playwright",
                    }
                ]
            },
            "confirmed_env_errors": [],  # Orchestrator 没有确认
            "config": {},
        })

        assert result.status == VerifyStatus.FAILED
        violations = result.details["violations"]
        rule_ids = [v["rule_id"] for v in violations]
        assert "no_tool_missing_without_check" in rule_ids

    def test_tool_missing_with_confirmation(self):
        """测试有确认的工具缺失"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "claimed_tool_missing": True,
                        "missing_tool": "playwright",
                    }
                ]
            },
            "confirmed_env_errors": ["command_missing:playwright"],  # Orchestrator 确认
            "config": {},
        })

        assert result.status == VerifyStatus.PASSED

    def test_p0_case_without_evidence(self):
        """测试 P0 用例缺少证据"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "priority": "P0",
                        "evidence_bundle": None,
                    }
                ]
            },
            "confirmed_env_errors": [],
            "config": {},
        })

        assert result.status == VerifyStatus.FAILED
        violations = result.details["violations"]
        rule_ids = [v["rule_id"] for v in violations]
        assert "evidence_required_for_p0_p1" in rule_ids

    def test_pass_without_evidence(self):
        """测试无证据的 pass 结论"""
        verifier = BehaviorComplianceVerifier()
        result = verifier.verify({
            "runner_output": {
                "case_results": [
                    {
                        "case_id": "TC001",
                        "status": "pass",
                        "evidence_bundle": {},  # 空证据
                    }
                ]
            },
            "confirmed_env_errors": [],
            "config": {},
        })

        assert result.status == VerifyStatus.FAILED
        violations = result.details["violations"]
        rule_ids = [v["rule_id"] for v in violations]
        assert "no_fabricated_pass" in rule_ids


# ============================================================================
# check_env CLI 工具测试
# ============================================================================

class TestEnvChecker:
    """EnvChecker 单元测试"""

    def test_command_exists_pass(self):
        """测试命令存在"""
        checker = EnvChecker()
        result = checker.check([
            {"type": "command_exists", "commands": ["python", "ls"]}
        ])

        assert result.all_passed is True
        assert len(result.failures) == 0

    def test_command_not_exists(self):
        """测试命令不存在"""
        checker = EnvChecker()
        result = checker.check([
            {"type": "command_exists", "commands": ["nonexistent_command_xyz"]}
        ])

        assert result.all_passed is False
        assert "command_missing:nonexistent_command_xyz" in result.failures

    def test_directory_writable(self):
        """测试目录可写"""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = EnvChecker(project_root=tmpdir)
            result = checker.check([
                {"type": "directory_writable", "paths": ["test_dir"]}
            ])

            assert result.all_passed is True
            # 目录应该被创建
            assert (Path(tmpdir) / "test_dir").exists()

    def test_service_not_reachable(self):
        """测试服务不可达"""
        checker = EnvChecker()
        result = checker.check([
            {"type": "service_reachable", "endpoints": [{"url": "nonexistent.invalid.local", "port": 12345}]}
        ])

        assert result.all_passed is False
        assert any("network:" in f for f in result.failures)

    def test_run_check_env_with_output(self):
        """测试 run_check_env 函数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "result.json"

            result = run_check_env(
                checks=[{"type": "command_exists", "commands": ["python"]}],
                output_path=str(output_path)
            )

            assert result.all_passed is True
            assert output_path.exists()

            # 验证 JSON 内容
            with open(output_path) as f:
                data = json.load(f)
            assert data["all_passed"] is True


# ============================================================================
# GateEngine 评估器测试
# ============================================================================

class TestGateEngineNewEvaluators:
    """GateEngine 新增评估器测试"""

    def test_pattern_not_contains_pass(self):
        """测试模式不包含 - 通过"""
        engine = GateEngine()
        passed, actual, expected, error = engine._evaluate_pattern_not_contains(
            "result_text NOT_CONTAINS mock,模拟",
            {"result_text": "Test passed successfully"}
        )

        assert passed is True
        assert error is None

    def test_pattern_not_contains_fail(self):
        """测试模式不包含 - 失败"""
        engine = GateEngine()
        passed, actual, expected, error = engine._evaluate_pattern_not_contains(
            "result_text NOT_CONTAINS mock,模拟",
            {"result_text": "使用 mock 数据进行测试"}
        )

        assert passed is False
        assert "mock" in actual

    def test_error_source_valid_pass(self):
        """测试错误来源有效 - 通过"""
        engine = GateEngine()
        passed, actual, expected, error = engine._evaluate_error_source_valid(
            "runtime_errors.source",
            {"runtime_errors": {"source": "runner_cli"}}
        )

        assert passed is True

    def test_error_source_valid_fail(self):
        """测试错误来源有效 - 失败"""
        engine = GateEngine()
        passed, actual, expected, error = engine._evaluate_error_source_valid(
            "runtime_errors.source",
            {"runtime_errors": {"source": "ai_claimed"}}
        )

        assert passed is False
        assert "ai_claimed" in str(actual)

    def test_error_source_valid_no_error(self):
        """测试无错误时通过"""
        engine = GateEngine()
        passed, actual, expected, error = engine._evaluate_error_source_valid(
            "runtime_errors.source",
            {}  # 没有 runtime_errors
        )

        assert passed is True

    def test_evidence_exists_evaluator_pass(self):
        """测试证据存在评估器 - 通过"""
        engine = GateEngine()
        passed, actual, expected, error = engine._evaluate_evidence_exists(
            "evidence_bundle",
            {"evidence_bundle": {"logs": "test.log", "screenshots": ["s1.png"]}}
        )

        assert passed is True

    def test_evidence_exists_evaluator_fail(self):
        """测试证据存在评估器 - 失败"""
        engine = GateEngine()
        passed, actual, expected, error = engine._evaluate_evidence_exists(
            "evidence_bundle",
            {"evidence_bundle": None}
        )

        assert passed is False


# ============================================================================
# VerifierEngine 集成测试
# ============================================================================

class TestVerifierEngineIntegration:
    """VerifierEngine 集成测试"""

    def test_evidence_exists_registered(self):
        """测试 evidence_exists 已注册"""
        engine = VerifierEngine("/tmp")
        assert "evidence_exists" in engine._registry

    def test_evidence_reference_registered(self):
        """测试 evidence_reference 已注册"""
        engine = VerifierEngine("/tmp")
        assert "evidence_reference" in engine._registry

    def test_behavior_compliance_registered(self):
        """测试 behavior_compliance 已注册"""
        engine = VerifierEngine("/tmp")
        assert "behavior_compliance" in engine._registry

    def test_run_behavior_compliance(self):
        """测试运行 behavior_compliance 验证器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = VerifierEngine(tmpdir)

            results = engine.run(
                verifiers=[
                    {
                        "type": "behavior_compliance",
                        "config": {},
                    }
                ],
                context={
                    "runner_output": {
                        "case_results": [
                            {
                                "case_id": "TC001",
                                "result_text": "mock 数据",
                                "meta": {"allow_mock": False},
                            }
                        ]
                    },
                    "confirmed_env_errors": [],
                }
            )

            assert len(results) == 1
            assert results[0].status == VerifyStatus.FAILED


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
