import json
import shutil
import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner

from lee.cli.commands.ssot import ssot
from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTType
from lee.orchestrator.execution.artifacts.chain_testing import (
    ChainTestContext,
    ChainTestResult,
    ChainTestRunner,
    SampleLibrary,
)


class _DummyTester:
    def __init__(self, tester_id: str):
        self.tester_id = tester_id

    def run(self, context: ChainTestContext) -> ChainTestResult:
        return ChainTestResult(
            tester_id=self.tester_id,
            passed=True,
            checked_ids=list(context.sampled_ids),
            metrics={"checked_count": len(context.sampled_ids)},
        )


def _create_requirement_chain(project_root: Path) -> ArtifactManager:
    manager = ArtifactManager(project_root=project_root, root_path=project_root / ".artifacts")
    src = manager.create_ssot(
        ssot_type=SSOTType.SRC,
        title="Chain Source",
        content="# SRC\n",
        run_id="run-chain-001",
    )
    epic = manager.create_ssot(
        ssot_type=SSOTType.EPIC,
        title="Chain Epic",
        content="# EPIC\n",
        run_id="run-chain-001",
        derived_from=[{"id": src.id, "version": "v1"}],
        source_refs=[f"{src.id}#goal"],
    )
    feat = manager.create_ssot(
        ssot_type=SSOTType.FEAT,
        title="Chain Feat",
        content="# FEAT\n",
        run_id="run-chain-001",
        parent_id=epic.id,
        source_refs=[f"{epic.id}#scope"],
    )
    manager.create_ssot(
        ssot_type=SSOTType.TASK,
        title="Chain Task",
        content="# TASK\n",
        run_id="run-chain-001",
        parent_id=feat.id,
        source_refs=[f"{feat.id}#delivery"],
    )
    manager.registry.rebuild()
    return manager


def test_chain_test_runner_registers_and_runs_custom_testers():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = _create_requirement_chain(temp_dir)
        runner = ChainTestRunner(manager)
        runner.register(_DummyTester("alpha"))
        runner.register(_DummyTester("beta"))

        report = runner.run(tester_ids=["alpha", "beta"], sample_strategy="all", use_cache=False)

        assert report.tester_ids == ["alpha", "beta"]
        assert {result.tester_id for result in report.results} == {"alpha", "beta"}
        assert report.metrics["overall_passed"] is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_chain_test_runner_sampling_is_reproducible():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = _create_requirement_chain(temp_dir)
        runner = ChainTestRunner(manager).register_defaults()

        first = runner.run(
            tester_ids=["schema"],
            sample_strategy="random",
            sample_size=2,
            seed=11,
            use_cache=False,
        )
        second = runner.run(
            tester_ids=["schema"],
            sample_strategy="random",
            sample_size=2,
            seed=11,
            use_cache=False,
        )

        assert first.sampled_ids == second.sampled_ids
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_trace_tester_reports_broken_source_refs():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = _create_requirement_chain(temp_dir)
        feat_path = next((temp_dir / "spec" / "requirements" / "features").glob("FEAT-*__*.md"))
        text = feat_path.read_text(encoding="utf-8")
        _, front_matter_text, body = text.split("---", 2)
        front_matter = yaml.safe_load(front_matter_text)
        front_matter["source_refs"] = ["EPIC-404#scope"]
        feat_path.write_text(
            f"---\n{yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()}\n---\n{body}",
            encoding="utf-8",
        )
        manager.registry.rebuild()

        runner = ChainTestRunner(manager).register_defaults()
        report = runner.run(tester_ids=["trace"], use_cache=False)
        issues = [issue.code for issue in report.results[0].issues]

        assert "BROKEN_SOURCE_REF" in issues
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_chain_test_cli_writes_report_and_scorecard():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        _create_requirement_chain(temp_dir)
        runner = CliRunner()

        result = runner.invoke(
            ssot,
            [
                "chain-test",
                "--project-root",
                str(temp_dir),
                "--tester",
                "schema",
                "--tester",
                "trace",
            ],
        )

        assert result.exit_code == 0, result.output
        report_path = temp_dir / ".artifacts" / "trace" / "chain-tests" / "report.json"
        scorecard_path = temp_dir / ".artifacts" / "trace" / "chain-tests" / "scorecard.md"
        assert report_path.exists()
        assert scorecard_path.exists()
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        assert payload["tester_ids"] == ["schema", "trace"]
        assert "overall_passed" in payload["metrics"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_semantic_overlap_replay_and_executable_testers_emit_metrics():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = _create_requirement_chain(temp_dir)
        runner = ChainTestRunner(manager).register_defaults()
        report = runner.run(
            tester_ids=["semantic", "overlap", "replay", "executable"],
            use_cache=False,
        )

        metrics = report.metrics
        assert "semantic_alignment_score" in metrics
        assert metrics["embedding_backend"] in {"sentence-transformers", "token-fallback"}
        assert "overlap_rate" in metrics
        assert "overlap_cluster_count" in metrics
        assert "replay_stability_score" in metrics
        assert metrics["replay_count"] == 3
        assert "environment_consistent" in metrics
        assert "executability_rate" in metrics
        assert "feedback_path" in metrics
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_sample_library_initializes_and_validates_default_counts():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        library = SampleLibrary(temp_dir / "samples")
        counts = library.initialize_defaults()
        validation = library.validate()

        assert counts == {"positive": 50, "negative": 30, "boundary": 20}
        assert validation["is_valid"] is True
        assert validation["counts"] == counts
        assert library.active_version() == "v1"
        manifest = library.load(version="v1", category="positive")
        assert manifest["version"] == "v1"
        assert len(manifest["samples"]) == 50
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_sample_library_supports_version_creation_and_activation():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        library = SampleLibrary(temp_dir / "samples")
        library.initialize_defaults()
        counts = library.create_version(
            "v2",
            {
                "positive": [{"id": "pos-a", "title": "Positive A", "input": {"value": 1}, "expected": {"status": "pass"}}],
                "negative": [{"id": "neg-a", "title": "Negative A", "input": {"value": 2}, "expected": {"status": "review"}}],
                "boundary": [{"id": "bou-a", "title": "Boundary A", "input": {"value": 3}, "expected": {"status": "review"}}],
            },
        )
        library.activate_version("v1")

        assert counts == {"positive": 1, "negative": 1, "boundary": 1}
        assert library.list_versions() == ["v1", "v2"]
        assert library.active_version() == "v1"

        library.activate_version("v2")
        loaded = library.load(category="positive")
        validation = library.validate("v2")

        assert library.active_version() == "v2"
        assert loaded["samples"][0]["id"] == "pos-a"
        assert validation["is_valid"] is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_chain_test_cli_fail_under_returns_non_zero():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        _create_requirement_chain(temp_dir)
        runner = CliRunner()
        result = runner.invoke(
            ssot,
            [
                "chain-test",
                "--project-root",
                str(temp_dir),
                "--tester",
                "schema",
                "--fail-under",
                "101",
            ],
        )

        assert result.exit_code != 0
        assert "below fail-under" in result.output
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_chain_install_ci_command_writes_templates():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        runner = CliRunner()
        result = runner.invoke(
            ssot,
            [
                "chain-install-ci",
                "--project-root",
                str(temp_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert (temp_dir / ".github" / "workflows" / "requirement-chain-test.yml").exists()
        assert (temp_dir / "deploy" / "ci" / "gitlab.requirement-chain-test.yml").exists()
        assert (temp_dir / "deploy" / "ci" / "Dockerfile.chain-test").exists()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
