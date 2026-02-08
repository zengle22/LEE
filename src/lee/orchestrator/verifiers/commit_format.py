"""Commit format verifier."""

from __future__ import annotations

import re
import subprocess
from typing import Dict

from lee.orchestrator.verifiers.base import BaseVerifier, VerifyResult, VerifyStatus


class CommitFormatVerifier(BaseVerifier):
    @property
    def verifier_id(self) -> str:
        return "commit_format"

    def verify(self, context: Dict) -> VerifyResult:
        config = context.get("config", {}) or {}
        pattern = config.get("pattern")
        fail_on_error = config.get("fail_on_error", True)
        project_root = context.get("project_root", ".")

        if not pattern:
            return VerifyResult(
                status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message="commit format pattern not provided",
            )

        try:
            result = subprocess.run(
                "git log -1 --pretty=%s",
                shell=True,
                cwd=project_root,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return VerifyResult(
                    status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                    verifier_id=self.verifier_id,
                    message="git log failed",
                    details={"stderr": result.stderr},
                )

            subject = result.stdout.strip()
            if not re.match(pattern, subject):
                return VerifyResult(
                    status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                    verifier_id=self.verifier_id,
                    message=f"commit message does not match pattern: {subject}",
                    details={"pattern": pattern, "subject": subject},
                )

            return VerifyResult(
                status=VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message="commit format ok",
                details={"subject": subject},
            )
        except Exception as e:
            return VerifyResult(
                status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message=f"commit format verification error: {e}",
            )
