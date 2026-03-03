"""Workflow Generator - Generates valid workflow.yaml from templates.

This module ensures AI-generated workflows comply with standard templates,
preventing steps from being omitted or simplified.

Core principles:
1. Template provides STRUCTURAL elements (steps, dependencies, gates)
2. PhaseConfig provides CUSTOMIZATION (paths, descriptions, metadata)
3. Structural elements are IMMUTABLE - all required steps must be preserved
4. Only non-structural fields can be overridden
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import copy
import yaml
import re


@dataclass
class PhaseConfig:
    """Phase-level configuration that AI can specify.

    This defines what AI is ALLOWED to customize when generating a workflow.
    Structural elements (steps, dependencies, gates) cannot be modified.
    """
    # Required fields
    id: str                              # e.g., "phase11-logging"
    name: str                            # e.g., "日志体系改造"
    phase_dir: str                       # e.g., "project/AI跑步教练/dev/phase11"

    # Optional fields
    description: str = ""                # Multi-line phase description
    change_id: str = "CHG-001"           # OpenSpec change ID
    project_dir: str = ""                # Project root for knowledge merge

    # Step customizations (description only, not structure)
    step_descriptions: Dict[str, str] = field(default_factory=dict)

    # Path overrides for step inputs/outputs
    step_path_overrides: Dict[str, Dict] = field(default_factory=dict)

    # Gate description overrides
    gate_descriptions: Dict[str, str] = field(default_factory=dict)

    # Quality threshold overrides
    quality_overrides: Dict[str, Any] = field(default_factory=dict)

    # Output path mappings
    output_paths: Dict[str, str] = field(default_factory=dict)

    # Deliverables list
    deliverables: List[Dict[str, str]] = field(default_factory=list)

    # Standards references
    standards: List[Dict[str, Any]] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of workflow generation."""
    success: bool
    workflow_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    generated_workflow: Optional[Dict] = None
    step_count: int = 0


@dataclass
class L2InstanceConfig:
    """Configuration for L2 instance generation.

    Used to generate L2 workflow instances from L2 templates.
    """
    # Required identification
    id: str                              # Instance ID (e.g., "instance.dev.feature_timing_v1")
    name: str                            # Instance name
    template_id: str = "template.dev.feature_l2"  # L2 template to use

    # Context information
    project: str = ""
    module: str = ""
    module_version: str = ""
    prd_path: str = ""
    repos: List[Dict[str, str]] = field(default_factory=list)

    # Phase complexity overrides (optional, uses template defaults if not specified)
    phase_complexities: Optional[Dict[str, str]] = None  # {"plan": "S", "frontend_dev": "L"}

    # Additional metadata
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class L3InstanceConfig:
    """Configuration for L3 instance generation.

    Used to generate L3 workflow instances from Points.
    """
    # Point information
    point: 'Point'  # Forward reference, will be resolved at runtime

    # Parent references
    parent_l2_id: str
    parent_phase_id: str

    # Repository context
    repo_id: str

    # PRD reference
    prd_path: str = ""

    # Template
    template_id: str = "template.dev.task_l3"

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowGenerator:
    """Generates valid workflow.yaml from a template.

    Usage:
        generator = WorkflowGenerator(template_path)
        config = PhaseConfig(id="phase11", name="日志改造", phase_dir="...")
        result = generator.generate(config, output_path="./workflow.yaml")
    """

    # Step IDs that MUST exist in generated workflow (phase-openspec-flow v1.5)
    REQUIRED_STEPS = [
        "p1_openspec_init",
        "p2_requirement_calibration",
        "p3_test_contract",
        "p4_openspec_proposal",
        "p5_implementation",
        "p6_unit_test",
        "p7_code_review",
        "p8_retrospective",
        "p9_knowledge_update",
        "p10_openspec_archive",
        "p11_phase_acceptance",
        "p12_knowledge_merge",
        "p13_handover"
    ]

    # Fields that CAN be overridden (non-structural)
    OVERRIDABLE_WORKFLOW_FIELDS = [
        "name", "description", "owner", "tags", "metadata"
    ]

    OVERRIDABLE_STEP_FIELDS = [
        "name", "description"  # Structure (inputs/outputs paths) handled separately
    ]

    # Fields that CANNOT be overridden (structural)
    PROTECTED_WORKFLOW_FIELDS = [
        "kind", "version", "steps", "enforcement", "preconditions",
        "human_in_the_loop"
    ]

    PROTECTED_STEP_FIELDS = [
        "id", "depends_on", "run", "mandatory", "skip_allowed",
        "human_gate", "quality_gate", "remediation", "on_success", "on_failure"
    ]

    def __init__(self, template_path: str):
        """Initialize generator with template path.

        Args:
            template_path: Path to the template workflow.yaml
        """
        self.template_path = Path(template_path)
        self._template: Optional[Dict] = None

        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

    @property
    def template(self) -> Dict:
        """Lazy load and cache template."""
        if self._template is None:
            with open(self.template_path, encoding='utf-8') as f:
                self._template = yaml.safe_load(f)
        return self._template

    def generate(self, config: PhaseConfig, output_path: str = None) -> GenerationResult:
        """Generate a workflow.yaml from template and config.

        Args:
            config: Phase configuration with allowed overrides
            output_path: Optional output path for generated workflow

        Returns:
            GenerationResult with success status and any errors
        """
        errors = []
        warnings = []

        # 1. Deep copy template to avoid mutation
        workflow = copy.deepcopy(self.template)

        # 2. Apply instance-specific ID and kind
        workflow["id"] = config.id
        workflow["kind"] = "workflow-instance"  # Mark as generated instance

        # 3. Apply non-structural overrides
        self._apply_metadata_overrides(workflow, config, warnings)
        self._apply_path_substitutions(workflow, config, warnings)
        self._apply_step_customizations(workflow, config, warnings)
        self._apply_gate_overrides(workflow, config, warnings)
        self._apply_quality_overrides(workflow, config, warnings)
        self._add_instance_metadata(workflow, config)

        # 4. Validate result
        validation_errors = self.validate_workflow(workflow)
        if validation_errors:
            errors.extend(validation_errors)
            return GenerationResult(
                success=False,
                errors=errors,
                warnings=warnings
            )

        step_count = len(workflow.get("steps", []))

        # 5. Write output if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Custom YAML representer for multiline strings
            def str_representer(dumper, data):
                if '\n' in data:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)

            yaml.add_representer(str, str_representer)

            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(workflow, f, allow_unicode=True,
                         default_flow_style=False, sort_keys=False)

        return GenerationResult(
            success=True,
            workflow_path=str(output_path) if output_path else None,
            warnings=warnings,
            generated_workflow=workflow,
            step_count=step_count
        )

    def _apply_metadata_overrides(self, workflow: Dict, config: PhaseConfig,
                                   warnings: List[str]):
        """Apply workflow-level metadata overrides."""
        if config.name:
            workflow["name"] = config.name
        if config.description:
            workflow["description"] = config.description
        if config.metadata:
            workflow.setdefault("metadata", {}).update(config.metadata)

        # Add deliverables to metadata
        if config.deliverables:
            workflow.setdefault("metadata", {})["deliverables"] = config.deliverables

        # Add standards references
        if config.standards:
            workflow["standards"] = config.standards

    def _apply_path_substitutions(self, workflow: Dict, config: PhaseConfig,
                                   warnings: List[str]):
        """Substitute path variables in the workflow.

        IMPORTANT: For step inputs/outputs, paths must be RELATIVE to phase_dir
        since the state machine resolves them from project_dir (which IS the phase_dir).

        - "{phase_dir}/openspec/x.md" -> "openspec/x.md"  (for step paths)
        - "{project_dir}/knowledge/" -> "../../knowledge/" (relative from phase_dir)
        - "{phase_dir}" -> config.phase_dir (for other contexts like completion)
        """
        # Calculate relative path from phase_dir to project_dir
        # e.g., phase_dir = "project/foo/dev/phase11" -> project_dir = "project/foo"
        # relative = "../.."
        project_dir = config.project_dir
        if not project_dir and "/dev/" in config.phase_dir:
            project_dir = config.phase_dir.rsplit("/dev/", 1)[0]
        
        # Calculate depth from phase_dir to project_dir
        if project_dir and config.phase_dir.startswith(project_dir):
            # Count path segments after project_dir
            remaining = config.phase_dir[len(project_dir):].strip("/")
            depth = len(remaining.split("/")) if remaining else 0
            relative_to_project = "/".join([".." for _ in range(depth)])
        else:
            relative_to_project = project_dir or ""

        # Get current date for {date} substitution
        from datetime import datetime
        current_date = datetime.now().strftime("%Y%m%d")

        # For step paths: convert to relative paths
        step_substitutions = {
            "{phase_dir}/": "",  # Remove prefix, making paths relative
            "{project_dir}/": relative_to_project + "/" if relative_to_project else "",
            "{project_dir}": relative_to_project,
            "{change-id}": config.change_id,
            "{date}": current_date,
        }

        # For global sections: use full path
        global_substitutions = {
            "{phase_dir}": config.phase_dir,
            "{change-id}": config.change_id,
            "{project_dir}": project_dir or config.phase_dir,
            "{date}": current_date,
        }

        def substitute_step_paths(obj):
            """Substitute paths in steps (relative to phase_dir)."""
            if isinstance(obj, str):
                result = obj
                for pattern, replacement in step_substitutions.items():
                    if replacement is not None:
                        result = result.replace(pattern, replacement)
                return result
            elif isinstance(obj, dict):
                return {k: substitute_step_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_step_paths(item) for item in obj]
            return obj

        def substitute_global(obj):
            """Substitute paths in global sections (full paths)."""
            if isinstance(obj, str):
                result = obj
                for pattern, replacement in global_substitutions.items():
                    if replacement:
                        result = result.replace(pattern, replacement)
                return result
            elif isinstance(obj, dict):
                return {k: substitute_global(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_global(item) for item in obj]
            return obj

        # Apply step-relative substitutions to steps
        if "steps" in workflow:
            workflow["steps"] = substitute_step_paths(workflow["steps"])

        # Apply global substitutions to other sections (needs full paths)
        global_sections = [
            "completion",
            "knowledge_access_protocol",
            "outputs",
            "preconditions",
            "enforcement",
            "human_in_the_loop",
        ]
        for section in global_sections:
            if section in workflow:
                workflow[section] = substitute_global(workflow[section])

        # Apply output_paths if provided
        if config.output_paths:
            workflow["output_paths"] = config.output_paths

    def _apply_step_customizations(self, workflow: Dict, config: PhaseConfig,
                                    warnings: List[str]):
        """Apply step-level customizations (descriptions and paths only)."""
        for step in workflow.get("steps", []):
            step_id = step.get("id")

            # Apply description override
            if step_id in config.step_descriptions:
                step["description"] = config.step_descriptions[step_id]

            # Apply path overrides
            if step_id in config.step_path_overrides:
                overrides = config.step_path_overrides[step_id]

                # Override inputs (paths only)
                if "inputs" in overrides and "inputs" in step:
                    if isinstance(step["inputs"], dict):
                        step["inputs"].update(overrides["inputs"])

                # Override outputs (paths only)
                if "outputs" in overrides:
                    # Merge output path overrides
                    for i, output in enumerate(step.get("outputs", [])):
                        if isinstance(output, dict) and i < len(overrides["outputs"]):
                            output["path"] = overrides["outputs"][i].get("path", output.get("path"))

    def _apply_gate_overrides(self, workflow: Dict, config: PhaseConfig,
                               warnings: List[str]):
        """Apply human gate description overrides."""
        if not config.gate_descriptions:
            return

        for gate in workflow.get("human_in_the_loop", []):
            gate_id = gate.get("id")
            if gate_id in config.gate_descriptions:
                gate["purpose"] = config.gate_descriptions[gate_id]

    def _apply_quality_overrides(self, workflow: Dict, config: PhaseConfig,
                                  warnings: List[str]):
        """Apply quality threshold overrides."""
        if not config.quality_overrides:
            return

        # Update validation section if exists
        if "overrides" not in workflow:
            workflow["overrides"] = {}

        if "validation" not in workflow["overrides"]:
            workflow["overrides"]["validation"] = {}

        workflow["overrides"]["validation"].update(config.quality_overrides)

    def _add_instance_metadata(self, workflow: Dict, config: PhaseConfig):
        """Add generation metadata to workflow."""
        workflow.setdefault("metadata", {})
        workflow["metadata"]["generated"] = {
            "template": str(self.template_path),
            "config_id": config.id,
            "generator_version": "1.0.0"
        }

    def validate_workflow(self, workflow: Dict) -> List[str]:
        """Validate that workflow meets structural requirements.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # 1. Check all required steps exist
        step_ids = {s.get("id") for s in workflow.get("steps", [])}
        missing_steps = set(self.REQUIRED_STEPS) - step_ids
        if missing_steps:
            errors.append(
                f"Missing required steps: {', '.join(sorted(missing_steps))}"
            )

        # 2. Check step count
        expected_count = len(self.REQUIRED_STEPS)
        actual_count = len(workflow.get("steps", []))
        if actual_count < expected_count:
            errors.append(
                f"Expected at least {expected_count} steps, found {actual_count}"
            )

        # 3. Check mandatory fields preserved
        for step in workflow.get("steps", []):
            step_id = step.get("id", "unknown")
            if step.get("mandatory") is False:
                errors.append(f"Step {step_id} cannot have mandatory: false")
            if step.get("skip_allowed") is True:
                errors.append(f"Step {step_id} cannot have skip_allowed: true")

        # 4. Check enforcement section exists
        if not workflow.get("enforcement"):
            errors.append("Enforcement section is required")
        else:
            enforcement = workflow["enforcement"]
            if not enforcement.get("skip_prevention", {}).get("enabled"):
                errors.append("skip_prevention must be enabled")
            if not enforcement.get("bypass_prevention", {}).get("enabled"):
                errors.append("bypass_prevention must be enabled")

        # 5. Validate dependency chain
        errors.extend(self._validate_dependency_chain(workflow))

        return errors

    def _validate_dependency_chain(self, workflow: Dict) -> List[str]:
        """Validate the dependency chain is intact."""
        errors = []
        steps = {s["id"]: s for s in workflow.get("steps", [])}

        for step in workflow.get("steps", []):
            step_id = step.get("id")
            deps = step.get("depends_on", [])
            for dep in deps:
                if dep not in steps:
                    errors.append(
                        f"Step {step_id} depends on non-existent step: {dep}"
                    )

        # Check for circular dependencies
        visited = set()
        rec_stack = set()

        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)

            step = steps.get(step_id, {})
            for dep in step.get("depends_on", []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    errors.append(f"Circular dependency detected involving: {step_id}")
                    return True

            rec_stack.remove(step_id)
            return False

        for step_id in steps:
            if step_id not in visited:
                has_cycle(step_id)

        return errors

    @classmethod
    def load_phase_config(cls, config_path: str) -> PhaseConfig:
        """Load PhaseConfig from a phase-config.yaml file.

        Args:
            config_path: Path to phase-config.yaml

        Returns:
            PhaseConfig instance
        """
        with open(config_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return PhaseConfig(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            phase_dir=data.get("phase_dir", ""),
            change_id=data.get("change_id", "CHG-001"),
            project_dir=data.get("project_dir", ""),
            step_descriptions=data.get("step_descriptions", {}),
            step_path_overrides=data.get("step_path_overrides", {}),
            gate_descriptions=data.get("gate_descriptions", {}),
            quality_overrides=data.get("quality_overrides", {}),
            output_paths=data.get("output_paths", {}),
            deliverables=data.get("deliverables", []),
            standards=data.get("standards", []),
            metadata=data.get("metadata", {})
        )

    # ============ L2/L3 Instance Generation (P0) ============

    def generate_l2_instance(
        self,
        config: L2InstanceConfig,
        output_path: Optional[str] = None
    ) -> GenerationResult:
        """Generate L2 instance from template with complexity fields.

        Args:
            config: L2InstanceConfig with project context and phase complexities
            output_path: Optional output path for generated instance

        Returns:
            GenerationResult with success status and generated instance
        """
        errors = []
        warnings = []

        # Load L2 template
        template_path = Path("spec-global/departments/dev/workflows/templates/feature-l2-template.yaml")
        if not template_path.exists():
            # Try relative to project root
            template_path = Path(self.template_path).parent.parent.parent.parent / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates" / "feature-l2-template.yaml"

        if not template_path.exists():
            return GenerationResult(
                success=False,
                errors=["L2 template not found: feature-l2-template.yaml"]
            )

        try:
            with open(template_path, encoding='utf-8') as f:
                template = yaml.safe_load(f)
        except Exception as e:
            return GenerationResult(
                success=False,
                errors=[f"Failed to load L2 template: {e}"]
            )

        # Build instance from template
        instance = {
            "kind": "l2_workflow_instance",
            "version": template.get("version", "1.0"),
            "id": config.id,
            "template_id": config.template_id,
            "name": config.name,
            "description": config.description or template.get("description", ""),
            "status": "pending",
            "context": {
                "project": config.project,
                "module": config.module,
                "module_version": config.module_version,
                "prd_path": config.prd_path,
                "repos": config.repos,
            },
            "phases": [],
            "pma_splits": [],  # Will be populated during execution
        }

        # Add phases with complexity settings
        for phase_template in template.get("phases", []):
            phase_id = phase_template["id"]
            # Use override if provided, otherwise use template default
            complexity = config.phase_complexities.get(phase_id) if config.phase_complexities else None
            if complexity is None:
                complexity = phase_template.get("default_complexity", "M")

            instance["phases"].append({
                "id": phase_id,
                "name": phase_template.get("name", ""),
                "description": phase_template.get("description", ""),
                "complexity": complexity,
                "status": "pending",
                "l3_instance_ids": [],
            })

        # Add metadata
        if config.metadata:
            instance["metadata"] = config.metadata

        # Write output if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(instance, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return GenerationResult(
            success=True,
            workflow_path=str(output_path) if output_path else None,
            warnings=warnings,
            generated_workflow=instance,
            step_count=len(instance["phases"])
        )

    def generate_l3_instance(
        self,
        config: L3InstanceConfig,
        output_path: Optional[str] = None
    ) -> GenerationResult:
        """Generate L3 instance from Point.

        Args:
            config: L3InstanceConfig with point information
            output_path: Optional output path for generated instance

        Returns:
            GenerationResult with success status and generated instance
        """
        errors = []
        warnings = []

        # Use the template path provided during WorkflowGenerator initialization
        # This allows using L3 v3 template by passing it to the constructor
        template_path = Path(self.template_path)

        if not template_path.exists():
            # Fallback to default L3 template location
            template_path = Path("spec-global/departments/dev/workflows/templates/task-l3-template.yaml")
            if not template_path.exists():
                # Try relative to project root
                template_path = Path(self.template_path).parent.parent.parent.parent / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates" / "task-l3-template.yaml"

        if not template_path.exists():
            return GenerationResult(
                success=False,
                errors=[f"L3 template not found: {self.template_path}"]
            )

        try:
            with open(template_path, encoding='utf-8') as f:
                template = yaml.safe_load(f)
        except Exception as e:
            return GenerationResult(
                success=False,
                errors=[f"Failed to load L3 template: {e}"]
            )

        # Build instance from template
        point = config.point
        instance = {
            "kind": "l3_workflow_instance",
            "version": template.get("version", "1.0"),
            "id": f"instance.l3.{point.id}",
            "template_id": config.template_id,
            "name": f"L3: {point.title}",
            "description": point.desc,
            "status": "pending",
            # Point reference
            "point_id": point.id,
            # Parent references
            "parent_l2_id": config.parent_l2_id,
            "parent_phase_id": config.parent_phase_id,
            # Repository context
            "repo_id": config.repo_id,
            # PRD reference
            "prd_path": config.prd_path,
            # Point data
            "point": {
                "id": point.id,
                "title": point.title,
                "desc": point.desc,
                "layer": point.layer,
                "estimated_complexity": point.estimated_complexity.value,
                "files_hint": point.files_hint,
                "depends_on": point.depends_on,
            },
            # Steps from template
            "steps": template.get("steps", []),
        }

        # Add metadata
        if config.metadata:
            instance["metadata"] = config.metadata

        # Write output if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(instance, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return GenerationResult(
            success=True,
            workflow_path=str(output_path) if output_path else None,
            warnings=warnings,
            generated_workflow=instance,
            step_count=len(instance["steps"])
        )


def validate_workflow_against_template(
    workflow_path: str,
    template_path: str
) -> Tuple[bool, List[str]]:
    """Validate a workflow file against a template.

    This is used by orchestrator init to verify workflows are complete.

    Args:
        workflow_path: Path to the workflow.yaml to validate
        template_path: Path to the template to validate against

    Returns:
        (is_valid, list of error messages)
    """
    errors = []

    try:
        with open(workflow_path, encoding='utf-8') as f:
            workflow = yaml.safe_load(f)
    except Exception as e:
        return False, [f"Failed to load workflow: {e}"]

    try:
        generator = WorkflowGenerator(template_path)
    except Exception as e:
        return False, [f"Failed to load template: {e}"]

    # Get template step IDs
    template_step_ids = {s.get("id") for s in generator.template.get("steps", [])}
    workflow_step_ids = {s.get("id") for s in workflow.get("steps", [])}

    # Check for missing steps
    missing = template_step_ids - workflow_step_ids
    if missing:
        errors.append(
            f"Missing {len(missing)} required steps from template: "
            f"{', '.join(sorted(missing))}"
        )

    # Check for extra steps (warning, not error)
    extra = workflow_step_ids - template_step_ids
    if extra:
        # This is allowed - phases can add extra steps
        pass

    # Check step count
    template_count = len(generator.template.get("steps", []))
    workflow_count = len(workflow.get("steps", []))

    if workflow_count < template_count:
        errors.append(
            f"Workflow has fewer steps ({workflow_count}) than "
            f"template requires ({template_count})"
        )

    return len(errors) == 0, errors
