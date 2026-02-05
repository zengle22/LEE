"""
L3 Test Orchestration Demo - Complete Workflow Simulation
=========================================================

This script demonstrates the complete L3 test orchestration workflow:
1. Load test execution bundle (test-execution-bundle.yaml)
2. Parse test results (test-results.yaml)
3. Validate result completeness
4. Group failed test cases
5. Generate Bug contracts
6. Calculate metrics
7. Generate test reports (JSON + Markdown)
8. Execute gate evaluation
9. Create test-round.yaml

Usage:
    python demo_l3.py
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR
OUTPUT_DIR = BASE_DIR / "output"
BUGS_DIR = OUTPUT_DIR / "bugs"

# Directories
OUTPUT_DIR.mkdir(exist_ok=True)
BUGS_DIR.mkdir(exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("L3-Orchestration-Demo")


# =============================================================================
# Enums and Data Classes
# =============================================================================

class TestStatus(Enum):
    """Test execution status."""
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class Priority(Enum):
    """Test/Bug priority levels."""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class BugCategory(Enum):
    """Bug category types."""
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DATA = "data"
    REQUIREMENT = "requirement"
    FLAKY = "flaky"
    ENV = "env"


class RoundDecision(Enum):
    """Test round conclusion decision."""
    NEXT_ROUND = "next_round"
    RELEASE_CANDIDATE = "release_candidate"
    BLOCKED = "blocked"
    ABORTED = "aborted"


@dataclass
class TestCase:
    """Test case from execution bundle."""
    case_id: str
    title: str
    suite: str
    priority: str
    type: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    description: Optional[str] = None
    automated: bool = False


@dataclass
class TestResult:
    """Single test execution result."""
    case_id: str
    status: str
    executed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    failure_info: Optional[dict[str, Any]] = None
    evidence: Optional[dict[str, Any]] = None
    blocked_info: Optional[dict[str, Any]] = None


@dataclass
class BugContract:
    """Generated bug contract."""
    bug_id: str
    title: str
    severity: str
    category: str
    status: str = "new"
    detected_in_round: str = ""
    detected_in_version: str = ""
    test_case_id: str = ""
    trace_id: str = ""
    error_message: str = ""
    owner_team: str = "backend"


@dataclass
class TestMetrics:
    """Test execution metrics."""
    total_cases: int
    total_executed: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    pass_rate: float

    # By priority
    p0_total: int = 0
    p0_passed: int = 0
    p0_pass_rate: float = 0.0

    p1_total: int = 0
    p1_passed: int = 0
    p1_pass_rate: float = 0.0

    # By suite
    smoke_total: int = 0
    smoke_passed: int = 0
    smoke_pass_rate: float = 0.0

    # Bugs
    new_bug_count: int = 0
    p0_bug_count: int = 0
    p1_bug_count: int = 0


@dataclass
class GateEvaluation:
    """Gate evaluation result."""
    passed: bool
    decision: str
    rationale: str
    exit_criteria_met: bool
    blockers: list[dict[str, str]] = field(default_factory=list)


# =============================================================================
# Main Workflow Engine
# =============================================================================

class L3OrchestrationEngine:
    """
    L3 Test Orchestration Engine

    Implements the complete workflow for test result aggregation,
    bug generation, reporting, and gate evaluation.
    """

    def __init__(self, round_number: int = 1):
        self.round_number = round_number
        self.round_id = f"TSTR-{round_number:04d}"
        self.start_time = datetime.now()

        # Data containers
        self.test_cases: dict[str, TestCase] = {}
        self.test_results: dict[str, TestResult] = {}
        self.failed_results: list[TestResult] = []
        self.bugs: list[BugContract] = []

        # Bug ID counter
        self._bug_seq = 1

    # -------------------------------------------------------------------------
    # Stage 1: Load Test Execution Bundle
    # -------------------------------------------------------------------------
    def load_bundle(self, bundle_path: Path) -> None:
        """Load test execution bundle YAML."""
        logger.info(f"Loading test execution bundle: {bundle_path}")

        with open(bundle_path, encoding="utf-8") as f:
            bundle_data = yaml.safe_load(f)

        # Extract test cases
        for case_data in bundle_data.get("test_cases", []):
            case = TestCase(
                case_id=case_data["case_id"],
                title=case_data["title"],
                suite=case_data["suite"],
                priority=case_data["priority"],
                type=case_data.get("type"),
                tags=case_data.get("tags", []),
                description=case_data.get("description"),
                automated=case_data.get("execution_config", {}).get("automated", False),
            )
            self.test_cases[case.case_id] = case

        logger.info(f"Loaded {len(self.test_cases)} test cases from bundle")
        self.target_version = bundle_data.get("target_version", "unknown")

    # -------------------------------------------------------------------------
    # Stage 2: Parse Test Results
    # -------------------------------------------------------------------------
    def parse_results(self, results_path: Path) -> None:
        """Parse test execution results YAML."""
        logger.info(f"Parsing test results: {results_path}")

        with open(results_path, encoding="utf-8") as f:
            results_data = yaml.safe_load(f)

        for result_data in results_data.get("results", []):
            result = TestResult(
                case_id=result_data["case_id"],
                status=result_data["status"],
                executed_at=result_data.get("executed_at"),
                duration_seconds=result_data.get("duration_seconds"),
                failure_info=result_data.get("failure_info"),
                evidence=result_data.get("evidence"),
                blocked_info=result_data.get("blocked_info"),
            )
            self.test_results[result.case_id] = result

            if result.status == TestStatus.FAIL.value:
                self.failed_results.append(result)

        logger.info(
            f"Parsed {len(self.test_results)} results "
            f"({len(self.failed_results)} failed)"
        )

    # -------------------------------------------------------------------------
    # Stage 3: Validate Completeness
    # -------------------------------------------------------------------------
    def validate_completeness(self) -> dict[str, Any]:
        """Validate that all test cases have results."""
        logger.info("Validating result completeness...")

        missing_cases = set(self.test_cases.keys()) - set(self.test_results.keys())
        has_p0_p1_missing = any(
            self.test_cases[cid].priority in [Priority.P0.value, Priority.P1.value]
            for cid in missing_cases
        )

        validation_result = {
            "status": "VALID",
            "total_cases": len(self.test_cases),
            "cases_with_results": len(self.test_results),
            "missing_cases": list(missing_cases),
            "has_p0_p1_missing": has_p0_p1_missing,
        }

        if missing_cases:
            if has_p0_p1_missing:
                validation_result["status"] = "INCOMPLETE"
                logger.warning(
                    f"INCOMPLETE: Missing {len(missing_cases)} results "
                    f"(including P0/P1 cases)"
                )
            else:
                validation_result["status"] = "WARNING"
                logger.warning(
                    f"WARNING: Missing {len(missing_cases)} P2/P3 results"
                )
        else:
            logger.info("VALID: All test cases have results")

        return validation_result

    # -------------------------------------------------------------------------
    # Stage 4: Group Failures and Generate Bugs
    # -------------------------------------------------------------------------
    def _generate_bug_id(self) -> str:
        """Generate next bug ID."""
        year = datetime.now().year
        bug_id = f"BUG-{year}-{self._bug_seq:04d}"
        self._bug_seq += 1
        return bug_id

    def _map_priority_to_severity(self, case_priority: str) -> str:
        """Map test case priority to bug severity."""
        return case_priority  # Direct mapping: P0 -> P0, etc.

    def _infer_bug_category(self, error_type: str | None) -> str:
        """Infer bug category from error type."""
        if error_type == "timeout":
            return BugCategory.PERFORMANCE.value
        if error_type == "network_error":
            return BugCategory.FUNCTIONAL.value
        if error_type == "unexpected_exception":
            return BugCategory.REQUIREMENT.value
        return BugCategory.FUNCTIONAL.value

    def _determine_owner_team(self, test_suite: str, error_message: str) -> str:
        """Determine responsible team based on suite and error."""
        test_suite_lower = test_suite.lower() if test_suite else ""
        error_msg_lower = error_message.lower() if error_message else ""

        if "api" in test_suite_lower:
            return "backend"
        if "element_not_found" in error_msg_lower or "upload" in error_msg_lower:
            return "frontend"
        return "backend"  # Default

    def generate_bugs(self) -> None:
        """Generate bug contracts from failed test results."""
        logger.info("Generating bug contracts from failures...")

        for result in self.failed_results:
            case = self.test_cases.get(result.case_id)
            if not case:
                logger.warning(f"Case {result.case_id} not found in bundle, skipping bug generation")
                continue

            # Extract evidence
            trace_id = (result.evidence or {}).get("trace_id", "")
            error_message = (result.failure_info or {}).get("error_message", "")

            bug = BugContract(
                bug_id=self._generate_bug_id(),
                title=f"{case.title} - {error_message[:50]}",
                severity=self._map_priority_to_severity(case.priority),
                category=self._infer_bug_category(
                    (result.failure_info or {}).get("error_type")
                ),
                detected_in_round=self.round_id,
                detected_in_version=self.target_version,
                test_case_id=case.case_id,
                trace_id=trace_id,
                error_message=error_message,
                owner_team=self._determine_owner_team(case.suite, error_message),
            )
            self.bugs.append(bug)

            logger.info(
                f"Generated bug {bug.bug_id} from failed case {case.case_id} "
                f"(severity={bug.severity}, category={bug.category})"
            )

        logger.info(f"Generated {len(self.bugs)} bug contracts")

    def save_bugs(self) -> None:
        """Save bug contracts to individual YAML files."""
        logger.info(f"Saving bug contracts to {BUGS_DIR}...")

        for bug in self.bugs:
            bug_file = BUGS_DIR / f"{bug.bug_id}.contract.yaml"

            bug_data = {
                "bug_id": bug.bug_id,
                "title": bug.title,
                "severity": bug.severity,
                "category": bug.category,
                "status": bug.status,
                "detected_in": {
                    "round_id": bug.detected_in_round,
                    "version": bug.detected_in_version,
                    "test_case_id": bug.test_case_id,
                },
                "evidence": {
                    "trace_id": bug.trace_id,
                },
                "routing": {
                    "owner_team": bug.owner_team,
                    "owner_agent": "dev-agent",
                    "qa_agent": "qa-agent",
                },
                "created_at": datetime.now().isoformat(),
            }

            with open(bug_file, "w", encoding="utf-8") as f:
                yaml.dump(bug_data, f, allow_unicode=True, default_flow_style=False)

            logger.info(f"Saved bug contract: {bug_file}")

    # -------------------------------------------------------------------------
    # Stage 5: Calculate Metrics
    # -------------------------------------------------------------------------
    def calculate_metrics(self) -> TestMetrics:
        """Calculate test execution metrics."""
        logger.info("Calculating test metrics...")

        total_executed = sum(
            1 for r in self.test_results.values()
            if r.status != TestStatus.SKIPPED.value
        )
        passed = sum(
            1 for r in self.test_results.values()
            if r.status == TestStatus.PASS.value
        )
        failed = len(self.failed_results)
        blocked = sum(
            1 for r in self.test_results.values()
            if r.status == TestStatus.BLOCKED.value
        )
        skipped = sum(
            1 for r in self.test_results.values()
            if r.status == TestStatus.SKIPPED.value
        )

        pass_rate = (passed / total_executed * 100) if total_executed > 0 else 0

        # By priority
        p0_cases = [c for c in self.test_cases.values() if c.priority == Priority.P0.value]
        p0_passed = 0
        for case in p0_cases:
            result = self.test_results.get(case.case_id)
            if result and result.status == TestStatus.PASS.value:
                p0_passed += 1

        p1_cases = [c for c in self.test_cases.values() if c.priority == Priority.P1.value]
        p1_passed = 0
        for case in p1_cases:
            result = self.test_results.get(case.case_id)
            if result and result.status == TestStatus.PASS.value:
                p1_passed += 1

        # By suite
        smoke_cases = [c for c in self.test_cases.values() if c.suite == "smoke"]
        smoke_passed = 0
        for case in smoke_cases:
            result = self.test_results.get(case.case_id)
            if result and result.status == TestStatus.PASS.value:
                smoke_passed += 1

        # Bug counts by severity
        p0_bugs = sum(1 for b in self.bugs if b.severity == Priority.P0.value)
        p1_bugs = sum(1 for b in self.bugs if b.severity == Priority.P1.value)

        metrics = TestMetrics(
            total_cases=len(self.test_cases),
            total_executed=total_executed,
            passed=passed,
            failed=failed,
            blocked=blocked,
            skipped=skipped,
            pass_rate=round(pass_rate, 2),
            p0_total=len(p0_cases),
            p0_passed=p0_passed,
            p0_pass_rate=round(p0_passed / len(p0_cases) * 100, 2) if p0_cases else 0,
            p1_total=len(p1_cases),
            p1_passed=p1_passed,
            p1_pass_rate=round(p1_passed / len(p1_cases) * 100, 2) if p1_cases else 0,
            smoke_total=len(smoke_cases),
            smoke_passed=smoke_passed,
            smoke_pass_rate=round(smoke_passed / len(smoke_cases) * 100, 2) if smoke_cases else 0,
            new_bug_count=len(self.bugs),
            p0_bug_count=p0_bugs,
            p1_bug_count=p1_bugs,
        )

        logger.info(
            f"Metrics: {metrics.passed} passed, {metrics.failed} failed, "
            f"{metrics.pass_rate}% pass rate, {metrics.new_bug_count} new bugs"
        )

        return metrics

    # -------------------------------------------------------------------------
    # Stage 6: Generate Reports
    # -------------------------------------------------------------------------
    def generate_json_report(self, metrics: TestMetrics) -> dict[str, Any]:
        """Generate JSON test report."""
        logger.info("Generating JSON report...")

        report = {
            "report_type": "test_orchestration_report",
            "round_id": self.round_id,
            "round_number": self.round_number,
            "target_version": self.target_version,
            "generated_at": datetime.now().isoformat(),
            "execution_time": self.start_time.isoformat(),
            "summary": {
                "total_cases": metrics.total_cases,
                "total_executed": metrics.total_executed,
                "passed": metrics.passed,
                "failed": metrics.failed,
                "blocked": metrics.blocked,
                "skipped": metrics.skipped,
                "pass_rate": metrics.pass_rate,
            },
            "by_priority": {
                "p0": {
                    "total": metrics.p0_total,
                    "passed": metrics.p0_passed,
                    "pass_rate": metrics.p0_pass_rate,
                },
                "p1": {
                    "total": metrics.p1_total,
                    "passed": metrics.p1_passed,
                    "pass_rate": metrics.p1_pass_rate,
                },
            },
            "by_suite": {
                "smoke": {
                    "total": metrics.smoke_total,
                    "passed": metrics.smoke_passed,
                    "pass_rate": metrics.smoke_pass_rate,
                },
            },
            "bugs": {
                "new_bugs": metrics.new_bug_count,
                "by_severity": {
                    "p0": metrics.p0_bug_count,
                    "p1": metrics.p1_bug_count,
                },
                "bug_ids": [b.bug_id for b in self.bugs],
            },
            "failed_test_cases": [
                {
                    "case_id": r.case_id,
                    "error_message": (r.failure_info or {}).get("error_message", ""),
                    "error_type": (r.failure_info or {}).get("error_type", ""),
                }
                for r in self.failed_results
            ],
        }

        # Save JSON report
        json_report_path = OUTPUT_DIR / "test-report.json"
        with open(json_report_path, "w", encoding="utf-8") as f:
            import json
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved JSON report: {json_report_path}")
        return report

    def generate_markdown_report(self, metrics: TestMetrics) -> str:
        """Generate Markdown test report."""
        logger.info("Generating Markdown report...")

        lines = [
            "# Test Execution Report",
            "",
            f"**Round ID**: {self.round_id}",
            f"**Target Version**: {self.target_version}",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Test Cases | {metrics.total_cases} |",
            f"| Executed | {metrics.total_executed} |",
            f"| Passed | {metrics.passed} |",
            f"| Failed | {metrics.failed} |",
            f"| Blocked | {metrics.blocked} |",
            f"| Skipped | {metrics.skipped} |",
            f"| Pass Rate | **{metrics.pass_rate}%** |",
            "",
            "---",
            "",
            "## Test Results by Priority",
            "",
            "| Priority | Total | Passed | Failed | Pass Rate |",
            "|----------|-------|--------|--------|-----------|",
            f"| P0 | {metrics.p0_total} | {metrics.p0_passed} | {metrics.p0_total - metrics.p0_passed} | {metrics.p0_pass_rate}% |",
            f"| P1 | {metrics.p1_total} | {metrics.p1_passed} | {metrics.p1_total - metrics.p1_passed} | {metrics.p1_pass_rate}% |",
            "",
            "---",
            "",
            "## Test Results by Suite",
            "",
            "| Suite | Total | Passed | Failed | Pass Rate |",
            "|-------|-------|--------|--------|-----------|",
            f"| Smoke | {metrics.smoke_total} | {metrics.smoke_passed} | {metrics.smoke_total - metrics.smoke_passed} | {metrics.smoke_pass_rate}% |",
            "",
            "---",
            "",
            "## Bug Summary",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| New Bugs | {metrics.new_bug_count} |",
            f"| P0 Bugs | {metrics.p0_bug_count} |",
            f"| P1 Bugs | {metrics.p1_bug_count} |",
            "",
        ]

        if self.bugs:
            lines.extend([
                "### Bug Details",
                "",
                "| Bug ID | Title | Severity | Category | Test Case |",
                f"|--------|-------|----------|----------|-----------|",
            ])
            for bug in self.bugs:
                lines.append(
                    f"| {bug.bug_id} | {bug.title[:40]}... | {bug.severity} | {bug.category} | {bug.test_case_id} |"
                )

        if self.failed_results:
            lines.extend([
                "",
                "---",
                "",
                "## Failed Test Cases",
                "",
            ])
            for result in self.failed_results:
                case = self.test_cases.get(result.case_id)
                lines.extend([
                    f"### {result.case_id}: {case.title if case else 'Unknown'}",
                    "",
                    f"**Priority**: {case.priority if case else 'N/A'}",
                    f"**Suite**: {case.suite if case else 'N/A'}",
                    "",
                    "**Error**:",
                    f"```",
                    f"{(result.failure_info or {}).get('error_message', 'Unknown error')}",
                    f"```",
                    "",
                ])

        lines.extend([
            "---",
            "",
            "## Recommendations",
            "",
        ])

        if metrics.p0_bug_count > 0:
            lines.append("- CRITICAL: P0 bugs detected, immediate fix required before release.")
        if metrics.smoke_pass_rate < 100:
            lines.append(f"- WARNING: Smoke tests not at 100% ({metrics.smoke_pass_rate}%)")
        if metrics.p1_bug_count > 3:
            lines.append("- WARNING: High number of P1 bugs detected.")
        if metrics.pass_rate >= 90:
            lines.append("- Good: Overall pass rate is healthy.")

        lines.append("")

        report = "\n".join(lines)

        # Save Markdown report
        md_report_path = OUTPUT_DIR / "test-report.md"
        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"Saved Markdown report: {md_report_path}")
        return report

    # -------------------------------------------------------------------------
    # Stage 7: Gate Evaluation
    # -------------------------------------------------------------------------
    def evaluate_gate(self, metrics: TestMetrics) -> GateEvaluation:
        """Evaluate exit criteria gate."""
        logger.info("Evaluating exit criteria gate...")

        blockers = []
        exit_criteria_met = True
        rationale_parts = []

        # Rule 1: P0 Bug must be zero
        if metrics.p0_bug_count > 0:
            exit_criteria_met = False
            blockers.append({
                "blocker_id": f"BLOCKER-P0-{metrics.p0_bug_count}",
                "description": f"{metrics.p0_bug_count} P0 bugs detected",
                "bug_id": ",".join([b.bug_id for b in self.bugs if b.severity == "P0"]),
            })
            rationale_parts.append(f"P0 bugs detected ({metrics.p0_bug_count})")

        # Rule 2: Smoke must be 100%
        if metrics.smoke_pass_rate < 100:
            exit_criteria_met = False
            blockers.append({
                "blocker_id": "BLOCKER-SMOKE",
                "description": f"Smoke tests not 100% ({metrics.smoke_pass_rate}%)",
            })
            rationale_parts.append(f"Smoke pass rate is {metrics.smoke_pass_rate}% (required: 100%)")

        # Rule 3: P1 threshold check
        p1_threshold = 3
        if metrics.p1_bug_count > p1_threshold:
            exit_criteria_met = False
            blockers.append({
                "blocker_id": "BLOCKER-P1",
                "description": f"P1 bugs exceed threshold ({metrics.p1_bug_count} > {p1_threshold})",
            })
            rationale_parts.append(f"P1 bugs exceed threshold ({metrics.p1_bug_count})")

        # Determine decision
        if not exit_criteria_met:
            decision = RoundDecision.NEXT_ROUND.value
            rationale = "; ".join(rationale_parts) + ". Requires another round."
        elif metrics.pass_rate < 85:
            decision = RoundDecision.NEXT_ROUND.value
            rationale = f"Pass rate ({metrics.pass_rate}%) below target (85%). Requires another round."
        else:
            decision = RoundDecision.RELEASE_CANDIDATE.value
            rationale = "All exit criteria met. Ready for release."

        evaluation = GateEvaluation(
            passed=exit_criteria_met,
            decision=decision,
            rationale=rationale,
            exit_criteria_met=exit_criteria_met,
            blockers=blockers,
        )

        logger.info(
            f"Gate evaluation: {'PASSED' if evaluation.passed else 'FAILED'}, "
            f"decision={evaluation.decision}"
        )

        return evaluation

    # -------------------------------------------------------------------------
    # Stage 8: Create Test Round Record
    # -------------------------------------------------------------------------
    def create_round_record(self, metrics: TestMetrics, gate_eval: GateEvaluation) -> dict[str, Any]:
        """Create test-round.yaml record."""
        logger.info("Creating test round record...")

        end_time = datetime.now()
        duration_hours = (end_time - self.start_time).total_seconds() / 3600

        round_data = {
            "round_id": self.round_id,
            "round_number": self.round_number,
            "target_version": self.target_version,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_hours": round(duration_hours, 2),
            "status": "completed",
            "environment": {
                "env_type": "test",
                "deployed_version": self.target_version,
                "health_check_result": "healthy",
            },
            "suites_executed": [
                {
                    "suite_name": "smoke",
                    "status": "passed" if metrics.smoke_pass_rate == 100 else "failed",
                    "total_cases": metrics.smoke_total,
                    "passed": metrics.smoke_passed,
                    "failed": metrics.smoke_total - metrics.smoke_passed,
                    "pass_rate": metrics.smoke_pass_rate,
                },
                {
                    "suite_name": "e2e_chrome",
                    "status": "failed" if metrics.failed > 0 else "passed",
                    "total_cases": metrics.p0_total + metrics.p1_total - metrics.smoke_total,
                    "passed": metrics.p0_passed + metrics.p1_passed - metrics.smoke_passed,
                    "failed": metrics.failed,
                    "pass_rate": metrics.pass_rate,
                },
            ],
            "summary": {
                "new_bugs": metrics.new_bug_count,
                "total_open_bugs": metrics.new_bug_count,
                "bug_breakdown": {
                    "p0_open": metrics.p0_bug_count,
                    "p0_new": metrics.p0_bug_count,
                    "p1_open": metrics.p1_bug_count,
                    "p1_new": metrics.p1_bug_count,
                    "p2_open": sum(1 for b in self.bugs if b.severity == "P2"),
                    "p2_new": sum(1 for b in self.bugs if b.severity == "P2"),
                },
                "bug_ids": [b.bug_id for b in self.bugs],
            },
            "round_goal": {
                "objective": "首次完整功能验证" if self.round_number == 1 else "Bug修复验证",
                "achieved": gate_eval.exit_criteria_met,
            },
            "conclusion": {
                "decision": gate_eval.decision,
                "rationale": gate_eval.rationale,
                "exit_criteria_met": gate_eval.exit_criteria_met,
                "blockers": gate_eval.blockers,
                "next_round_focus": "修复P0/P1 Bug后重新测试" if not gate_eval.exit_criteria_met else "无",
            },
            "artifacts": {
                "reports": ["test-report.json", "test-report.md"],
                "bugs": [f"bugs/{b.bug_id}.contract.yaml" for b in self.bugs],
                "frozen": True,
            },
            "metrics": {
                "total_test_time_seconds": int((end_time - self.start_time).total_seconds()),
                "bug_detection_rate": round(metrics.new_bug_count / metrics.total_executed * 100, 2),
            },
            "created_by": "l3-orchestration-engine",
            "notes": "Generated by L3 Test Orchestration Demo",
        }

        # Save round record
        round_path = OUTPUT_DIR / "test-round.yaml"
        with open(round_path, "w", encoding="utf-8") as f:
            yaml.dump(round_data, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"Saved test round record: {round_path}")
        return round_data


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the demo."""
    logger.info("=" * 60)
    logger.info("L3 Test Orchestration Demo - Starting")
    logger.info("=" * 60)

    # Initialize engine
    engine = L3OrchestrationEngine(round_number=1)

    try:
        # Stage 1: Load test execution bundle
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 1: Load Test Execution Bundle")
        logger.info("=" * 60)
        bundle_path = INPUT_DIR / "test-execution-bundle.yaml"
        engine.load_bundle(bundle_path)

        # Stage 2: Parse test results
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 2: Parse Test Results")
        logger.info("=" * 60)
        results_path = INPUT_DIR / "test-results.yaml"
        engine.parse_results(results_path)

        # Stage 3: Validate completeness
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 3: Validate Result Completeness")
        logger.info("=" * 60)
        validation = engine.validate_completeness()
        if validation["status"] == "INCOMPLETE":
            logger.error("Cannot proceed: P0/P1 test cases missing results")
            return 1

        # Stage 4: Generate bugs
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 4: Generate Bug Contracts")
        logger.info("=" * 60)
        engine.generate_bugs()
        engine.save_bugs()

        # Stage 5: Calculate metrics
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 5: Calculate Test Metrics")
        logger.info("=" * 60)
        metrics = engine.calculate_metrics()

        # Stage 6: Generate reports
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 6: Generate Test Reports")
        logger.info("=" * 60)
        engine.generate_json_report(metrics)
        engine.generate_markdown_report(metrics)

        # Stage 7: Gate evaluation
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 7: Gate Evaluation")
        logger.info("=" * 60)
        gate_eval = engine.evaluate_gate(metrics)

        # Stage 8: Create test round record
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 8: Create Test Round Record")
        logger.info("=" * 60)
        engine.create_round_record(metrics, gate_eval)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("L3 Orchestration Workflow Completed Successfully")
        logger.info("=" * 60)
        logger.info(f"Round ID: {engine.round_id}")
        logger.info(f"Total Cases: {metrics.total_cases}")
        logger.info(f"Passed: {metrics.passed}, Failed: {metrics.failed}")
        logger.info(f"Pass Rate: {metrics.pass_rate}%")
        logger.info(f"New Bugs: {metrics.new_bug_count}")
        logger.info(f"Gate Decision: {gate_eval.decision}")
        logger.info(f"\nOutput files created in: {OUTPUT_DIR}")
        logger.info("  - test-report.json")
        logger.info("  - test-report.md")
        logger.info("  - test-round.yaml")
        logger.info(f"  - bugs/*.contract.yaml ({len(engine.bugs)} files)")

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
