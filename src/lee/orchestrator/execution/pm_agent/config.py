"""
PM Agent Configuration System

Manages intent classification patterns, permission rules, and
department-specific configuration overrides.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Import IntentType from models to avoid duplication
from .models import IntentType

@dataclass
class PatternConfig:
    """Pattern configuration for intent matching"""
    regex: str
    priority: int = 1
    case_sensitive: bool = False
    description: str = ""

@dataclass
class IntentConfig:
    """Configuration for a single intent"""
    type: IntentType
    patterns: List[PatternConfig] = field(default_factory=list)
    llm_fallback: bool = True
    allowed_tools: List[str] = field(default_factory=list)
    requires_params: bool = False
    description: str = ""

@dataclass
class PermissionConfig:
    """Permission configuration"""
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
    constitution_rules: List[str] = field(default_factory=list)

@dataclass
class DepartmentConfig:
    """Department-specific configuration"""
    department_id: str
    intents: Dict[str, IntentConfig] = field(default_factory=dict)
    permissions: Optional[PermissionConfig] = None
    custom_patterns: Dict[str, List[PatternConfig]] = field(default_factory=dict)

class IntentClassifierConfig:
    """
    Intent Classifier Configuration Manager

    Loads and manages intent classification patterns from YAML configuration.
    Supports department-specific overrides and hierarchical configuration.
    """

    DEFAULT_CONFIG_PATH = "config/intent_classifier.yaml"

    def __init__(self, config_path: Optional[str] = None, project_root: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_path: Path to configuration file (relative to project_root)
            project_root: Project root directory
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config_path = Path(config_path) if config_path else self.project_root / self.DEFAULT_CONFIG_PATH

        # Configuration cache
        self._intents: Dict[str, IntentConfig] = {}
        self._permissions: PermissionConfig = PermissionConfig()
        self._departments: Dict[str, DepartmentConfig] = {}

        # Load configuration
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file"""
        # Try to load from config path
        config_file = self.config_path
        if not config_file.is_absolute():
            config_file = self.project_root / config_file

        if not config_file.exists():
            # Use default configuration
            self._load_default_config()
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}

            # Load intents
            self._load_intents(config_data.get('intents', {}))

            # Load permissions
            self._load_permissions(config_data.get('permissions', {}))

            # Load department-specific configs
            self._load_departments(config_data.get('departments', {}))

        except Exception as e:
            # Fallback to default config on error
            self._load_default_config()

    def _load_intents(self, intents_data: Dict[str, Any]):
        """Load intent configurations"""
        for intent_id, intent_data in intents_data.items():
            try:
                intent_type = IntentType(intent_id)
            except ValueError:
                continue

            # Load patterns
            patterns = []
            for pattern_data in intent_data.get('patterns', []):
                patterns.append(PatternConfig(
                    regex=pattern_data.get('regex', ''),
                    priority=pattern_data.get('priority', 1),
                    case_sensitive=pattern_data.get('case_sensitive', False),
                    description=pattern_data.get('description', '')
                ))

            self._intents[intent_id] = IntentConfig(
                type=intent_type,
                patterns=patterns,
                llm_fallback=intent_data.get('llm_fallback', True),
                allowed_tools=intent_data.get('allowed_tools', []),
                requires_params=intent_data.get('requires_params', False),
                description=intent_data.get('description', '')
            )

    def _load_permissions(self, permissions_data: Dict[str, Any]):
        """Load permission configuration"""
        self._permissions = PermissionConfig(
            allowed_tools=permissions_data.get('allowed_tools', []),
            denied_tools=permissions_data.get('denied_tools', []),
            constitution_rules=permissions_data.get('constitution_rules', [])
        )

    def _load_departments(self, departments_data: Dict[str, Any]):
        """Load department-specific configurations"""
        for dept_id, dept_data in departments_data.items():
            # Load department-specific intents
            dept_intents = {}
            for intent_id, intent_data in dept_data.get('intents', {}).items():
                try:
                    intent_type = IntentType(intent_id)
                except ValueError:
                    continue

                patterns = []
                for pattern_data in intent_data.get('patterns', []):
                    patterns.append(PatternConfig(
                        regex=pattern_data.get('regex', ''),
                        priority=pattern_data.get('priority', 1),
                        case_sensitive=pattern_data.get('case_sensitive', False),
                        description=pattern_data.get('description', '')
                    ))

                dept_intents[intent_id] = IntentConfig(
                    type=intent_type,
                    patterns=patterns,
                    llm_fallback=intent_data.get('llm_fallback', True),
                    allowed_tools=intent_data.get('allowed_tools', []),
                    requires_params=intent_data.get('requires_params', False),
                    description=intent_data.get('description', '')
                )

            # Load department permissions
            permissions = None
            if 'permissions' in dept_data:
                perm_data = dept_data['permissions']
                permissions = PermissionConfig(
                    allowed_tools=perm_data.get('allowed_tools', []),
                    denied_tools=perm_data.get('denied_tools', []),
                    constitution_rules=perm_data.get('constitution_rules', [])
                )

            self._departments[dept_id] = DepartmentConfig(
                department_id=dept_id,
                intents=dept_intents,
                permissions=permissions,
                custom_patterns=dept_data.get('custom_patterns', {})
            )

    def _load_default_config(self):
        """Load default configuration when file is not available"""
        # Default intent patterns
        default_intents = {
            'query_status': IntentConfig(
                type=IntentType.QUERY_STATUS,
                patterns=[
                    PatternConfig(regex=r'^(当前)?状态|status|state', priority=1, description='Status query'),
                    PatternConfig(regex=r'^查看|显示|列出|list|show', priority=2, description='List/show query'),
                    PatternConfig(regex=r'^怎么.*了|如何.*了|完成.*了', priority=3, description='Progress query'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.workflow.status'],
                description='Query workflow status and progress'
            ),
            'execute_step': IntentConfig(
                type=IntentType.EXECUTE_STEP,
                patterns=[
                    PatternConfig(regex=r'^(运行|执行|跑|run|execute)', priority=1, description='Execute command'),
                    PatternConfig(regex=r'^(开始|启动|start)', priority=2, description='Start command'),
                    PatternConfig(regex=r'^(继续|continue)', priority=3, description='Continue command'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.workflow.run'],
                requires_params=True,
                description='Execute a workflow step'
            ),
            'approve_gate': IntentConfig(
                type=IntentType.APPROVE_GATE,
                patterns=[
                    PatternConfig(regex=r'^(批准|通过|同意|approve|accept)', priority=1, description='Approve gate'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.gate.approve'],
                requires_params=True,
                description='Approve a human gate'
            ),
            'reject_gate': IntentConfig(
                type=IntentType.REJECT_GATE,
                patterns=[
                    PatternConfig(regex=r'^(拒绝|reject|deny)', priority=1, description='Reject gate'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.gate.reject'],
                requires_params=True,
                description='Reject a human gate'
            ),
            'revise_gate': IntentConfig(
                type=IntentType.REVISE_GATE,
                patterns=[
                    PatternConfig(regex=r'^(修订|修正|revise|retry gate)', priority=1, description='Revise gate'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.gate.reject'],
                requires_params=True,
                description='Revise a human gate and retry'
            ),
            'flag_gate': IntentConfig(
                type=IntentType.FLAG_GATE,
                patterns=[
                    PatternConfig(regex=r'^(标记|flag)', priority=1, description='Flag gate'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.gate.reject'],
                requires_params=True,
                description='Flag issues on a human gate'
            ),
            'list_workflows': IntentConfig(
                type=IntentType.LIST_WORKFLOWS,
                patterns=[
                    PatternConfig(regex=r'^有哪些工作流|工作流列表|list.*workflow', priority=1, description='List workflows'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.workflow.status'],
                description='List available workflows'
            ),
            'list_gates': IntentConfig(
                type=IntentType.LIST_GATES,
                patterns=[
                    PatternConfig(
                        regex=(
                            r'^(有哪些门禁|门禁列表|查看.*(门禁|gate|gates)|显示.*(门禁|gate|gates)'
                            r'|列出.*(门禁|gate|gates)|当前.*(门禁|gate|gates)|查.*(门禁|gate|gates)'
                            r'|list.*gate|gate.*有哪些)'
                        ),
                        priority=1,
                        description='List gates',
                    ),
                ],
                llm_fallback=True,
                allowed_tools=['lee.workflow.status'],
                description='List gates'
            ),
            'pause_workflow': IntentConfig(
                type=IntentType.PAUSE_WORKFLOW,
                patterns=[
                    PatternConfig(regex=r'^(暂停|pause)', priority=1, description='Pause workflow'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.workflow.run'],
                requires_params=True,
                description='Pause workflow execution'
            ),
            'resume_workflow': IntentConfig(
                type=IntentType.RESUME_WORKFLOW,
                patterns=[
                    PatternConfig(regex=r'^(恢复|继续执行|resume)', priority=1, description='Resume workflow'),
                ],
                llm_fallback=True,
                allowed_tools=['lee.workflow.run'],
                requires_params=True,
                description='Resume paused workflow execution'
            ),
            'run_workflow': IntentConfig(
                type=IntentType.RUN_WORKFLOW,
                patterns=[
                    PatternConfig(
                        regex=r'^(全新|重新|新建)?\s*(运行|run|执行|execute|启动|start).*(工作流|workflow)\s*[a-z][a-z0-9_.-]+',
                        priority=0,
                        description='Run workflow template',
                    ),
                    PatternConfig(
                        regex=r'^(运行|run|执行|execute|启动|start).*\s+([a-z][a-z0-9_]+\.)?[a-z][a-z0-9_]+\.[a-z][a-z0-9_]+',
                        priority=1,
                        description='Run workflow by template id',
                    ),
                ],
                llm_fallback=True,
                allowed_tools=['lee.workflow.run'],
                requires_params=True,
                description='Run a workflow template'
            ),
            'show_help': IntentConfig(
                type=IntentType.SHOW_HELP,
                patterns=[
                    PatternConfig(regex=r'^(帮助|help|怎么用|使用指南)', priority=1, description='Help request'),
                ],
                llm_fallback=False,
                allowed_tools=[],
                description='Show help information'
            ),
        }

        self._intents = default_intents
        self._permissions = PermissionConfig(
            allowed_tools=[
                'lee.workflow.run',
                'lee.workflow.status',
                'lee.gate.approve',
                'lee.gate.reject',
                'lee.step.retry',
                'lee.run.verify',
                'lee.context.query',
            ],
            denied_tools=[
                'shell',
                'git',
                'file_write',
            ],
            constitution_rules=[
                'All code changes must go through workflow -> executor -> patch/receipt',
                'On failure, only allow: retry | human_gate_required | switch_executor',
            ]
        )

    def get_intent_config(self, intent_id: str, department: Optional[str] = None) -> Optional[IntentConfig]:
        """
        Get intent configuration

        Args:
            intent_id: Intent identifier
            department: Department ID for department-specific config

        Returns:
            IntentConfig or None
        """
        # Check department-specific config first
        if department and department in self._departments:
            dept_config = self._departments[department]
            if intent_id in dept_config.intents:
                return dept_config.intents[intent_id]

        return self._intents.get(intent_id)

    def get_all_intents(self, department: Optional[str] = None) -> Dict[str, IntentConfig]:
        """Get all intent configurations"""
        if department and department in self._departments:
            dept_config = self._departments[department]
            # Merge department-specific with default
            merged = dict(self._intents)
            merged.update(dept_config.intents)
            return merged
        return self._intents

    def get_permissions(self, department: Optional[str] = None) -> PermissionConfig:
        """Get permission configuration"""
        if department and department in self._departments and self._departments[department].permissions:
            return self._departments[department].permissions
        return self._permissions

    def get_patterns_for_intent(self, intent_id: str, department: Optional[str] = None) -> List[PatternConfig]:
        """Get all patterns for a specific intent"""
        config = self.get_intent_config(intent_id, department)
        return config.patterns if config else []

    def validate(self) -> List[str]:
        """
        Validate configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate intent patterns
        for intent_id, intent_config in self._intents.items():
            for pattern in intent_config.patterns:
                try:
                    re.compile(pattern.regex)
                except re.error as e:
                    errors.append(f"Invalid regex in intent '{intent_id}': {pattern.regex} - {e}")

        # Validate permissions
        for tool in self._permissions.allowed_tools:
            if tool in self._permissions.denied_tools:
                errors.append(f"Tool '{tool}' is both allowed and denied")

        return errors
