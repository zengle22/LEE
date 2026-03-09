"""
Unit tests for DockerRunner
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from subprocess import CompletedProcess

from lee.qa.runner.docker import DockerRunner
from lee.qa.runner.base import TestConfig


class TestDockerRunner:
    """Tests for DockerRunner"""

    @pytest.fixture
    def config(self, tmp_path):
        """Test configuration"""
        script_path = tmp_path / "test_script.py"
        script_path.write_text("def test(): pass")

        return TestConfig(
            scripts=[script_path],
            base_url="http://localhost:3000",
            output_dir=tmp_path / "output",
            environment="test",
        )

    @pytest.fixture
    def runner(self, config):
        """DockerRunner instance"""
        return DockerRunner(config)

    def test_runner_name(self, runner):
        """Test runner name"""
        assert runner.name == "docker"

    def test_docker_image_constant(self, runner):
        """Test Docker image constant"""
        assert runner.DOCKER_IMAGE == "lee-e2e-runner:latest"

    @patch('lee.qa.runner.docker.subprocess.run')
    def test_check_environment_with_docker(self, mock_run):
        """Test environment check with Docker available"""
        mock_run.side_effect = [
            Mock(returncode=0),  # docker --version
            Mock(returncode=0),  # docker info
            Mock(returncode=0),  # docker image inspect
        ]

        runner = DockerRunner(TestConfig(
            scripts=[Path("test.py")],
            base_url="http://localhost:3000",
        ))

        checks = runner.check_environment()
        assert checks.get("docker") is True

    @patch('lee.qa.runner.docker.subprocess.run')
    def test_check_environment_without_docker(self, mock_run):
        """Test environment check without Docker"""
        mock_run.side_effect = [
            Mock(returncode=1),  # docker --version failed
        ]

        runner = DockerRunner(TestConfig(
            scripts=[Path("test.py")],
            base_url="http://localhost:3000",
        ))

        checks = runner.check_environment()
        assert checks.get("docker") is False

    @patch('lee.qa.runner.docker.subprocess.run')
    def test_check_environment_without_image(self, mock_run):
        """Test environment check without Docker image"""
        mock_run.side_effect = [
            Mock(returncode=0),  # docker --version
            Mock(returncode=0),  # docker info
            Mock(returncode=1),  # docker image inspect failed
        ]

        runner = DockerRunner(TestConfig(
            scripts=[Path("test.py")],
            base_url="http://localhost:3000",
        ))

        checks = runner.check_environment()
        assert checks.get("image") is False

    @patch('lee.qa.runner.docker.subprocess.run')
    def test_execute_success(self, mock_run, tmp_path):
        """Test successful execution"""
        # Create report file
        report_dir = tmp_path / "output"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "results.json"
        report_file.write_text('{"summary": {"total": 5, "passed": 5, "failed": 0}}')

        mock_run.return_value = Mock(returncode=0)

        config = TestConfig(
            scripts=[tmp_path / "test.py"],
            base_url="http://localhost:3000",
            output_dir=report_dir,
        )

        runner = DockerRunner(config)
        result = runner.execute()

        assert result is not None

    @patch('lee.qa.runner.docker.subprocess.run')
    def test_execute_timeout(self, mock_run):
        """Test execution timeout"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 600)

        runner = DockerRunner(TestConfig(
            scripts=[Path("test.py")],
            base_url="http://localhost:3000",
        ))

        result = runner.execute()

        assert result.exit_code == 2
        assert "timed out" in result.error.lower()

    def test_build_docker_command(self, runner):
        """Test Docker command building"""
        cmd = runner._build_docker_command()

        assert "docker" in cmd
        assert "run" in cmd
        assert "--rm" in cmd
        assert "--name" in cmd
        assert any(str(part).startswith("lee-e2e-") for part in cmd)
        assert "-e" in cmd
        assert any(str(part).startswith("BASE_URL=") for part in cmd)

    def test_parse_result_with_report(self, runner, tmp_path):
        """Test parsing result with report file"""
        # Create report
        report_dir = runner.config.output_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "results.json"
        report_file.write_text('{"summary": {"total": 3, "passed": 2, "failed": 1}}')

        completed = Mock(returncode=1)
        result = runner._parse_result(completed, 5000)

        assert result.total == 3
        assert result.passed == 2
        assert result.failed == 1

    def test_parse_result_without_report(self, runner):
        """Test parsing result without report file"""
        completed = Mock(returncode=1, stdout="")

        result = runner._parse_result(completed, 5000)

        # Should return default result
        assert result.total == 0

    def test_parse_from_stdout(self, runner):
        """Test parsing from pytest stdout"""
        stdout = """
5 passed, 1 failed in 10.5s
"""

        result = runner._parse_from_stdout(stdout, 1, 10500)

        assert result.total == 6
        assert result.passed == 5
        assert result.failed == 1

    def test_parse_from_stdout_no_match(self, runner):
        """Test parsing from stdout with no match"""
        stdout = "Test output without summary"

        result = runner._parse_from_stdout(stdout, 1, 1000)

        assert result.total == 0

    @patch('lee.qa.runner.docker.subprocess.run')
    def test_build_image(self, mock_run):
        """Test building Docker image"""
        mock_run.return_value = Mock(returncode=0)

        runner = DockerRunner(TestConfig(
            scripts=[Path("test.py")],
            base_url="http://localhost:3000",
        ))

        result = runner.build_image()

        mock_run.assert_called_once()
        assert result is True
