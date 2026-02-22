"""
Unit Tests for Permission Checker

Tests for:
- Permission validation for different intents
- Constitution rule enforcement
- Session-based permissions
- Department-specific permissions
- Permission denial scenarios
- Security tests for bypass attempts
"""

import pytest
from unittest.mock import Mock
from lee.orchestrator.execution.pm_agent.permission_checker import PermissionChecker, PermissionCheckerBuilder
from lee.orchestrator.execution.pm_agent.config import IntentClassifierConfig, IntentConfig, PermissionConfig
from lee.orchestrator.execution.pm_agent.models import Intent, IntentType, ConversationContext
from lee.orchestrator.execution.pm_agent.exceptions import PermissionDeniedError


@pytest.fixture
def mock_config():
    """Create a mock configuration with permissions"""
    config = Mock(spec=IntentClassifierConfig)

    # Mock intent configurations with allowed tools
    config.get_intent_config = Mock(side_effect=lambda intent_id, dept=None: MOCK_INTENTS.get(intent_id))

    # Mock permissions
    config.get_permissions = Mock(return_value=GLOBAL_PERMISSIONS)

    # Mock get_all_intents
    config.get_all_intents = Mock(return_value=MOCK_INTENTS)

    return config


# Mock data
MOCK_INTENTS = {
    'query_status': IntentConfig(
        type=IntentType.QUERY_STATUS,
        patterns=[],
        llm_fallback=True,
        allowed_tools=['lee.workflow.status'],
        description='Query status'
    ),
    'execute_step': IntentConfig(
        type=IntentType.EXECUTE_STEP,
        patterns=[],
        llm_fallback=True,
        allowed_tools=['lee.workflow.run'],
        description='Execute step'
    ),
    'approve_gate': IntentConfig(
        type=IntentType.APPROVE_GATE,
        patterns=[],
        llm_fallback=True,
        allowed_tools=['lee.gate.approve'],
        description='Approve gate'
    ),
    'pause_workflow': IntentConfig(
        type=IntentType.PAUSE_WORKFLOW,
        patterns=[],
        llm_fallback=True,
        allowed_tools=['lee.workflow.run'],
        description='Pause workflow'
    ),
    'list_gates': IntentConfig(
        type=IntentType.LIST_GATES,
        patterns=[],
        llm_fallback=True,
        allowed_tools=['lee.workflow.status'],
        description='List gates'
    ),
    'shell_command': IntentConfig(
        type=IntentType.UNKNOWN,  # Custom intent
        patterns=[],
        llm_fallback=True,
        allowed_tools=['shell'],
        description='Shell command'
    ),
}

GLOBAL_PERMISSIONS = PermissionConfig(
    allowed_tools=['lee.workflow.run', 'lee.workflow.status', 'lee.gate.approve', 'lee.gate.reject'],
    denied_tools=['shell', 'git', 'file_write'],
    constitution_rules=[
        'All code changes must go through workflow',
        'On failure, only allow: retry | human_gate_required'
    ]
)


@pytest.fixture
def permission_checker(mock_config):
    """Create a Permission Checker instance"""
    return PermissionChecker(config=mock_config, default_department=None)


@pytest.fixture
def sample_context():
    """Create a sample context"""
    return ConversationContext(
        session_id="test_session",
        user_permissions=['lee.workflow.run', 'lee.workflow.status'],
        department="dev"
    )


class TestPermissionCheckerInitialization:
    """Test Permission Checker initialization"""

    def test_init_with_config(self, mock_config):
        """Test initialization with configuration"""
        checker = PermissionChecker(mock_config)
        assert checker.config == mock_config
        assert checker.default_department is None
        assert checker._total_checks == 0

    def test_init_with_department(self, mock_config):
        """Test initialization with default department"""
        checker = PermissionChecker(mock_config, default_department="dev")
        assert checker.default_department == "dev"


class TestPermissionChecking:
    """Test permission checking functionality"""

    def test_check_allowed_intent(self, permission_checker):
        """Test checking an allowed intent"""
        intent = Intent(
            type=IntentType.QUERY_STATUS,
            confidence=0.9,
            reasoning="User wants to know status"
        )

        result = permission_checker.check(intent)
        assert result is True
        assert permission_checker._allowed_count == 1

    def test_check_denied_tool_in_intent(self, permission_checker):
        """Test checking intent with denied tool"""
        intent = Intent(
            type=IntentType.UNKNOWN,  # shell_command intent
            confidence=0.9,
            reasoning="User wants to run shell command"
        )

        # Mock to return shell_command config
        permission_checker.config.get_intent_config = Mock(
            return_value=MOCK_INTENTS['shell_command']
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            permission_checker.check(intent)

        assert "Permission denied" in str(exc_info.value)
        assert permission_checker._denied_count == 1

    def test_check_unknown_intent(self, permission_checker):
        """Test checking unknown intent"""
        intent = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            reasoning="Unknown intent"
        )

        # Mock to return None
        permission_checker.config.get_intent_config = Mock(return_value=None)

        with pytest.raises(PermissionDeniedError) as exc_info:
            permission_checker.check(intent)

        assert "Unknown intent" in str(exc_info.value)

    def test_check_with_context(self, permission_checker, sample_context):
        """Test permission checking with context"""
        intent = Intent(
            type=IntentType.EXECUTE_STEP,
            confidence=0.9,
            reasoning="Execute step"
        )

        result = permission_checker.check(intent, sample_context)
        assert result is True

    def test_check_with_insufficient_session_permissions(self, permission_checker):
        """Test checking with insufficient session permissions"""
        context = ConversationContext(
            session_id="test",
            user_permissions=['lee.workflow.status']  # Missing execute permission
        )

        intent = Intent(
            type=IntentType.EXECUTE_STEP,
            confidence=0.9,
            reasoning="Execute step"
        )

        with pytest.raises(PermissionDeniedError) as exc_info:
            permission_checker.check(intent, context)

        assert "session permissions" in str(exc_info.value).lower()


class TestConstitutionRuleEnforcement:
    """Test constitution rule enforcement"""

    def test_check_constitution_compliance(self, permission_checker, sample_context):
        """Test constitution rule compliance"""
        intent = Intent(
            type=IntentType.QUERY_STATUS,
            confidence=0.9,
            reasoning="Query status"
        )

        result = permission_checker._check_constitution(
            intent,
            GLOBAL_PERMISSIONS.constitution_rules,
            sample_context
        )
        assert result is True

    def test_check_constitution_after_failure(self, permission_checker):
        """Test constitution rules after step failure"""
        context = ConversationContext(
            session_id="test",
            metadata={"last_step_failed": True}
        )

        # EXECUTE_STEP might not be appropriate after failure
        # But this shouldn't deny, just log warning
        result = permission_checker._check_constitution(
            Intent(type=IntentType.EXECUTE_STEP, confidence=0.9, reasoning=""),
            GLOBAL_PERMISSIONS.constitution_rules,
            context
        )
        # Should return True (denial happens elsewhere)
        assert result is True


class TestSessionPermissions:
    """Test session-based permission checking"""

    def test_check_session_permissions_sufficient(self, permission_checker):
        """Test with sufficient session permissions"""
        context = ConversationContext(
            session_id="test",
            user_permissions=['lee.workflow.run', 'lee.workflow.status']
        )

        result = permission_checker._check_session_permissions(
            Intent(type=IntentType.EXECUTE_STEP, confidence=0.9, reasoning=""),
            context
        )
        assert result is True

    def test_check_session_permissions_insufficient(self, permission_checker):
        """Test with insufficient session permissions"""
        context = ConversationContext(
            session_id="test",
            user_permissions=['lee.workflow.status']  # Missing execute
        )

        result = permission_checker._check_session_permissions(
            Intent(type=IntentType.EXECUTE_STEP, confidence=0.9, reasoning=""),
            context
        )
        assert result is False

    def test_check_session_permissions_no_context(self, permission_checker):
        """Test without context (should pass)"""
        result = permission_checker._check_session_permissions(
            Intent(type=IntentType.EXECUTE_STEP, confidence=0.9, reasoning=""),
            None
        )
        assert result is True

    def test_check_session_permissions_pause_requires_run(self, permission_checker):
        """Test PAUSE_WORKFLOW requires run permission"""
        context = ConversationContext(
            session_id="test",
            user_permissions=['lee.workflow.status']
        )
        result = permission_checker._check_session_permissions(
            Intent(type=IntentType.PAUSE_WORKFLOW, confidence=0.9, reasoning=""),
            context
        )
        assert result is False

    def test_check_session_permissions_list_gates_uses_status(self, permission_checker):
        """Test LIST_GATES uses status permission"""
        context = ConversationContext(
            session_id="test",
            user_permissions=['lee.workflow.status']
        )
        result = permission_checker._check_session_permissions(
            Intent(type=IntentType.LIST_GATES, confidence=0.9, reasoning=""),
            context
        )
        assert result is True


class TestDepartmentSpecificPermissions:
    """Test department-specific permission handling"""

    def test_get_intent_config_for_department(self, permission_checker):
        """Test getting intent config for specific department"""
        # This would use department-specific overrides
        config = permission_checker.config.get_intent_config('query_status', 'stg')
        # Mock returns default
        assert config is not None

    def test_get_permissions_for_department(self, permission_checker):
        """Test getting permissions for specific department"""
        permissions = permission_checker.get_permissions('dev')
        # Mock returns global permissions
        assert permissions.allowed_tools is not None


class TestPermissionUtilities:
    """Test permission checker utility methods"""

    def test_get_required_tools(self, permission_checker):
        """Test getting required tools for intent"""
        tools = permission_checker.get_required_tools(IntentType.QUERY_STATUS)
        assert 'lee.workflow.status' in tools

    def test_get_permissions_summary(self, permission_checker):
        """Test getting permissions summary"""
        summary = permission_checker.get_permissions_summary()
        assert 'allowed_tools' in summary
        assert 'denied_tools' in summary
        assert 'constitution_rules' in summary


class TestMetrics:
    """Test metrics collection"""

    def test_initial_metrics(self, permission_checker):
        """Test initial metrics"""
        metrics = permission_checker.get_metrics()
        assert metrics['total_checks'] == 0
        assert metrics['allowed_count'] == 0
        assert metrics['denied_count'] == 0
        assert metrics['denial_rate'] == 0

    def test_metrics_after_checks(self, permission_checker):
        """Test metrics after permission checks"""
        intent = Intent(type=IntentType.QUERY_STATUS, confidence=0.9, reasoning="")

        # Allowed check
        permission_checker.check(intent)

        # Denied check
        permission_checker.config.get_intent_config = Mock(return_value=None)
        try:
            permission_checker.check(Intent(type=IntentType.UNKNOWN, confidence=0, reasoning=""))
        except:
            pass

        metrics = permission_checker.get_metrics()
        assert metrics['total_checks'] == 2
        assert metrics['allowed_count'] == 1
        assert metrics['denied_count'] == 1
        assert metrics['denial_rate'] == 0.5

    def test_metrics_reset(self, permission_checker):
        """Test metrics reset"""
        permission_checker._total_checks = 10
        permission_checker._allowed_count = 8
        permission_checker._denied_count = 2

        permission_checker.reset_metrics()

        metrics = permission_checker.get_metrics()
        assert metrics['total_checks'] == 0
        assert metrics['allowed_count'] == 0
        assert metrics['denied_count'] == 0


class TestPermissionCheckerBuilder:
    """Test Permission Checker Builder"""

    def test_builder_with_custom_rules(self, mock_config):
        """Test building checker with custom rules"""
        builder = PermissionCheckerBuilder(mock_config)
        builder.allow_tool("custom.tool")
        builder.deny_tool("dangerous.tool")
        builder.add_rule("Custom constitution rule")

        checker = builder.build()

        # Note: Custom rules are stored in the checker
        assert hasattr(checker, 'custom_allowed_tools')
        assert 'custom.tool' in checker.custom_allowed_tools
        assert 'dangerous.tool' in checker.custom_denied_tools
        assert len(checker.custom_rules) > 0

    def test_builder_with_fallback_disabled(self, mock_config):
        """Test building with fallback disabled"""
        builder = PermissionCheckerBuilder(mock_config)
        # Build without adding custom rules
        checker = builder.build()
        assert checker is not None

    def test_builder_missing_components(self):
        """Test builder with None config"""
        builder = PermissionCheckerBuilder(None)
        # Should raise error when trying to build
        with pytest.raises(ValueError):
            builder.build()


class TestSecurityScenarios:
    """Test security-related scenarios"""

    def test_permission_denial_for_shell_access(self, permission_checker):
        """Test that shell access is denied"""
        # Create intent that would require shell tool
        permission_checker.config.get_intent_config = Mock(
            return_value=MOCK_INTENTS['shell_command']
        )

        intent = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.9,
            reasoning="Run shell command"
        )

        with pytest.raises(PermissionDeniedError):
            permission_checker.check(intent)

    def test_permission_denial_for_git_access(self, permission_checker):
        """Test that git access is denied"""
        # Create intent requiring git
        git_intent_config = IntentConfig(
            type=IntentType.UNKNOWN,
            patterns=[],
            llm_fallback=True,
            allowed_tools=['git'],
            description='Git command'
        )

        permission_checker.config.get_intent_config = Mock(return_value=git_intent_config)

        intent = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.9,
            reasoning="Run git command"
        )

        with pytest.raises(PermissionDeniedError):
            permission_checker.check(intent)

    def test_allowed_workflow_operations(self, permission_checker):
        """Test that workflow operations are allowed"""
        intent = Intent(
            type=IntentType.EXECUTE_STEP,
            confidence=0.9,
            reasoning="Execute workflow step"
        )

        result = permission_checker.check(intent)
        assert result is True

    def test_allowed_gate_operations(self, permission_checker):
        """Test that gate operations are allowed"""
        intent = Intent(
            type=IntentType.APPROVE_GATE,
            confidence=0.9,
            reasoning="Approve gate"
        )

        result = permission_checker.check(intent)
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
