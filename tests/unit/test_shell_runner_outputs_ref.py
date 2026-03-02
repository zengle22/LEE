"""
Unit tests for shell_runner output reference resolution.

Tests the $outputs.step_id.field reference resolution feature.
"""

import json
import platform
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from lee.orchestrator.execution.runners.shell_runner import (
    SkillRunner,
    _OUTPUTS_REF_PATTERN,
)


class TestOutputsRefPattern:
    """Test the regex pattern for output references."""

    def test_simple_field(self):
        """Test simple field reference."""
        pattern = "$outputs.s1_1_analyze_files.gitignore_recommendations"
        match = _OUTPUTS_REF_PATTERN.match(pattern)
        assert match is not None
        assert match.group(1) == "s1_1_analyze_files.gitignore_recommendations"

    def test_field_with_hyphen(self):
        """Test field name with hyphen."""
        pattern = "$outputs.s1_1_analyze_files.gitignore-recommendations"
        match = _OUTPUTS_REF_PATTERN.match(pattern)
        assert match is not None
        assert match.group(1) == "s1_1_analyze_files.gitignore-recommendations"

    def test_nested_field(self):
        """Test nested field reference."""
        pattern = "$outputs.s1_1_analyze_files.results.items"
        match = _OUTPUTS_REF_PATTERN.match(pattern)
        assert match is not None
        assert match.group(1) == "s1_1_analyze_files.results.items"

    def test_deep_nested_field(self):
        """Test deeply nested field reference."""
        pattern = "$outputs.s1_1_analyze_files.data.nested.deep.value"
        match = _OUTPUTS_REF_PATTERN.match(pattern)
        assert match is not None

    def test_no_field_path(self):
        """Test reference without field path (should not match)."""
        pattern = "$outputs.s1_1_analyze_files"
        match = _OUTPUTS_REF_PATTERN.match(pattern)
        assert match is None

    def test_invalid_format(self):
        """Test invalid reference format."""
        patterns = [
            "$outputs.",  # No step_id
            "$outputs",   # Missing dot
            "outputs.s1.field",  # Missing $
            "${outputs.s1.field}",  # Wrong format
        ]
        for pattern in patterns:
            match = _OUTPUTS_REF_PATTERN.match(pattern)
            assert match is None, f"Pattern {pattern} should not match"


class TestResolveOutputsRef:
    """Test the _resolve_outputs_ref method."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory with test files."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create .workflow directory
        workflow_dir = project_root / ".workflow" / "workspace-cleanup"
        workflow_dir.mkdir(parents=True)

        yield project_root

    def test_resolve_yaml_output(self, temp_project):
        """Test resolving a field from YAML output file."""
        # Create test output file
        output_file = temp_project / ".workflow" / "workspace-cleanup" / "file-analysis.yaml"
        output_data = {
            "analysis_result": {"total": 100},
            "gitignore_recommendations": [
                {"pattern": "*.tmp", "category": "temporary_files"},
                {"pattern": "*.log", "category": "logs"},
            ],
        }
        output_file.write_text(yaml.dump(output_data), encoding="utf-8")

        # Create workflow data
        workflow_data = {
            "step_outputs": {
                "s1_1_analyze_files": {
                    "paths": [".workflow/workspace-cleanup/file-analysis.yaml"]
                }
            }
        }

        # Test resolution
        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1_1_analyze_files.gitignore_recommendations",
            str(temp_project),
            workflow_data,
        )

        assert result is not None
        assert len(result) == 2
        assert result[0]["pattern"] == "*.tmp"

    def test_resolve_json_output(self, temp_project):
        """Test resolving a field from JSON output file."""
        # Create test output file
        output_file = temp_project / ".workflow" / "output.json"
        output_data = {
            "results": {"count": 42},
            "items": ["a", "b", "c"],
        }
        output_file.write_text(json.dumps(output_data), encoding="utf-8")

        workflow_data = {
            "step_outputs": {
                "s2_process": {
                    "paths": [".workflow/output.json"]
                }
            }
        }

        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s2_process.items",
            str(temp_project),
            workflow_data,
        )

        assert result == ["a", "b", "c"]

    def test_resolve_nested_field(self, temp_project):
        """Test resolving a nested field."""
        output_file = temp_project / ".workflow" / "output.yaml"
        output_data = {
            "data": {
                "nested": {
                    "deep": {
                        "value": "found_me"
                    }
                }
            }
        }
        output_file.write_text(yaml.dump(output_data), encoding="utf-8")

        workflow_data = {
            "step_outputs": {
                "s1": {
                    "paths": [".workflow/output.yaml"]
                }
            }
        }

        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1.data.nested.deep.value",
            str(temp_project),
            workflow_data,
        )

        assert result == "found_me"

    def test_resolve_nonexistent_step(self, temp_project):
        """Test resolving from a step that doesn't exist."""
        workflow_data = {
            "step_outputs": {
                "other_step": {
                    "paths": [".workflow/output.yaml"]
                }
            }
        }

        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1_analyze.some_field",
            str(temp_project),
            workflow_data,
        )

        assert result is None

    def test_resolve_nonexistent_file(self, temp_project):
        """Test resolving when output file doesn't exist."""
        workflow_data = {
            "step_outputs": {
                "s1_analyze": {
                    "paths": [".workflow/nonexistent.yaml"]
                }
            }
        }

        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1_analyze.some_field",
            str(temp_project),
            workflow_data,
        )

        assert result is None

    def test_resolve_missing_field(self, temp_project):
        """Test resolving a field that doesn't exist in the output."""
        output_file = temp_project / ".workflow" / "output.yaml"
        output_file.write_text(yaml.dump({"other_field": "value"}), encoding="utf-8")

        workflow_data = {
            "step_outputs": {
                "s1": {
                    "paths": [".workflow/output.yaml"]
                }
            }
        }

        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1.missing_field",
            str(temp_project),
            workflow_data,
        )

        assert result is None

    def test_resolve_no_workflow_data(self, temp_project):
        """Test resolving when no workflow data is provided."""
        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1_analyze.some_field",
            str(temp_project),
            None,
        )

        assert result is None

    def test_resolve_no_step_outputs(self, temp_project):
        """Test resolving when step_outputs is empty."""
        workflow_data = {
            "step_outputs": {}
        }

        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1_analyze.some_field",
            str(temp_project),
            workflow_data,
        )

        assert result is None

    def test_resolve_multiple_output_paths(self, temp_project):
        """Test resolving from multiple output paths (returns first match)."""
        # Create two output files
        output1 = temp_project / ".workflow" / "output1.yaml"
        output1.write_text(yaml.dump({"target": "from_file1"}), encoding="utf-8")

        output2 = temp_project / ".workflow" / "output2.yaml"
        output2.write_text(yaml.dump({"target": "from_file2"}), encoding="utf-8")

        workflow_data = {
            "step_outputs": {
                "s1": {
                    "paths": [".workflow/output1.yaml", ".workflow/output2.yaml"]
                }
            }
        }

        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1.target",
            str(temp_project),
            workflow_data,
        )

        assert result == "from_file1"


class TestResolveParams:
    """Test the _resolve_params method with outputs reference support."""

    def test_resolve_params_with_outputs_ref(self, tmp_path):
        """Test resolving params that include outputs references."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create output file
        workflow_dir = project_root / ".workflow"
        workflow_dir.mkdir()
        output_file = workflow_dir / "output.yaml"
        output_file.write_text(yaml.dump({"items": ["a", "b"]}), encoding="utf-8")

        # Use actual project_root as workspace_path for file resolution
        params = {
            "workspace_path": str(project_root),
            "patterns_to_add": "$outputs.s1.items",
        }
        workflow_params = {}
        workflow_data = {
            "step_outputs": {
                "s1": {
                    "paths": [".workflow/output.yaml"]
                }
            }
        }

        result = SkillRunner._resolve_params(
            params,
            workflow_params,
            str(project_root),
            workflow_data,
        )

        assert result["workspace_path"] == str(project_root)
        assert result["patterns_to_add"] == ["a", "b"]

    def test_resolve_params_uses_workspace_path(self, tmp_path):
        """Test that workspace_path is used as base path for output resolution."""
        # Create two different directories
        project_root = tmp_path / "lee_project"
        project_root.mkdir()

        workspace_dir = tmp_path / "target_workspace"
        workspace_dir.mkdir()

        # Output file is in target_workspace, not lee_project
        output_dir = workspace_dir / ".workflow"
        output_dir.mkdir()
        output_file = output_dir / "output.yaml"
        output_file.write_text(yaml.dump({"items": ["x", "y", "z"]}), encoding="utf-8")

        params = {
            "workspace_path": str(workspace_dir),
            "patterns_to_add": "$outputs.s1.items",
        }
        workflow_params = {}
        workflow_data = {
            "step_outputs": {
                "s1": {
                    "paths": [".workflow/output.yaml"]
                }
            }
        }

        # Even though project_root is different, workspace_path should be used
        result = SkillRunner._resolve_params(
            params,
            workflow_params,
            str(project_root),  # Different from workspace_path
            workflow_data,
        )

        assert result["workspace_path"] == str(workspace_dir)
        assert result["patterns_to_add"] == ["x", "y", "z"]

    def test_resolve_params_without_outputs_ref(self):
        """Test resolving params without outputs references."""
        params = {
            "workspace_path": "/some/path",
            "patterns_to_add": ["*.tmp"],
        }
        workflow_params = {"author": "test"}

        result = SkillRunner._resolve_params(
            params,
            workflow_params,
            None,
            None,
        )

        assert result["workspace_path"] == "/some/path"
        assert result["patterns_to_add"] == ["*.tmp"]


class TestRenderTemplate:
    """Test the _render_template method with Jinja2 and Python format support."""

    def test_render_jinja2_template_with_inputs(self):
        """Test rendering Jinja2 template with nested inputs context (BUG-0056)."""
        template = "test-runner run-e2e --suite {{ inputs.suite }} --env {{ inputs.env }}"
        jinja_context = {
            "suite": "smoke",
            "env": "test",
            "inputs": {
                "suite": "smoke",
                "env": "test",
                "test_set_path": "/path/to/cases.yaml"
            }
        }
        format_values = {"suite": "smoke", "env": "test"}

        result = SkillRunner._render_template(template, jinja_context, format_values)

        assert "--suite smoke" in result
        assert "--env test" in result

    def test_render_jinja2_template_flat_variables(self):
        """Test rendering Jinja2 template with flat variable names."""
        template = "run --suite {{ suite }} --env {{ env }}"
        jinja_context = {
            "suite": "regression",
            "env": "staging"
        }
        format_values = {"suite": "regression", "env": "staging"}

        result = SkillRunner._render_template(template, jinja_context, format_values)

        assert "--suite regression" in result
        assert "--env staging" in result

    def test_render_python_format_fallback(self):
        """Test fallback to Python format when no Jinja2 syntax detected."""
        template = "run --suite {suite} --env {env}"
        jinja_context = {}
        format_values = {"suite": "unit", "env": "dev"}

        result = SkillRunner._render_template(template, jinja_context, format_values)

        assert "--suite unit" in result
        assert "--env dev" in result

    def test_render_jinja2_with_missing_variable(self):
        """Test Jinja2 rendering with missing variable (should keep placeholder)."""
        template = "run --suite {{ inputs.missing }} --env {{ inputs.env }}"
        jinja_context = {
            "inputs": {"env": "test"}  # missing 'suite'
        }
        format_values = {"env": "test"}

        result = SkillRunner._render_template(template, jinja_context, format_values)

        # Jinja2 renders empty string for missing variables
        assert "--suite" in result
        assert "--env test" in result


class TestResolvePythonCommand:
    """Test the _resolve_python_command method for cross-platform compatibility (BUG-0058)."""

    def test_resolve_python_command_on_windows(self, monkeypatch):
        """Test Windows uses 'python'."""
        monkeypatch.setattr(platform, "system", lambda: "Windows")

        result = SkillRunner._resolve_python_command("python")

        assert result == "python"

    def test_resolve_python_command_on_linux_with_python3(self, monkeypatch):
        """Test Linux with python3 available uses 'python3'."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr("shutil.which", lambda cmd: cmd == "python3")

        result = SkillRunner._resolve_python_command("python")

        assert result == "python3"

    def test_resolve_python_command_on_linux_without_python3(self, monkeypatch):
        """Test Linux without python3 falls back to 'python'."""
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr("shutil.which", lambda cmd: None)

        result = SkillRunner._resolve_python_command("python")

        assert result == "python"

    def test_resolve_python_command_non_python_command(self):
        """Test non-python commands are passed through unchanged."""
        result = SkillRunner._resolve_python_command("node")

        assert result == "node"

    def test_resolve_python_command_on_macos(self, monkeypatch):
        """Test macOS uses 'python3' when available."""
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr("shutil.which", lambda cmd: cmd == "python3")

        result = SkillRunner._resolve_python_command("python")

        assert result == "python3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
