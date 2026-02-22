"""
Unit Tests for Intent Classifier

Tests for:
- Rule-based pattern matching
- LLM fallback behavior
- Priority and conflict resolution
- Configuration loading
- Metrics collection
- Edge cases and error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from lee.orchestrator.execution.pm_agent.intent_classifier import IntentClassifier
from lee.orchestrator.execution.pm_agent.config import IntentClassifierConfig, IntentConfig, PatternConfig
from lee.orchestrator.execution.pm_agent.models import Intent, IntentType, ConversationContext


@pytest.fixture
def mock_config():
    """Create a mock configuration"""
    config = Mock(spec=IntentClassifierConfig)

    # Mock get_all_intents to return test intents
    config.get_all_intents = Mock(return_value={
        'query_status': IntentConfig(
            type=IntentType.QUERY_STATUS,
            patterns=[
                PatternConfig(regex=r'^(当前)?状态|status', priority=1, description='Status query'),
                PatternConfig(regex=r'^查看|显示|list', priority=2, description='List query'),
            ],
            llm_fallback=True,
            allowed_tools=['lee.workflow.status'],
            description='Query status'
        ),
        'execute_step': IntentConfig(
            type=IntentType.EXECUTE_STEP,
            patterns=[
                PatternConfig(regex=r'^(运行|执行|run)', priority=1, description='Execute'),
            ],
            llm_fallback=True,
            allowed_tools=['lee.workflow.run'],
            description='Execute step'
        ),
    })

    config.get_intent_config = Mock(side_effect=lambda intent_id, dept=None: config.get_all_intents().get(intent_id))

    return config


@pytest.fixture
def mock_llm_executor():
    """Create a mock LLM executor"""
    executor = Mock()
    executor.execute = AsyncMock(return_value={
        'status': 'completed',
        'generated_text': '{"intent_type": "query_status", "confidence": 0.8, "reasoning": "LLM classification"}',
    })
    return executor


@pytest.fixture
def intent_classifier(mock_config, mock_llm_executor):
    """Create an Intent Classifier instance"""
    return IntentClassifier(
        config=mock_config,
        llm_executor=mock_llm_executor,
        default_department=None
    )


class TestIntentClassifierInitialization:
    """Test Intent Classifier initialization"""

    def test_init_with_components(self, mock_config, mock_llm_executor):
        """Test initialization with all components"""
        classifier = IntentClassifier(mock_config, mock_llm_executor)
        assert classifier.config == mock_config
        assert classifier.llm == mock_llm_executor
        assert classifier._rule_match_count == 0
        assert classifier._llm_fallback_count == 0

    def test_pattern_compilation(self, intent_classifier):
        """Test that patterns are compiled correctly"""
        # Should have compiled patterns for configured intents
        assert 'query_status' in intent_classifier._compiled_patterns
        assert 'execute_step' in intent_classifier._compiled_patterns


class TestRuleBasedClassification:
    """Test rule-based intent classification"""

    @pytest.mark.asyncio
    async def test_status_query_pattern_match(self, intent_classifier):
        """Test status query pattern matching"""
        intent = await intent_classifier._rule_based_classification("当前状态")
        assert intent.type == IntentType.QUERY_STATUS
        assert intent.confidence == 0.9
        assert "matched pattern" in intent.reasoning.lower()

    @pytest.mark.asyncio
    async def test_execute_step_pattern_match(self, intent_classifier):
        """Test execute step pattern matching"""
        intent = await intent_classifier._rule_based_classification("运行下一步")
        assert intent.type == IntentType.EXECUTE_STEP
        assert intent.confidence == 0.9

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, intent_classifier):
        """Test case-insensitive pattern matching"""
        intent1 = await intent_classifier._rule_based_classification("STATUS")
        intent2 = await intent_classifier._rule_based_classification("status")
        assert intent1.type == IntentType.QUERY_STATUS
        assert intent2.type == IntentType.QUERY_STATUS

    @pytest.mark.asyncio
    async def test_no_pattern_match(self, intent_classifier):
        """Test when no pattern matches"""
        intent = await intent_classifier._rule_based_classification("xyzabc123")
        assert intent.type == IntentType.UNKNOWN
        assert intent.confidence == 0.0

    @pytest.mark.asyncio
    async def test_priority_resolution(self, intent_classifier):
        """Test priority-based conflict resolution"""
        # Add multiple matching patterns with different priorities
        intent = await intent_classifier._rule_based_classification("查看状态")
        # Should match the highest priority pattern
        assert intent.type == IntentType.QUERY_STATUS

    @pytest.mark.asyncio
    async def test_list_gates_pattern_match(self, intent_classifier, mock_config):
        """Test rule-based LIST_GATES pattern matching"""
        intents = mock_config.get_all_intents.return_value
        intents['list_gates'] = IntentConfig(
            type=IntentType.LIST_GATES,
            patterns=[PatternConfig(regex=r'^门禁列表|查.*(门禁|gate|gates)|list.*gate', priority=1, description='List gates')],
            llm_fallback=True,
            allowed_tools=['lee.workflow.status'],
            description='List gates'
        )
        intent_classifier._compile_patterns()

        intent = await intent_classifier._rule_based_classification("门禁列表")
        assert intent.type == IntentType.LIST_GATES

        intent = await intent_classifier._rule_based_classification("查一下gate有哪些")
        assert intent.type == IntentType.LIST_GATES


class TestLLMFallback:
    """Test LLM fallback classification"""

    @pytest.mark.asyncio
    async def test_llm_fallback_success(self, intent_classifier):
        """Test successful LLM fallback"""
        # Use input that won't match rules
        intent = await intent_classifier._llm_classification("告诉我现在怎么样", None)
        assert intent.type == IntentType.QUERY_STATUS
        assert intent.confidence == 0.8

    @pytest.mark.asyncio
    async def test_llm_fallback_parse_error(self, intent_classifier, mock_llm_executor):
        """Test LLM fallback with parsing error"""
        # Mock LLM to return invalid JSON
        mock_llm_executor.execute.return_value = {
            'status': 'completed',
            'generated_text': 'This is not valid JSON',
        }

        # Should handle gracefully and return UNKNOWN
        intent = await intent_classifier._llm_classification("test input", None)
        assert intent.type == IntentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_llm_fallback_execution_error(self, intent_classifier, mock_llm_executor):
        """Test LLM fallback with execution error"""
        # Mock LLM to raise exception
        mock_llm_executor.execute.side_effect = Exception("LLM error")

        # Should return UNKNOWN
        intent = await intent_classifier._llm_classification("test input", None)
        assert intent.type == IntentType.UNKNOWN


class TestClassificationPipeline:
    """Test the complete classification pipeline"""

    @pytest.mark.asyncio
    async def test_rule_based_classification(self, intent_classifier):
        """Test classification using rules (no LLM)"""
        intent = await intent_classifier.classify("当前状态")
        assert intent.type == IntentType.QUERY_STATUS
        assert intent_classifier._rule_match_count == 1
        assert intent_classifier._llm_fallback_count == 0

    @pytest.mark.asyncio
    async def test_llm_fallback_triggering(self, intent_classifier):
        """Test LLM fallback when rules don't match"""
        intent = await intent_classifier.classify("随便说点什么")
        assert intent_classifier._llm_fallback_count == 1

    @pytest.mark.asyncio
    async def test_no_llm_no_fallback(self, mock_config):
        """Test classification without LLM (no fallback)"""
        classifier = IntentClassifier(mock_config, llm_executor=None)

        intent = await classifier.classify("随便说点什么")
        assert intent.type == IntentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_with_conversation_context(self, intent_classifier):
        """Test classification with conversation context"""
        context = ConversationContext(
            session_id="test_session",
            department="stg",
            history=[],
            current_workflow_id="workflow_123"
        )

        intent = await intent_classifier.classify("当前状态", context)
        assert intent.type == IntentType.QUERY_STATUS


class TestMetrics:
    """Test metrics collection"""

    def test_initial_metrics(self, intent_classifier):
        """Test initial metrics state"""
        metrics = intent_classifier.get_metrics()
        assert metrics['total_classifications'] == 0
        assert metrics['rule_match_count'] == 0
        assert metrics['llm_fallback_count'] == 0
        assert metrics['rule_match_rate'] == 0

    @pytest.mark.asyncio
    async def test_metrics_update(self, intent_classifier):
        """Test metrics update after classifications"""
        await intent_classifier.classify("当前状态")
        await intent_classifier.classify("随便说点什么")

        metrics = intent_classifier.get_metrics()
        assert metrics['total_classifications'] == 2
        assert metrics['rule_match_count'] == 1
        assert metrics['llm_fallback_count'] == 1
        assert metrics['rule_match_rate'] == 0.5

    def test_metrics_reset(self, intent_classifier):
        """Test metrics reset"""
        # Simulate some classifications
        intent_classifier._rule_match_count = 10
        intent_classifier._llm_fallback_count = 5
        intent_classifier._total_classifications = 15

        # Reset
        intent_classifier.reset_metrics()
        metrics = intent_classifier.get_metrics()
        assert metrics['total_classifications'] == 0
        assert metrics['rule_match_count'] == 0
        assert metrics['llm_fallback_count'] == 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_input(self, intent_classifier):
        """Test with empty input"""
        intent = await intent_classifier.classify("")
        assert intent.type == IntentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_whitespace_only_input(self, intent_classifier):
        """Test with whitespace-only input"""
        intent = await intent_classifier.classify("   \n\t   ")
        assert intent.type == IntentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_very_long_input(self, intent_classifier):
        """Test with very long input"""
        long_input = "test " * 10000
        intent = await intent_classifier.classify(long_input)
        # Should not crash, may be UNKNOWN or matched
        assert isinstance(intent, Intent)

    @pytest.mark.asyncio
    async def test_special_characters(self, intent_classifier):
        """Test with special characters"""
        intent = await intent_classifier.classify("!@#$%^&*()")
        assert intent.type == IntentType.UNKNOWN

    @pytest.mark.asyncio
    async def test_multilingual_input(self, intent_classifier):
        """Test with multilingual input"""
        # Chinese
        intent1 = await intent_classifier.classify("状态")
        assert intent1.type == IntentType.QUERY_STATUS

        # English
        intent2 = await intent_classifier.classify("status")
        assert intent2.type == IntentType.QUERY_STATUS

        # Mixed
        intent3 = await intent_classifier.classify("当前 STATUS")
        assert intent3.type == IntentType.QUERY_STATUS


class TestConfiguration:
    """Test configuration handling"""

    def test_get_intent_config(self, intent_classifier):
        """Test getting intent configuration"""
        config = intent_classifier.config.get_intent_config("query_status")
        assert config is not None
        assert config.type == IntentType.QUERY_STATUS

    def test_get_nonexistent_intent_config(self, intent_classifier):
        """Test getting non-existent intent configuration"""
        config = intent_classifier.config.get_intent_config("nonexistent")
        assert config is None

    def test_get_all_intents(self, intent_classifier):
        """Test getting all intents"""
        intents = intent_classifier.config.get_all_intents()
        assert isinstance(intents, dict)
        assert len(intents) >= 2  # At least query_status and execute_step


class TestRealConfigGateMatching:
    """Regression tests against real project config patterns."""

    @pytest.mark.asyncio
    async def test_view_current_gate_maps_to_list_gates(self):
        config = IntentClassifierConfig(project_root=str(Path.cwd()))
        classifier = IntentClassifier(config=config, llm_executor=None)

        intent = await classifier.classify("查看当前的gate")
        assert intent.type == IntentType.LIST_GATES


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
