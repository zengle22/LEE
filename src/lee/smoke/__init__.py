"""
Smoke Gate Package
==================
SRC-058 Dev Smoke Gate - Merge 门禁集成
"""

from .models import (
    SmokeGateStatus,
    GateResult,
    FailureSeverity,
    SmokeGateEvent,
    SmokeGateContext,
    TestExecutionRecord,
    SmokeGateReport,
    MergeGateState,
    SmokeGateConfig,
    SmokeGateEventPayload,
)
from .executor import SmokeExecutor
from .gate.manager import SmokeGateManager
from .integration.merge_gate import MergeGateIntegrator
from .hooks.pre_merge import PreMergeHook
from .storage import SmokeStore

__all__ = [
    # Enums
    "SmokeGateStatus",
    "GateResult",
    "FailureSeverity",
    "SmokeGateEvent",
    # Models
    "SmokeGateContext",
    "TestExecutionRecord",
    "SmokeGateReport",
    "MergeGateState",
    "SmokeGateConfig",
    "SmokeGateEventPayload",
    # Components
    "SmokeExecutor",
    "SmokeGateManager",
    "MergeGateIntegrator",
    "PreMergeHook",
    "SmokeStore",
]

__version__ = "1.0.0"
