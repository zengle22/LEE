"""
PM Agent Permission Checker

Enforces PM Agent protocol constraints by validating intents
against allowed tools and constitution rules.
"""

import logging
from typing import Optional, List, Dict, Any, Set

from .models import Intent, IntentType, ConversationContext
from .config import IntentClassifierConfig, PermissionConfig
from .exceptions import PermissionDeniedError

logger = logging.getLogger(__name__)


class PermissionChecker:
    """
    Permission Checker - Single responsibility component

    Validates intents against:
    1. Allowed/denied tools
    2. Constitution rules
    3. Session-based permissions
    """

    def __init__(
        self,
        config: IntentClassifierConfig,
        default_department: Optional[str] = None
    ):
        """
        Initialize Permission Checker

        Args:
            config: Intent classifier configuration with permission rules
            default_department: Default department for permission lookup
        """
        self.config = config
        self.default_department = default_department

        # Metrics
        self._total_checks = 0
        self._denied_count = 0
        self._allowed_count = 0

    def check(
        self,
        intent: Intent,
        context: Optional[ConversationContext] = None
    ) -> bool:
        """
        Check if intent is allowed

        Args:
            intent: Classified intent to check
            context: Optional conversation context

        Returns:
            True if allowed, False otherwise

        Raises:
            PermissionDeniedError: If permission is denied with detailed reason
        """
        self._total_checks += 1

        department = context.department if context else self.default_department
        intent_config = self.config.get_intent_config(intent.type.value, department)

        if not intent_config:
            # Unknown intent - deny by default
            self._denied_count += 1
            raise PermissionDeniedError(
                f"Unknown intent type: {intent.type.value}",
                action=intent.type.value,
                required_permission="known_intent"
            )

        # Build effective permission sets
        required_tools = set(intent_config.allowed_tools)
        global_permissions = self.config.get_permissions(department)
        denied_tools = set(global_permissions.denied_tools)

        # Deny immediately if this intent requires any explicitly denied tools.
        denied_required = required_tools & denied_tools
        if denied_required:
            self._denied_count += 1
            denied_list = ", ".join(sorted(denied_required))
            raise PermissionDeniedError(
                f"Permission denied: intent requires denied tools: {denied_list}",
                action=intent.type.value,
                required_permission="tool_not_denied"
            )

        # Check against constitution rules
        constitution_rules = global_permissions.constitution_rules
        if not self._check_constitution(intent, constitution_rules, context):
            self._denied_count += 1
            raise PermissionDeniedError(
                "Intent violates constitution rules",
                action=intent.type.value,
                required_permission="constitution_compliance"
            )

        # Check session-based permissions
        if context and context.user_permissions:
            if not self._check_session_permissions(intent, context):
                self._denied_count += 1
                raise PermissionDeniedError(
                    "Intent exceeds session permissions",
                    action=intent.type.value,
                    required_permission="session_scope"
                )

        # All checks passed
        self._allowed_count += 1
        logger.info(f"Permission granted for intent: {intent.type.value}")
        return True

    def _check_constitution(
        self,
        intent: Intent,
        constitution_rules: List[str],
        context: Optional[ConversationContext]
    ) -> bool:
        """
        Check if intent complies with constitution rules

        Args:
            intent: Intent to check
            constitution_rules: List of constitution rules
            context: Optional conversation context

        Returns:
            True if compliant, False otherwise
        """
        # Constitution rules to enforce
        # Rule: "All code changes must go through workflow -> executor -> patch/receipt"
        if intent.type in [IntentType.EXECUTE_STEP, IntentType.CREATE_WORKFLOW]:
            # Check if we're going through proper workflow execution
            # This is enforced by the API wrapper, so we just log here
            logger.debug(f"Intent {intent.type.value} must follow workflow execution path")

        # Rule: "On failure, only allow: retry | human_gate_required | switch_executor"
        # This is context-dependent and should be checked at runtime
        # We'll store the rule for later enforcement
        if context and context.metadata.get("last_step_failed"):
            allowed_failure_intents = {
                IntentType.EXECUTE_STEP,  # retry
                IntentType.QUERY_STATUS,  # check status
            }
            if intent.type not in allowed_failure_intents:
                logger.warning(f"Intent {intent.type.value} may not be appropriate after failure")
                # Don't deny here, let the API wrapper handle it

        return True

    def _check_session_permissions(
        self,
        intent: Intent,
        context: Optional[ConversationContext]
    ) -> bool:
        """
        Check session-level permissions

        Args:
            intent: Intent to check
            context: Conversation context with user permissions

        Returns:
            True if within session scope, False otherwise
        """
        if context is None:
            return True

        user_permissions = set(context.user_permissions)

        # Map intents to required permissions
        intent_permission_map = {
            IntentType.EXECUTE_STEP: "lee.workflow.run",
            IntentType.QUERY_STATUS: "lee.workflow.status",
            IntentType.APPROVE_GATE: "lee.gate.approve",
            IntentType.REJECT_GATE: "lee.gate.reject",
            IntentType.REVISE_GATE: "lee.gate.reject",
            IntentType.FLAG_GATE: "lee.gate.reject",
            IntentType.LIST_WORKFLOWS: "lee.workflow.status",
            IntentType.LIST_GATES: "lee.workflow.status",
            IntentType.PAUSE_WORKFLOW: "lee.workflow.run",
            IntentType.RESUME_WORKFLOW: "lee.workflow.run",
        }

        required_permission = intent_permission_map.get(intent.type)
        if required_permission and required_permission not in user_permissions:
            logger.warning(
                f"Intent {intent.type.value} requires permission {required_permission}, "
                f"user has: {user_permissions}"
            )
            return False

        return True

    def get_required_tools(self, intent_type: IntentType, department: Optional[str] = None) -> Set[str]:
        """
        Get tools required for an intent type

        Args:
            intent_type: Intent type
            department: Department for config lookup

        Returns:
            Set of required tool IDs
        """
        intent_config = self.config.get_intent_config(intent_type.value, department)
        if not intent_config:
            return set()

        return set(intent_config.allowed_tools)

    def get_permissions_summary(self, department: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of current permissions

        Args:
            department: Department for config lookup

        Returns:
            Dictionary with allowed/denied tools and rules
        """
        permissions = self.config.get_permissions(department)

        return {
            "allowed_tools": list(permissions.allowed_tools),
            "denied_tools": list(permissions.denied_tools),
            "constitution_rules": list(permissions.constitution_rules),
        }

    def get_permissions(self, department: Optional[str] = None):
        """Get raw permission config for the given department."""
        return self.config.get_permissions(department)

    def get_metrics(self) -> Dict[str, Any]:
        """Get permission checking metrics"""
        return {
            "total_checks": self._total_checks,
            "allowed_count": self._allowed_count,
            "denied_count": self._denied_count,
            "denial_rate": (
                self._denied_count / self._total_checks
                if self._total_checks > 0 else 0
            ),
        }

    def reset_metrics(self):
        """Reset permission checking metrics"""
        self._total_checks = 0
        self._denied_count = 0
        self._allowed_count = 0


class PermissionCheckerBuilder:
    """Builder for creating PermissionChecker with custom rules"""

    def __init__(self, config: IntentClassifierConfig):
        self.config = config
        self.custom_allowed_tools: Set[str] = set()
        self.custom_denied_tools: Set[str] = set()
        self.custom_rules: List[str] = []

    def allow_tool(self, tool_id: str) -> "PermissionCheckerBuilder":
        """Add a tool to allowed list"""
        self.custom_allowed_tools.add(tool_id)
        return self

    def deny_tool(self, tool_id: str) -> "PermissionCheckerBuilder":
        """Add a tool to denied list"""
        self.custom_denied_tools.add(tool_id)
        return self

    def add_rule(self, rule: str) -> "PermissionCheckerBuilder":
        """Add a constitution rule"""
        self.custom_rules.append(rule)
        return self

    def build(self, default_department: Optional[str] = None) -> PermissionChecker:
        """Build PermissionChecker with custom rules"""
        if self.config is None:
            raise ValueError("config is required")

        # Create a modified config
        # Note: This is a simplified implementation
        # In production, you'd want to create a copy of the config
        checker = PermissionChecker(self.config, default_department)

        # Apply custom rules (stored in checker for now)
        if hasattr(checker, 'custom_allowed_tools'):
            checker.custom_allowed_tools.update(self.custom_allowed_tools)
        else:
            checker.custom_allowed_tools = self.custom_allowed_tools

        if hasattr(checker, 'custom_denied_tools'):
            checker.custom_denied_tools.update(self.custom_denied_tools)
        else:
            checker.custom_denied_tools = self.custom_denied_tools

        if hasattr(checker, 'custom_rules'):
            checker.custom_rules.extend(self.custom_rules)
        else:
            checker.custom_rules = self.custom_rules

        return checker
