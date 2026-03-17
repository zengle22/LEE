"""
Smoke Gate Storage
==================
SRC-058 Dev Smoke Gate - 数据持久化存储
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from ..models import (
    SmokeGateContext,
    SmokeGateReport,
    MergeGateState,
    SmokeGateStatus,
    GateResult,
    TestExecutionRecord,
    FailureSeverity,
)


class SmokeStore:
    """
    Smoke Gate 数据持久化存储 (SQLite)。
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化存储。

        Args:
            db_path: 数据库文件路径，默认为项目根目录/.lee/smoke.db
        """
        if db_path is None:
            db_path = str(Path.home() / ".lee" / "smoke.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表结构。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Gate Context 表
                CREATE TABLE IF NOT EXISTS gate_contexts (
                    merge_request_id TEXT PRIMARY KEY,
                    branch_name TEXT NOT NULL,
                    target_branch TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    test_set_ref TEXT NOT NULL,
                    priority_filter TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 3,
                    timeout_minutes INTEGER DEFAULT 30,
                    status TEXT NOT NULL,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                );

                -- Gate Reports 表
                CREATE TABLE IF NOT EXISTS gate_reports (
                    smoke_run_id TEXT PRIMARY KEY,
                    merge_request_id TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    test_set_ref TEXT NOT NULL,
                    total_cases INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    skipped INTEGER NOT NULL,
                    pass_rate REAL NOT NULL,
                    result TEXT NOT NULL,
                    status TEXT NOT NULL,
                    failure_details TEXT,
                    blocker_count INTEGER DEFAULT 0,
                    critical_count INTEGER DEFAULT 0,
                    flaky_count INTEGER DEFAULT 0,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    log_path TEXT NOT NULL,
                    evidence_dir TEXT NOT NULL,
                    report_html_path TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- Merge Gate State 表
                CREATE TABLE IF NOT EXISTS merge_gate_states (
                    merge_request_id TEXT PRIMARY KEY,
                    branch_name TEXT NOT NULL,
                    target_branch TEXT NOT NULL,
                    current_commit_sha TEXT NOT NULL,
                    gate_status TEXT NOT NULL,
                    gate_result TEXT,
                    last_run_id TEXT,
                    last_run_at TEXT,
                    run_count INTEGER DEFAULT 0,
                    blocker_issues TEXT,
                    is_mergeable BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER DEFAULT 1
                );

                -- Test Executions 表（历史记录）
                CREATE TABLE IF NOT EXISTS test_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smoke_run_id TEXT NOT NULL,
                    test_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT,
                    duration_ms INTEGER NOT NULL,
                    error_message TEXT,
                    retry_attempts INTEGER DEFAULT 0,
                    evidence_path TEXT,
                    is_flaky BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (smoke_run_id) REFERENCES gate_reports (smoke_run_id)
                );

                -- 索引
                CREATE INDEX IF NOT EXISTS idx_reports_mr ON gate_reports (merge_request_id);
                CREATE INDEX IF NOT EXISTS idx_states_mergeable ON merge_gate_states (is_mergeable);
                CREATE INDEX IF NOT EXISTS idx_executions_run_id ON test_executions (smoke_run_id);
            """)

    # === Gate Context 操作 ===

    def create_gate_context(self, context: SmokeGateContext) -> None:
        """创建 Gate 上下文记录。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO gate_contexts (
                    merge_request_id, branch_name, target_branch, commit_sha,
                    test_set_ref, priority_filter, retry_count, timeout_minutes,
                    status, result, created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.merge_request_id,
                    context.branch_name,
                    context.target_branch,
                    context.commit_sha,
                    context.test_set_ref,
                    json.dumps(context.priority_filter),
                    context.retry_count,
                    context.timeout_minutes,
                    context.status.value,
                    context.result.value if context.result else None,
                    context.created_at.isoformat(),
                    context.started_at.isoformat() if context.started_at else None,
                    context.completed_at.isoformat() if context.completed_at else None,
                )
            )

    def get_gate_context(self, merge_request_id: str) -> Optional[SmokeGateContext]:
        """获取 Gate 上下文记录。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM gate_contexts WHERE merge_request_id = ?",
                (merge_request_id,)
            ).fetchone()

            if row is None:
                return None

            return SmokeGateContext(
                merge_request_id=row["merge_request_id"],
                branch_name=row["branch_name"],
                target_branch=row["target_branch"],
                commit_sha=row["commit_sha"],
                test_set_ref=row["test_set_ref"],
                priority_filter=json.loads(row["priority_filter"]),
                retry_count=row["retry_count"],
                timeout_minutes=row["timeout_minutes"],
                status=SmokeGateStatus(row["status"]),
                result=GateResult(row["result"]) if row["result"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            )

    def update_gate_context(self, context: SmokeGateContext) -> bool:
        """更新 Gate 上下文记录。"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                """
                UPDATE gate_contexts SET
                    status = ?,
                    result = ?,
                    started_at = ?,
                    completed_at = ?
                WHERE merge_request_id = ?
                """,
                (
                    context.status.value,
                    context.result.value if context.result else None,
                    context.started_at.isoformat() if context.started_at else None,
                    context.completed_at.isoformat() if context.completed_at else None,
                    context.merge_request_id,
                )
            )
            return result.rowcount > 0

    # === Gate Report 操作 ===

    def create_gate_report(self, report: SmokeGateReport) -> None:
        """创建 Gate 执行报告。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO gate_reports (
                    smoke_run_id, merge_request_id, commit_sha, test_set_ref,
                    total_cases, passed, failed, skipped, pass_rate,
                    result, status, failure_details,
                    blocker_count, critical_count, flaky_count,
                    started_at, completed_at, duration_seconds,
                    log_path, evidence_dir, report_html_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.smoke_run_id,
                    report.merge_request_id,
                    report.commit_sha,
                    report.test_set_ref,
                    report.total_cases,
                    report.passed,
                    report.failed,
                    report.skipped,
                    report.pass_rate,
                    report.result.value,
                    report.status.value,
                    json.dumps([self._execution_to_dict(e) for e in report.failure_details]),
                    report.blocker_count,
                    report.critical_count,
                    report.flaky_count,
                    report.started_at.isoformat(),
                    report.completed_at.isoformat(),
                    report.duration_seconds,
                    report.log_path,
                    report.evidence_dir,
                    report.report_html_path,
                )
            )

            for execution in report.failure_details:
                conn.execute(
                    """
                    INSERT INTO test_executions (
                        smoke_run_id, test_id, test_name, priority, status,
                        severity, duration_ms, error_message, retry_attempts,
                        evidence_path, is_flaky
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report.smoke_run_id,
                        execution.test_id,
                        execution.test_name,
                        execution.priority,
                        execution.status,
                        execution.severity.value if execution.severity else None,
                        execution.duration_ms,
                        execution.error_message,
                        execution.retry_attempts,
                        execution.evidence_path,
                        execution.is_flaky,
                    )
                )

    def get_gate_report(self, smoke_run_id: str) -> Optional[SmokeGateReport]:
        """获取 Gate 执行报告。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM gate_reports WHERE smoke_run_id = ?",
                (smoke_run_id,)
            ).fetchone()

            if row is None:
                return None

            failure_details = json.loads(row["failure_details"]) if row["failure_details"] else []

            return SmokeGateReport(
                smoke_run_id=row["smoke_run_id"],
                merge_request_id=row["merge_request_id"],
                commit_sha=row["commit_sha"],
                test_set_ref=row["test_set_ref"],
                total_cases=row["total_cases"],
                passed=row["passed"],
                failed=row["failed"],
                skipped=row["skipped"],
                pass_rate=row["pass_rate"],
                result=GateResult(row["result"]),
                status=SmokeGateStatus(row["status"]),
                failure_details=[self._dict_to_execution(d) for d in failure_details],
                blocker_count=row["blocker_count"],
                critical_count=row["critical_count"],
                flaky_count=row["flaky_count"],
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]),
                duration_seconds=row["duration_seconds"],
                log_path=row["log_path"],
                evidence_dir=row["evidence_dir"],
                report_html_path=row["report_html_path"],
            )

    def get_latest_report(self, merge_request_id: str) -> Optional[SmokeGateReport]:
        """获取 MR 的最新执行报告。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM gate_reports
                WHERE merge_request_id = ?
                ORDER BY completed_at DESC
                LIMIT 1
                """,
                (merge_request_id,)
            ).fetchone()

            if row is None:
                return None

            failure_details = json.loads(row["failure_details"]) if row["failure_details"] else []

            return SmokeGateReport(
                smoke_run_id=row["smoke_run_id"],
                merge_request_id=row["merge_request_id"],
                commit_sha=row["commit_sha"],
                test_set_ref=row["test_set_ref"],
                total_cases=row["total_cases"],
                passed=row["passed"],
                failed=row["failed"],
                skipped=row["skipped"],
                pass_rate=row["pass_rate"],
                result=GateResult(row["result"]),
                status=SmokeGateStatus(row["status"]),
                failure_details=[self._dict_to_execution(d) for d in failure_details],
                blocker_count=row["blocker_count"],
                critical_count=row["critical_count"],
                flaky_count=row["flaky_count"],
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]),
                duration_seconds=row["duration_seconds"],
                log_path=row["log_path"],
                evidence_dir=row["evidence_dir"],
                report_html_path=row["report_html_path"],
            )

    # === Merge Gate State 操作 ===

    def create_merge_gate_state(self, state: MergeGateState) -> None:
        """创建 Merge Gate 状态记录。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO merge_gate_states (
                    merge_request_id, branch_name, target_branch, current_commit_sha,
                    gate_status, gate_result, last_run_id, last_run_at, run_count,
                    blocker_issues, is_mergeable, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.merge_request_id,
                    state.branch_name,
                    state.target_branch,
                    state.current_commit_sha,
                    state.gate_status.value,
                    state.gate_result.value if state.gate_result else None,
                    state.last_run_id,
                    state.last_run_at.isoformat() if state.last_run_at else None,
                    state.run_count,
                    json.dumps(state.blocker_issues),
                    state.is_mergeable,
                    state.created_at.isoformat(),
                    state.updated_at.isoformat(),
                )
            )

    def update_merge_gate_state(self, state: MergeGateState) -> bool:
        """更新 Merge Gate 状态记录。"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                """
                UPDATE merge_gate_states SET
                    gate_status = ?,
                    gate_result = ?,
                    last_run_id = ?,
                    last_run_at = ?,
                    run_count = ?,
                    blocker_issues = ?,
                    is_mergeable = ?,
                    updated_at = ?,
                    version = version + 1
                WHERE merge_request_id = ?
                """,
                (
                    state.gate_status.value,
                    state.gate_result.value if state.gate_result else None,
                    state.last_run_id,
                    state.last_run_at.isoformat() if state.last_run_at else None,
                    state.run_count,
                    json.dumps(state.blocker_issues),
                    state.is_mergeable,
                    state.updated_at.isoformat(),
                    state.merge_request_id,
                )
            )
            return result.rowcount > 0

    def get_merge_gate_state(self, merge_request_id: str) -> Optional[MergeGateState]:
        """获取 Merge Gate 状态记录。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM merge_gate_states WHERE merge_request_id = ?",
                (merge_request_id,)
            ).fetchone()

            if row is None:
                return None

            return MergeGateState(
                merge_request_id=row["merge_request_id"],
                branch_name=row["branch_name"],
                target_branch=row["target_branch"],
                current_commit_sha=row["current_commit_sha"],
                gate_status=SmokeGateStatus(row["gate_status"]),
                gate_result=GateResult(row["gate_result"]) if row["gate_result"] else None,
                last_run_id=row["last_run_id"],
                last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
                run_count=row["run_count"],
                blocker_issues=json.loads(row["blocker_issues"]) if row["blocker_issues"] else [],
                is_mergeable=row["is_mergeable"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    # === 辅助方法 ===

    def _execution_to_dict(self, execution: TestExecutionRecord) -> Dict[str, Any]:
        """将 TestExecutionRecord 转换为字典。"""
        return {
            "test_id": execution.test_id,
            "test_name": execution.test_name,
            "priority": execution.priority,
            "status": execution.status,
            "severity": execution.severity.value if execution.severity else None,
            "duration_ms": execution.duration_ms,
            "error_message": execution.error_message,
            "retry_attempts": execution.retry_attempts,
            "evidence_path": execution.evidence_path,
            "is_flaky": execution.is_flaky,
        }

    def _dict_to_execution(self, data: Dict[str, Any]) -> TestExecutionRecord:
        """将字典转换为 TestExecutionRecord。"""
        return TestExecutionRecord(
            test_id=data["test_id"],
            test_name=data["test_name"],
            priority=data["priority"],
            status=data["status"],
            severity=FailureSeverity(data["severity"]) if data["severity"] else None,
            duration_ms=data["duration_ms"],
            error_message=data["error_message"],
            retry_attempts=data.get("retry_attempts", 0),
            evidence_path=data.get("evidence_path"),
            is_flaky=data.get("is_flaky", False),
        )
