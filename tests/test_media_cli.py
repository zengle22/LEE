"""
Unit tests for diagram_gen, diagram_insert, and md_to_wechat CLIs.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lee.cli.commands.diagram_gen import diagram_gen, generate_mermaid, _sanitize_id, _escape_label
from lee.cli.commands.diagram_insert import diagram_insert, insert_diagrams, _format_placeholder
from lee.cli.commands.md_to_wechat import md_to_wechat, _verify_html


# ============================================================
# diagram_gen tests
# ============================================================

class TestDiagramGenCore:
    """Test diagram generation core logic."""

    def test_sanitize_id(self):
        assert _sanitize_id("hello-world") == "hello_world"
        assert _sanitize_id("foo bar") == "foo_bar"
        assert _sanitize_id("valid_id") == "valid_id"

    def test_escape_label(self):
        assert _escape_label('say "hello"') == "say #quot;hello#quot;"
        assert _escape_label("no quotes") == "no quotes"

    def test_generate_flowchart(self):
        diagram = {
            "type": "governance_loop",
            "structure_dsl": {
                "direction": "TD",
                "nodes": [
                    {"id": "A", "label": "Start", "type": "actor"},
                    {"id": "B", "label": "Process", "type": "process"},
                ],
                "edges": [
                    {"from": "A", "to": "B"},
                ],
            },
        }
        result = generate_mermaid(diagram)
        assert result.startswith("flowchart TD")
        assert 'A["Start"]' in result
        assert 'B["Process"]' in result
        assert "A --> B" in result

    def test_generate_with_edge_labels(self):
        diagram = {
            "type": "workflow",
            "structure_dsl": {
                "direction": "LR",
                "nodes": [
                    {"id": "X", "label": "X", "type": "default"},
                    {"id": "Y", "label": "Y", "type": "default"},
                ],
                "edges": [
                    {"from": "X", "to": "Y", "label": "next"},
                ],
            },
        }
        result = generate_mermaid(diagram)
        assert '-->|"next"|' in result

    def test_generate_decision_node(self):
        diagram = {
            "type": "decision_tree",
            "structure_dsl": {
                "direction": "TD",
                "nodes": [
                    {"id": "D", "label": "Is OK?", "type": "decision"},
                ],
                "edges": [],
            },
        }
        result = generate_mermaid(diagram)
        assert 'D{"Is OK?"}' in result

    def test_generate_state_diagram(self):
        diagram = {
            "type": "state_machine",
            "structure_dsl": {
                "direction": "LR",
                "nodes": [{"id": "S1", "label": "Idle"}],
                "edges": [],
            },
        }
        result = generate_mermaid(diagram)
        assert result.startswith("stateDiagram-v2")


class TestDiagramGenCLI:
    """Test diagram-gen CLI."""

    def test_render_to_stdout(self, tmp_path):
        input_data = {
            "diagram": {
                "id": "test_001",
                "type": "flowchart",
                "structure_dsl": {
                    "direction": "TD",
                    "nodes": [{"id": "A", "label": "Start"}],
                    "edges": [],
                },
            }
        }
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))

        runner = CliRunner()
        result = runner.invoke(diagram_gen, ["render", "-i", str(input_file)])
        assert result.exit_code == 0
        assert "flowchart TD" in result.output

    def test_render_to_file(self, tmp_path):
        input_data = {
            "type": "workflow",
            "structure_dsl": {
                "direction": "LR",
                "nodes": [{"id": "N1", "label": "Node1"}],
                "edges": [],
            },
        }
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))
        output_file = tmp_path / "out.mmd"

        runner = CliRunner()
        result = runner.invoke(diagram_gen, [
            "render", "-i", str(input_file), "-o", str(output_file)
        ])
        assert result.exit_code == 0
        assert output_file.exists()
        assert json.loads(result.output)["ok"] is True

    def test_render_missing_file(self):
        runner = CliRunner()
        result = runner.invoke(diagram_gen, ["render", "-i", "/nonexistent.json"])
        assert result.exit_code == 3

    def test_render_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        runner = CliRunner()
        result = runner.invoke(diagram_gen, ["render", "-i", str(bad_file)])
        assert result.exit_code == 3


# ============================================================
# diagram_insert tests
# ============================================================

class TestDiagramInsertCore:
    """Test diagram insertion core logic."""

    def test_format_placeholder_standard(self):
        asset = {
            "id": "dia_001",
            "caption": "架构图",
            "files": {
                "png": {"path": "images/dia_001.png"},
                "mmd": {"path": "images/dia_001.mmd"},
            },
        }
        result = _format_placeholder(asset, "standard")
        assert "DIAGRAM:dia_001" in result
        assert "架构图" in result
        assert "images/dia_001.png" in result

    def test_format_placeholder_minimal(self):
        asset = {
            "id": "dia_002",
            "caption": "流程图",
            "files": {"png": {"path": "img/flow.png"}},
        }
        result = _format_placeholder(asset, "minimal")
        assert "流程图" in result
        assert "img/flow.png" in result

    def test_insert_after_paragraph(self):
        article = "Para 1\n\nPara 2\n\nPara 3"
        assets = [
            {
                "id": "d1",
                "caption": "Test",
                "files": {"png": {"path": "test.png"}, "mmd": {"path": "test.mmd"}},
                "insertion_guide": {"suggested_position": {"after_paragraph": 2}},
            }
        ]
        result, report = insert_diagrams(article, assets)
        assert report["total_placeholders"] == 1
        assert "DIAGRAM:d1" in result
        assert "Para 1" in result
        assert "Para 2" in result
        assert "Para 3" in result

    def test_insert_at_end_when_no_position(self):
        article = "Para 1\n\nPara 2"
        assets = [
            {
                "id": "d2",
                "caption": "End",
                "files": {"png": {"path": "end.png"}, "mmd": {"path": "end.mmd"}},
                "insertion_guide": {},
            }
        ]
        result, report = insert_diagrams(article, assets)
        assert "DIAGRAM:d2" in result
        assert result.index("Para 2") < result.index("DIAGRAM:d2")


class TestDiagramInsertCLI:
    """Test diagram-insert CLI."""

    def test_insert_command(self, tmp_path):
        article_file = tmp_path / "article.md"
        article_file.write_text("# Title\n\nParagraph one.\n\nParagraph two.")

        assets_file = tmp_path / "assets.json"
        assets_data = [
            {
                "id": "fig1",
                "caption": "示意图",
                "files": {"png": {"path": "fig1.png"}, "mmd": {"path": "fig1.mmd"}},
                "insertion_guide": {"suggested_position": {"after_paragraph": 1}},
            }
        ]
        assets_file.write_text(json.dumps(assets_data))

        output_file = tmp_path / "output.md"
        report_file = tmp_path / "report.json"

        runner = CliRunner()
        result = runner.invoke(diagram_insert, [
            "insert",
            "-a", str(article_file),
            "-s", str(assets_file),
            "-o", str(output_file),
            "-r", str(report_file),
        ])
        assert result.exit_code == 0
        assert output_file.exists()
        assert report_file.exists()
        assert "DIAGRAM:fig1" in output_file.read_text()

    def test_insert_missing_article(self, tmp_path):
        assets_file = tmp_path / "assets.json"
        assets_file.write_text("[]")
        runner = CliRunner()
        result = runner.invoke(diagram_insert, [
            "insert", "-a", "/nonexistent.md", "-s", str(assets_file)
        ])
        assert result.exit_code == 3


# ============================================================
# md_to_wechat tests
# ============================================================

class TestMdToWechatVerify:
    """Test WeChat HTML verification."""

    def test_clean_html_passes(self, tmp_path):
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        f = tmp_path / "clean.html"
        f.write_text(html)
        violations = _verify_html(str(f))
        assert violations == []

    def test_forbidden_tag_detected(self, tmp_path):
        html = "<html><body><div>Bad</div></body></html>"
        f = tmp_path / "bad.html"
        f.write_text(html)
        violations = _verify_html(str(f))
        assert any("div" in v for v in violations)

    def test_external_css_detected(self, tmp_path):
        html = '<html><head><link rel="stylesheet" href="style.css"></head></html>'
        f = tmp_path / "ext.html"
        f.write_text(html)
        violations = _verify_html(str(f))
        assert any("CSS" in v for v in violations)


class TestMdToWechatCLI:
    """Test md-to-wechat CLI."""

    def test_convert_basic(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nThis is a test.\n\n## Section\n\nMore content.")
        output_file = tmp_path / "output.html"

        runner = CliRunner()
        result = runner.invoke(md_to_wechat, [
            "convert", "-i", str(md_file), "-o", str(output_file)
        ])
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["ok"] is True
        assert output_file.exists()

    def test_convert_missing_file(self):
        runner = CliRunner()
        result = runner.invoke(md_to_wechat, [
            "convert", "-i", "/nonexistent.md"
        ])
        assert result.exit_code == 3
