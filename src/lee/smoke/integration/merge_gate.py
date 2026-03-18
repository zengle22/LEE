"""
Merge Gate Integrator
=====================
SRC-058 Dev Smoke Gate - Merge 门禁集成
"""

from datetime import datetime
from typing import List, Optional

from ..models import (
    MergeGateState,
    SmokeGateStatus,
    GateResult,
    SmokeGateReport,
    FailureSeverity,
)
from ..storage.store import SmokeStore


class MergeGateIntegrator:
    """
    Merge Gate 集成器，负责与 Git 平台集成。
    """

    def __init__(self, store: Optional[SmokeStore] = None):
        """
        初始化集成器。

        Args:
            store: 数据存储实例
        """
        self.store = store or SmokeStore()

    async def check_merge_eligibility(
        self,
        merge_request_id: str
    ) -> MergeGateState:
        """
        检查 MR 是否满足 merge 条件。

        Args:
            merge_request_id: Merge 请求 ID

        Returns:
            MergeGateState 包含可合并性判定
        """
        # 获取或创建状态
        state = self.store.get_merge_gate_state(merge_request_id)

        if state is None:
            # 没有状态记录，返回不可合并
            state = MergeGateState(
                merge_request_id=merge_request_id,
                branch_name="",
                target_branch="main",
                current_commit_sha="",
                gate_status=SmokeGateStatus.NOT_STARTED,
                is_mergeable=False,
                blocker_issues=["Smoke Gate has not been executed"]
            )

        return state

    async def block_merge(
        self,
        merge_request_id: str,
        reason: str
    ) -> None:
        """
        阻塞 merge 请求。

        Args:
            merge_request_id: Merge 请求 ID
            reason: 阻塞原因

        Raises:
            ValueError: 如果原因为空
        """
        if not reason:
            raise ValueError("reason cannot be empty")

        # 获取或创建状态
        state = self.store.get_merge_gate_state(merge_request_id)

        if state is None:
            state = MergeGateState(
                merge_request_id=merge_request_id,
                branch_name="",
                target_branch="main",
                current_commit_sha="",
                gate_status=SmokeGateStatus.FAILED,
                gate_result=GateResult.BLOCK_MERGE,
                is_mergeable=False,
                blocker_issues=[reason]
            )
            self.store.create_merge_gate_state(state)
        else:
            if reason not in state.blocker_issues:
                state.blocker_issues.append(reason)
            state.is_mergeable = False
            state.gate_result = GateResult.BLOCK_MERGE
            state.updated_at = datetime.now()
            self.store.update_merge_gate_state(state)

        # 实际项目中需要调用 Git 平台 API 设置阻塞状态
        # self._update_git_platform_status(merge_request_id, blocked=True, reason=reason)

    async def allow_merge(self, merge_request_id: str) -> None:
        """
        允许 merge 请求。

        Args:
            merge_request_id: Merge 请求 ID
        """
        # 获取或创建状态
        state = self.store.get_merge_gate_state(merge_request_id)

        if state is None:
            state = MergeGateState(
                merge_request_id=merge_request_id,
                branch_name="",
                target_branch="main",
                current_commit_sha="",
                gate_status=SmokeGateStatus.PASSED,
                gate_result=GateResult.ALLOW_MERGE,
                is_mergeable=True,
                blocker_issues=[]
            )
            self.store.create_merge_gate_state(state)
        else:
            state.is_mergeable = True
            state.gate_result = GateResult.ALLOW_MERGE
            state.blocker_issues = []
            state.updated_at = datetime.now()
            self.store.update_merge_gate_state(state)

        # 实际项目中需要调用 Git 平台 API 清除阻塞状态
        # self._update_git_platform_status(merge_request_id, blocked=False)

    async def update_gate_status_display(
        self,
        merge_request_id: str,
        status: SmokeGateStatus
    ) -> None:
        """
        更新 Gate 状态可视化显示。

        Args:
            merge_request_id: Merge 请求 ID
            status: Gate 状态
        """
        # 实际项目中需要更新 Git 平台的 MR 页面状态显示
        # 例如添加 label、badge 或 status check
        pass

    async def update_from_report(
        self,
        merge_request_id: str,
        report: SmokeGateReport
    ) -> MergeGateState:
        """
        从报告更新 Merge Gate 状态。

        Args:
            merge_request_id: Merge 请求 ID
            report: Smoke Gate 报告

        Returns:
            更新后的 MergeGateState
        """
        state = self.store.get_merge_gate_state(merge_request_id)

        if state is None:
            state = MergeGateState(
                merge_request_id=merge_request_id,
                branch_name="",
                target_branch="main",
                current_commit_sha=report.commit_sha,
                gate_status=report.status,
                gate_result=report.result,
                last_run_id=report.smoke_run_id,
                last_run_at=report.completed_at,
                run_count=1
            )
        else:
            state.update_from_report(report)

        # 保存状态
        if state.run_count == 1:
            self.store.create_merge_gate_state(state)
        else:
            self.store.update_merge_gate_state(state)

        # 根据结果更新 merge 状态
        if report.result == GateResult.BLOCK_MERGE:
            blocker_messages = [
                f"{e.test_name}: {e.error_message}"
                for e in report.failure_details
                if e.severity == FailureSeverity.BLOCKER
            ]
            for msg in blocker_messages:
                await self.block_merge(merge_request_id, msg)
        elif report.result == GateResult.ALLOW_MERGE:
            await self.allow_merge(merge_request_id)

        return state

    def is_mergeable(self, state: MergeGateState) -> bool:
        """
        判断是否允许 merge。

        Args:
            state: Merge Gate 状态

        Returns:
            bool
        """
        return (
            state.gate_status == SmokeGateStatus.PASSED and
            state.gate_result == GateResult.ALLOW_MERGE and
            len(state.blocker_issues) == 0
        )
