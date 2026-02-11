"""check_env - 环境探测工具

由 Orchestrator 直接执行的环境检查工具。
AI 无法干预，只能读取结果。

这是 runtime_errors 的唯一合法来源之一（source: orchestrator）。
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class CheckResult:
    """单项检查结果"""
    check_type: str
    target: str
    passed: bool
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class EnvCheckResult:
    """环境检查总结果"""
    all_passed: bool
    checks: List[CheckResult]
    failures: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "checks": [asdict(c) for c in self.checks],
            "failures": self.failures,
            "timestamp": self.timestamp,
        }


class EnvChecker:
    """
    环境检查器

    支持的检查类型：
    - command_exists: 检查命令是否存在（which）
    - service_reachable: 检查服务是否可达（socket connect）
    - directory_writable: 检查目录是否可写（touch）
    """

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or ".").resolve()

    def check(self, checks: List[Dict[str, Any]]) -> EnvCheckResult:
        """执行所有检查"""
        results: List[CheckResult] = []
        failures: List[str] = []

        for check_config in checks:
            check_type = check_config.get("type")

            if check_type == "command_exists":
                commands = check_config.get("commands", [])
                for cmd in commands:
                    result = self._check_command_exists(cmd)
                    results.append(result)
                    if not result.passed:
                        failures.append(f"command_missing:{cmd}")

            elif check_type == "service_reachable":
                endpoints = check_config.get("endpoints", [])
                for ep in endpoints:
                    url = ep.get("url", "")
                    port = ep.get("port", 443)
                    result = self._check_service_reachable(url, port)
                    results.append(result)
                    if not result.passed:
                        failures.append(f"network:{url}:{port}")

            elif check_type == "directory_writable":
                paths = check_config.get("paths", [])
                for path in paths:
                    result = self._check_directory_writable(path)
                    results.append(result)
                    if not result.passed:
                        failures.append(f"directory_not_writable:{path}")

        return EnvCheckResult(
            all_passed=len(failures) == 0,
            checks=results,
            failures=failures,
            timestamp=datetime.now().isoformat(),
        )

    def _check_command_exists(self, command: str) -> CheckResult:
        """检查命令是否存在"""
        path = shutil.which(command)
        if path:
            return CheckResult(
                check_type="command_exists",
                target=command,
                passed=True,
                details={"path": path},
            )
        return CheckResult(
            check_type="command_exists",
            target=command,
            passed=False,
            error=f"Command not found: {command}",
        )

    def _check_service_reachable(self, host: str, port: int, timeout: float = 5.0) -> CheckResult:
        """检查服务是否可达"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return CheckResult(
                    check_type="service_reachable",
                    target=f"{host}:{port}",
                    passed=True,
                )
            return CheckResult(
                check_type="service_reachable",
                target=f"{host}:{port}",
                passed=False,
                error=f"Connection failed: error code {result}",
            )
        except socket.gaierror as e:
            return CheckResult(
                check_type="service_reachable",
                target=f"{host}:{port}",
                passed=False,
                error=f"DNS resolution failed: {e}",
            )
        except socket.timeout:
            return CheckResult(
                check_type="service_reachable",
                target=f"{host}:{port}",
                passed=False,
                error=f"Connection timeout after {timeout}s",
            )
        except Exception as e:
            return CheckResult(
                check_type="service_reachable",
                target=f"{host}:{port}",
                passed=False,
                error=str(e),
            )

    def _check_directory_writable(self, path: str) -> CheckResult:
        """检查目录是否可写"""
        target = self.project_root / path if not Path(path).is_absolute() else Path(path)

        try:
            # 确保目录存在
            target.mkdir(parents=True, exist_ok=True)

            # 尝试创建临时文件
            test_file = target / ".write_test"
            test_file.write_text("test")
            test_file.unlink()

            return CheckResult(
                check_type="directory_writable",
                target=str(target),
                passed=True,
            )
        except Exception as e:
            return CheckResult(
                check_type="directory_writable",
                target=str(target),
                passed=False,
                error=str(e),
            )


def run_check_env(checks: List[Dict[str, Any]], output_path: Optional[str] = None) -> EnvCheckResult:
    """
    运行环境检查（供 Orchestrator 调用）

    Args:
        checks: 检查配置列表
        output_path: 输出 JSON 文件路径（可选）

    Returns:
        EnvCheckResult
    """
    checker = EnvChecker()
    result = checker.check(checks)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    return result


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Environment check tool")
    parser.add_argument("--config", "-c", help="Check config JSON file")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            config = json.load(f)
        checks = config.get("checks", [])
    else:
        # 默认检查
        checks = [
            {"type": "command_exists", "commands": ["node", "npx"]},
        ]

    result = run_check_env(checks, args.output)
    print(json.dumps(result.to_dict(), indent=2))
