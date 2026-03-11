from lee.orchestrator.execution.error_hints import (
    append_executor_hints,
    diagnose_executor_error,
)


def test_diagnose_claude_connection_error():
    hints = diagnose_executor_error(
        "API Error: Unable to connect to API (ConnectionRefused)"
    )

    assert any("Claude 环境连通性问题" in item for item in hints)
    assert any("claude auth status" in item for item in hints)


def test_diagnose_codex_access_denied():
    hints = diagnose_executor_error(
        "Codex CLI invocation failed: [WinError 5] 拒绝访问。"
    )

    assert any("权限问题" in item for item in hints)
    assert any("codex exec --help" in item for item in hints)


def test_append_executor_hints_is_idempotent():
    enriched = append_executor_hints(
        "Claude CLI binary not found: claude. Install with: npm install -g @anthropic-ai/claude-code"
    )
    enriched_twice = append_executor_hints(enriched)

    assert enriched is not None
    assert "环境排查:" in enriched
    assert enriched_twice == enriched
