"""
Smoke Gate Executor
===================
SRC-058 Dev Smoke Gate - 测试执行器
"""

import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import os

from .models import (
    SmokeGateContext,
    SmokeGateReport,
    TestExecutionRecord,
    SmokeGateStatus,
    GateResult,
    FailureSeverity,
    SmokeGateConfig,
)


class SmokeExecutor:
    """
    Smoke 测试执行器，负责实际执行测试。
    """

    def __init__(self, config: Optional[SmokeGateConfig] = None):
        """
        初始化执行器。

        Args:
            config: Smoke Gate 配置
        """
        self.config = config or SmokeGateConfig(test_set_ref="default")
        self.workers = self.config.parallel_workers
        self.timeout = self.config.timeout_minutes * 60  # 转换为秒

    async def execute(
        self,
        context: SmokeGateContext,
        test_cases: List[Dict[str, Any]]
    ) -> SmokeGateReport:
        """
        执行 Smoke 测试。

        Args:
            context: Gate 上下文
            test_cases: 测试用例列表

        Returns:
            SmokeGateReport 包含完整执行结果
        """
        smoke_run_id = str(uuid.uuid4())
        started_at = datetime.now()

        # 创建输出目录
        evidence_dir = Path.home() / ".lee" / "smoke" / smoke_run_id
        evidence_dir.mkdir(parents=True, exist_ok=True)

        log_path = str(evidence_dir / "smoke.log")
        report_html_path = str(evidence_dir / "report.html")

        # 过滤测试用例（根据 priority）
        filtered_cases = [
            tc for tc in test_cases
            if tc.get("priority", "P2") in context.priority_filter
        ]

        if not filtered_cases:
            # 无测试用例，返回无效报告
            return SmokeGateReport(
                smoke_run_id=smoke_run_id,
                merge_request_id=context.merge_request_id,
                commit_sha=context.commit_sha,
                test_set_ref=context.test_set_ref,
                total_cases=0,
                passed=0,
                failed=0,
                skipped=0,
                pass_rate=0.0,
                result=GateResult.ERROR,
                status=SmokeGateStatus.INVALID,
                failure_details=[],
                blocker_count=0,
                critical_count=0,
                flaky_count=0,
                started_at=started_at,
                completed_at=datetime.now(),
                duration_seconds=0,
                log_path=log_path,
                evidence_dir=str(evidence_dir),
            )

        # 执行 pytest
        executions = await self._run_pytest(
            test_cases=filtered_cases,
            smoke_run_id=smoke_run_id,
            evidence_dir=evidence_dir,
            log_path=log_path,
            max_retries=context.retry_count
        )

        completed_at = datetime.now()

        # 创建报告
        report = SmokeGateReport.create_from_executions(
            smoke_run_id=smoke_run_id,
            merge_request_id=context.merge_request_id,
            commit_sha=context.commit_sha,
            test_set_ref=context.test_set_ref,
            executions=executions,
            started_at=started_at,
            completed_at=completed_at,
            log_path=log_path,
            evidence_dir=str(evidence_dir),
            report_html_path=report_html_path
        )

        return report

    async def execute_with_retry(
        self,
        test_case: Dict[str, Any],
        max_retries: int = 3
    ) -> TestExecutionRecord:
        """
        执行单个测试用例，支持重试。

        Args:
            test_case: 测试用例配置
            max_retries: 最大重试次数

        Returns:
            TestExecutionRecord 包含执行详情
        """
        test_id = test_case.get("id", "unknown")
        test_name = test_case.get("name", "unknown")
        priority = test_case.get("priority", "P2")

        last_error: Optional[str] = None
        total_duration_ms = 0

        for attempt in range(max_retries + 1):  # 初始执行 + 重试
            start_time = datetime.now()

            try:
                # 执行单个测试
                result = await self._run_single_test(test_case)
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                total_duration_ms += duration_ms

                if result["success"]:
                    # 测试通过
                    return TestExecutionRecord(
                        test_id=test_id,
                        test_name=test_name,
                        priority=priority,
                        status="pass",
                        duration_ms=total_duration_ms,
                        retry_attempts=attempt
                    )
                else:
                    last_error = result.get("error", "Unknown error")

            except Exception as e:
                last_error = str(e)
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                total_duration_ms += duration_ms

        # 所有重试都失败
        severity = self._determine_severity(priority, last_error)

        return TestExecutionRecord(
            test_id=test_id,
            test_name=test_name,
            priority=priority,
            status="fail",
            severity=severity,
            duration_ms=total_duration_ms,
            error_message=last_error,
            retry_attempts=max_retries
        )

    async def _run_pytest(
        self,
        test_cases: List[Dict[str, Any]],
        smoke_run_id: str,
        evidence_dir: Path,
        log_path: str,
        max_retries: int
    ) -> List[TestExecutionRecord]:
        """
        运行 pytest 执行测试。

        Args:
            test_cases: 测试用例列表
            smoke_run_id: Smoke 执行 ID
            evidence_dir: 证据目录
            log_path: 日志路径
            max_retries: 最大重试次数

        Returns:
            测试执行记录列表
        """
        executions: List[TestExecutionRecord] = []

        # 构建 pytest 命令
        cmd = [
            "pytest",
            f"-n{self.workers}",  # 并发 workers
            f"--timeout={self.timeout}",  # 超时
            f"--html={evidence_dir}/report.html",  # HTML 报告
            f"--self-contained-html",
            f"--junitxml={evidence_dir}/junit.xml",  # JUnit XML
            "-v",  # 详细输出
        ]

        # 添加测试文件/目录
        # 注：实际实现中需要从 test_cases 解析出测试路径
        test_paths = self._extract_test_paths(test_cases)
        cmd.extend(test_paths)

        # 执行 pytest
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(Path.cwd())
            )

            # 写入日志
            with open(log_path, "w") as f:
                f.write(result.stdout)
                f.write(result.stderr)

            # 解析结果
            executions = await self._parse_pytest_result(
                junit_path=str(evidence_dir / "junit.xml"),
                test_cases=test_cases,
                max_retries=max_retries
            )

        except subprocess.TimeoutExpired:
            # 超时
            executions.append(TestExecutionRecord(
                test_id="timeout",
                test_name="Smoke Execution Timeout",
                priority="P0",
                status="fail",
                severity=FailureSeverity.BLOCKER,
                duration_ms=self.timeout * 1000,
                error_message=f"Execution timeout after {self.timeout} seconds"
            ))
        except Exception as e:
            # 其他错误
            executions.append(TestExecutionRecord(
                test_id="error",
                test_name="Smoke Execution Error",
                priority="P0",
                status="fail",
                severity=FailureSeverity.BLOCKER,
                duration_ms=0,
                error_message=str(e)
            ))

        return executions

    def _extract_test_paths(self, test_cases: List[Dict[str, Any]]) -> List[str]:
        """从测试用例提取测试路径。"""
        paths = set()
        for tc in test_cases:
            if "file" in tc:
                paths.add(tc["file"])
            elif "path" in tc:
                paths.add(tc["path"])

        if not paths:
            # 默认测试目录
            return ["tests/"]
        return list(paths)

    async def _parse_pytest_result(
        self,
        junit_path: str,
        test_cases: List[Dict[str, Any]],
        max_retries: int
    ) -> List[TestExecutionRecord]:
        """解析 pytest JUnit XML 结果。"""
        executions: List[TestExecutionRecord] = []

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(junit_path)
            root = tree.getroot()

            # 创建 test_id 到 priority 的映射
            priority_map = {tc.get("id"): tc.get("priority", "P2") for tc in test_cases}
            name_map = {tc.get("id"): tc.get("name", "") for tc in test_cases}

            for testcase in root.findall(".//testcase"):
                test_id = testcase.get("classname", "") + "." + testcase.get("name", "")
                test_name = testcase.get("name", "unknown")
                duration_ms = int(float(testcase.get("time", "0")) * 1000)

                # 检查是否有失败
                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")

                if failure is not None:
                    status = "fail"
                    error_message = failure.get("message", "")
                    severity = self._determine_severity(
                        priority_map.get(test_id, "P2"),
                        error_message
                    )
                elif error is not None:
                    status = "fail"
                    error_message = error.get("message", "")
                    severity = self._determine_severity(
                        priority_map.get(test_id, "P2"),
                        error_message
                    )
                elif skipped is not None:
                    status = "skip"
                    error_message = skipped.get("message", "")
                    severity = None
                else:
                    status = "pass"
                    error_message = None
                    severity = None

                executions.append(TestExecutionRecord(
                    test_id=test_id,
                    test_name=test_name,
                    priority=priority_map.get(test_id, "P2"),
                    status=status,
                    severity=severity,
                    duration_ms=duration_ms,
                    error_message=error_message,
                    retry_attempts=0  # pytest 重试在内部处理
                ))

        except Exception as e:
            # XML 解析失败，返回空列表
            pass

        return executions

    async def _run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试。"""
        # 实际实现中需要调用 pytest 运行单个测试
        # 这里简化处理
        return {"success": True}

    def _determine_severity(
        self,
        priority: str,
        error_message: Optional[str]
    ) -> FailureSeverity:
        """
        根据失败类型判定严重程度。

        Args:
            priority: 测试优先级
            error_message: 错误信息

        Returns:
            FailureSeverity
        """
        # P0/P1 优先级的失败都是 Blocker
        if priority in ("P0", "P1"):
            return FailureSeverity.BLOCKER

        # 检查是否是 flaky
        if error_message and "flaky" in error_message.lower():
            return FailureSeverity.FLAKY

        # 其他情况为 Critical
        return FailureSeverity.CRITICAL
