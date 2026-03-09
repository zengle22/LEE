#!/usr/bin/env python
"""
Lint L3 Workflow Templates against JSON Schema

Usage:
    python scripts/lint_l3_templates.py [paths...]
    
If no paths provided, scans all L3 templates in spec-global/departments/*/workflows/
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    print("❌ Missing dependency: jsonschema")
    print("   Install with: pip install jsonschema")
    sys.exit(1)


# L3 Workflow Template JSON Schema
L3_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://lee-framework.dev/schemas/l3_workflow_template.schema.json",
    "title": "LEE L3 Workflow Template",
    "type": "object",
    "required": ["kind", "version", "id", "name", "stages"],
    "properties": {
        "kind": {"const": "l3_workflow_template"},
        "version": {"type": "string"},
        "id": {"type": "string", "minLength": 3},
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "owner": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "stages": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/$defs/stage"}
        },
        "stage_order": {
            "type": "array",
            "items": {"type": "string"}
        },
        "instance_schema": {"type": "object"}
    },
    "allOf": [
        {
            "description": "Hard rule: root-level 'steps' is forbidden.",
            "not": {"required": ["steps"]}
        }
    ],
    "additionalProperties": True,
    "$defs": {
        "gate": {
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["human_review", "human_approval", "auto_check"]
                },
                "gate_id": {"type": "string"},
                "on_pass": {"type": "string"},
                "on_fail": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object"}
                    ]
                }
            },
            "additionalProperties": True
        },
        "stage": {
            "type": "object",
            "required": ["id", "name", "kind"],
            "properties": {
                "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                "name": {"type": "string"},
                "kind": {"const": "stage"},
                "description": {"type": "string"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "gate": {"$ref": "#/$defs/gate"},
                "steps": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/step"}
                },
                "step_order": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "additionalProperties": True
        },
        "step": {
            "type": "object",
            "required": ["id", "name", "kind", "mandatory", "depends_on"],
            "properties": {
                "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                "name": {"type": "string"},
                "kind": {"type": "string", "enum": ["agent", "skill", "gate"]},
                "description": {"type": "string"},
                "mandatory": {"type": "boolean"},
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "agent_id": {"type": "string"},
                "skill_id": {"type": "string"},
                "on_failure": {"type": "string"},
                "condition": {"type": "string"},
                "gate": {"$ref": "#/$defs/gate"},
                "input": {"type": "object"},
                "outputs": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "object"}
                        ]
                    }
                },
                "role_constraints": {"type": "object"},
                "checks": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            },
            "allOf": [
                {
                    "description": "agent step must have agent_id",
                    "if": {"properties": {"kind": {"const": "agent"}}},
                    "then": {"required": ["agent_id"]}
                },
                {
                    "description": "skill step must have skill_id",
                    "if": {
                        "properties": {"kind": {"const": "skill"}},
                        "not": {
                            "properties": {
                                "config": {
                                    "type": "object",
                                    "properties": {
                                        "execution": {
                                            "type": "object",
                                            "required": ["command"],
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "then": {"required": ["skill_id"]}
                },
                {
                    "description": "gate step must provide gate config",
                    "if": {"properties": {"kind": {"const": "gate"}}},
                    "then": {
                        "properties": {
                            "config": {
                                "type": "object",
                                "required": ["gate"],
                                "properties": {
                                    "gate": {"$ref": "#/$defs/gate"}
                                }
                            }
                        },
                        "required": ["config"]
                    }
                }
            ],
            "additionalProperties": True
        }
    }
}


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load YAML file and return parsed content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def find_l3_templates(paths: List[Path]) -> List[Path]:
    """Find all L3 workflow template files in given paths."""
    templates = []
    
    for path in paths:
        if path.is_file() and path.suffix in ('.yaml', '.yml'):
            templates.append(path)
        elif path.is_dir():
            # Search recursively for workflow templates
            for yaml_file in path.rglob("*.yaml"):
                try:
                    data = load_yaml_file(yaml_file)
                    if data and data.get('kind') == 'l3_workflow_template':
                        templates.append(yaml_file)
                except Exception:
                    continue
    
    return sorted(set(templates))


def validate_template(file_path: Path) -> List[str]:
    """
    Validate a single L3 template against the schema.
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    try:
        data = load_yaml_file(file_path)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]
    
    # Create validator
    validator = Draft202012Validator(L3_SCHEMA)
    
    # Validate
    for error in validator.iter_errors(data):
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        errors.append(f"{path}: {error.message}")
    
    return errors


def lint_templates(paths: List[Path], verbose: bool = True) -> bool:
    """
    Lint all L3 templates in given paths.
    
    Returns:
        True if all templates are valid, False otherwise
    """
    templates = find_l3_templates(paths)
    
    if not templates:
        print("⚠️  No L3 templates found")
        return True
    
    print(f"📋 Found {len(templates)} L3 template(s):\n")
    
    all_valid = True
    error_summary = []
    
    for template_path in templates:
        try:
            rel_path = template_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = template_path
        print(f"📄 {rel_path}")
        
        errors = validate_template(template_path)
        
        if errors:
            all_valid = False
            error_summary.append((rel_path, errors))
            for error in errors:
                print(f"   ❌ {error}")
        else:
            print(f"   ✅ Valid")
        
        if verbose:
            # Print additional info
            try:
                data = load_yaml_file(template_path)
                stages_count = len(data.get('stages', []))
                total_steps = sum(
                    len(stage.get('steps', []))
                    for stage in data.get('stages', [])
                )
                print(f"   📊 {stages_count} stages, {total_steps} total steps")
            except Exception:
                pass
        
        print()
    
    # Print summary
    print("=" * 60)
    if all_valid:
        print("✅ All templates are valid")
    else:
        print(f"❌ {len(error_summary)} template(s) have validation errors:")
        for rel_path, errors in error_summary:
            print(f"   - {rel_path}: {len(errors)} error(s)")
        print()
        print("💡 Tip: Run 'python scripts/migrate_l3_templates.py' to auto-fix old format")
    
    return all_valid


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Lint L3 Workflow Templates against JSON Schema"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("spec-global/departments")],
        help="Paths to lint (default: spec-global/departments)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode (only show errors)"
    )
    
    args = parser.parse_args()
    
    # Validate paths exist
    for path in args.paths:
        if not path.exists():
            print(f"❌ Path not found: {path}")
            sys.exit(1)
    
    # Run lint
    all_valid = lint_templates(args.paths, verbose=not args.quiet)
    
    # Exit code
    if all_valid:
        print("✅ All templates are valid")
        sys.exit(0)
    else:
        print("❌ Some templates have validation errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
