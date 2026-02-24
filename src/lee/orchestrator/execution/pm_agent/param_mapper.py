"""
PM Agent Parameter Mapper

Extracts workflow parameters from natural language input using LLM.
Integrates with TemplateManager for workflow discovery and validation.
"""

import json
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .models import Intent, IntentType, WorkflowParams, ConversationContext
from .exceptions import ParameterExtractionError
from lee.orchestrator.execution.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class ParamMapper:
    """
    Parameter Mapper - Single responsibility component

    Extracts workflow parameters from natural language using LLM.
    Validates extracted parameters against available workflows.
    """

    def __init__(
        self,
        llm_executor,
        template_manager: TemplateManager,
        max_retries: int = 2
    ):
        """
        Initialize Parameter Mapper

        Args:
            llm_executor: LLM executor for parameter extraction
            template_manager: Template manager for workflow discovery
            max_retries: Maximum retries on extraction failure
        """
        self.llm = llm_executor
        self.template_manager = template_manager
        self.max_retries = max_retries

        # Cache for workflow metadata
        self._workflow_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 300  # 5 minutes

        # Metrics
        self._total_extractions = 0
        self._successful_extractions = 0
        self._cache_hits = 0

    async def map_params(
        self,
        user_input: str,
        intent: Intent,
        context: Optional[ConversationContext] = None
    ) -> WorkflowParams:
        """
        Map user input to workflow parameters

        Args:
            user_input: User's natural language input
            intent: Classified intent
            context: Optional conversation context

        Returns:
            Extracted WorkflowParams

        Raises:
            ParameterExtractionError: If extraction fails
        """
        self._total_extractions += 1

        # Fast path: Try rule-based extraction for common patterns
        rule_based_params = self._try_rule_based_extraction(user_input, intent.type)
        if rule_based_params:
            if intent.type in {IntentType.RUN_WORKFLOW, IntentType.CREATE_WORKFLOW}:
                rule_based_params = await self._normalize_workflow_params(rule_based_params)
            if (
                intent.type in {
                    IntentType.EXECUTE_STEP,
                    IntentType.APPROVE_GATE,
                    IntentType.REJECT_GATE,
                    IntentType.REVISE_GATE,
                    IntentType.FLAG_GATE,
                    IntentType.PAUSE_WORKFLOW,
                    IntentType.RESUME_WORKFLOW,
                }
                and not rule_based_params.workflow_ref
                and context
                and context.current_workflow_id
            ):
                rule_based_params.workflow_ref = context.current_workflow_id
            logger.info(f"Rule-based parameter extraction successful: {rule_based_params}")
            self._successful_extractions += 1
            return rule_based_params

        # Skip parameter extraction for intents that don't require it
        if not self._intent_requires_params(intent.type):
            return WorkflowParams()

        # Discover available workflows
        workflows = await self._discover_workflows()

        # Build workflow summary for prompt
        workflow_summary = self._build_workflow_summary(workflows)

        # Build context information
        context_info = self._build_context_info(context)

        # Build system prompt
        system_prompt = self._build_extraction_system_prompt(intent.type, workflow_summary)

        # Extract parameters with retry
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._extract_with_llm(
                    user_input,
                    system_prompt,
                    context_info,
                    intent
                )

                # Validate and normalize parameters
                params = self._validate_and_normalize_params(result, workflows, intent.type)
                if (
                    intent.type in {
                        IntentType.EXECUTE_STEP,
                        IntentType.APPROVE_GATE,
                        IntentType.REJECT_GATE,
                        IntentType.REVISE_GATE,
                        IntentType.FLAG_GATE,
                        IntentType.PAUSE_WORKFLOW,
                        IntentType.RESUME_WORKFLOW,
                    }
                    and not params.workflow_ref
                    and context
                    and context.current_workflow_id
                ):
                    params.workflow_ref = context.current_workflow_id

                self._successful_extractions += 1
                logger.info(f"Parameter extraction successful: {params}")
                return params

            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"Parameter extraction attempt {attempt + 1} failed: {e}, retrying...")
                    continue
                else:
                    logger.error(f"Parameter extraction failed after {self.max_retries + 1} attempts: {e}")
                    raise ParameterExtractionError(
                        f"Failed to extract parameters: {e}",
                        intent=intent.type.value
                    ) from e

    def _intent_requires_params(self, intent_type: IntentType) -> bool:
        """Check if intent type requires parameter extraction"""
        param_intents = {
            IntentType.EXECUTE_STEP,
            IntentType.APPROVE_GATE,
            IntentType.REJECT_GATE,
            IntentType.REVISE_GATE,
            IntentType.FLAG_GATE,
            IntentType.PAUSE_WORKFLOW,
            IntentType.RESUME_WORKFLOW,
            IntentType.CREATE_WORKFLOW,
            IntentType.RUN_WORKFLOW,
        }
        return intent_type in param_intents

    async def _discover_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Discover available workflows with caching"""
        import time

        now = time.time()

        # Check cache
        if (
            self._workflow_cache
            and self._cache_timestamp
            and (now - self._cache_timestamp) < self._cache_ttl
        ):
            self._cache_hits += 1
            return self._workflow_cache

        # Discover workflows from template manager
        try:
            workflows: Dict[str, Dict[str, Any]] = {}

            # 1) Try explicit list API first.
            workflow_ids: List[str] = []
            if hasattr(self.template_manager, "list_workflows"):
                try:
                    workflow_ids = list(self.template_manager.list_workflows() or [])
                except Exception as e:
                    logger.warning(f"Failed to list workflows: {e}")

            # 2) Fallback to eager loading from template manager.
            preloaded_templates: Dict[str, Any] = {}
            if not workflow_ids and hasattr(self.template_manager, "load_all_templates"):
                try:
                    preloaded_templates = self.template_manager.load_all_templates() or {}
                    workflow_ids = list(preloaded_templates.keys())
                except Exception as e:
                    logger.warning(f"Failed to load all templates: {e}")

            # 3) Last resort for mock/custom managers.
            if not workflow_ids:
                workflow_ids = list(getattr(self.template_manager, "workflows", {}).keys())

            # Resolve template loader by capability.
            template_loader = None
            eager_load_template_details = False
            if hasattr(self.template_manager, "load_workflow"):
                template_loader = self.template_manager.load_workflow
                eager_load_template_details = True
            elif hasattr(self.template_manager, "get_template"):
                template_loader = self.template_manager.get_template

            for workflow_id in workflow_ids:
                try:
                    template = preloaded_templates.get(workflow_id)
                    if template is None and template_loader and eager_load_template_details:
                        template = template_loader(workflow_id)
                    if template is None:
                        workflows[workflow_id] = {
                            "id": workflow_id,
                            "name": workflow_id,
                            "description": "",
                            "steps": [],
                        }
                        continue

                    workflows[workflow_id] = {
                        "id": getattr(template, "id", workflow_id),
                        "name": getattr(template, "name", workflow_id),
                        "description": getattr(template, "description", ""),
                        "steps": [
                            {
                                "id": step.id,
                                "name": step.name,
                                "kind": step.kind,
                                "description": getattr(step, "description", ""),
                            }
                            for step in getattr(template, "steps", [])
                        ],
                    }
                except Exception as e:
                    logger.warning(f"Failed to load workflow {workflow_id}: {e}")

            self._workflow_cache = workflows
            self._cache_timestamp = now

            return workflows

        except Exception as e:
            logger.error(f"Workflow discovery failed: {e}")
            return {}

    def _build_workflow_summary(self, workflows: Dict[str, Dict[str, Any]]) -> str:
        """Build human-readable workflow summary for prompt"""
        if not workflows:
            return "No workflows available."

        lines = ["Available workflows:"]
        for wf_id, wf_info in workflows.items():
            lines.append(f"\n- {wf_id}: {wf_info['name']}")
            lines.append(f"  Description: {wf_info['description']}")

            if wf_info['steps']:
                lines.append(f"  Steps:")
                for step in wf_info['steps'][:5]:  # Limit to first 5 steps
                    lines.append(f"    - {step['id']}: {step['name']} ({step['kind']})")
                if len(wf_info['steps']) > 5:
                    lines.append(f"    ... and {len(wf_info['steps']) - 5} more steps")

        return "\n".join(lines)

    def _build_context_info(self, context: Optional[ConversationContext]) -> str:
        """Build context information for prompt"""
        if not context:
            return ""

        lines = []
        lines.append("\nContext:")

        if context.current_workflow_id:
            lines.append(f"Current workflow: {context.current_workflow_id}")

        if context.department:
            lines.append(f"Department: {context.department}")

        recent_history = context.get_recent_history(2)
        if recent_history:
            lines.append("\nRecent conversation:")
            for turn in recent_history:
                lines.append(f"- User: {turn.get('user_input', '')}")

        return "\n".join(lines)

    def _build_extraction_system_prompt(self, intent_type: IntentType, workflow_summary: str) -> str:
        """Build system prompt for parameter extraction"""
        base_prompt = f"""You are a parameter extractor for the LEE workflow system.

{workflow_summary}

Your task is to extract workflow parameters from user input.

Respond with a JSON object in the following format:
{{
  "workflow_ref": "workflow_id or null",
  "step_id": "step_id or null",
  "gate_id": "gate_id or null",
  "params": {{}},
  "approval_comment": "comment or null",
  "confidence": 0.0_to_1.0,
  "reasoning": "brief_explanation"
}}

"""

        intent_specific = {
            IntentType.EXECUTE_STEP: """
For EXECUTE_STEP intent:
- If user mentions a specific step name/ID, extract it as step_id
- If user mentions a workflow name/ID, extract it as workflow_ref
- If no specific step mentioned, step_id should be null (will auto-select next step)
- If user clearly asks to continue workflow (e.g. "继续工作流", "continue workflow"),
  set params.execution_mode = "until_blocked" (and optionally params.max_steps)
- params should include any additional parameters mentioned
""",
            IntentType.APPROVE_GATE: """
For APPROVE_GATE intent:
- Extract gate_id if mentioned
- Extract approval_comment if user provides reason/comment
""",
            IntentType.REJECT_GATE: """
For REJECT_GATE intent:
- Extract gate_id if mentioned
- Extract approval_comment (rejection reason) if provided
""",
            IntentType.REVISE_GATE: """
For REVISE_GATE intent:
- Extract gate_id if mentioned
- Put revise reason into approval_comment
- If target step is mentioned, put it in params.target_step
""",
            IntentType.FLAG_GATE: """
For FLAG_GATE intent:
- Extract gate_id if mentioned
- Put issue summary into approval_comment
- If issues list is explicit, put it in params.issues as array
""",
            IntentType.PAUSE_WORKFLOW: """
For PAUSE_WORKFLOW intent:
- Extract workflow_ref if user mentions it
""",
            IntentType.RESUME_WORKFLOW: """
For RESUME_WORKFLOW intent:
- Extract workflow_ref if user mentions it
""",
            IntentType.CREATE_WORKFLOW: """
For CREATE_WORKFLOW intent:
- Extract workflow_ref (template ID)
- Extract any initialization parameters in params
""",
        }

        return base_prompt + intent_specific.get(intent_type, "")

    async def _extract_with_llm(
        self,
        user_input: str,
        system_prompt: str,
        context_info: str,
        intent: Intent
    ) -> Dict[str, Any]:
        """Extract parameters using LLM"""
        full_input = f"User input: {user_input}{context_info}"
        full_input += f"\nIntent type: {intent.type.value}"

        result = await self.llm.execute({
            "prompt": full_input,
            "system_message": system_prompt,
            "temperature": 0.3,
            "max_tokens": 500
        })

        if result.get("status") != "completed":
            raise ParameterExtractionError(f"LLM execution failed: {result.get('error', 'Unknown error')}")

        response_text = result.get("generated_text", "")
        params_data = self._extract_json_object(response_text)
        if not isinstance(params_data, dict):
            raise ParameterExtractionError("No valid JSON object in LLM response")
        return params_data

    def _validate_and_normalize_params(
        self,
        params_data: Dict[str, Any],
        workflows: Dict[str, Dict[str, Any]],
        intent_type: IntentType
    ) -> WorkflowParams:
        """Validate and normalize extracted parameters"""
        # Extract workflow reference
        workflow_ref = params_data.get("workflow_ref")

        # For workflow creation/run intents, also accept params.template_id as source.
        params = params_data.get("params", {})
        if not isinstance(params, dict):
            params = {}
        if not workflow_ref and intent_type in {IntentType.CREATE_WORKFLOW, IntentType.RUN_WORKFLOW}:
            template_from_params = params.get("template_id")
            if isinstance(template_from_params, str) and template_from_params.strip():
                workflow_ref = template_from_params.strip()

        original_workflow_ref = workflow_ref
        if workflow_ref and workflow_ref not in workflows:
            # Try to fuzzy match workflow name
            workflow_ref = self._fuzzy_match_workflow(workflow_ref, workflows) or original_workflow_ref

        # Extract step ID and validate
        step_id = params_data.get("step_id")
        if step_id and workflow_ref:
            # Validate step exists in workflow
            if workflow_ref in workflows:
                step_ids = [s["id"] for s in workflows[workflow_ref]["steps"]]
                if step_id not in step_ids:
                    # Try fuzzy match
                    step_id = self._fuzzy_match_step(step_id, step_ids)
                    if not step_id:
                        logger.warning(f"Step {params_data.get('step_id')} not found in workflow {workflow_ref}")

        # Extract gate ID
        gate_id = params_data.get("gate_id")

        # Keep template_id in params synchronized with normalized workflow_ref for run/create intents.
        if workflow_ref and intent_type in {IntentType.CREATE_WORKFLOW, IntentType.RUN_WORKFLOW}:
            params["template_id"] = workflow_ref
            if original_workflow_ref and original_workflow_ref != workflow_ref:
                params["template_input"] = original_workflow_ref
                params["template_resolved"] = workflow_ref

        # Extract approval comment
        approval_comment = params_data.get("approval_comment")

        # Extract confidence
        confidence = float(params_data.get("confidence", 0.7))

        return WorkflowParams(
            workflow_ref=workflow_ref,
            step_id=step_id,
            gate_id=gate_id,
            params=params,
            approval_comment=approval_comment,
            confidence=confidence
        )

    def _fuzzy_match_workflow(
        self,
        workflow_ref: str,
        workflows: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """Fuzzy match workflow reference"""
        if not workflow_ref:
            return None
        if not workflows:
            return workflow_ref

        workflow_ref_lower = workflow_ref.lower()
        workflow_ref_norm = self._normalize_token(workflow_ref)

        # Exact match
        if workflow_ref in workflows:
            return workflow_ref

        # Case-insensitive match
        for wf_id in workflows:
            if wf_id.lower() == workflow_ref_lower:
                return wf_id

        # Name match
        for wf_id, wf_info in workflows.items():
            wf_name = str(wf_info.get("name", "")).lower()
            if workflow_ref_lower in wf_name:
                return wf_id
            if workflow_ref_norm and workflow_ref_norm in self._normalize_token(wf_name):
                return wf_id

        # ID suffix/normalized suffix match (supports short aliases like workspace_cleanup)
        for wf_id in workflows:
            wf_id_lower = wf_id.lower()
            wf_id_norm = self._normalize_token(wf_id_lower)
            if (
                wf_id_lower.endswith(f".{workflow_ref_lower}")
                or wf_id_lower.endswith(f"-{workflow_ref_lower}")
                or wf_id_norm.endswith(workflow_ref_norm)
            ):
                return wf_id

        return None

    def _fuzzy_match_step(self, step_id: str, available_steps: List[str]) -> Optional[str]:
        """Fuzzy match step ID"""
        step_id_lower = step_id.lower()

        # Exact match
        if step_id in available_steps:
            return step_id

        # Case-insensitive match
        for s in available_steps:
            if s.lower() == step_id_lower:
                return s

        # Partial match
        for s in available_steps:
            if step_id_lower in s.lower() or s.lower() in step_id_lower:
                return s

        return None

    def _try_rule_based_extraction(self, user_input: str, intent_type: IntentType) -> Optional[WorkflowParams]:
        """
        Try to extract parameters using simple regex patterns (fast path)

        This handles common patterns like:
        - "继续工作流 wf_task_123"
        - "运行 step_generate_code"
        - "批准 gate_review"

        Args:
            user_input: User's input
            intent_type: Classified intent type

        Returns:
            WorkflowParams if extraction successful, None otherwise
        """
        import re

        user_input_lower = user_input.lower().strip()
        is_continue_command = bool(re.match(r'^\s*(继续|continue)', user_input_lower, re.IGNORECASE))

        # Pattern 1: Extract workflow ID from "继续工作流 XXX" or "继续 wf_XXX"
        # Matches: "继续工作流wf_task_123", "继续 wf_abc", "continue workflow wf_123"
        workflow_patterns = [
            r'(?:继续|continue|运行|run|执行|execute)(?:工作流|workflow)?\s*(wf_[a-z0-9_]+)',
            r'(?:继续|continue|运行|run|执行|execute)(?:工作流|workflow)?\s*(workflow\.[a-z0-9_.]+)',
            r'^(?:继续|continue)(?:\s+工作流|\s+workflow)?\s*([a-z0-9_]+)',
        ]

        for pattern in workflow_patterns:
            match = re.search(pattern, user_input_lower, re.IGNORECASE)
            if match:
                workflow_id = match.group(1)
                logger.info(f"Rule-based extraction: workflow_id={workflow_id}")
                return WorkflowParams(
                    workflow_ref=workflow_id,
                    step_id=None,
                    gate_id=None,
                    params=(
                        {"execution_mode": "until_blocked", "max_steps": 20}
                        if intent_type == IntentType.EXECUTE_STEP and is_continue_command
                        else {}
                    ),
                    confidence=0.95
                )

        # Pattern 1.5: Extract template/workflow alias for RUN_WORKFLOW intent
        if intent_type in [IntentType.RUN_WORKFLOW, IntentType.CREATE_WORKFLOW]:
            # Extract directory + template using string operations (more reliable than regex for paths)
            workspace_path = None

            # Pattern: "在目录<PATH>运行工作流<TEMPLATE>" or similar
            if "在目录" in user_input:
                try:
                    start = user_input.index("在目录") + len("在目录")
                    # Find the end of the path - look for common separators or Chinese keywords
                    remaining = user_input[start:]

                    # Try to find path end markers: Chinese comma, space, or keywords
                    path_end_markers = ["，", ",", "运行", "工作流", "全新", "重新", " "]
                    end_pos = len(remaining)  # default to end of string

                    for marker in path_end_markers:
                        if marker in remaining:
                            pos = remaining.index(marker)
                            if pos < end_pos:
                                end_pos = pos

                    potential_path = remaining[:end_pos].strip()
                    # Validate it looks like a path (has : or /)
                    if ":" in potential_path or potential_path.startswith("/"):
                        workspace_path = potential_path
                        logger.debug(f"Extracted workspace_path: {workspace_path}")
                except (ValueError, IndexError):
                    pass

            # Also try pattern: "在<PATH>目录运行"
            if not workspace_path and "目录" in user_input:
                try:
                    start = user_input.index("在") + len("在")
                    end = user_input.index("目录")
                    potential_path = user_input[start:end].strip()
                    if ":" in potential_path or potential_path.startswith("/"):
                        workspace_path = potential_path
                        logger.debug(f"Extracted workspace_path (alt pattern): {workspace_path}")
                except (ValueError, IndexError):
                    pass

            # Extract template ID
            template_id = None
            # Pattern: after "工作流" keyword
            template_patterns = [
                r'(?:工作流|workflow)\s*([a-z][a-z0-9_.-]+)',
                r'(?:运行|run|execute)\s*([a-z][a-z0-9_.-]+\.[a-z][a-z0-9_.-]+)',
            ]
            for pattern in template_patterns:
                match = re.search(pattern, user_input_lower, re.IGNORECASE)
                if match:
                    template_id = match.group(1)
                    break

            # If we found both path and template
            if workspace_path and template_id:
                logger.info(f"Rule-based extraction (run workflow with dir): template_id={template_id}, workspace_path={workspace_path}")
                return WorkflowParams(
                    workflow_ref=template_id,
                    step_id=None,
                    gate_id=None,
                    params={"template_id": template_id, "workspace_path": workspace_path},
                    confidence=0.95
                )

            # Fallback: template only patterns
            template_patterns_relaxed = [
                r'(?:全新|重新|新建)?\s*(?:运行|run|执行|execute|启动|start)\s*(?:工作流|workflow)\s*([a-z][a-z0-9_.-]+)',
                r'(?:在.*目录)?(?:运行|run|执行|execute|启动|start)\s*([a-z][a-z0-9_.-]+)',
            ]
            for pattern in template_patterns_relaxed:
                match = re.search(pattern, user_input_lower, re.IGNORECASE)
                if match:
                    template_id = match.group(1)
                    # If we found a path but no template, use the extracted path
                    if workspace_path:
                        logger.info(f"Rule-based extraction (run workflow with dir, template inferred): template_id={template_id}, workspace_path={workspace_path}")
                        return WorkflowParams(
                            workflow_ref=template_id,
                            step_id=None,
                            gate_id=None,
                            params={"template_id": template_id, "workspace_path": workspace_path},
                            confidence=0.92
                        )
                    else:
                        logger.info(f"Rule-based extraction (run workflow): template_id={template_id}")
                        return WorkflowParams(
                            workflow_ref=template_id,
                            step_id=None,
                            gate_id=None,
                            params={"template_id": template_id},
                            confidence=0.92
                        )

        # Pattern 2: Extract step ID from "运行 step_XXX" or "执行 XXX_step"
        step_patterns = [
            r'(?:运行|run|执行|execute)(?:步骤|step)?\s*(step_[a-z0-9_]+)',
            r'(?:运行|run|执行|execute)\s+([a-z0-9_]+_step)',
            r'(?:运行|run|执行|execute)(?:步骤|step)?\s*([a-z0-9_]+)(?=\s|$)',
        ]

        for pattern in step_patterns:
            match = re.search(pattern, user_input_lower, re.IGNORECASE)
            if match:
                step_id = match.group(1)
                logger.info(f"Rule-based extraction: step_id={step_id}")
                return WorkflowParams(
                    workflow_ref=None,
                    step_id=step_id,
                    gate_id=None,
                    params={},
                    confidence=0.95
                )

        # Pattern 3: Extract template ID for "运行 workflow XXX"
        template_patterns = [
            r'(?:运行|run|执行|execute|启动|start)(?:工作流|workflow)?\s*([a-z][a-z0-9_.-]+\.[a-z][a-z0-9_.-]+)',
            r'(?:在.*目录)?(?:运行|run)(?:工作流|workflow)?\s*([a-z][a-z0-9_.-]+\.[a-z][a-z0-9_.-]+\.[a-z][a-z0-9_.-]+)',
            r'(?:在.*目录)?(?:运行|run)(?:工作流|workflow)?\s*([a-z][a-z0-9_.-]+\.[a-z][a-z0-9_.-]+)',
        ]

        for pattern in template_patterns:
            match = re.search(pattern, user_input_lower, re.IGNORECASE)
            if match:
                template_id = match.group(1)
                logger.info(f"Rule-based extraction: template_id={template_id}")
                return WorkflowParams(
                    workflow_ref=None,
                    step_id=None,
                    gate_id=None,
                    params={"template_id": template_id},
                    confidence=0.95
                )

        # Pattern 4: Extract gate ID for approve/reject intents
        if intent_type in [IntentType.APPROVE_GATE, IntentType.REJECT_GATE, IntentType.REVISE_GATE, IntentType.FLAG_GATE]:
            gate_patterns = [
                r'(?:批准|通过|同意|approve|accept|拒绝|reject|deny|修订|修正|revise|retry\s+gate|标记|flag)\s*(gate_[a-z0-9_]+)',
                r'(?:批准|通过|同意|approve|accept|拒绝|reject|deny|修订|修正|revise|retry\s+gate|标记|flag)\s*([a-z0-9_]+)(?=\s|$)',
            ]

            for pattern in gate_patterns:
                match = re.search(pattern, user_input_lower, re.IGNORECASE)
                if match:
                    gate_id = match.group(1)
                    # Ensure gate_id starts with "gate_"
                    if not gate_id.startswith('gate_'):
                        gate_id = f"gate_{gate_id}"
                    logger.info(f"Rule-based extraction: gate_id={gate_id}")
                    return WorkflowParams(
                        workflow_ref=None,
                        step_id=None,
                        gate_id=gate_id,
                        params={},
                        confidence=0.95
                    )

        # No rule-based match found
        # Pattern 5: pause/resume workflow command
        if intent_type in [IntentType.PAUSE_WORKFLOW, IntentType.RESUME_WORKFLOW]:
            control_patterns = [
                r'(?:暂停|pause|恢复|resume|继续执行)\s*(wf_[a-z0-9_]+)',
                r'(?:暂停|pause|恢复|resume|继续执行)\s*(workflow\.[a-z0-9_.]+)',
            ]

            for pattern in control_patterns:
                match = re.search(pattern, user_input_lower, re.IGNORECASE)
                if match:
                    workflow_id = match.group(1)
                    logger.info(f"Rule-based extraction: workflow_id={workflow_id}")
                    return WorkflowParams(
                        workflow_ref=workflow_id,
                        step_id=None,
                        gate_id=None,
                        params={},
                        confidence=0.95
                    )

        return None

    async def _normalize_workflow_params(self, params: WorkflowParams) -> WorkflowParams:
        """
        Normalize template/workflow reference for run/create intents.
        """
        candidate = params.params.get("template_id") or params.workflow_ref
        if not candidate:
            return params

        workflows = await self._discover_workflows()
        resolved = self._fuzzy_match_workflow(candidate, workflows) if workflows else candidate
        if not resolved:
            resolved = candidate

        params.workflow_ref = resolved
        params.params["template_id"] = resolved
        if candidate != resolved:
            params.params["template_input"] = candidate
            params.params["template_resolved"] = resolved
        return params

    @staticmethod
    def _normalize_token(value: str) -> str:
        """Normalize token for fuzzy matching."""
        return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

    @staticmethod
    def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract first valid JSON object from LLM output.

        Handles fenced code blocks and nested objects.
        """
        if not text:
            return None

        stripped = text.strip()
        decoder = json.JSONDecoder()

        # Fast path: direct decode.
        try:
            obj, _ = decoder.raw_decode(stripped)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # Fenced block path.
        fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

        # Sliding raw_decode path.
        for idx, ch in enumerate(text):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[idx:])
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue

        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get parameter extraction metrics"""
        return {
            "total_extractions": self._total_extractions,
            "successful_extractions": self._successful_extractions,
            "success_rate": (
                self._successful_extractions / self._total_extractions
                if self._total_extractions > 0 else 0
            ),
            "cache_hits": self._cache_hits,
            "workflow_cache_size": len(self._workflow_cache),
        }

    def clear_cache(self):
        """Clear workflow cache"""
        self._workflow_cache = {}
        self._cache_timestamp = None
