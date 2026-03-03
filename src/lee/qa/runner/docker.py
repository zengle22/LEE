"""
QA Module - Docker Runner

Docker-based test runner for CI/CD environments.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Optional

from lee.qa.runner.base import BaseRunner, TestConfig, TestResult


class DockerRunner(BaseRunner):
    """
    Docker-based test runner.

    Executes tests in isolated Docker containers.
    Useful for CI/CD pipelines.
    """

    DOCKER_IMAGE = "lee-e2e-runner:latest"

    @property
    def name(self) -> str:
        return "docker"

    def check_environment(self) -> Dict[str, bool]:
        """Check if Docker is available"""
        checks = {}

        # Check docker command
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5
            )
            checks["docker"] = result.returncode == 0
        except Exception:
            checks["docker"] = False

        # Check docker daemon
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            checks["docker_daemon"] = result.returncode == 0
        except Exception:
            checks["docker_daemon"] = False

        # Check image
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.DOCKER_IMAGE],
                capture_output=True,
                timeout=5
            )
            checks["image"] = result.returncode == 0
        except Exception:
            checks["image"] = False

        return checks

    def execute(self) -> TestResult:
        """
        Execute tests in Docker container.

        Returns:
            TestResult with execution results
        """
        import time
        start_time = time.time()

        # Build docker command
        cmd = self._build_docker_command()

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes max
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse results
            return self._parse_result(result, duration_ms)

        except subprocess.TimeoutExpired:
            return TestResult(
                exit_code=2,
                total=0,
                passed=0,
                failed=0,
                error="Docker execution timed out",
            )

    def _build_docker_command(self) -> list:
        """Build Docker run command"""
        scripts_dir = self.config.scripts[0].parent if self.config.scripts else Path(".")

        cmd = [
            "docker", "run", "--rm",
            "--name", f"lee-e2e-{int(__import__('time').time())}",
            "--network", "host",
            "-e", f"BASE_URL={self.config.base_url}",
            "-e", f"TEST_ENV={self.config.environment}",
            "-e", f"HEADLESS={str(self.config.headless).lower()}",
            "-v", f"{scripts_dir}:/app/tests:ro",
            "-v", f"{self.config.output_dir}:/app/output",
            "-v", f"{self.config.screenshot_dir}:/app/screenshots",
            self.DOCKER_IMAGE,
            "pytest", "tests/", "-v",
            "--json-report",
            "--json-report-file=/app/output/results.json",
        ]

        return cmd

    def _parse_result(
        self,
        docker_result: subprocess.CompletedProcess,
        duration_ms: int
    ) -> TestResult:
        """Parse Docker execution result"""
        report_path = self.config.output_dir / "results.json"

        # Try to read JSON report
        if report_path.exists():
            try:
                with open(report_path) as f:
                    data = json.load(f)

                return TestResult(
                    exit_code=docker_result.returncode,
                    total=data.get("summary", {}).get("total", 0),
                    passed=data.get("summary", {}).get("passed", 0),
                    failed=data.get("summary", {}).get("failed", 0),
                    skipped=data.get("summary", {}).get("skipped", 0),
                    duration_ms=duration_ms,
                    report_path=report_path,
                )
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse from stdout
        return self._parse_from_stdout(
            docker_result.stdout,
            docker_result.returncode,
            duration_ms
        )

    def _parse_from_stdout(
        self,
        stdout: str,
        exit_code: int,
        duration_ms: int
    ) -> TestResult:
        """Parse test results from pytest stdout"""
        import re

        # Parse pytest summary line
        # Example: "5 passed, 1 failed in 10.5s"
        summary_match = re.search(
            r'(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?',
            stdout
        )

        if summary_match:
            passed = int(summary_match.group(1))
            failed = int(summary_match.group(2)) if summary_match.group(2) else 0
            skipped = int(summary_match.group(3)) if summary_match.group(3) else 0

            return TestResult(
                exit_code=exit_code,
                total=passed + failed + skipped,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration_ms=duration_ms,
            )

        # Default result
        return TestResult(
            exit_code=exit_code,
            total=0,
            passed=0,
            failed=0,
            duration_ms=duration_ms,
            error="Could not parse test results",
        )

    def build_image(self, dockerfile: Optional[Path] = None) -> bool:
        """
        Build Docker image for test execution.

        Args:
            dockerfile: Path to Dockerfile (default: builtin)

        Returns:
            True if successful
        """
        if dockerfile is None:
            dockerfile = self._get_default_dockerfile_path()

        cmd = [
            "docker", "build",
            "-t", self.DOCKER_IMAGE,
            "-f", str(dockerfile),
            "."
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except Exception:
            return False

    def _get_default_dockerfile_path(self) -> Path:
        """Get path to default Dockerfile"""
        # Return path to a Dockerfile in the project
        return Path.cwd() / "Dockerfile.e2e"
