"""Project configuration validator.

Validates project.yaml files:
- Required fields (kind, version, id, name)
- Repository paths exist
- Path aliases are correctly defined
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..base import BaseValidator, ValidatorRegistry
from ..models import SpecType, ValidationIssue, ValidationResult


@ValidatorRegistry.register
class ProjectConfigValidator(BaseValidator):
    """Validates project.yaml configuration files."""

    name = "project_config"
    description = "Validates project configuration files"
    applies_to = [SpecType.PROJECT]

    # Required top-level fields
    REQUIRED_FIELDS = ["kind", "version", "id", "name"]

    # Required fields for repository entries
    REQUIRED_REPO_FIELDS = ["path"]

    def validate(
        self,
        path: Path,
        spec_type: SpecType,
        content: Any,
        result: ValidationResult,
    ) -> None:
        if not isinstance(content, dict):
            result.add_issue(ValidationIssue(
                message="project.yaml must be a YAML object",
                validator=self.name,
                severity="error",
            ))
            return

        # 1. Validate required fields
        self._validate_required_fields(content, result)

        # 2. Validate kind field
        self._validate_kind(content, result)

        # 3. Validate repositories
        self._validate_repositories(path, content, result)

        # 4. Validate path aliases
        self._validate_path_aliases(content, result)

    def _validate_required_fields(self, content: dict, result: ValidationResult) -> None:
        """Check that all required fields are present."""
        for field in self.REQUIRED_FIELDS:
            if field not in content:
                result.add_issue(ValidationIssue(
                    message=f"Missing required field: {field}",
                    validator=self.name,
                    severity="error",
                ))
            elif not content[field]:
                result.add_issue(ValidationIssue(
                    message=f"Required field '{field}' cannot be empty",
                    validator=self.name,
                    severity="error",
                ))

    def _validate_kind(self, content: dict, result: ValidationResult) -> None:
        """Validate the 'kind' field."""
        kind = content.get("kind")
        if kind and kind != "project":
            result.add_issue(ValidationIssue(
                message=f"Invalid kind: '{kind}', expected 'project'",
                validator=self.name,
                severity="error",
            ))

    def _validate_repositories(
        self, config_path: Path, content: dict, result: ValidationResult
    ) -> None:
        """Validate repository configurations and check paths exist."""
        repos = content.get("repositories", {})

        if not isinstance(repos, dict):
            result.add_issue(ValidationIssue(
                message="'repositories' must be a mapping (object)",
                validator=self.name,
                severity="error",
            ))
            return

        base_path = config_path.parent

        for repo_id, repo_config in repos.items():
            if isinstance(repo_config, str):
                # Simple format: repo_id: "path/to/repo"
                repo_path = repo_config
            elif isinstance(repo_config, dict):
                # Full format: repo_id: {type: git, path: "...", ...}
                repo_path = repo_config.get("path")
                if not repo_path:
                    result.add_issue(ValidationIssue(
                        message=f"Repository '{repo_id}' missing required field 'path'",
                        validator=self.name,
                        severity="error",
                    ))
                    continue
            else:
                result.add_issue(ValidationIssue(
                    message=f"Repository '{repo_id}' must be a string or object",
                    validator=self.name,
                    severity="error",
                ))
                continue

            # Check if path exists
            resolved_path = (base_path / repo_path).resolve()
            if not resolved_path.exists():
                result.add_issue(ValidationIssue(
                    message=f"Repository '{repo_id}' path does not exist: {resolved_path}",
                    validator=self.name,
                    severity="error",
                ))
            elif not resolved_path.is_dir():
                result.add_issue(ValidationIssue(
                    message=f"Repository '{repo_id}' path is not a directory: {resolved_path}",
                    validator=self.name,
                    severity="error",
                ))

    def _validate_path_aliases(self, content: dict, result: ValidationResult) -> None:
        """Validate path alias definitions."""
        aliases = content.get("path_aliases", {})
        repos = content.get("repositories", {})

        if not isinstance(aliases, dict):
            result.add_issue(ValidationIssue(
                message="'path_aliases' must be a mapping (object)",
                validator=self.name,
                severity="error",
            ))
            return

        for alias, target in aliases.items():
            # Check alias format (should start with @)
            if not alias.startswith("@"):
                result.add_issue(ValidationIssue(
                    message=f"Path alias '{alias}' should start with '@'",
                    validator=self.name,
                    severity="warning",
                ))

            # Check if target references a valid repository
            if isinstance(target, str) and "${repositories." in target:
                # Extract repository reference
                import re
                match = re.search(r'\$\{repositories\.(\w+)\.', target)
                if match:
                    repo_id = match.group(1)
                    if repo_id not in repos:
                        result.add_issue(ValidationIssue(
                            message=f"Path alias '{alias}' references unknown repository: {repo_id}",
                            validator=self.name,
                            severity="error",
                        ))


def validate_project_config(project_yaml_path: Path) -> Tuple[bool, List[str]]:
    """Standalone function to validate a project.yaml file.

    Args:
        project_yaml_path: Path to project.yaml

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    import yaml

    errors = []

    if not project_yaml_path.exists():
        return False, [f"project.yaml not found: {project_yaml_path}"]

    try:
        with open(project_yaml_path, encoding='utf-8') as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [f"Invalid YAML syntax: {e}"]

    if not isinstance(content, dict):
        return False, ["project.yaml must be a YAML object"]

    # Required fields
    required = ["kind", "version", "id", "name"]
    for field in required:
        if field not in content:
            errors.append(f"Missing required field: {field}")

    # Kind check
    if content.get("kind") != "project":
        errors.append(f"Invalid kind: '{content.get('kind')}', expected 'project'")

    # Repository paths
    repos = content.get("repositories", {})
    base_path = project_yaml_path.parent

    for repo_id, repo_config in repos.items():
        if isinstance(repo_config, str):
            repo_path = repo_config
        elif isinstance(repo_config, dict):
            repo_path = repo_config.get("path")
            if not repo_path:
                errors.append(f"Repository '{repo_id}' missing 'path'")
                continue
        else:
            errors.append(f"Repository '{repo_id}' invalid format")
            continue

        resolved = (base_path / repo_path).resolve()
        if not resolved.exists():
            errors.append(f"Repository '{repo_id}' path not found: {resolved}")
        elif not resolved.is_dir():
            errors.append(f"Repository '{repo_id}' path is not a directory: {resolved}")

    # Path aliases referencing unknown repos
    aliases = content.get("path_aliases", {})
    import re
    for alias, target in aliases.items():
        if isinstance(target, str) and "${repositories." in target:
            match = re.search(r'\$\{repositories\.(\w+)\.', target)
            if match:
                repo_id = match.group(1)
                if repo_id not in repos:
                    errors.append(f"Alias '{alias}' references unknown repo: {repo_id}")

    return len(errors) == 0, errors
