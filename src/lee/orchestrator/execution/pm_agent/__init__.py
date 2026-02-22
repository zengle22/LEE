"""
PM Agent Package

Natural language understanding and decision-making layer for LEE workflows.
"""

from .models import (
    Intent,
    IntentType,
    WorkflowParams,
    Decision,
    ConversationContext,
    CompiledParams,
    APIRequest,
    APIResponse,
    ExecutionContext,
    DecisionError,
    PermissionDeniedError,
    IntentRecognitionError,
    ParameterExtractionError,
    APIExecutionError,
)

from .exceptions import (
    PMAgentException,
    IntentClassificationError,
    ParameterExtractionError,
    PermissionDeniedError,
    ConfigurationError,
    SecurityError,
    LLMExecutionError,
    APIExecutionError,
    WorkflowDiscoveryError,
)

from .config import (
    IntentClassifierConfig,
    IntentConfig,
    PatternConfig,
    PermissionConfig,
    DepartmentConfig,
)

from .intent_classifier import IntentClassifier
from .param_mapper import ParamMapper
from .permission_checker import PermissionChecker
from .decision_engine import DecisionEngine
from .api_wrapper import OrchestratorAPIWrapper
from .security import (
    SecurityManager,
    PromptInjectionDetector,
    RateLimiter,
    AuditLogger,
    SecurityConfig,
)
from .cache import (
    IntentCache,
    WorkflowMetadataCache,
    APIResponseCache,
    CompositeCache,
)

__all__ = [
    # Models
    "Intent",
    "IntentType",
    "WorkflowParams",
    "Decision",
    "ConversationContext",
    "CompiledParams",
    "APIRequest",
    "APIResponse",
    "ExecutionContext",
    "DecisionError",
    "PermissionDeniedError",
    "IntentRecognitionError",
    "ParameterExtractionError",
    "APIExecutionError",
    # Exceptions
    "PMAgentException",
    "IntentClassificationError",
    "ParameterExtractionError",
    "PermissionDeniedError",
    "ConfigurationError",
    "SecurityError",
    "LLMExecutionError",
    "APIExecutionError",
    "WorkflowDiscoveryError",
    # Config
    "IntentClassifierConfig",
    "IntentConfig",
    "PatternConfig",
    "PermissionConfig",
    "DepartmentConfig",
    # Core Components
    "IntentClassifier",
    "ParamMapper",
    "PermissionChecker",
    "DecisionEngine",
    "OrchestratorAPIWrapper",
    # Security
    "SecurityManager",
    "PromptInjectionDetector",
    "RateLimiter",
    "AuditLogger",
    "SecurityConfig",
    # Cache
    "IntentCache",
    "WorkflowMetadataCache",
    "APIResponseCache",
    "CompositeCache",
]
