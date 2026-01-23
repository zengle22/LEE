"""
Shell Skill Executor - 执行 Shell 命令和脚本

支持执行本地 Shell 命令，用于：
- 运行测试（pytest, npm test）
- 构建项目（npm build, make）
- 部署操作（kubectl, docker）
- 其他确定性操作
"""

import asyncio
import os
import shlex
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..base import AbstractExecutor
from ..protocol import StepExecutionRequest, StepExecutionResult, ArtifactReference


class ShellSkillExecutor(AbstractExecutor):
    """
    Shell 执行器 - 执行 Shell 命令

    配置示例（skill.yaml）：
    ```yaml
    kind: skill
    id: ci.run_tests
    engine:
      type: shell
      command: |
        cd {{ project_dir }} && pytest --maxfail=1 -q \
          --junitxml=reports/unit_test_report.xml
      timeout: 300
      shell: /bin/bash  # 可选，默认 /bin/sh
      working_dir: {{ project_dir }}  # 可选
    ```
    """

    async def execute(self, request: StepExecutionRequest) -> StepExecutionResult:
        """执行步骤"""
        started_at = datetime.now().isoformat()

        try:
            # 1. 验证请求
            valid, error = self.validate_request(request)
            if not valid:
                return StepExecutionResult(
                    status="failed",
                    error=f"Invalid request: {error}",
                    started_at=started_at,
                    engine_type="shell"
                )

            # 2. 获取命令
            command = self._get_command(request)
            if not command:
                return StepExecutionResult(
                    status="failed",
                    error="No command specified in engine configuration",
                    started_at=started_at,
                    engine_type="shell"
                )

            # 3. 获取工作目录
            working_dir = self._get_working_dir(request)

            # 4. 获取超时设置
            timeout = self._get_timeout(request)

            # 5. 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
                env=self._get_env(request)
            )

            # 等待命令完成（带超时）
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                completed_at = datetime.now().isoformat()
                return StepExecutionResult(
                    status="timeout",
                    error=f"Command timed out after {timeout} seconds",
                    messages=[
                        {"role": "command", "content": command},
                        {"role": "error", "content": "Timeout"}
                    ],
                    started_at=started_at,
                    completed_at=completed_at,
                    engine_type="shell"
                )

            # 解码输出
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # 6. 检查返回码
            return_code = process.returncode

            # 7. 保存输出到工作目录
            workspace = request.get_working_dir()
            stdout_file = workspace / "stdout.txt"
            stderr_file = workspace / "stderr.txt"

            stdout_file.write_text(stdout_text, encoding="utf-8")
            stderr_file.write_text(stderr_text, encoding="utf-8")

            # 8. 构建结果
            completed_at = datetime.now().isoformat()
            duration = (
                datetime.fromisoformat(completed_at) -
                datetime.fromisoformat(started_at)
            ).total_seconds()

            outputs = [
                ArtifactReference(
                    id="stdout",
                    path=str(stdout_file.relative_to(request.project_dir)),
                    content_type="text/plain",
                    summary="Command stdout"
                ),
                ArtifactReference(
                    id="stderr",
                    path=str(stderr_file.relative_to(request.project_dir)),
                    content_type="text/plain",
                    summary="Command stderr"
                )
            ]

            # 查找额外的输出文件
            expected_outputs = request.context.get("expected_outputs", [])
            if expected_outputs:
                for out_path in expected_outputs:
                    full_path = Path(request.project_dir) / out_path
                    if full_path.exists():
                        outputs.append(
                            ArtifactReference(
                                id=out_path,
                                path=out_path,
                                content_type="application/octet-stream",
                                summary=f"Output file: {out_path}"
                            )
                        )

            messages = [
                {"role": "command", "content": command},
                {"role": "stdout", "content": stdout_text},
                {"role": "stderr", "content": stderr_text},
                {"role": "return_code", "content": str(return_code)}
            ]

            if return_code == 0:
                status = "completed"
            else:
                status = "failed"

            return StepExecutionResult(
                status=status,
                outputs=outputs,
                messages=messages,
                error=stderr_text if return_code != 0 else None,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                engine_type="shell"
            )

        except Exception as e:
            completed_at = datetime.now().isoformat()
            return StepExecutionResult(
                status="failed",
                error=str(e),
                error_details={
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                },
                started_at=started_at,
                completed_at=completed_at,
                engine_type="shell"
            )

    def _get_command(self, request: StepExecutionRequest) -> Optional[str]:
        """获取要执行的命令"""
        # 从 engine 配置获取命令模板
        command_template = self.engine_config.get("command")

        if not command_template:
            return None

        # 简单的变量替换
        replacements = {
            "{{ project_dir }}": str(request.project_dir),
            "{{ step_id }}": request.step_id,
            "{{ run_id }}": request.run_id,
        }

        command = command_template
        for key, value in replacements.items():
            command = command.replace(key, value)

        # 环境变量替换
        if "{{" in command and "}}" in command:
            # 支持 {{ENV_VAR}} 格式
            import re
            pattern = r"\{\{(\w+)\}\}"
            matches = re.findall(pattern, command)
            for env_var in matches:
                env_value = os.getenv(env_var, "")
                command = command.replace(f"{{{{{env_var}}}}}", env_value)

        return command

    def _get_working_dir(self, request: StepExecutionRequest) -> Path:
        """获取工作目录"""
        # 从 engine 配置获取
        working_dir_config = self.engine_config.get("working_dir")
        if working_dir_config:
            # 简单的变量替换
            working_dir_config = working_dir_config.replace(
                "{{ project_dir }}",
                str(request.project_dir)
            )
            return Path(working_dir_config)

        # 否则使用项目目录
        return Path(request.project_dir)

    def _get_timeout(self, request: StepExecutionRequest) -> int:
        """获取超时时间（秒）"""
        # 优先使用 engine 配置的超时
        if "timeout" in self.engine_config:
            return int(self.engine_config["timeout"])

        # 否则使用请求的超时
        if request.timeout_seconds:
            return request.timeout_seconds

        # 默认 300 秒（5 分钟）
        return 300

    def _get_env(self, request: StepExecutionRequest) -> Dict[str, str]:
        """获取环境变量"""
        env = os.environ.copy()

        # 添加上下文环境变量
        env["PROJECT_DIR"] = str(request.project_dir)
        env["STEP_ID"] = request.step_id
        env["RUN_ID"] = request.run_id

        # 从 engine 配置添加额外的环境变量
        extra_env = self.engine_config.get("env", {})
        if extra_env:
            env.update(extra_env)

        return env


def create_executor(agent_spec: Dict, project_dir: str) -> ShellSkillExecutor:
    """工厂函数：创建 ShellSkillExecutor 实例"""
    return ShellSkillExecutor(project_dir, agent_spec)
