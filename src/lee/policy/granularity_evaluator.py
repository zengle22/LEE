"""Bugfix granularity control for canonical bugfix delivery workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GranularityDecision:
    """Decision returned by the bugfix granularity evaluator."""

    mode: str
    allowed: bool
    reason: str
    checks: Dict[str, bool] = field(default_factory=dict)
    split_required: bool = False


class GranularityPolicyEvaluator:
    """Evaluate whether bugfix execution should run as single or batch mode."""

    FIVE_SAME_FIELDS = (
        "same_module",
        "same_root_cause_class",
        "same_fix_strategy",
        "same_verification_surface",
        "same_release_window",
    )

    def evaluate(
        self,
        *,
        bug_ids: List[str],
        batch_mode: bool = False,
        batch_context: Dict[str, Any] | None = None,
    ) -> GranularityDecision:
        """Evaluate bugfix granularity for a prospective workflow run."""
        batch_context = batch_context or {}
        normalized_bug_ids = [bug_id for bug_id in bug_ids if bug_id]

        if not normalized_bug_ids:
            return GranularityDecision(
                mode="invalid",
                allowed=False,
                reason="bug_ids_required",
            )

        if not batch_mode:
            if len(normalized_bug_ids) != 1:
                return GranularityDecision(
                    mode="single_bug",
                    allowed=False,
                    split_required=True,
                    reason="single_bug_mode_requires_exactly_one_bug",
                )
            return GranularityDecision(
                mode="single_bug",
                allowed=True,
                reason="default_single_bug_rule",
            )

        if len(normalized_bug_ids) < 2:
            return GranularityDecision(
                mode="batch",
                allowed=False,
                reason="batch_mode_requires_multiple_bugs",
            )

        checks = {
            field_name: bool(batch_context.get(field_name))
            for field_name in self.FIVE_SAME_FIELDS
        }
        if all(checks.values()):
            return GranularityDecision(
                mode="batch",
                allowed=True,
                reason="five_same_rule_passed",
                checks=checks,
            )

        return GranularityDecision(
            mode="batch",
            allowed=False,
            split_required=True,
            reason="five_same_rule_failed",
            checks=checks,
        )
