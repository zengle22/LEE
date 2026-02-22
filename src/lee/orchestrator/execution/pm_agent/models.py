"""
PM Agent Shared Data Models

Common data structures used across PM Agent components.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime


class IntentType(Enum):
    """Intent type enumeration"""
    QUERY_STATUS = "query_status"
    EXECUTE_STEP = "execute_step"
    LIST_WORKFLOWS = "list_workflows"
    LIST_GATES = "list_gates"
    APPROVE_GATE = "approve_gate"
    REJECT_GATE = "reject_gate"
    REVISE_GATE = "revise_gate"
    FLAG_GATE = "flag_gate"
    PAUSE_WORKFLOW = "pause_workflow"
    RESUME_WORKFLOW = "resume_workflow"
    CREATE_WORKFLOW = "create_workflow"
    RUN_WORKFLOW = "run_workflow"
    SHOW_HELP = "show_help"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Recognized intent from user input"""
    type: IntentType
    confidence: float
    reasoning: str
    matched_pattern: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowParams:
    """Extracted workflow parameters"""
    workflow_ref: Optional[str] = None
    step_id: Optional[str] = None
    gate_id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    approval_comment: Optional[str] = None
    confidence: float = 0.0


@dataclass
class Decision:
    """Decision made by Decision Engine"""
    intent: Intent
    params: WorkflowParams
    action: str
    allowed: bool = True
    denial_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Context for a conversation session"""
    session_id: str
    user_id: Optional[str] = None
    department: Optional[str] = None
    user_permissions: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    current_workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, user_input: str, decision: Decision, response: str):
        """Add a conversation turn"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'decision': {
                'intent_type': decision.intent.type.value,
                'action': decision.action,
                'allowed': decision.allowed,
            },
            'response': response
        })

    def get_recent_history(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        return self.history[-count:]


@dataclass
class CompiledParams:
    """Compiled parameters from user prompt"""
    workflow_ref: str
    params: Dict[str, Any]
    confidence: float
    reasoning: str


@dataclass
class APIRequest:
    """API request to Orchestrator"""
    action: str
    params: Dict[str, Any]
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class APIResponse:
    """API response from Orchestrator"""
    status: str
    data: Dict[str, Any]
    error: Optional[str] = None
    action: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionContext:
    """Context for executing a decision"""
    project_dir: str
    workflow_id: Optional[str] = None
    session_id: Optional[str] = None
    user_permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DecisionError(Exception):
    """Base exception for decision errors"""
    pass


class PermissionDeniedError(DecisionError):
    """Exception raised when permission is denied"""
    pass


class IntentRecognitionError(DecisionError):
    """Exception raised when intent recognition fails"""
    pass


class ParameterExtractionError(DecisionError):
    """Exception raised when parameter extraction fails"""
    pass


class APIExecutionError(DecisionError):
    """Exception raised when API execution fails"""
    pass
