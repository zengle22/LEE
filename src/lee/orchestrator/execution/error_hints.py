from __future__ import annotations

from typing import List


def diagnose_executor_error(error: str | None) -> List[str]:
    if not error:
        return []

    raw = str(error)
    text = raw.lower()
    hints: List[str] = []

    if "claude cli binary not found" in text:
        hints.extend(
            [
                "确认 Claude Code CLI 已安装，并且 `claude --version` 可在当前终端直接执行。",
                "如果二进制不在 PATH 中，补充 PATH 或设置 `CLAUDE_CODE_BIN` 指向正确可执行文件。",
            ]
        )
    elif (
        "unable to connect to api" in text
        or "connectionrefused" in text
        or "connection error" in text
    ) and ("api error" in text or "claude" in text):
        hints.extend(
            [
                "这是 Claude 环境连通性问题，不是 workflow 输入问题。",
                "先手动检查 `claude --version` 与 `claude auth status` 是否正常。",
                "确认 `ANTHROPIC_AUTH_TOKEN` 或 Claude 本地登录态有效，并检查 `ANTHROPIC_BASE_URL` 是否可访问。",
                "如果是公司代理或网关环境，先验证当前机器能连通 Claude API，再重新执行 workflow。",
            ]
        )
    elif (
        "unauthorized" in text
        or "authentication" in text
        or "auth token" in text
    ) and "claude" in text:
        hints.extend(
            [
                "这是 Claude 认证问题。",
                "检查 `ANTHROPIC_AUTH_TOKEN`、本地登录态或组织网关配置是否失效。",
            ]
        )

    if "codex cli binary not found" in text:
        hints.extend(
            [
                "确认 Codex CLI 已安装，并且 `codex --version` 可在当前终端直接执行。",
                "如果二进制不在 PATH 中，补充 PATH 或使用显式可执行路径。",
            ]
        )
    elif "codex cli invocation failed" in text and (
        "winerror 5" in text or "拒绝访问" in raw
    ):
        hints.extend(
            [
                "这是 Codex CLI 启动权限问题，不是 workflow 输入问题。",
                "先手动执行 `codex exec --help`，确认当前用户对 Codex 可执行文件和工作目录有访问权限。",
                "检查 Windows Defender、企业安全策略或 AppLocker 是否拦截了 `codex exec`。",
                "如果使用 `--sandbox workspace-write`，确认当前工作目录没有被系统或安全软件拒绝访问。",
            ]
        )

    if "kimi cli binary not found" in text:
        hints.extend(
            [
                "确认 Kimi CLI 已安装，并且 `kimi-cli --help` 可在当前终端直接执行。",
                "如果二进制不在 PATH 中，设置 `KIMI_CLI_BINARY` 指向正确的可执行文件。",
            ]
        )
    elif "kimi cli invocation failed" in text and (
        "winerror 5" in text or "拒绝访问" in raw
    ):
        hints.extend(
            [
                "这是 Kimi CLI 启动权限问题，不是 workflow 输入问题。",
                "先手动执行 `kimi-cli --help`，确认当前用户对 Kimi 可执行文件和工作目录有访问权限。",
                "检查 Windows Defender、企业安全策略或 AppLocker 是否拦截了 `kimi-cli`。",
            ]
        )

    if "environment diagnosis:" in text or "环境排查:" in raw:
        return []
    return hints


def append_executor_hints(error: str | None) -> str | None:
    if not error:
        return error
    hints = diagnose_executor_error(error)
    if not hints:
        return error
    bullet_block = "\n".join(f"- {item}" for item in hints)
    return f"{error}\n环境排查:\n{bullet_block}"
