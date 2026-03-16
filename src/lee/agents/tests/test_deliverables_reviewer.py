"""
Tests for Deliverables Reviewer Agent
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from lee.agents.deliverables_reviewer import (
    DeliverablesChecker,
    DeliverablesCheckResult,
    DeliverablesReportGenerator,
    check_deliverables,
    DeliverableRequirement,
)


@pytest.fixture
def temp_project():
    """Create a temporary project structure"""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / 'src' / 'lee' / 'agents').mkdir(parents=True)
    (temp_dir / 'spec' / 'requirements').mkdir(parents=True)
    (temp_dir / 'docs').mkdir(parents=True)
    (temp_dir / 'examples').mkdir(parents=True)

    yield temp_dir

    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_feat_spec(temp_project: Path) -> str:
    """Create a sample FEAT spec file"""
    spec_content = """---
id: FEAT-TEST-001
title: Test Feature for Deliverables Check
status: frozen
outputs:
  - test_module.py Main test module
  - schema.yaml Schema definition
  - usage-guide.md Usage documentation
  - example.json Example file
---

# Test Feature

This is a test feature for deliverables checking.
"""
    spec_path = temp_project / 'spec' / 'requirements' / 'FEAT-TEST-001.md'
    spec_path.write_text(spec_content)

    # Create some (but not all) deliverables
    (temp_project / 'src' / 'lee' / 'agents' / 'test_module.py').write_text('# Test')
    (temp_project / 'spec' / 'requirements' / 'schema.yaml').write_text('test: true')

    return str(spec_path.relative_to(temp_project))


# =============================================================================
# DeliverablesChecker Tests
# =============================================================================

class TestDeliverablesChecker:

    def test_init(self, temp_project: Path):
        """Test checker initialization"""
        checker = DeliverablesChecker(str(temp_project))
        assert checker.project_root == temp_project

    def test_load_feat_spec(self, temp_project: Path, sample_feat_spec: str):
        """Test loading FEAT specification"""
        checker = DeliverablesChecker(str(temp_project))
        spec = checker.load_feat_spec(sample_feat_spec)

        assert spec['id'] == 'FEAT-TEST-001'
        assert spec['title'] == 'Test Feature for Deliverables Check'
        assert 'outputs' in spec

    def test_load_feat_spec_not_found(self, temp_project: Path):
        """Test loading non-existent FEAT spec"""
        checker = DeliverablesChecker(str(temp_project))

        with pytest.raises(FileNotFoundError):
            checker.load_feat_spec('nonexistent.md')

    def test_extract_required_outputs(self, temp_project: Path, sample_feat_spec: str):
        """Test extracting required outputs"""
        checker = DeliverablesChecker(str(temp_project))
        spec = checker.load_feat_spec(sample_feat_spec)
        outputs = checker.extract_required_outputs(spec)

        assert len(outputs) == 4
        assert 'test_module.py Main test module' in outputs

    def test_find_deliverable_path_found(self, temp_project: Path, sample_feat_spec: str):
        """Test finding existing deliverable"""
        checker = DeliverablesChecker(str(temp_project))

        path = checker.find_deliverable_path(
            'test_module.py',
            ['src', 'spec', 'docs']
        )

        assert path is not None
        assert 'test_module.py' in path

    def test_find_deliverable_path_not_found(self, temp_project: Path, sample_feat_spec: str):
        """Test finding non-existent deliverable"""
        checker = DeliverablesChecker(str(temp_project))

        path = checker.find_deliverable_path(
            'nonexistent.py',
            ['src', 'spec', 'docs']
        )

        assert path is None

    def test_check_deliverables_complete(self, temp_project: Path):
        """Test checking all deliverables complete"""
        # Create all deliverables
        (temp_project / 'src' / 'module.py').write_text('# Module')
        (temp_project / 'spec' / 'schema.yaml').write_text('test: true')

        # Create spec
        spec_content = """---
id: FEAT-COMPLETE-001
title: Complete Feature
outputs:
  - module.py Test module
  - schema.yaml Schema file
---
"""
        spec_path = temp_project / 'spec' / 'feat-complete.md'
        spec_path.write_text(spec_content)

        checker = DeliverablesChecker(str(temp_project))
        result = checker.check_deliverables(
            str(spec_path.relative_to(temp_project)),
            ['src', 'spec']
        )

        assert result.status == 'pass'
        assert result.gate_decision == 'pass'
        assert result.complete_count == 2
        assert result.missing_count == 0
        assert result.completeness_percentage == 100.0

    def test_check_deliverables_missing(self, temp_project: Path):
        """Test checking with missing deliverables"""
        # Create only one deliverable
        (temp_project / 'src' / 'module.py').write_text('# Module')

        # Create spec
        spec_content = """---
id: FEAT-MISSING-001
title: Incomplete Feature
outputs:
  - module.py Test module
  - schema.yaml Schema file
  - docs.md Documentation
---
"""
        spec_path = temp_project / 'spec' / 'feat-missing.md'
        spec_path.write_text(spec_content)

        checker = DeliverablesChecker(str(temp_project))
        result = checker.check_deliverables(
            str(spec_path.relative_to(temp_project)),
            ['src', 'spec', 'docs']
        )

        assert result.status == 'partial_pass'
        assert result.gate_decision == 'fail'
        assert result.complete_count == 1
        assert result.missing_count == 2
        assert len(result.issues) == 2

    def test_check_deliverables_all_missing(self, temp_project: Path):
        """Test checking with all deliverables missing"""
        # Create spec without deliverables
        spec_content = """---
id: FEAT-EMPTY-001
title: Empty Feature
outputs:
  - module.py Test module
  - schema.yaml Schema file
---
"""
        spec_path = temp_project / 'spec' / 'feat-empty.md'
        spec_path.write_text(spec_content)

        checker = DeliverablesChecker(str(temp_project))
        result = checker.check_deliverables(
            str(spec_path.relative_to(temp_project)),
            ['src', 'spec']
        )

        assert result.status == 'fail'
        assert result.gate_decision == 'fail'
        assert result.complete_count == 0
        assert result.missing_count == 2


# =============================================================================
# DeliverablesReportGenerator Tests
# =============================================================================

class TestDeliverablesReportGenerator:

    @pytest.fixture
    def sample_result(self) -> DeliverablesCheckResult:
        """Create a sample check result"""
        return DeliverablesCheckResult(
            feature_id='FEAT-TEST-001',
            feature_title='Test Feature',
            check_timestamp='2026-03-16T12:00:00',
            feat_spec_path='spec/requirements/FEAT-TEST-001.md',
            required_deliverables=[
                DeliverableRequirement(
                    name='module.py',
                    description='Main module',
                    status='complete',
                    path='src/module.py',
                ),
                DeliverableRequirement(
                    name='schema.yaml',
                    description='Schema',
                    status='missing',
                    path=None,
                ),
            ],
            complete_count=1,
            missing_count=1,
            total_count=2,
            completeness_percentage=50.0,
            status='partial_pass',
            gate_decision='fail',
            issues=[{
                'id': 'DELIVERABLE-GAP-001',
                'severity': 'medium',
                'title': 'Missing deliverable: schema.yaml',
                'file': 'schema.yaml',
            }],
        )

    def test_generate_json_report(self, temp_project: Path, sample_result: DeliverablesCheckResult):
        """Test JSON report generation"""
        generator = DeliverablesReportGenerator()
        output_path = temp_project / 'output' / 'report.json'

        result_path = generator.generate_json_report(sample_result, str(output_path))

        assert Path(result_path).exists()
        assert Path(result_path).suffix == '.json'

        # Verify content
        import json
        with open(result_path) as f:
            report = json.load(f)

        assert report['feature_id'] == 'FEAT-TEST-001'
        assert report['status'] == 'partial_pass'
        assert report['completeness']['percentage'] == 50.0
        assert len(report['required_deliverables']) == 2

    def test_generate_markdown_report(self, temp_project: Path, sample_result: DeliverablesCheckResult):
        """Test Markdown report generation"""
        generator = DeliverablesReportGenerator()
        output_path = temp_project / 'output' / 'report.md'

        result_path = generator.generate_markdown_report(sample_result, str(output_path))

        assert Path(result_path).exists()
        assert Path(result_path).suffix == '.md'

        # Verify content
        content = Path(result_path).read_text()
        assert 'FEAT-TEST-001' in content
        assert 'PARTIAL_PASS' in content  # Status is uppercase in report
        assert 'schema.yaml' in content


# =============================================================================
# Public API Tests
# =============================================================================

class TestPublicAPI:

    def test_check_deliverables_api(self, temp_project: Path, sample_feat_spec: str):
        """Test public check_deliverables function"""
        # Create output directory
        output_dir = temp_project / 'output'
        output_dir.mkdir()

        result = check_deliverables(
            feat_spec_path=sample_feat_spec,
            project_root=str(temp_project),
            output_dir=str(output_dir),
            search_dirs=['src', 'spec', 'docs', 'examples'],
        )

        assert isinstance(result, DeliverablesCheckResult)
        assert result.feature_id == 'FEAT-TEST-001'

        # Verify reports were generated
        assert (output_dir / 'deliverables-check.json').exists()
        assert (output_dir / 'deliverables-check.md').exists()


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:

    def test_full_workflow_complete(self, temp_project: Path):
        """Test full workflow with all deliverables complete"""
        # Create deliverables
        (temp_project / 'src' / 'agent.py').write_text('# Agent')
        (temp_project / 'spec' / 'schema.yaml').write_text('schema: v1')
        (temp_project / 'docs' / 'guide.md').write_text('# Guide')
        (temp_project / 'examples' / 'example.json').write_text('{}')

        # Create spec
        spec_content = """---
id: FEAT-FULL-001
title: Full Feature
outputs:
  - agent.py Agent implementation
  - schema.yaml Schema definition
  - guide.md Documentation
  - example.json Example
---
"""
        spec_path = temp_project / 'spec' / 'feat-full.md'
        spec_path.write_text(spec_content)

        result = check_deliverables(
            feat_spec_path=str(spec_path.relative_to(temp_project)),
            project_root=str(temp_project),
        )

        assert result.status == 'pass'
        assert result.gate_decision == 'pass'
        assert result.completeness_percentage == 100.0

    def test_full_workflow_incomplete(self, temp_project: Path):
        """Test full workflow with missing deliverables"""
        # Create only some deliverables
        (temp_project / 'src' / 'agent.py').write_text('# Agent')

        # Create spec
        spec_content = """---
id: FEAT-PARTIAL-001
title: Partial Feature
outputs:
  - agent.py Agent implementation
  - schema.yaml Schema definition
  - guide.md Documentation
---
"""
        spec_path = temp_project / 'spec' / 'feat-partial.md'
        spec_path.write_text(spec_content)

        result = check_deliverables(
            feat_spec_path=str(spec_path.relative_to(temp_project)),
            project_root=str(temp_project),
        )

        assert result.status == 'partial_pass'
        assert result.gate_decision == 'fail'
        assert result.completeness_percentage < 100.0
        assert len(result.issues) == 2
