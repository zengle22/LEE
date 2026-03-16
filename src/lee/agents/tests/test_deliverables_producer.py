"""
Tests for Deliverables Producer Agent
"""

import json
import os
import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Any, Dict

from lee.agents.deliverables_producer import (
    DeliverablesProducer,
    DeliverableProductionResult,
    produce_deliverables,
)


class TestDeliverablesProducer:
    """Test DeliverablesProducer class"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure"""
        # Create directories
        (tmp_path / "spec" / "requirements").mkdir(parents=True)
        (tmp_path / "src").mkdir()
        (tmp_path / "docs").mkdir()
        (tmp_path / "examples").mkdir()

        # Create a test FEAT spec
        feat_spec = {
            "id": "TEST-001",
            "title": "Test Feature",
            "outputs": [
                "test_schema.schema.yaml",
                "test_example.yaml",
                "test_guide.md"
            ]
        }

        feat_spec_path = tmp_path / "spec" / "requirements" / "TEST-001.md"
        with open(feat_spec_path, 'w') as f:
            f.write("---\n")
            f.write(yaml.dump(feat_spec))
            f.write("---\n")
            f.write("# Test Feature\n")

        return tmp_path

    def test_init(self, temp_project):
        """Test initialization"""
        producer = DeliverablesProducer(str(temp_project))
        assert producer.project_root == temp_project

    def test_load_feat_spec(self, temp_project):
        """Test loading FEAT specification"""
        producer = DeliverablesProducer(str(temp_project))
        feat_spec_path = temp_project / "spec" / "requirements" / "TEST-001.md"
        spec = producer.load_feat_spec(str(feat_spec_path))

        assert spec["id"] == "TEST-001"
        assert spec["title"] == "Test Feature"
        assert "outputs" in spec

    def test_load_feat_spec_not_found(self, temp_project):
        """Test loading non-existent FEAT spec"""
        producer = DeliverablesProducer(str(temp_project))

        with pytest.raises(FileNotFoundError):
            producer.load_feat_spec("nonexistent.md")

    def test_get_deliverable_type_schema(self, temp_project):
        """Test deliverable type detection for schema"""
        producer = DeliverablesProducer(str(temp_project))

        assert producer.get_deliverable_type("test.schema.yaml") == "schema"
        assert producer.get_deliverable_type("test.schema.json") == "schema"

    def test_get_deliverable_type_example(self, temp_project):
        """Test deliverable type detection for example"""
        producer = DeliverablesProducer(str(temp_project))

        assert producer.get_deliverable_type("example-test.yaml") == "example"
        assert producer.get_deliverable_type("example-test.json") == "example"

    def test_get_deliverable_type_guide(self, temp_project):
        """Test deliverable type detection for guide"""
        producer = DeliverablesProducer(str(temp_project))

        assert producer.get_deliverable_type("usage-guide.md") == "guide"
        assert producer.get_deliverable_type("test-guide.md") == "guide"

    def test_produce_schema_yaml(self, temp_project):
        """Test producing YAML schema file"""
        producer = DeliverablesProducer(str(temp_project))
        feat_spec = producer.load_feat_spec(
            str(temp_project / "spec" / "requirements" / "TEST-001.md")
        )

        result = producer.produce_deliverable(
            "test_schema.schema.yaml",
            feat_spec,
            ["src", "spec", "docs"]
        )

        assert result["status"] == "produced"
        assert result["type"] == "schema"
        assert os.path.exists(result["path"])

        # Verify content is valid YAML
        with open(result["path"]) as f:
            content = yaml.safe_load(f)
        assert "$schema" in content

    def test_produce_example(self, temp_project):
        """Test producing example file"""
        producer = DeliverablesProducer(str(temp_project))
        feat_spec = producer.load_feat_spec(
            str(temp_project / "spec" / "requirements" / "TEST-001.md")
        )

        result = producer.produce_deliverable(
            "example-test.yaml",
            feat_spec,
            ["src", "spec", "docs"]
        )

        assert result["status"] == "produced"
        assert result["type"] == "example"
        assert os.path.exists(result["path"])

    def test_produce_guide(self, temp_project):
        """Test producing usage guide"""
        producer = DeliverablesProducer(str(temp_project))
        feat_spec = producer.load_feat_spec(
            str(temp_project / "spec" / "requirements" / "TEST-001.md")
        )

        result = producer.produce_deliverable(
            "usage-guide.md",
            feat_spec,
            ["src", "spec", "docs"]
        )

        assert result["status"] == "produced"
        assert result["type"] == "guide"
        assert os.path.exists(result["path"])

        # Verify content is markdown
        with open(result["path"]) as f:
            content = f.read()
        assert "# " in content  # Markdown header

    def test_produce_all(self, temp_project):
        """Test producing all deliverables"""
        producer = DeliverablesProducer(str(temp_project))
        feat_spec_path = temp_project / "spec" / "requirements" / "TEST-001.md"

        missing = ["test_schema.schema.yaml", "example-test.yaml", "usage-guide.md"]

        result = producer.produce_all(str(feat_spec_path), missing, ["src", "spec", "docs"])

        assert result.feature_id == "TEST-001"
        assert result.deliverables_production_result == "pass"
        assert len(result.produced_deliverables) == 3
        assert all(d["status"] == "produced" for d in result.produced_deliverables)


class TestDeliverablesProductionResult:
    """Test DeliverableProductionResult dataclass"""

    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = DeliverableProductionResult(
            feature_id="TEST-001",
            produced_deliverables=[
                {"name": "test.yaml", "path": "/test", "type": "schema", "status": "produced"}
            ],
            production_notes="Test notes",
            deliverables_production_result="pass"
        )

        d = result.to_dict()
        assert d["feature_id"] == "TEST-001"
        assert len(d["produced_deliverables"]) == 1
        assert d["production_notes"] == "Test notes"
        assert d["deliverables_production_result"] == "pass"


class TestPublicAPI:
    """Test public API functions"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure"""
        (tmp_path / "spec" / "requirements").mkdir(parents=True)
        (tmp_path / "output").mkdir()

        feat_spec = {
            "id": "TEST-002",
            "title": "Test Feature 2",
            "outputs": ["test.schema.yaml"]
        }

        feat_spec_path = tmp_path / "spec" / "requirements" / "TEST-002.md"
        with open(feat_spec_path, 'w') as f:
            f.write("---\n")
            f.write(yaml.dump(feat_spec))
            f.write("---\n")

        return tmp_path

    def test_produce_deliverables_api(self, temp_project):
        """Test produce_deliverables public API"""
        feat_spec_path = temp_project / "spec" / "requirements" / "TEST-002.md"

        result = produce_deliverables(
            feat_spec_ref=str(feat_spec_path),
            missing_deliverables=["test.schema.yaml"],
            output_base=str(temp_project / "output"),
            search_dirs=["src", "spec"],
            project_root=str(temp_project),
        )

        assert result["feature_id"] == "TEST-002"
        assert result["deliverables_production_result"] == "pass"
        assert len(result["produced_deliverables"]) == 1


class TestIntegration:
    """Integration tests"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure"""
        (tmp_path / "spec" / "requirements").mkdir(parents=True)
        (tmp_path / "output").mkdir()

        # Create FEAT spec similar to FEAT-SRC-056-002
        feat_spec = {
            "id": "FEAT-TEST-001",
            "title": "Test Agent Implementation",
            "outputs": [
                "test_agent.py agent core module",
                "test_schema.schema.yaml schema definition",
                "example-output.yaml example output",
                "usage-guide.md usage documentation"
            ]
        }

        feat_spec_path = tmp_path / "spec" / "requirements" / "FEAT-TEST-001.md"
        with open(feat_spec_path, 'w') as f:
            f.write("---\n")
            f.write(yaml.dump(feat_spec))
            f.write("---\n")
            f.write("# Test\n")

        return tmp_path

    def test_full_production_workflow(self, temp_project):
        """Test full production workflow"""
        feat_spec_path = temp_project / "spec" / "requirements" / "FEAT-TEST-001.md"

        # Simulate missing deliverables
        missing = [
            "test_schema.schema.yaml",
            "example-output.yaml",
            "usage-guide.md"
        ]

        result = produce_deliverables(
            feat_spec_ref=str(feat_spec_path),
            missing_deliverables=missing,
            output_base=str(temp_project / "output"),
            search_dirs=["src", "spec", "docs", "examples"],
            project_root=str(temp_project),
        )

        # Verify results
        assert result["feature_id"] == "FEAT-TEST-001"
        assert result["deliverables_production_result"] == "pass"
        assert result["produced_count"] == 3 if "produced_count" in result else 3
        assert len(result["produced_deliverables"]) == 3

        # Verify files exist
        for deliverable in result["produced_deliverables"]:
            if deliverable["status"] == "produced":
                assert os.path.exists(deliverable["path"])
