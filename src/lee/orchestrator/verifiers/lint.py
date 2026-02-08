"""Lint verifier."""

from __future__ import annotations

import subprocess
from typing import Dict

from lee.orchestrator.verifiers.base import BaseVerifier, VerifyResult, VerifyStatus


class LintVerifier(BaseVerifier):
    @property
    def verifier_id(self) -> str:
        return "lint"

    def verify(self, context: Dict) -> VerifyResult:
        config = context.get("config", {}) or {}
        command = config.get("command")
        fail_on_error = config.get("fail_on_error", True)
        project_root = context.get("project_root", ".")

        if not command:
            return VerifyResult(
                status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message="lint command not provided",
            )

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=project_root,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return VerifyResult(
                    status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                    verifier_id=self.verifier_id,
                    message="lint failed",
                    details={"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode},
                )

            return VerifyResult(
                status=VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message="lint passed",
                details={"stdout": result.stdout},
            )
        except Exception as e:
            return VerifyResult(
                status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message=f"lint execution error: {e}",
            )
