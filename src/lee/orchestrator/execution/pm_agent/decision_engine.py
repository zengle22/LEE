"""
PM Agent Decision Engine

Orchestrates Intent Classifier, Param Mapper, and Permission Checker
to make workflow execution decisions from natural language input.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import asdict

from .models import (
    Intent,
    IntentType,
    WorkflowParams,
    Decision,
    ConversationContext,
)
from .intent_classifier import IntentClassifier
from .param_mapper import ParamMapper
from .permission_checker import PermissionChecker
from .exceptions import (
    IntentClassificationError,
    ParameterExtractionError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Decision Engine - Orchestration Layer

    Coordinates the decision-making pipeline:
    1. Intent Classification (Intent Classifier)
    2. Permission Checking (Permission Checker)
    3. Parameter Mapping (Param Mapper)
    4. Decision Construction

    Ensures all security and validation checks before
    returning an executable decision.
    """

    def __init__(
        self,
        intent_classifier: IntentClassifier,
        param_mapper: ParamMapper,
        permission_checker: PermissionChecker,
        enable_fallback: bool = True
    ):
        """
        Initialize Decision Engine

        Args:
            intent_classifier: Intent classifier component
            param_mapper: Parameter mapper component
            permission_checker: Permission checker component
            enable_fallback: Enable fallback strategies on errors
        """
        self.intent_classifier = intent_classifier
        self.param_mapper = param_mapper
        self.permission_checker = permission_checker
        self.enable_fallback = enable_fallback

        # Decision history for analytics
        self._decision_history: list = []

        # Metrics
        self._total_decisions = 0
        self._successful_decisions = 0
        self._failed_decisions = 0
        self._fallback_count = 0

    async def decide(
        self,
        user_input: str,
        context: Optional[ConversationContext] = None
    ) -> Decision:
        """
        Make a decision from user input

        Args:
            user_input: User's natural language input
            context: Optional conversation context

        Returns:
            Decision with intent, parameters, and action

        Raises:
            IntentClassificationError: If intent classification fails
            PermissionDeniedError: If permission is denied
            ParameterExtractionError: If parameter extraction fails
        """
        self._total_decisions += 1

        decision_start = datetime.now()

        try:
            # Phase 1: Classify Intent
            logger.info(f"Classifying intent for input: {user_input[:100]}...")
            intent = await self.intent_classifier.classify(user_input, context)

            if intent.type == IntentType.UNKNOWN:
                if self.enable_fallback:
                    # Fallback: Try to infer from context
                    intent = self._fallback_intent_inference(user_input, context)
                else:
                    raise IntentClassificationError(
                        "Unable to classify intent",
                        input_text=user_input
                    )

            logger.info(f"Intent classified: {intent.type.value} (confidence: {intent.confidence})")

            # Phase 2: Check Permissions
            logger.info("Checking permissions...")
            try:
                self.permission_checker.check(intent, context)
                permission_granted = True
                denial_reason = None
            except PermissionDeniedError as e:
                permission_granted = False
                denial_reason = str(e)
                logger.warning(f"Permission denied: {e}")

            # Phase 3: Map Parameters
            params = WorkflowParams()
            if permission_granted:
                logger.info("Extracting parameters...")
                try:
                    params = await self.param_mapper.map_params(user_input, intent, context)
                except Exception as e:
                    if self.enable_fallback:
                        logger.warning(f"Parameter extraction failed, using fallback: {e}")
                        params = self._fallback_parameter_extraction(intent, context)
                        self._fallback_count += 1
                    else:
                        if isinstance(e, ParameterExtractionError):
                            raise
                        raise ParameterExtractionError(
                            f"Failed to extract parameters: {e}",
                            intent=intent.type.value
                        ) from e

            # Phase 4: Map Intent to Action
            action = self._map_intent_to_action(intent.type, params)
            logger.debug(f"Mapped intent {intent.type.value} to action {action}")

            # Phase 5: Build Decision
            decision = Decision(
                intent=intent,
                params=params,
                action=action,
                allowed=permission_granted,
                denial_reason=denial_reason,
                timestamp=datetime.now(),
                metadata={
                    "processing_time_ms": (datetime.now() - decision_start).total_seconds() * 1000,
                    "fallback_used": self._fallback_count > self._total_decisions - 1,
                }
            )

            # Record decision
            self._record_decision(decision)

            if permission_granted:
                self._successful_decisions += 1
            else:
                self._failed_decisions += 1

            logger.info(f"Decision made: action={action}, allowed={permission_granted}")
            return decision

        except Exception as e:
            self._failed_decisions += 1
            logger.error(f"Decision making failed: {e}")
            raise

    def _map_intent_to_action(self, intent_type: IntentType, params: WorkflowParams) -> str:
        """
        Map intent type to Orchestrator API action

        Args:
            intent_type: Classified intent type
            params: Extracted parameters

        Returns:
            API action string
        """
        action_map = {
            IntentType.QUERY_STATUS: "get_state",
            IntentType.EXECUTE_STEP: "run_step" if params.step_id else "next_step",
            IntentType.LIST_WORKFLOWS: "list_workflows",
            IntentType.LIST_GATES: "list_gates",
            IntentType.APPROVE_GATE: "approve_gate",
            IntentType.REJECT_GATE: "reject_gate",
            IntentType.REVISE_GATE: "revise_gate",
            IntentType.FLAG_GATE: "flag_gate",
            IntentType.PAUSE_WORKFLOW: "pause_workflow",
            IntentType.RESUME_WORKFLOW: "resume_workflow",
            IntentType.CREATE_WORKFLOW: "create_workflow",
            IntentType.RUN_WORKFLOW: "run_workflow",
            IntentType.SHOW_HELP: "show_help",
            IntentType.UNKNOWN: "unknown",
        }

        return action_map.get(intent_type, "unknown")

    def _fallback_intent_inference(
        self,
        user_input: str,
        context: Optional[ConversationContext]
    ) -> Intent:
        """
        Fallback intent inference when classification fails

        Args:
            user_input: User input
            context: Conversation context

        Returns:
            Inferred intent
        """
        # Simple heuristics as fallback
        user_input_lower = user_input.lower().strip()

        # Check for common patterns
        if any(word in user_input_lower for word in ["状态", "status", "怎么样"]):
            return Intent(
                type=IntentType.QUERY_STATUS,
                confidence=0.4,
                reasoning="Fallback inference: Status query pattern detected"
            )

        if any(word in user_input_lower for word in ["帮助", "help", "怎么"]):
            return Intent(
                type=IntentType.SHOW_HELP,
                confidence=0.6,
                reasoning="Fallback inference: Help request pattern detected"
            )

        # Default to unknown
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            reasoning="Fallback inference: No pattern matched"
        )

    def _fallback_parameter_extraction(
        self,
        intent: Intent,
        context: Optional[ConversationContext]
    ) -> WorkflowParams:
        """
        Fallback parameter extraction when LLM extraction fails

        Args:
            intent: Classified intent
            context: Conversation context

        Returns:
            Default parameters
        """
        # For execute_step, try to use current workflow
        if intent.type == IntentType.EXECUTE_STEP and context:
            return WorkflowParams(
                workflow_ref=context.current_workflow_id,
                step_id=None,  # Auto-select next step
                confidence=0.5
            )

        # For query_status, no params needed
        if intent.type == IntentType.QUERY_STATUS:
            return WorkflowParams(confidence=1.0)

        # Default: empty params
        return WorkflowParams(confidence=0.3)

    def _record_decision(self, decision: Decision):
        """Record decision to history"""
        self._decision_history.append({
            'timestamp': decision.timestamp.isoformat(),
            'intent_type': decision.intent.type.value,
            'action': decision.action,
            'allowed': decision.allowed,
            'confidence': decision.intent.confidence,
        })

        # Keep only last 1000 decisions
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get decision engine metrics"""
        return {
            "total_decisions": self._total_decisions,
            "successful_decisions": self._successful_decisions,
            "failed_decisions": self._failed_decisions,
            "success_rate": (
                self._successful_decisions / self._total_decisions
                if self._total_decisions > 0 else 0
            ),
            "fallback_count": self._fallback_count,
            "fallback_rate": (
                self._fallback_count / self._total_decisions
                if self._total_decisions > 0 else 0
            ),
        }

    def get_decision_history(self, limit: int = 100) -> list:
        """Get recent decision history"""
        return self._decision_history[-limit:]

    def reset_metrics(self):
        """Reset decision engine metrics"""
        self._total_decisions = 0
        self._successful_decisions = 0
        self._failed_decisions = 0
        self._fallback_count = 0
        self._decision_history = []


class DecisionEngineBuilder:
    """Builder for creating Decision Engine with custom configuration"""

    def __init__(self):
        self.intent_classifier: Optional[IntentClassifier] = None
        self.param_mapper: Optional[ParamMapper] = None
        self.permission_checker: Optional[PermissionChecker] = None
        self.enable_fallback: bool = True

    def with_intent_classifier(self, classifier: IntentClassifier) -> "DecisionEngineBuilder":
        """Set intent classifier"""
        self.intent_classifier = classifier
        return self

    def with_param_mapper(self, mapper: ParamMapper) -> "DecisionEngineBuilder":
        """Set parameter mapper"""
        self.param_mapper = mapper
        return self

    def with_permission_checker(self, checker: PermissionChecker) -> "DecisionEngineBuilder":
        """Set permission checker"""
        self.permission_checker = checker
        return self

    def with_fallback(self, enabled: bool) -> "DecisionEngineBuilder":
        """Enable or disable fallback strategies"""
        self.enable_fallback = enabled
        return self

    def build(self) -> DecisionEngine:
        """Build Decision Engine"""
        if not all([self.intent_classifier, self.param_mapper, self.permission_checker]):
            raise ValueError("All components (classifier, mapper, checker) must be set")

        return DecisionEngine(
            intent_classifier=self.intent_classifier,
            param_mapper=self.param_mapper,
            permission_checker=self.permission_checker,
            enable_fallback=self.enable_fallback
        )
