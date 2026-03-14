from __future__ import annotations

from typing import Any, Dict, Optional

from .pm_planner_builders import normalize_task_payload
from .pm_planner_postprocess import finalize_payload
from .pm_planner_task_context import PmPlannerContext


class PmPlannerTaskNormalizer:
    @staticmethod
    def normalize(
        *,
        runner_cls,
        step,
        workflow_id: str,
        business_output: Any,
        structured_payload: Any,
        instance_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        if getattr(step, "agent_id", "") != "agent.product.pm_planner":
            return business_output, structured_payload
        if not isinstance(business_output, dict):
            return business_output, structured_payload

        payload = (
            business_output.get("task_planning")
            if isinstance(business_output.get("task_planning"), dict)
            else business_output
        )
        if not isinstance(payload, dict):
            return business_output, structured_payload

        ctx = PmPlannerContext.from_instance(
            runner_cls=runner_cls,
            workflow_id=workflow_id,
            instance_data=instance_data,
        )
        normalized_business = normalize_task_payload(payload, ctx)
        return finalize_payload(normalized_business, structured_payload, ctx)
