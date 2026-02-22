"""
Unit Tests for Param Mapper

Tests for:
- Parameter extraction from natural language
- Workflow discovery and caching
- Fuzzy matching (workflow_id, step_id)
- Validation and normalization
- Error handling and retry logic
- Metrics collection
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from lee.orchestrator.execution.pm_agent.param_mapper import ParamMapper
from lee.orchestrator.execution.pm_agent.models import Intent, IntentType, WorkflowParams, ConversationContext
from lee.orchestrator.execution.template_manager import TemplateManager


@pytest.fixture
def mock_llm_executor():
    """Create a mock LLM executor"""
    executor = Mock()
    executor.execute = AsyncMock(return_value={
        'status': 'completed',
        'generated_text': '''{"workflow_ref": "workflow.stg.opportunity_discovery",
"step_id": "search_signals",
"params": {"keywords": ["AI", "ML"]},
"confidence": 0.85,
"reasoning": "User wants to search for signals"}''',
    })
    return executor


@pytest.fixture
def mock_template_manager():
    """Create a mock Template Manager"""
    manager = Mock(spec=TemplateManager)

    # Mock list_workflows
    manager.list_workflows = Mock(return_value=[
        'workflow.stg.opportunity_discovery',
        'workflow.dev.feature',
        'workflow.qa.test_plan_execution',
        'workflow.office.workspace_cleanup',
    ])

    # Mock load_workflow
    def mock_load_workflow(workflow_id):
        workflow = Mock()
        workflow.id = workflow_id
        workflow.name = f"Test Workflow: {workflow_id}"
        workflow.description = "Test description"

        # Create mock steps
        step1 = Mock()
        step1.id = "search_signals"
        step1.name = "Search Signals"
        step1.kind = "agent"
        step1.description = "Search for signals"

        step2 = Mock()
        step2.id = "analyze_signals"
        step2.name = "Analyze Signals"
        step2.kind = "agent"
        step2.description = "Analyze search results"

        workflow.steps = [step1, step2]
        return workflow

    manager.load_workflow = Mock(side_effect=mock_load_workflow)

    return manager


@pytest.fixture
def param_mapper(mock_llm_executor, mock_template_manager):
    """Create a Param Mapper instance"""
    return ParamMapper(
        llm_executor=mock_llm_executor,
        template_manager=mock_template_manager,
        max_retries=2
    )


@pytest.fixture
def sample_intent():
    """Create a sample intent"""
    return Intent(
        type=IntentType.EXECUTE_STEP,
        confidence=0.9,
        reasoning="User wants to execute a step"
    )


@pytest.fixture
def sample_context():
    """Create a sample context"""
    return ConversationContext(
        session_id="test_session",
        department="stg",
        current_workflow_id="workflow.stg.opportunity_discovery",
        history=[]
    )


class TestParamMapperInitialization:
    """Test Param Mapper initialization"""

    def test_init_with_components(self, mock_llm_executor, mock_template_manager):
        """Test initialization with all components"""
        mapper = ParamMapper(mock_llm_executor, mock_template_manager)
        assert mapper.llm == mock_llm_executor
        assert mapper.template_manager == mock_template_manager
        assert mapper.max_retries == 2
        assert mapper._workflow_cache == {}
        assert mapper._total_extractions == 0

    def test_init_with_custom_max_retries(self, mock_llm_executor, mock_template_manager):
        """Test initialization with custom max retries"""
        mapper = ParamMapper(mock_llm_executor, mock_template_manager, max_retries=5)
        assert mapper.max_retries == 5


class TestIntentRequiresParams:
    """Test _intent_requires_params"""

    def test_execute_step_requires_params(self, param_mapper):
        """Test that EXECUTE_STEP requires params"""
        assert param_mapper._intent_requires_params(IntentType.EXECUTE_STEP) == True

    def test_approve_gate_requires_params(self, param_mapper):
        """Test that APPROVE_GATE requires params"""
        assert param_mapper._intent_requires_params(IntentType.APPROVE_GATE) == True

    def test_query_status_no_params(self, param_mapper):
        """Test that QUERY_STATUS doesn't require params"""
        assert param_mapper._intent_requires_params(IntentType.QUERY_STATUS) == False

    def test_show_help_no_params(self, param_mapper):
        """Test that SHOW_HELP doesn't require params"""
        assert param_mapper._intent_requires_params(IntentType.SHOW_HELP) == False

    def test_pause_workflow_requires_params(self, param_mapper):
        """Test that PAUSE_WORKFLOW requires params"""
        assert param_mapper._intent_requires_params(IntentType.PAUSE_WORKFLOW) == True


class TestWorkflowDiscovery:
    """Test workflow discovery functionality"""

    @pytest.mark.asyncio
    async def test_workflow_discovery(self, param_mapper):
        """Test workflow discovery populates cache"""
        workflows = await param_mapper._discover_workflows()
        assert len(workflows) >= 1
        assert 'workflow.stg.opportunity_discovery' in workflows
        assert len(param_mapper._workflow_cache) > 0

    @pytest.mark.asyncio
    async def test_workflow_cache_hit(self, param_mapper):
        """Test that cache is used on subsequent calls"""
        # First call
        workflows1 = await param_mapper._discover_workflows()
        cache_timestamp = param_mapper._cache_timestamp

        # Second call should use cache
        workflows2 = await param_mapper._discover_workflows()
        assert workflows2 == workflows1
        assert param_mapper._cache_timestamp == cache_timestamp

    @pytest.mark.asyncio
    async def test_workflow_cache_expiration(self, param_mapper):
        """Test workflow cache expiration"""
        import time

        # First discovery
        await param_mapper._discover_workflows()
        cache_timestamp = param_mapper._cache_timestamp

        # Expire cache
        param_mapper._cache_timestamp = time.time() - param_mapper._cache_ttl - 10

        # Should refresh cache
        await param_mapper._discover_workflows()
        assert param_mapper._cache_timestamp > cache_timestamp

    @pytest.mark.asyncio
    async def test_workflow_discovery_error_handling(self, param_mapper, mock_template_manager):
        """Test workflow discovery error handling"""
        # Mock template manager to raise error
        mock_template_manager.list_workflows = Mock(side_effect=Exception("Discovery error"))

        # Should return empty dict, not crash
        workflows = await param_mapper._discover_workflows()
        assert workflows == {}

    @pytest.mark.asyncio
    async def test_workflow_discovery_fallback_to_load_all_and_get_template(self, mock_llm_executor):
        """Support template managers that expose get_template/load_all_templates only."""
        manager = Mock(spec=TemplateManager)
        manager.load_all_templates = Mock()
        manager.get_template = Mock()

        wf = Mock()
        wf.id = "workflow.office.workspace_cleanup"
        wf.name = "Workspace Cleanup"
        wf.description = "Cleanup workspace files"
        wf.steps = []

        manager.load_all_templates.return_value = {"workflow.office.workspace_cleanup": wf}
        manager.get_template.return_value = wf

        mapper = ParamMapper(mock_llm_executor, manager)
        workflows = await mapper._discover_workflows()

        assert "workflow.office.workspace_cleanup" in workflows
        assert workflows["workflow.office.workspace_cleanup"]["name"] == "Workspace Cleanup"


class TestParameterMapping:
    """Test parameter mapping functionality"""

    @pytest.mark.asyncio
    async def test_map_params_for_execute_step(self, param_mapper, sample_intent, sample_context):
        """Test parameter mapping for EXECUTE_STEP intent"""
        params = await param_mapper.map_params(
            "运行 search_signals 步骤",
            sample_intent,
            sample_context
        )

        assert isinstance(params, WorkflowParams)
        assert params.workflow_ref == "workflow.stg.opportunity_discovery"
        assert params.step_id == "search_signals"
        assert params.confidence >= 0.85

    @pytest.mark.asyncio
    async def test_map_params_for_query_status(self, param_mapper, sample_context):
        """Test parameter mapping for QUERY_STATUS (no params needed)"""
        intent = Intent(type=IntentType.QUERY_STATUS, confidence=0.9, reasoning="Query")

        params = await param_mapper.map_params(
            "当前状态",
            intent,
            sample_context
        )

        assert isinstance(params, WorkflowParams)
        assert params.workflow_ref is None
        assert params.step_id is None

    @pytest.mark.asyncio
    async def test_map_params_for_pause_workflow_rule(self, param_mapper, sample_context):
        """Test rule-based mapping for PAUSE_WORKFLOW intent"""
        intent = Intent(type=IntentType.PAUSE_WORKFLOW, confidence=0.9, reasoning="Pause")

        params = await param_mapper.map_params(
            "暂停 wf_task_abc",
            intent,
            sample_context
        )

        assert params.workflow_ref == "wf_task_abc"
        assert params.step_id is None

    @pytest.mark.asyncio
    async def test_map_params_for_revise_gate_rule(self, param_mapper, sample_context):
        """Test rule-based mapping for REVISE_GATE intent"""
        intent = Intent(type=IntentType.REVISE_GATE, confidence=0.9, reasoning="Revise")

        params = await param_mapper.map_params(
            "修订 gate_review",
            intent,
            sample_context
        )

        assert params.workflow_ref == sample_context.current_workflow_id
        assert params.gate_id == "gate_review"

    @pytest.mark.asyncio
    async def test_map_params_for_flag_gate_rule(self, param_mapper, sample_context):
        """Test rule-based mapping for FLAG_GATE intent"""
        intent = Intent(type=IntentType.FLAG_GATE, confidence=0.9, reasoning="Flag")

        params = await param_mapper.map_params(
            "标记 gate_quality",
            intent,
            sample_context
        )

        assert params.workflow_ref == sample_context.current_workflow_id
        assert params.gate_id == "gate_quality"

    @pytest.mark.asyncio
    async def test_map_params_with_retry(self, param_mapper, sample_intent, sample_context, mock_llm_executor):
        """Test parameter mapping with retry on failure"""
        # Mock LLM to fail once, then succeed
        call_count = 0

        async def failing_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'status': 'failed', 'error': 'LLM error'}
            return {
                'status': 'completed',
                'generated_text': '{"workflow_ref": "test", "step_id": null, "params": {}, "confidence": 0.5, "reasoning": "test"}'
            }

        mock_llm_executor.execute = AsyncMock(side_effect=failing_execute)

        params = await param_mapper.map_params("test input", sample_intent, sample_context)
        assert call_count == 2  # Initial + 1 retry
        assert isinstance(params, WorkflowParams)

    @pytest.mark.asyncio
    async def test_map_params_for_run_workflow_alias(self, param_mapper, sample_context):
        """RUN_WORKFLOW should map short alias to canonical template ID."""
        intent = Intent(type=IntentType.RUN_WORKFLOW, confidence=0.9, reasoning="Run workflow")

        params = await param_mapper.map_params(
            "全新运行工作流workspace_cleanup",
            intent,
            sample_context,
        )

        assert params.workflow_ref == "workflow.office.workspace_cleanup"
        assert params.params.get("template_id") == "workflow.office.workspace_cleanup"
        assert params.params.get("template_input") == "workspace_cleanup"
        assert params.params.get("template_resolved") == "workflow.office.workspace_cleanup"

    @pytest.mark.asyncio
    async def test_map_params_max_retries_exceeded(self, param_mapper, sample_intent, sample_context, mock_llm_executor):
        """Test parameter mapping when max retries exceeded"""
        # Mock LLM to always fail
        mock_llm_executor.execute = AsyncMock(
            return_value={'status': 'failed', 'error': 'LLM error'}
        )

        with pytest.raises(Exception) as exc_info:
            await param_mapper.map_params("test input", sample_intent, sample_context)

        assert "Failed to extract parameters" in str(exc_info.value)
        assert mock_llm_executor.execute.call_count == param_mapper.max_retries + 1


class TestFuzzyMatching:
    """Test fuzzy matching functionality"""

    def test_fuzzy_match_workflow_exact(self, param_mapper):
        """Test exact workflow matching"""
        workflows = {
            'workflow.stg.opportunity_discovery': {'id': '...', 'name': '...', 'steps': []}
        }

        result = param_mapper._fuzzy_match_workflow('workflow.stg.opportunity_discovery', workflows)
        assert result == 'workflow.stg.opportunity_discovery'

    def test_fuzzy_match_workflow_case_insensitive(self, param_mapper):
        """Test case-insensitive workflow matching"""
        workflows = {
            'workflow.stg.opportunity_discovery': {'id': '...', 'name': '...', 'steps': []}
        }

        result = param_mapper._fuzzy_match_workflow('WORKFLOW.STG.OPPORTUNITY_DISCOVERY', workflows)
        assert result == 'workflow.stg.opportunity_discovery'

    def test_fuzzy_match_workflow_name(self, param_mapper):
        """Test workflow name matching"""
        workflows = {
            'workflow.stg.opportunity_discovery': {
                'id': '...',
                'name': '商业机会发现工作流',
                'steps': []
            }
        }

        result = param_mapper._fuzzy_match_workflow('商业机会', workflows)
        assert result == 'workflow.stg.opportunity_discovery'

    def test_fuzzy_match_workflow_no_match(self, param_mapper):
        """Test workflow fuzzy matching with no match"""
        workflows = {
            'workflow.stg.opportunity_discovery': {'id': '...', 'name': '...', 'steps': []}
        }

        result = param_mapper._fuzzy_match_workflow('nonexistent', workflows)
        assert result is None

    def test_fuzzy_match_workflow_suffix_alias(self, param_mapper):
        workflows = {
            'workflow.office.workspace_cleanup': {'id': '...', 'name': 'Workspace cleanup', 'steps': []}
        }
        result = param_mapper._fuzzy_match_workflow('workspace_cleanup', workflows)
        assert result == 'workflow.office.workspace_cleanup'

    def test_fuzzy_match_step_exact(self, param_mapper):
        """Test exact step matching"""
        steps = ['search_signals', 'analyze_signals', 'build_opportunity']

        result = param_mapper._fuzzy_match_step('search_signals', steps)
        assert result == 'search_signals'

    def test_fuzzy_match_step_case_insensitive(self, param_mapper):
        """Test case-insensitive step matching"""
        steps = ['search_signals', 'analyze_signals']

        result = param_mapper._fuzzy_match_step('SEARCH_SIGNALS', steps)
        assert result == 'search_signals'

    def test_fuzzy_match_step_partial(self, param_mapper):
        """Test partial step matching"""
        steps = ['search_signals', 'analyze_user_signals']

        result = param_mapper._fuzzy_match_step('search', steps)
        assert result == 'search_signals'

    def test_fuzzy_match_step_no_match(self, param_mapper):
        """Test step fuzzy matching with no match"""
        steps = ['search_signals', 'analyze_signals']

        result = param_mapper._fuzzy_match_step('nonexistent_step', steps)
        assert result is None


class TestParameterValidation:
    """Test parameter validation and normalization"""

    @pytest.mark.asyncio
    async def test_validate_and_normalize_params(self, param_mapper):
        """Test parameter validation and normalization"""
        params_data = {
            'workflow_ref': 'workflow.stg.opportunity_discovery',
            'step_id': 'search_signals',
            'params': {'keywords': ['AI', 'ML']},
            'confidence': 0.85
        }

        workflows = await param_mapper._discover_workflows()
        intent_type = IntentType.EXECUTE_STEP

        params = param_mapper._validate_and_normalize_params(params_data, workflows, intent_type)

        assert params.workflow_ref == 'workflow.stg.opportunity_discovery'
        assert params.step_id == 'search_signals'
        assert params.params == {'keywords': ['AI', 'ML']}
        assert params.confidence == 0.85


class TestMetrics:
    """Test metrics collection"""

    def test_initial_metrics(self, param_mapper):
        """Test initial metrics state"""
        metrics = param_mapper.get_metrics()
        assert metrics['total_extractions'] == 0
        assert metrics['successful_extractions'] == 0
        assert metrics['success_rate'] == 0

    @pytest.mark.asyncio
    async def test_metrics_update_on_success(self, param_mapper, sample_intent, sample_context):
        """Test metrics update after successful extraction"""
        await param_mapper.map_params("test input", sample_intent, sample_context)

        metrics = param_mapper.get_metrics()
        assert metrics['total_extractions'] == 1
        assert metrics['successful_extractions'] == 1
        assert metrics['success_rate'] == 1.0

    @pytest.mark.asyncio
    async def test_metrics_update_on_failure(self, param_mapper, sample_intent, sample_context, mock_llm_executor):
        """Test metrics update after failed extraction"""
        mock_llm_executor.execute = AsyncMock(
            return_value={'status': 'failed', 'error': 'LLM error'}
        )

        with pytest.raises(Exception):
            await param_mapper.map_params("test input", sample_intent, sample_context)

        metrics = param_mapper.get_metrics()
        assert metrics['total_extractions'] == 1
        assert metrics['successful_extractions'] == 0
        assert metrics['success_rate'] == 0

    def test_cache_clear(self, param_mapper):
        """Test cache clearing"""
        # Add some data to cache
        param_mapper._workflow_cache = {'test': {'id': 'test'}}
        param_mapper._cache_timestamp = 123.0

        # Clear cache
        param_mapper.clear_cache()

        assert param_mapper._workflow_cache == {}
        assert param_mapper._cache_timestamp is None


class TestContextBuilding:
    """Test context building for prompts"""

    def test_build_workflow_summary(self, param_mapper):
        """Test workflow summary building"""
        workflows = {
            'test_workflow': {
                'id': 'test_workflow',
                'name': 'Test Workflow',
                'description': 'A test workflow',
                'steps': [
                    {'id': 'step1', 'name': 'Step 1', 'kind': 'agent', 'description': 'First step'},
                    {'id': 'step2', 'name': 'Step 2', 'kind': 'agent', 'description': 'Second step'},
                ]
            }
        }

        summary = param_mapper._build_workflow_summary(workflows)

        assert 'test_workflow' in summary
        assert 'Test Workflow' in summary
        assert 'step1' in summary

    def test_build_context_info(self, param_mapper, sample_context):
        """Test context info building"""
        context_info = param_mapper._build_context_info(sample_context)

        assert sample_context.current_workflow_id in context_info
        assert 'stg' in context_info

    def test_build_context_info_no_context(self, param_mapper):
        """Test context info building with no context"""
        context_info = param_mapper._build_context_info(None)
        assert context_info == ""

    def test_extract_json_object_supports_nested_params(self, param_mapper):
        text = (
            '{"workflow_ref":"workflow.office.workspace_cleanup",'
            '"step_id":null,"gate_id":null,"params":{"template_id":"workspace_cleanup"},'
            '"approval_comment":null,"confidence":0.95,"reasoning":"test"}'
        )
        parsed = param_mapper._extract_json_object(text)
        assert parsed is not None
        assert parsed.get("workflow_ref") == "workflow.office.workspace_cleanup"
        assert isinstance(parsed.get("params"), dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
