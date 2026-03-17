"""
Smoke Gate Models
=================
SRC-058 Dev Smoke Gate - 数据模型与枚举定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SmokeGateStatus(str, Enum):
    """枚举 Smoke Gate 的状态，用于表示门禁的当前状态。"""

    NOT_STARTED = "not_started"      # 尚未开始执行
    RUNNING = "running"              # 正在执行中
    PASSED = "passed"                # 已通过
    FAILED = "failed"                # 失败（有 blocker）
    INVALID = "invalid"              # 无效执行（环境错误等）


class GateResult(str, Enum):
    """枚举 Gate 的最终判定结果。"""

    ALLOW_MERGE = "allow_merge"      # 允许合并
    BLOCK_MERGE = "block_merge"      # 阻塞合并
    PENDING = "pending"              # 等待中（执行中或环境准备中）
    ERROR = "error"                  # 错误状态


class FailureSeverity(str, Enum):
    """枚举测试失败的严重程度，用于区分阻塞级别。"""

    BLOCKER = "blocker"              # 阻塞性问题，必须修复
    CRITICAL = "critical"            # 严重问题，但可能不阻塞
    FLAKY = "flaky"                  # 不稳定测试，不阻塞但需追踪


class SmokeGateEvent(str, Enum):
    """Smoke Gate 生命周期事件。"""

    GATE_CREATED = "gate.created"           # Gate 创建
    EXECUTION_STARTED = "execution.started" # 执行开始
    EXECUTION_COMPLETED = "execution.completed"  # 执行完成
    GATE_PASSED = "gate.passed"             # Gate 通过
    GATE_FAILED = "gate.failed"             # Gate 失败
    MERGE_BLOCKED = "merge.blocked"         # Merge 被阻塞
    MERGE_ALLOWED = "merge.allowed"         # Merge 被允许


@dataclass
class SmokeGateContext:
    """
    Smoke Gate 执行的上下文信息。
    """

    # === 基础标识 ===
    merge_request_id: str                     # Merge 请求 ID
    branch_name: str                          # 分支名称
    target_branch: str                        # 目标分支（如 main）
    commit_sha: str                           # 当前 commit SHA

    # === 测试配置 ===
    test_set_ref: str                         # Test Set 引用
    priority_filter: List[str]                # 优先级过滤 [P0, P1]

    # === 执行状态 ===
    status: SmokeGateStatus                   # Gate 状态

    # === 带默认值的字段必须放在最后 ===
    retry_count: int = 3                      # 重试次数
    timeout_minutes: int = 30                 # 超时时间
    result: Optional[GateResult] = None       # 判定结果

    # === 时间戳 ===
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def start_execution(self) -> None:
        """启动执行，更新状态和时间戳。"""
        if self.status != SmokeGateStatus.NOT_STARTED:
            raise ValueError(f"Cannot start execution from status: {self.status}")
        self.status = SmokeGateStatus.RUNNING
        self.started_at = datetime.now()

    def complete_execution(self, result: GateResult) -> None:
        """完成执行，更新状态和结果。"""
        if self.status != SmokeGateStatus.RUNNING:
            raise ValueError(f"Cannot complete execution from status: {self.status}")
        self.result = result
        self.completed_at = datetime.now()
        if result == GateResult.ALLOW_MERGE:
            self.status = SmokeGateStatus.PASSED
        elif result == GateResult.BLOCK_MERGE:
            self.status = SmokeGateStatus.FAILED
        else:
            self.status = SmokeGateStatus.INVALID


@dataclass
class TestExecutionRecord:
    """
    单个测试用例的执行记录。
    """

    test_id: str                              # 测试用例 ID
    test_name: str                            # 测试用例名称
    priority: str                             # 优先级 P0/P1/P2
    status: str                               # 执行状态 pass/fail/skip
    duration_ms: int                          # 执行耗时（毫秒）

    # === 带默认值的字段必须放在最后 ===
    severity: Optional[FailureSeverity] = None  # 失败严重程度
    error_message: Optional[str] = None       # 错误信息
    retry_attempts: int = 0                   # 重试次数
    evidence_path: Optional[str] = None       # 证据文件路径（截图/日志）
    is_flaky: bool = False                    # 是否为 Flaky 测试


@dataclass
class SmokeGateReport:
    """
    Smoke Gate 执行报告，包含完整的执行结果和判定。
    """

    # === 执行标识 ===
    smoke_run_id: str                         # Smoke 执行 ID
    merge_request_id: str                     # 关联的 MR ID
    commit_sha: str                           # 关联的 commit
    test_set_ref: str                         # Test Set 引用

    # === 执行摘要 ===
    total_cases: int                          # 总用例数
    passed: int                               # 通过数
    failed: int                               # 失败数
    skipped: int                              # 跳过数
    pass_rate: float                          # 通过率

    # === 判定结果 ===
    result: GateResult                        # 判定结果
    status: SmokeGateStatus                   # 执行状态

    # === 失败详情 ===
    failure_details: List[TestExecutionRecord]  # 失败用例详情
    blocker_count: int                        # Blocker 数量
    critical_count: int                       # Critical 数量
    flaky_count: int                          # Flaky 数量

    # === 时间信息 ===
    started_at: datetime                      # 开始时间
    completed_at: datetime                    # 完成时间
    duration_seconds: int                     # 执行耗时

    # === 证据引用 ===
    log_path: str                             # 日志文件路径
    evidence_dir: str                         # 证据目录
    report_html_path: Optional[str] = None    # HTML 报告路径

    # === 元数据 ===
    version: int = 1

    @classmethod
    def create_from_executions(
        cls,
        smoke_run_id: str,
        merge_request_id: str,
        commit_sha: str,
        test_set_ref: str,
        executions: List[TestExecutionRecord],
        started_at: datetime,
        completed_at: datetime,
        log_path: str,
        evidence_dir: str,
        report_html_path: Optional[str] = None
    ) -> "SmokeGateReport":
        """从执行记录创建报告。"""
        total_cases = len(executions)
        passed = sum(1 for e in executions if e.status == "pass")
        failed = sum(1 for e in executions if e.status == "fail")
        skipped = sum(1 for e in executions if e.status == "skip")
        pass_rate = passed / total_cases if total_cases > 0 else 0.0

        # 计算严重程度计数
        blocker_count = sum(
            1 for e in executions
            if e.status == "fail" and e.severity == FailureSeverity.BLOCKER
        )
        critical_count = sum(
            1 for e in executions
            if e.status == "fail" and e.severity == FailureSeverity.CRITICAL
        )
        flaky_count = sum(
            1 for e in executions
            if e.status == "fail" and e.severity == FailureSeverity.FLAKY
        )

        # 判定结果
        if blocker_count > 0:
            result = GateResult.BLOCK_MERGE
            status = SmokeGateStatus.FAILED
        elif failed > 0:
            # 有失败但无 blocker（可能是 P2 用例）
            result = GateResult.ALLOW_MERGE
            status = SmokeGateStatus.PASSED
        else:
            result = GateResult.ALLOW_MERGE
            status = SmokeGateStatus.PASSED

        duration_seconds = int((completed_at - started_at).total_seconds())

        return cls(
            smoke_run_id=smoke_run_id,
            merge_request_id=merge_request_id,
            commit_sha=commit_sha,
            test_set_ref=test_set_ref,
            total_cases=total_cases,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=pass_rate,
            result=result,
            status=status,
            failure_details=[e for e in executions if e.status == "fail"],
            blocker_count=blocker_count,
            critical_count=critical_count,
            flaky_count=flaky_count,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            log_path=log_path,
            evidence_dir=evidence_dir,
            report_html_path=report_html_path
        )


@dataclass
class MergeGateState:
    """
    Merge Gate 的状态机，用于追踪整个 merge 流程的 Gate 状态。
    """

    merge_request_id: str                     # Merge 请求 ID
    branch_name: str                          # 分支名称
    target_branch: str                        # 目标分支
    current_commit_sha: str                   # 当前 commit

    # === Gate 状态 ===
    gate_status: SmokeGateStatus              # Smoke Gate 状态
    gate_result: Optional[GateResult] = None  # Gate 判定结果

    # === 执行历史 ===
    last_run_id: Optional[str] = None         # 最近一次执行 ID
    last_run_at: Optional[datetime] = None    # 最近执行时间
    run_count: int = 0                        # 执行次数

    # === Blocker 信息 ===
    blocker_issues: List[str] = field(default_factory=list)  # Blocker 问题列表
    is_mergeable: bool = True                 # 是否可合并

    # === 元数据 ===
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1

    def update_from_report(self, report: SmokeGateReport) -> None:
        """从报告更新状态。"""
        self.gate_status = report.status
        self.gate_result = report.result
        self.last_run_id = report.smoke_run_id
        self.last_run_at = report.completed_at
        self.run_count += 1
        self.updated_at = datetime.now()

        # 更新 blocker 信息
        self.blocker_issues = [
            f"{e.test_name}: {e.error_message}"
            for e in report.failure_details
            if e.severity == FailureSeverity.BLOCKER
        ]

        # 更新可合并性
        self.is_mergeable = (
            self.gate_status == SmokeGateStatus.PASSED and
            self.gate_result == GateResult.ALLOW_MERGE and
            len(self.blocker_issues) == 0
        )


@dataclass
class SmokeGateConfig:
    """
    Smoke Gate 配置。
    """

    test_set_ref: str                         # Test Set 引用
    priority_filter: List[str] = field(default_factory=lambda: ["P0", "P1"])
    retry_count: int = 3                      # 重试次数
    timeout_minutes: int = 30                 # 超时时间
    parallel_workers: int = 4                 # 并发 worker 数量
    flaky_threshold: float = 0.8              # Flaky 检测阈值（通过率）
    flaky_window: int = 5                     # Flaky 检测窗口（执行次数）


@dataclass
class SmokeGateEventPayload:
    """
    Smoke Gate 事件负载。
    """

    event_type: SmokeGateEvent
    timestamp: datetime
    merge_request_id: str
    smoke_run_id: Optional[str] = None
    status: Optional[SmokeGateStatus] = None
    result: Optional[GateResult] = None
    blocker_details: Optional[List[str]] = None
