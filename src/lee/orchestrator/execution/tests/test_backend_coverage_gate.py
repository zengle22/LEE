from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import LLMRunner


def test_backend_coverage_gate_passes_when_threshold_met():
    step = SimpleNamespace(config={"coverage_threshold": 80, "coverage_retry_target": "write_ut"})
    result = LLMRunner._evaluate_backend_coverage_gate(
        step,
        {"coverage_actual": "82%"},
    )

    assert result["passed"] is True
    assert result["actual"] == 82.0
    assert result["threshold"] == 80.0


def test_backend_coverage_gate_requests_retry_when_below_threshold():
    step = SimpleNamespace(config={"coverage_threshold": 80, "coverage_retry_target": "write_ut"})
    result = LLMRunner._evaluate_backend_coverage_gate(
        step,
        {"coverage_actual": 67},
    )

    assert result["passed"] is False
    assert result["retry_target"] == "write_ut"
    assert "67.0%" in result["message"]
