"""
Agent Context Injector - Minimal Implementation

This is a placeholder implementation to unblock the CLI.
The full implementation should handle context injection to various AI tools.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InjectionResult:
    """Context injection result"""
    success: bool
    injector_name: str
    context_location: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class AgentContext:
    """Agent context data class"""

    def __init__(self, agent_id: str, agent_name: str, context: Dict[str, Any]):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.context = context


class BaseInjector:
    """Base injector class"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def inject_context(self, context: AgentContext) -> InjectionResult:
        """Inject context - to be implemented by subclasses"""
        return InjectionResult(
            success=False,
            injector_name="base",
            details={"error": "Not implemented"}
        )

    def get_current_context(self) -> Optional[Dict[str, Any]]:
        """Get current injected context"""
        return None

    def clear_context(self) -> bool:
        """Clear injected context"""
        return False


class DefaultInjector(BaseInjector):
    """Default injector implementation"""

    def inject_context(self, context: AgentContext) -> InjectionResult:
        """Inject context to default location"""
        context_file = self.project_path / ".workflow" / "current-context.yaml"

        try:
            context_file.parent.mkdir(parents=True, exist_ok=True)

            import yaml
            with open(context_file, 'w', encoding='utf-8') as f:
                yaml.dump({
                    'agent_id': context.agent_id,
                    'agent_name': context.agent_name,
                    **context.context
                }, f, allow_unicode=True)

            return InjectionResult(
                success=True,
                injector_name="default",
                context_location=str(context_file),
                details={
                    'agent_id': context.agent_id,
                    'agent_name': context.agent_name
                }
            )
        except Exception as e:
            return InjectionResult(
                success=False,
                injector_name="default",
                details={'error': str(e)}
            )

    def get_current_context(self) -> Optional[Dict[str, Any]]:
        """Get current injected context"""
        context_file = self.project_path / ".workflow" / "current-context.yaml"

        if context_file.exists():
            import yaml
            with open(context_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return None

    def clear_context(self) -> bool:
        """Clear injected context"""
        context_file = self.project_path / ".workflow" / "current-context.yaml"

        if context_file.exists():
            context_file.unlink()
            return True
        return False


class InjectorRegistry:
    """Registry for context injectors"""

    _injectors: Dict[str, type] = {
        "default": DefaultInjector,
    }

    @classmethod
    def register(cls, name: str, injector_class: type):
        """Register a new injector"""
        cls._injectors[name] = injector_class

    @classmethod
    def create_injector(cls, project_path: str, injector_name: Optional[str] = None) -> Optional[BaseInjector]:
        """Create an injector instance

        Args:
            project_path: Project directory path
            injector_name: Injector name (if None, returns default injector)

        Returns:
            Injector instance or None if not found
        """
        if injector_name is None or injector_name == "auto":
            injector_name = "default"

        injector_class = cls._injectors.get(injector_name)
        if injector_class:
            return injector_class(project_path)
        return None

    @classmethod
    def list_injectors(cls) -> List[str]:
        """List all registered injectors"""
        return list(cls._injectors.keys())
