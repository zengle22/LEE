"""
QA Module - Runner Base

Base classes for test execution runners.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import time


@dataclass
class TestConfig:
    """Configuration for test execution"""
    scripts: List[Path]  # List of test script paths
    base_url: str = "http://localhost:3000"
    output_dir: Path = None
    headless: bool = True
    timeout: int = 30000
    screenshot_dir: Path = None
    trace_dir: Path = None
    video_dir: Path = None
    environment: str = "local"
    evidence_dir: Path = None  # Per-case evidence bundle directory

    def __post_init__(self):
        if self.output_dir is None:
            self.output_dir = Path.cwd() / "test_output"
        self.output_dir = Path(self.output_dir)

        if self.screenshot_dir is None:
            self.screenshot_dir = self.output_dir / "screenshots"
        if self.trace_dir is None:
            self.trace_dir = self.output_dir / "traces"
        if self.video_dir is None:
            self.video_dir = self.output_dir / "videos"
        if self.evidence_dir is None:
            self.evidence_dir = self.output_dir / "evidence"

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class CaseResult:
    """Result of a single test case"""
    case_id: str
    status: str  # passed, failed, skipped, invalid_run
    error: Optional[str] = None
    error_type: Optional[str] = None  # code_issue, system_issue, uncertain
    is_code_issue: Optional[bool] = None
    exit_code: int = 0
    duration_ms: int = 0
    screenshot_path: Optional[str] = None

    # Per-case evidence bundle fields (v1.1)
    evidence_dir: Optional[Path] = None  # Path to evidence directory for this case
    log_path: Optional[str] = None  # Path to log file
    video_path: Optional[str] = None  # Path to video (optional)
    network_trace_path: Optional[str] = None  # Path to network trace (optional)
    runner_result_ref: Optional[str] = None  # Reference in runner-output.json


@dataclass
class TestResult:
    """Result of test execution"""
    exit_code: int  # 0=success, 1=test failure, 2=infra error
    total: int
    passed: int
    failed: int
    skipped: int = 0
    duration_ms: int = 0
    cases: List[CaseResult] = field(default_factory=list)
    report_path: Optional[Path] = None
    error: Optional[str] = None


class BaseRunner(ABC):
    """
    Base class for test runners.

    Runners are responsible for executing test scripts and
    collecting results.
    """

    def __init__(self, config: TestConfig):
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self):
        """Create output directories if they don't exist"""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self.config.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.config.trace_dir.mkdir(parents=True, exist_ok=True)
        self.config.video_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def name(self) -> str:
        """Runner name"""
        pass

    @abstractmethod
    def check_environment(self) -> Dict[str, bool]:
        """
        Check if the required environment is available.

        Returns:
            Dict mapping check name to success status
        """
        pass

    @abstractmethod
    def execute(self) -> TestResult:
        """
        Execute the test scripts.

        Returns:
            TestResult with execution results
        """
        pass
