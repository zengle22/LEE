"""
PM Agent Custom Exceptions

Custom exception classes for PM Agent components.
"""

from typing import Optional, Dict, Any


class PMAgentException(Exception):
    """Base exception for PM Agent errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class IntentClassificationError(PMAgentException):
    """Exception raised when intent classification fails"""

    def __init__(self, message: str, input_text: Optional[str] = None):
        super().__init__(message)
        self.input_text = input_text


class ParameterExtractionError(PMAgentException):
    """Exception raised when parameter extraction fails"""

    def __init__(self, message: str, intent: Optional[str] = None):
        super().__init__(message)
        self.intent = intent


class PermissionDeniedError(PMAgentException):
    """Exception raised when permission check fails"""

    def __init__(self, message: str, action: Optional[str] = None, required_permission: Optional[str] = None):
        super().__init__(message)
        self.action = action
        self.required_permission = required_permission


class ConfigurationError(PMAgentException):
    """Exception raised when configuration is invalid"""

    def __init__(self, message: str, config_path: Optional[str] = None):
        super().__init__(message)
        self.config_path = config_path


class SecurityError(PMAgentException):
    """Exception raised when a security issue is detected"""

    def __init__(self, message: str, security_issue: Optional[str] = None):
        super().__init__(message)
        self.security_issue = security_issue


class LLMExecutionError(PMAgentException):
    """Exception raised when LLM execution fails"""

    def __init__(self, message: str, retry_count: Optional[int] = None):
        super().__init__(message)
        self.retry_count = retry_count


class APIExecutionError(PMAgentException):
    """Exception raised when API execution fails"""

    def __init__(self, message: str, action: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.action = action
        self.status_code = status_code


class WorkflowDiscoveryError(PMAgentException):
    """Exception raised when workflow discovery fails"""

    def __init__(self, message: str, workflow_ref: Optional[str] = None):
        super().__init__(message)
        self.workflow_ref = workflow_ref
