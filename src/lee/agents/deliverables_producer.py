"""
Deliverables Producer Agent - 交付物生产专家

根据 FEAT 规格书的 outputs 定义，自动生产缺失的交付物文件。
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeliverableProductionResult:
    """Result of deliverables production"""
    feature_id: str
    produced_deliverables: List[Dict[str, Any]] = field(default_factory=list)
    production_notes: str = ""
    deliverables_production_result: str = "pass"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "produced_deliverables": self.produced_deliverables,
            "production_notes": self.production_notes,
            "deliverables_production_result": self.deliverables_production_result,
        }


class DeliverablesProducer:
    """Produces missing deliverables based on FEAT specification"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def load_feat_spec(self, feat_spec_path: str) -> Dict[str, Any]:
        """Load FEAT specification and parse YAML frontmatter"""
        path = self.project_root / feat_spec_path
        if not path.exists():
            raise FileNotFoundError(f"FEAT spec not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 2:
                yaml_content = parts[1].strip()
                return yaml.safe_load(yaml_content)
        return {}

    def get_deliverable_type(self, filename: str) -> str:
        """Determine deliverable type from filename"""
        if '.schema.yaml' in filename or '.schema.json' in filename:
            return "schema"
        elif filename.startswith('example-'):
            return "example"
        elif '-guide.md' in filename or '-usage.md' in filename:
            return "guide"
        return "other"

    def get_output_location(self, deliverable_name: str, deliverable_type: str) -> Path:
        """Determine where to save the deliverable"""
        if deliverable_type == "schema":
            return self.project_root / "spec" / "contracts" / deliverable_name
        elif deliverable_type == "example":
            return self.project_root / "examples" / deliverable_name
        elif deliverable_type == "guide":
            return self.project_root / "docs" / deliverable_name
        else:
            return self.project_root / "output" / deliverable_name

    def extract_deliverable_context(
        self,
        feat_spec: Dict[str, Any],
        deliverable_name: str,
        search_dirs: List[str]
    ) -> Dict[str, Any]:
        """Extract context for producing a deliverable"""
        outputs = self._extract_outputs(feat_spec)
        description = ""
        for output in outputs:
            if deliverable_name in str(output):
                # Extract description if available
                if isinstance(output, str) and ' ' in output:
                    parts = output.split(' ', 1)
                    if len(parts) > 1:
                        description = parts[1]
                break

        # Search for related code/context
        context_files = []
        for search_dir in search_dirs:
            search_path = self.project_root / search_dir
            if search_path.exists():
                for f in search_path.rglob("*.py"):
                    if "deliverables" in f.stem.lower() or "reviewer" in f.stem.lower():
                        context_files.append(str(f.relative_to(self.project_root)))

        return {
            "description": description,
            "related_files": context_files[:5],  # Limit to 5 files
        }

    def _extract_outputs(self, feat_spec: Dict[str, Any]) -> List[str]:
        """Extract outputs from FEAT spec"""
        outputs = feat_spec.get('outputs', [])
        if isinstance(outputs, list) and outputs:
            return [str(o) for o in outputs if o]

        properties = feat_spec.get('properties', {})
        if isinstance(properties, dict):
            outputs = properties.get('outputs', [])
            if isinstance(outputs, list):
                return [str(o) for o in outputs if o]
        return []

    def produce_schema(
        self,
        deliverable_name: str,
        feat_spec: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate a schema file"""
        feature_id = feat_spec.get('id', 'UNKNOWN')

        # Create a basic JSON schema structure
        schema_content = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": f"{deliverable_name.replace('.schema.yaml', '').replace('.', '-')}-v1",
            "title": f"{deliverable_name.replace('.schema.yaml', '').replace('_', ' ').title()}",
            "description": f"Schema for {feature_id} - {context.get('description', 'deliverable')}",
            "type": "object",
            "required": [],
            "properties": {},
            "additionalProperties": False
        }

        # Convert to YAML for .schema.yaml files
        if deliverable_name.endswith('.yaml'):
            content = yaml.dump(schema_content, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            content = json.dumps(schema_content, indent=2)

        return content

    def produce_example(
        self,
        deliverable_name: str,
        feat_spec: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate an example file"""
        feature_id = feat_spec.get('id', 'UNKNOWN')

        example_content = {
            "# Example file for": f"{feature_id}",
            "# Generated by": "agent.dev.deliverables_producer",
            "# Description": context.get('description', 'Example deliverable'),
            "example_data": {
                "id": "example-001",
                "created_at": datetime.now().isoformat(),
                "status": "example",
                "metadata": {
                    "feature_id": feature_id,
                    "generated": True
                }
            }
        }

        if deliverable_name.endswith('.json'):
            # Remove comment lines for JSON
            content = json.dumps({"example_data": example_content.get("example_data")}, indent=2)
        else:
            content = yaml.dump(example_content, default_flow_style=False, allow_unicode=True)

        return content

    def produce_guide(
        self,
        deliverable_name: str,
        feat_spec: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate a usage guide markdown file"""
        feature_id = feat_spec.get('id', 'UNKNOWN')
        feature_title = feat_spec.get('title', 'Unknown Feature')
        description = context.get('description', 'This deliverable')

        guide_name = deliverable_name.replace('.md', '').replace('-', ' ').title()

        content = f"""# {guide_name}

## Overview

{description}

This guide is part of **{feature_id}**: {feature_title}

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Examples](#examples)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)

## Introduction

{description}

### Features

- Feature 1: Description here
- Feature 2: Description here
- Feature 3: Description here

## Installation

```bash
# Install the package
pip install -e .
```

## Usage

### CLI Usage

```bash
# Basic usage
lee command --option value

# Advanced usage
lee command --config config.yaml --verbose
```

### API Usage

```python
from lee.agents import module_name

# Initialize
agent = module_name.ModuleName()

# Use the agent
result = agent.run(input_data)
```

## Examples

### Example 1: Basic Usage

```python
# Import the module
from lee.agents import module_name

# Create instance and run
agent = module_name.ModuleName()
result = agent.run({{"key": "value"}})
print(result)
```

### Example 2: Advanced Usage

```python
# Configure with options
agent = module_name.ModuleName(
    config_path="config.yaml",
    verbose=True
)
result = agent.run(data)
```

## API Reference

### Class: ModuleName

Main class for {guide_name}.

#### Methods

##### `__init__(self, **kwargs)`

Initialize the module.

**Parameters:**
- `config_path` (str, optional): Path to configuration file
- `verbose` (bool): Enable verbose output

##### `run(self, input_data: Dict) -> Dict`

Run the main logic.

**Parameters:**
- `input_data` (Dict): Input data dictionary

**Returns:**
- Dict: Result dictionary

## Troubleshooting

### Common Issues

1. **Issue**: Module not found
   - **Solution**: Ensure the package is installed correctly

2. **Issue**: Configuration error
   - **Solution**: Check config file format and paths

## Related Documentation

- FEAT Specification: {feature_id}
- Technical Spec: See TECH-{{feature_id}}

## License

Copyright (c) 2026. All rights reserved.
"""
        return content

    def produce_deliverable(
        self,
        deliverable_name: str,
        feat_spec: Dict[str, Any],
        search_dirs: List[str]
    ) -> Dict[str, Any]:
        """Produce a single deliverable"""
        deliverable_type = self.get_deliverable_type(deliverable_name)
        context = self.extract_deliverable_context(feat_spec, deliverable_name, search_dirs)

        try:
            # Generate content based on type
            if deliverable_type == "schema":
                content = self.produce_schema(deliverable_name, feat_spec, context)
            elif deliverable_type == "example":
                content = self.produce_example(deliverable_name, feat_spec, context)
            elif deliverable_type == "guide":
                content = self.produce_guide(deliverable_name, feat_spec, context)
            else:
                content = f"# {deliverable_name}\n\nGenerated placeholder content."

            # Determine output location
            output_path = self.get_output_location(deliverable_name, deliverable_type)

            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "name": deliverable_name,
                "path": str(output_path),
                "type": deliverable_type,
                "status": "produced"
            }

        except Exception as e:
            return {
                "name": deliverable_name,
                "path": "",
                "type": deliverable_type,
                "status": "failed",
                "error": str(e)
            }

    def produce_all(
        self,
        feat_spec_path: str,
        missing_deliverables: List[str],
        search_dirs: Optional[List[str]] = None
    ) -> DeliverableProductionResult:
        """Produce all missing deliverables"""
        if search_dirs is None:
            search_dirs = ["src", "spec", "docs", "examples", "output"]

        # Load FEAT spec
        feat_spec = self.load_feat_spec(feat_spec_path)
        feature_id = feat_spec.get('id', 'UNKNOWN')

        result = DeliverableProductionResult(feature_id=feature_id)

        # Produce each missing deliverable
        for deliverable in missing_deliverables:
            production_result = self.produce_deliverable(
                deliverable, feat_spec, search_dirs
            )
            result.produced_deliverables.append(production_result)

            if production_result["status"] == "failed":
                result.deliverables_production_result = "fail"

        # Generate production notes
        produced_count = sum(
            1 for d in result.produced_deliverables if d["status"] == "produced"
        )
        failed_count = len(missing_deliverables) - produced_count

        result.production_notes = (
            f"Produced {produced_count}/{len(missing_deliverables)} deliverables. "
            f"Failed: {failed_count}"
        )

        return result


def produce_deliverables(
    *,
    feat_spec_ref: str,
    missing_deliverables: List[str],
    output_base: str,
    search_dirs: Optional[List[str]] = None,
    project_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Public API for producing deliverables.

    Args:
        feat_spec_ref: Path to FEAT specification
        missing_deliverables: List of missing deliverable filenames
        output_base: Base directory for output
        search_dirs: Directories to search for context
        project_root: Project root directory

    Returns:
        Dictionary with produced_deliverables, production_notes, etc.
    """
    if project_root is None:
        project_root = os.getcwd()

    producer = DeliverablesProducer(project_root)
    result = producer.produce_all(feat_spec_ref, missing_deliverables, search_dirs)
    return result.to_dict()


if __name__ == "__main__":
    import click

    @click.group()
    def cli():
        """Deliverables Producer CLI"""
        pass

    @cli.command()
    @click.option('--feat-spec', 'feat_spec_ref', required=True, help='FEAT spec path')
    @click.option('--missing', 'missing', multiple=True, help='Missing deliverable (repeatable)')
    @click.option('--output-base', default='output', help='Output base directory')
    @click.option('--search-dirs', default='src,spec,docs,examples,output', help='Search directories')
    @click.option('--project-root', default='.', help='Project root')
    def produce(feat_spec_ref, missing, output_base, search_dirs, project_root):
        """Produce missing deliverables"""
        search_dirs_list = [d.strip() for d in search_dirs.split(',')]

        result = produce_deliverables(
            feat_spec_ref=feat_spec_ref,
            missing_deliverables=list(missing),
            output_base=output_base,
            search_dirs=search_dirs_list,
            project_root=project_root,
        )

        click.echo(f"\nDeliverables Production: {result['feature_id']}")
        click.echo(f"Status: {result['deliverables_production_result'].upper()}")
        click.echo(f"Produced: {len([d for d in result['produced_deliverables'] if d['status'] == 'produced'])}")

        for d in result['produced_deliverables']:
            status_icon = "✅" if d['status'] == 'produced' else "❌"
            click.echo(f"  {status_icon} {d['name']}: {d.get('path', d.get('error', 'N/A'))}")

        click.echo(f"\nNotes: {result['production_notes']}")

        if result['deliverables_production_result'] == 'fail':
            import sys
            sys.exit(1)

    cli()
