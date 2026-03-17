"""
Pre-merge Git Hook
==================
SRC-058 Dev Smoke Gate - Pre-merge 拦截检查
"""

from typing import Optional

from ..models import SmokeGateStatus, GateResult
from ..storage.store import SmokeStore


class PreMergeHook:
    """
    Pre-merge Git Hook，在执行 merge 前拦截检查。
    """

    def __init__(self, store: Optional[SmokeStore] = None):
        """
        初始化 Hook。

        Args:
            store: 数据存储实例
        """
        self.store = store or SmokeStore()

    def execute(self, merge_request_id: str) -> bool:
        """
        执行 pre-merge 检查。

        Args:
            merge_request_id: Merge 请求 ID

        Returns:
            True: 允许 merge
            False: 阻塞 merge
        """
        # 获取 Gate 状态
        context = self.store.get_gate_context(merge_request_id)

        if context is None:
            # 没有执行过 Smoke Gate，阻塞 merge
            return False

        # 检查状态
        if context.status != SmokeGateStatus.PASSED:
            return False

        # 检查结果
        if context.result != GateResult.ALLOW_MERGE:
            return False

        # 获取最新报告检查 blocker
        report = self.store.get_latest_report(merge_request_id)
        if report is not None and report.blocker_count > 0:
            return False

        return True

    def get_block_message(self, merge_request_id: str) -> str:
        """
        获取 merge 阻塞原因消息。

        Args:
            merge_request_id: Merge 请求 ID

        Returns:
            包含 blocker 详情的消息
        """
        # 获取 Gate 状态
        context = self.store.get_gate_context(merge_request_id)

        if context is None:
            return (
                "Merge blocked: Smoke Gate has not been executed.\n"
                "Please wait for Smoke Gate to complete before merging."
            )

        if context.status == SmokeGateStatus.RUNNING:
            return (
                "Merge blocked: Smoke Gate is currently running.\n"
                "Please wait for Smoke Gate to complete before merging."
            )

        if context.status == SmokeGateStatus.FAILED:
            # 获取报告详情
            report = self.store.get_latest_report(merge_request_id)
            if report:
                blockers = [
                    f"- {e.test_name}: {e.error_message}"
                    for e in report.failure_details
                    if e.severity == "blocker"
                ]
                if blockers:
                    return (
                        "Merge blocked: Smoke Gate failed with blocker issues.\n\n"
                        "Blocker details:\n" + "\n".join(blockers) + "\n\n"
                        f"See report: {report.report_html_path}"
                    )
            return "Merge blocked: Smoke Gate failed. Please check the test report."

        if context.status == SmokeGateStatus.INVALID:
            return (
                "Merge blocked: Smoke Gate execution is invalid.\n"
                "Please check the execution environment and retry."
            )

        return "Merge blocked: Unknown reason. Please contact the maintainers."
