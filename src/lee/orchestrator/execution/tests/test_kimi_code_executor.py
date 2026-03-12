"""
Kimi code executor unit tests.
"""

from lee.orchestrator.execution.kimi_code_executor import KimiCodeExecutor


class TestKimiCodeExecutor:
    def setup_method(self):
        self.executor = KimiCodeExecutor()

    def test_initialization(self):
        assert self.executor._kimi_binary == "kimi-cli"
        assert self.executor._model == ""

    def test_build_kimi_command_without_model(self):
        assert self.executor._build_kimi_command() == [
            "kimi-cli",
            "--print",
            "--output-format",
            "text",
            "--final-message-only",
        ]

    def test_build_kimi_command_with_model(self):
        assert self.executor._build_kimi_command(model="kimi-k2") == [
            "kimi-cli",
            "--print",
            "--output-format",
            "text",
            "--final-message-only",
            "--model",
            "kimi-k2",
        ]

    def test_prepare_evidence_dir_defaults_to_kimi_code(self, tmp_path):
        evidence_dir = self.executor._prepare_evidence_dir("", str(tmp_path))

        assert evidence_dir.exists()
        assert ".workflow" in str(evidence_dir)
        assert "kimi-code" in str(evidence_dir)
