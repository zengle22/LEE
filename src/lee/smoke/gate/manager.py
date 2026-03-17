"""
Smoke Gate Manager
==================
SRC-058 Dev Smoke Gate - Gate 生命周期管理
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import (
    SmokeGateContext,
    SmokeGateReport,
    SmokeGateStatus,
    GateResult,
    SmokeGateConfig,
)
from ..executor import SmokeExecutor
from ..storage.store import SmokeStore


class SmokeGateManager:
    """
    Smoke Gate 管理器，负责 Gate 生命周期管理。
    """

    def __init__(self, store: Optional[SmokeStore] = None):
        """
        初始化管理器。

        Args:
            store: 数据存储实例
        """
        self.store = store or SmokeStore()

    async def create_gate(
        self,
        merge_request_id: str,
        config: SmokeGateConfig
    ) -> SmokeGateContext:
        """
        创建 Smoke Gate 实例。

        Args:
            merge_request_id: Merge 请求 ID
            config: Smoke Gate 配置

        Returns:
            SmokeGateContext

        Raises:
            ValueError: 如果 merge_request_id 无效
        """
        if not merge_request_id:
            raise ValueError("merge_request_id cannot be empty")

        # 从配置创建上下文
        context = SmokeGateContext(
            merge_request_id=merge_request_id,
            branch_name="",  # 需要从 Git 平台获取
            target_branch="main",
            commit_sha="",  # 需要从 Git 平台获取
            test_set_ref=config.test_set_ref,
            priority_filter=config.priority_filter,
            retry_count=config.retry_count,
            timeout_minutes=config.timeout_minutes,
            status=SmokeGateStatus.NOT_STARTED,
        )

        # 持久化
        self.store.create_gate_context(context)

        return context

    async def start_execution(self, context: SmokeGateContext) -> SmokeGateContext:
        """
        启动 Smoke 测试执行。

        Args:
            context: Gate 上下文

        Returns:
            更新后的 context

        Raises:
            RuntimeError: 如果状态不是 NOT_STARTED
        """
        if context.status != SmokeGateStatus.NOT_STARTED:
            raise RuntimeError(f"Cannot start execution from status: {context.status}")

        context.start_execution()
        self.store.update_gate_context(context)

        return context

    async def get_gate_status(self, merge_request_id: str) -> Optional[SmokeGateStatus]:
        """
        获取指定 MR 的 Gate 状态。

        Args:
            merge_request_id: Merge 请求 ID

        Returns:
            SmokeGateStatus 或 None
        """
        context = self.store.get_gate_context(merge_request_id)
        if context is None:
            return None
        return context.status

    async def get_gate_report(
        self,
        smoke_run_id: str
    ) -> Optional[SmokeGateReport]:
        """
        获取指定执行的报告。

        Args:
            smoke_run_id: Smoke 执行 ID

        Returns:
            SmokeGateReport 或 None
        """
        return self.store.get_gate_report(smoke_run_id)

    async def get_latest_report(
        self,
        merge_request_id: str
    ) -> Optional[SmokeGateReport]:
        """
        获取 MR 的最新执行报告。

        Args:
            merge_request_id: Merge 请求 ID

        Returns:
            SmokeGateReport 或 None
        """
        return self.store.get_latest_report(merge_request_id)

    async def execute_smoke(
        self,
        context: SmokeGateContext,
        test_cases: List[Dict[str, Any]]
    ) -> SmokeGateReport:
        """
        执行 Smoke 测试并更新状态。

        Args:
            context: Gate 上下文
            test_cases: 测试用例列表

        Returns:
            SmokeGateReport
        """
        # 启动执行
        await self.start_execution(context)

        # 创建执行器并执行
        config = SmokeGateConfig(
            test_set_ref=context.test_set_ref,
            priority_filter=context.priority_filter,
            retry_count=context.retry_count,
            timeout_minutes=context.timeout_minutes
        )
        executor = SmokeExecutor(config)
        report = await executor.execute(context, test_cases)

        # 更新 context
        context.complete_execution(report.result)
        self.store.update_gate_context(context)

        # 保存报告
        self.store.create_gate_report(report)

        return report

    async def get_or_create_context(
        self,
        merge_request_id: str,
        config: SmokeGateConfig
    ) -> SmokeGateContext:
        """
        获取或创建 Gate 上下文。

        Args:
            merge_request_id: Merge 请求 ID
            config: Smoke Gate 配置

        Returns:
            SmokeGateContext
        """
        context = self.store.get_gate_context(merge_request_id)
        if context is None:
            context = await self.create_gate(merge_request_id, config)
        return context
