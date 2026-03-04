"""
QA Module - Local Runner

Local test runner using Python Playwright API.
"""

import asyncio
import importlib.util
import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional

from lee.qa.runner.base import BaseRunner, TestConfig, TestResult, CaseResult
from lee.qa.classifier.context_collector import ContextCollector
from lee.qa.classifier.error_classifier import ErrorClassifier


class LocalRunner(BaseRunner):
    """
    Local test runner using Playwright Python API.

    Executes tests directly in the current Python process
    for better integration and error handling.
    """

    @property
    def name(self) -> str:
        return "local"

    def check_environment(self) -> Dict[str, bool]:
        """Check if required dependencies are available"""
        checks = {}

        # Check playwright module
        try:
            import playwright
            checks["playwright"] = True
        except ImportError:
            checks["playwright"] = False

        # Check chromium browser
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            checks["chromium"] = True
        except Exception:
            checks["chromium"] = False

        # Check pytest (使用 python -m pytest 确保兼容性)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                timeout=5
            )
            checks["pytest"] = result.returncode == 0
        except Exception:
            checks["pytest"] = False

        return checks

    def execute(self) -> TestResult:
        """
        Execute test scripts and collect results.

        Returns:
            TestResult with execution results
        """
        start_time = 0  # Placeholder for actual timing

        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "cases": [],
            "exit_code": 0,
            "error": None,
        }

        try:
            # Import playwright for execution
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.config.headless,
                    args=['--no-sandbox', '--disable-dev-shm-usage'],
                )

                context = browser.new_context(
                    base_url=self.config.base_url,
                    record_video_dir=str(self.config.video_dir) if self.config.video_dir else None,
                )

                page = context.new_page()
                page.set_default_timeout(self.config.timeout)

                # Execute each test script
                for script_path in self.config.scripts:
                    script_results = self._execute_script(
                        script_path, page, context
                    )
                    results["cases"].extend(script_results)

                browser.close()

        except Exception as e:
            results["exit_code"] = 2  # Infra error
            results["error"] = str(e)
            traceback.print_exc()

        # Aggregate results
        for case in results["cases"]:
            results["total"] += 1
            if case.status == "passed":
                results["passed"] += 1
            elif case.status == "failed":
                results["failed"] += 1
            elif case.status == "skipped":
                results["skipped"] += 1

            # Update exit code based on case results
            if case.exit_code not in [0, 1]:
                results["exit_code"] = 2

        # Generate runner-output.json with per-case evidence references
        self._generate_runner_output(results["cases"])

        return TestResult(
            exit_code=results["exit_code"],
            total=results["total"],
            passed=results["passed"],
            failed=results["failed"],
            skipped=results["skipped"],
            cases=results["cases"],
            report_path=self.config.output_dir / "results.json",
            error=results.get("error"),
        )

    def _execute_script(self, script_path: Path, page, context) -> List[CaseResult]:
        """
        Execute a single test script.

        Args:
            script_path: Path to test script
            page: Playwright page object
            context: Browser context

        Returns:
            List of CaseResult
        """
        results = []

        try:
            # Load the test module
            spec = importlib.util.spec_from_file_location(
                "test_module",
                script_path
            )
            if spec is None or spec.loader is None:
                return [CaseResult(
                    case_id=script_path.stem,
                    status="invalid_run",
                    error=f"Could not load script: {script_path}",
                    exit_code=2,
                )]

            module = importlib.util.module_from_spec(spec)
            sys.modules["test_module"] = module

            # Inject dependencies into module
            module.page = page
            module.context = context
            module.sync_playwright = lambda: None  # Already launched

            # Execute the module
            spec.loader.exec_module(module)

            # Find and execute test functions
            test_functions = [
                name for name in dir(module)
                if name.startswith("test_") and callable(getattr(module, name))
            ]

            for func_name in test_functions:
                case_result = self._execute_test_function(
                    module, func_name, page
                )
                results.append(case_result)

        except Exception as e:
            results.append(CaseResult(
                case_id=script_path.stem,
                status="invalid_run",
                error=str(e),
                exit_code=2,
            ))

        return results

    def _execute_test_function(
        self,
        module,
        func_name: str,
        page
    ) -> CaseResult:
        """
        Execute a single test function.

        Args:
            module: Test module
            func_name: Name of test function
            page: Playwright page object

        Returns:
            CaseResult
        """
        import time
        start_ms = int(time.time() * 1000)

        case_result = CaseResult(
            case_id=func_name.replace("test_", ""),
            status="failed",
            exit_code=1,
        )

        try:
            # Collect context before test
            context_before = ContextCollector.collect_before_test(page)

            # Execute test function
            test_func = getattr(module, func_name)

            # Check function signature
            import inspect
            sig = inspect.signature(test_func)
            if 'page' in sig.parameters:
                test_func(page)
            else:
                test_func()

            # Test passed
            case_result.status = "passed"
            case_result.exit_code = 0

        except AssertionError as e:
            # Assertion failure - likely system issue
            case_result.status = "failed"
            case_result.error = str(e)
            case_result.exit_code = 1

            # Classify the error
            classification = ErrorClassifier.classify(str(e), context_before)
            case_result.error_type = classification.type
            case_result.is_code_issue = classification.is_false_fail

            # Take screenshot
            case_result.screenshot_path = self._take_screenshot(page, func_name)

        except Exception as e:
            # Other error - classify it
            case_result.status = "failed"
            case_result.error = str(e)
            case_result.exit_code = 2

            # Classify the error - include exception type for better classification
            context_before = ContextCollector.collect_before_test(page)
            error_message = f"{type(e).__name__}: {str(e)}" if str(e) else type(e).__name__
            classification = ErrorClassifier.classify(error_message, context_before)

            case_result.error_type = classification.type
            case_result.is_code_issue = classification.is_false_fail

            # If code issue, mark as invalid_run
            if classification.type == "code_issue":
                case_result.status = "invalid_run"

            # Take screenshot
            case_result.screenshot_path = self._take_screenshot(page, func_name)

        end_ms = int(time.time() * 1000)
        case_result.duration_ms = end_ms - start_ms

        # Save per-case evidence bundle
        case_id = case_result.case_id
        evidence_dir = self._save_evidence_bundle(case_id, case_result)
        case_result.evidence_dir = evidence_dir

        return case_result

    def _take_screenshot(self, page, func_name: str) -> Optional[str]:
        """
        Take a screenshot of the current page.

        Args:
            page: Playwright page object
            func_name: Name of the test function (for filename)

        Returns:
            Path to screenshot or None
        """
        try:
            screenshot_path = self.config.screenshot_dir / f"{func_name}.png"
            page.screenshot(path=str(screenshot_path))
            return str(screenshot_path)
        except Exception:
            return None

    def _generate_runner_output(self, cases: List[CaseResult]) -> None:
        """
        Generate runner-output.json with per-case evidence references.

        Args:
            cases: List of CaseResult objects
        """
        output = {
            "execution_status": "success" if all(c.exit_code == 0 for c in cases) else "failed",
            "total_cases": len(cases),
            "cases": []
        }

        for case in cases:
            case_data = {
                "case_id": case.case_id,
                "status": case.status,
                "exit_code": case.exit_code,
                "duration_ms": case.duration_ms,
            }

            # Add evidence bundle reference
            if case.evidence_dir:
                case_data["evidence_bundle"] = {
                    "path": str(case.evidence_dir),
                    "bundle_file": str(case.evidence_dir / "bundle.yaml"),
                }

            # Add optional fields
            if case.error:
                case_data["error"] = case.error
            if case.screenshot_path:
                case_data["screenshot"] = case.screenshot_path
            if case.log_path:
                case_data["log"] = case.log_path

            output["cases"].append(case_data)

        # Write runner-output.json
        output_path = self.config.output_dir / "runner-output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    def _save_evidence_bundle(
        self,
        case_id: str,
        case_result: CaseResult,
    ) -> Path:
        """
        Save per-case evidence bundle.

        Args:
            case_id: Case identifier
            case_result: CaseResult object with evidence data

        Returns:
            Path to the evidence bundle directory
        """
        # Create per-case evidence directory
        evidence_dir = self.config.evidence_dir / case_id
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Build bundle data
        bundle = {
            "case_id": case_id,
            "status": case_result.status,
            "exit_code": case_result.exit_code,
            "duration_ms": case_result.duration_ms,
            "commands": [f"test_runner run --case {case_id}"],
            "logs": case_result.log_path or "",
            "runner_result_ref": f"runner-output.json#{case_id}",
            "stderr": case_result.error or "",
        }

        # Add screenshots if available
        if case_result.screenshot_path:
            bundle["screenshots"] = [case_result.screenshot_path]

        # Add video if available
        if case_result.video_path:
            bundle["video"] = case_result.video_path

        # Add network trace if available
        if case_result.network_trace_path:
            bundle["network_trace"] = case_result.network_trace_path

        # Save bundle.yaml
        bundle_path = evidence_dir / "bundle.yaml"
        import yaml
        with open(bundle_path, "w", encoding="utf-8") as f:
            yaml.dump(bundle, f, allow_unicode=True)

        return evidence_dir
