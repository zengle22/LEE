"""
Unit Tests for Decision Engine

Tests for:
- End-to-end decision pipeline
- Intent → Permission → Params → Action flow
- Fallback strategies
- Error handling and recovery
- Decision history and metrics
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from lee.orchestrator.execution.pm_agent.decision_engine import DecisionEngine, DecisionEngineBuilder
from lee.orchestrator.execution.pm_agent.intent_classifier import IntentClassifier
from lee.orchestrator.execution.pm_agent.param_mapper import ParamMapper
from lee.orchestrator.execution.pm_agent.permission_checker import PermissionChecker
from lee.orchestrator.execution.pm_agent.exceptions import PermissionDeniedError
from lee.orchestrator.execution.pm_agent.models import (
    Intent,
    IntentType,
    WorkflowParams,
    Decision,
    ConversationContext,
)


@pytest.fixture
def mock_components():
    """Create mock components"""
    intent_classifier = Mock(spec=IntentClassifier)
    param_mapper = Mock(spec=ParamMapper)
    permission_checker = Mock(spec=PermissionChecker)

    # Setup mock behaviors
    intent_classifier.classify = AsyncMock(
        return_value=Intent(
            type=IntentType.QUERY_STATUS,
            confidence=0.9,
            reasoning="User wants to know status"
        )
    )

    permission_checker.check = Mock(return_value=True)

    param_mapper.map_params = AsyncMock(
        return_value=WorkflowParams(
            workflow_ref="workflow_123",
            step_id=None,
            confidence=0.8
        )
    )

    return {
        'intent_classifier': intent_classifier,
        'param_mapper': param_mapper,
        'permission_checker': permission_checker,
    }


@pytest.fixture
def decision_engine(mock_components):
    """Create a Decision Engine instance"""
    return DecisionEngine(
        intent_classifier=mock_components['intent_classifier'],
        param_mapper=mock_components['param_mapper'],
        permission_checker=mock_components['permission_checker'],
        enable_fallback=True
    )


@pytest.fixture
def sample_context():
    """Create a sample context"""
    return ConversationContext(
        session_id="test_session",
        department="dev",
        current_workflow_id="workflow_123",
        history=[]
    )


class TestDecisionEngineInitialization:
    """Test Decision Engine initialization"""

    def test_init_with_all_components(self, mock_components):
        """Test initialization with all components"""
        engine = DecisionEngine(
            intent_classifier=mock_components['intent_classifier'],
            param_mapper=mock_components['param_mapper'],
            permission_checker=mock_components['permission_checker']
        )

        assert engine.intent_classifier == mock_components['intent_classifier']
        assert engine.param_mapper == mock_components['param_mapper']
        assert engine.permission_checker == mock_components['permission_checker']
        assert engine.enable_fallback is True

    def test_init_without_fallback(self, mock_components):
        """Test initialization with fallback disabled"""
        engine = DecisionEngine(
            intent_classifier=mock_components['intent_classifier'],
            param_mapper=mock_components['param_mapper'],
            permission_checker=mock_components['permission_checker'],
            enable_fallback=False
        )

        assert engine.enable_fallback is False


class TestDecisionPipeline:
    """Test the complete decision pipeline"""

    @pytest.mark.asyncio
    async def test_successful_decision(self, decision_engine, sample_context):
        """Test successful decision through all pipeline stages"""
        decision = await decision_engine.decide("当前状态", sample_context)

        assert isinstance(decision, Decision)
        assert decision.intent.type == IntentType.QUERY_STATUS
        assert decision.allowed is True
        assert decision.action == "get_state"
        assert decision.params.workflow_ref == "workflow_123"
        assert decision_engine._successful_decisions == 1

    @pytest.mark.asyncio
    async def test_decision_with_permission_denied(self, decision_engine, mock_components, sample_context):
        """Test decision when permission is denied"""
        # Mock permission checker to deny
        mock_components['permission_checker'].check = Mock(
            side_effect=PermissionDeniedError("Permission denied", action="execute_step")
        )

        decision = await decision_engine.decide("运行命令", sample_context)

        assert decision.allowed is False
        assert decision.denial_reason is not None
        assert decision_engine._failed_decisions == 1

    @pytest.mark.asyncio
    async def test_decision_with_unknown_intent(self, decision_engine, mock_components, sample_context):
        """Test decision when intent is unknown"""
        # Mock to return unknown intent
        mock_components['intent_classifier'].classify = AsyncMock(
            return_value=Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="Unknown intent"
            )
        )

        # With fallback enabled
        decision = await decision_engine.decide("xyzabc", sample_context)

        # Should use fallback inference
        assert isinstance(decision, Decision)

    @pytest.mark.asyncio
    async def test_decision_with_parameter_extraction_failure(self, decision_engine, mock_components, sample_context):
        """Test decision when parameter extraction fails"""
        # Mock param mapper to fail
        mock_components['param_mapper'].map_params = AsyncMock(
            side_effect=Exception("Extraction failed")
        )

        # With fallback enabled
        decision = await decision_engine.decide("运行命令", sample_context)

        # Should use fallback parameters
        assert isinstance(decision, Decision)
        assert decision_engine._fallback_count >= 1


class TestIntentToActionMapping:
    """Test intent to action mapping"""

    def test_map_query_status(self, decision_engine):
        """Test mapping QUERY_STATUS to action"""
        params = WorkflowParams(workflow_ref="workflow_123")
        action = decision_engine._map_intent_to_action(IntentType.QUERY_STATUS, params)
        assert action == "get_state"

    def test_map_execute_step_with_step_id(self, decision_engine):
        """Test mapping EXECUTE_STEP with specific step"""
        params = WorkflowParams(step_id="step_123")
        action = decision_engine._map_intent_to_action(IntentType.EXECUTE_STEP, params)
        assert action == "run_step"

    def test_map_execute_step_without_step_id(self, decision_engine):
        """Test mapping EXECUTE_STEP without specific step"""
        params = WorkflowParams()
        action = decision_engine._map_intent_to_action(IntentType.EXECUTE_STEP, params)
        assert action == "next_step"

    def test_map_approve_gate(self, decision_engine):
        """Test mapping APPROVE_GATE to action"""
        params = WorkflowParams(gate_id="gate_123")
        action = decision_engine._map_intent_to_action(IntentType.APPROVE_GATE, params)
        assert action == "approve_gate"

    def test_map_reject_gate(self, decision_engine):
        """Test mapping REJECT_GATE to action"""
        params = WorkflowParams(gate_id="gate_123")
        action = decision_engine._map_intent_to_action(IntentType.REJECT_GATE, params)
        assert action == "reject_gate"

    def test_map_show_help(self, decision_engine):
        """Test mapping SHOW_HELP to action"""
        params = WorkflowParams()
        action = decision_engine._map_intent_to_action(IntentType.SHOW_HELP, params)
        assert action == "show_help"

    def test_map_list_gates(self, decision_engine):
        """Test mapping LIST_GATES to action"""
        params = WorkflowParams()
        action = decision_engine._map_intent_to_action(IntentType.LIST_GATES, params)
        assert action == "list_gates"

    def test_map_pause_workflow(self, decision_engine):
        """Test mapping PAUSE_WORKFLOW to action"""
        params = WorkflowParams(workflow_ref="wf_task_1")
        action = decision_engine._map_intent_to_action(IntentType.PAUSE_WORKFLOW, params)
        assert action == "pause_workflow"

    def test_map_resume_workflow(self, decision_engine):
        """Test mapping RESUME_WORKFLOW to action"""
        params = WorkflowParams(workflow_ref="wf_task_1")
        action = decision_engine._map_intent_to_action(IntentType.RESUME_WORKFLOW, params)
        assert action == "resume_workflow"

    def test_map_revise_gate(self, decision_engine):
        """Test mapping REVISE_GATE to action"""
        params = WorkflowParams(gate_id="gate_123")
        action = decision_engine._map_intent_to_action(IntentType.REVISE_GATE, params)
        assert action == "revise_gate"

    def test_map_flag_gate(self, decision_engine):
        """Test mapping FLAG_GATE to action"""
        params = WorkflowParams(gate_id="gate_123")
        action = decision_engine._map_intent_to_action(IntentType.FLAG_GATE, params)
        assert action == "flag_gate"

    def test_map_unknown(self, decision_engine):
        """Test mapping UNKNOWN intent"""
        params = WorkflowParams()
        action = decision_engine._map_intent_to_action(IntentType.UNKNOWN, params)
        assert action == "unknown"


class TestFallbackStrategies:
    """Test fallback strategies"""

    def test_fallback_intent_inference_status(self, decision_engine):
        """Test fallback inference for status queries"""
        intent = decision_engine._fallback_intent_inference("怎么样了", None)
        assert intent.type == IntentType.QUERY_STATUS
        assert "fallback" in intent.reasoning.lower()

    def test_fallback_intent_inference_help(self, decision_engine):
        """Test fallback inference for help requests"""
        intent = decision_engine._fallback_intent_inference("帮助", None)
        assert intent.type == IntentType.SHOW_HELP

    def test_fallback_intent_inference_unknown(self, decision_engine):
        """Test fallback inference for unknown input"""
        intent = decision_engine._fallback_intent_inference("xyzabc123", None)
        assert intent.type == IntentType.UNKNOWN
        assert intent.confidence == 0.0

    def test_fallback_parameter_extraction_for_execute(self, decision_engine):
        """Test fallback parameter extraction for execute step"""
        intent = Intent(type=IntentType.EXECUTE_STEP, confidence=0.9, reasoning="")
        context = ConversationContext(
            session_id="test",
            current_workflow_id="workflow_123"
        )

        params = decision_engine._fallback_parameter_extraction(intent, context)
        assert params.workflow_ref == "workflow_123"
        assert params.step_id is None  # Auto-select

    def test_fallback_parameter_extraction_for_query(self, decision_engine):
        """Test fallback parameter extraction for query status"""
        intent = Intent(type=IntentType.QUERY_STATUS, confidence=0.9, reasoning="")

        params = decision_engine._fallback_parameter_extraction(intent, None)
        assert params.workflow_ref is None
        assert params.confidence == 1.0


class TestDecisionRecording:
    """Test decision history recording"""

    def test_record_decision(self, decision_engine):
        """Test recording a decision to history"""
        decision = Decision(
            intent=Intent(type=IntentType.QUERY_STATUS, confidence=0.9, reasoning=""),
            params=WorkflowParams(),
            action="get_state",
            allowed=True
        )

        decision_engine._record_decision(decision)

        assert len(decision_engine._decision_history) == 1
        assert decision_engine._decision_history[0]['action'] == "get_state"
        assert decision_engine._decision_history[0]['allowed'] is True

    def test_decision_history_limit(self, decision_engine):
        """Test that decision history is limited to 1000 entries"""
        # Add more than 1000 decisions
        for i in range(1100):
            decision = Decision(
                intent=Intent(type=IntentType.QUERY_STATUS, confidence=0.9, reasoning=""),
                params=WorkflowParams(),
                action="get_state",
                allowed=True
            )
            decision_engine._record_decision(decision)

        # Should keep only last 1000
        assert len(decision_engine._decision_history) == 1000

    def test_get_decision_history(self, decision_engine):
        """Test getting decision history"""
        # Add some decisions
        for i in range(10):
            decision = Decision(
                intent=Intent(type=IntentType.QUERY_STATUS, confidence=0.9, reasoning=""),
                params=WorkflowParams(),
                action="get_state",
                allowed=True
            )
            decision_engine._record_decision(decision)

        history = decision_engine.get_decision_history(limit=5)
        assert len(history) == 5


class TestMetrics:
    """Test metrics collection"""

    def test_initial_metrics(self, decision_engine):
        """Test initial metrics"""
        metrics = decision_engine.get_metrics()
        assert metrics['total_decisions'] == 0
        assert metrics['successful_decisions'] == 0
        assert metrics['failed_decisions'] == 0
        assert metrics['fallback_count'] == 0

    @pytest.mark.asyncio
    async def test_metrics_after_decisions(self, decision_engine, sample_context):
        """Test metrics after making decisions"""
        await decision_engine.decide("当前状态", sample_context)
        await decision_engine.decide("随便说", sample_context)  # Might use fallback

        metrics = decision_engine.get_metrics()
        assert metrics['total_decisions'] == 2
        assert metrics['successful_decisions'] >= 1

    def test_metrics_reset(self, decision_engine):
        """Test metrics reset"""
        decision_engine._total_decisions = 10
        decision_engine._successful_decisions = 8
        decision_engine._failed_decisions = 2
        decision_engine._fallback_count = 3

        decision_engine.reset_metrics()

        metrics = decision_engine.get_metrics()
        assert metrics['total_decisions'] == 0
        assert metrics['successful_decisions'] == 0
        assert metrics['failed_decisions'] == 0
        assert metrics['fallback_count'] == 0


class TestDecisionEngineBuilder:
    """Test Decision Engine Builder"""

    def test_builder_with_all_components(self, mock_components):
        """Test building with all components"""
        builder = DecisionEngineBuilder()
        engine = builder\
            .with_intent_classifier(mock_components['intent_classifier'])\
            .with_param_mapper(mock_components['param_mapper'])\
            .with_permission_checker(mock_components['permission_checker'])\
            .with_fallback(True)\
            .build()

        assert engine.intent_classifier == mock_components['intent_classifier']
        assert engine.param_mapper == mock_components['param_mapper']
        assert engine.permission_checker == mock_components['permission_checker']
        assert engine.enable_fallback is True

    def test_builder_with_fallback_disabled(self, mock_components):
        """Test building with fallback disabled"""
        builder = DecisionEngineBuilder()
        engine = builder\
            .with_intent_classifier(mock_components['intent_classifier'])\
            .with_param_mapper(mock_components['param_mapper'])\
            .with_permission_checker(mock_components['permission_checker'])\
            .with_fallback(False)\
            .build()

        assert engine.enable_fallback is False

    def test_builder_missing_components(self):
        """Test builder with missing components"""
        builder = DecisionEngineBuilder()
        builder.with_intent_classifier(Mock(spec=IntentClassifier))
        # Missing other components

        with pytest.raises(ValueError, match="All components"):
            builder.build()


class TestErrorHandling:
    """Test error handling in decision pipeline"""

    @pytest.mark.asyncio
    async def test_intent_classification_error(self, decision_engine, mock_components, sample_context):
        """Test handling of intent classification error"""
        mock_components['intent_classifier'].classify = AsyncMock(
            side_effect=Exception("Classification error")
        )

        with pytest.raises(Exception):
            await decision_engine.decide("test input", sample_context)

        assert decision_engine._failed_decisions == 1

    @pytest.mark.asyncio
    async def test_permission_check_error_without_fallback(self, decision_engine, mock_components, sample_context):
        """Test permission check error when fallback disabled"""
        decision_engine.enable_fallback = False

        mock_components['permission_checker'].check = Mock(
            side_effect=Exception("Permission error")
        )

        with pytest.raises(Exception):
            await decision_engine.decide("test input", sample_context)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
