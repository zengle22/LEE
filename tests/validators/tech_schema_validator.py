"""Validate TECH markdown documents against the canonical TECH schema."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml
from jsonschema import validate as jsonschema_validate


def _split_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("TECH document must start with YAML frontmatter")
    _, rest = text.split("---\n", 1)
    frontmatter_text, body = rest.split("\n---\n", 1)
    return yaml.safe_load(frontmatter_text) or {}, body


def _section(body: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _subsection(section_text: str, heading: str) -> str:
    pattern = rf"^### {re.escape(heading)}\n(.*?)(?=^### |\Z)"
    match = re.search(pattern, section_text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_architecture_decisions(section_text: str) -> List[Dict[str, Any]]:
    matches = re.findall(
        r"### ([^\n]+)\n- decision: (.+?)\n- reason: (.+?)\n- impact:\n((?:  - .+\n?)*)",
        section_text,
        re.MULTILINE,
    )
    decisions = []
    for decision_id, decision, reason, impact_block in matches:
        impacts = [line.strip()[2:].strip() for line in impact_block.splitlines() if line.strip().startswith("-")]
        decisions.append(
            {
                "id": decision_id.strip(),
                "decision": decision.strip(),
                "reason": reason.strip(),
                "impact": impacts or ["unspecified-impact"],
            }
        )
    return decisions


def _extract_feat_mapping(section_text: str, parent_id: str) -> Dict[str, Any]:
    goal_part = _subsection(section_text, "Goal Mapping")
    acceptance_part = _subsection(section_text, "Acceptance Mapping")

    goal_mappings = []
    goal_matches = re.findall(
        r"- FEAT clause: (.+?)\n\s*TECH response: (.+?)(?=\n- FEAT clause:|\Z)",
        goal_part,
        re.DOTALL,
    )
    for feat_clause, tech_response in goal_matches:
        goal_mappings.append(
            {
                "feat_clause": feat_clause.strip(),
                "tech_response": tech_response.strip(),
            }
        )

    acceptance_mappings = []
    acceptance_matches = re.findall(
        r"- acceptance_id: `?([^`\n]+)`?\n\s*implementation_unit: `?([^`\n]+)`?\n\s*evidence_ref: `?([^`\n]+)`?",
        acceptance_part,
    )
    for acceptance_id, implementation_unit, evidence_ref in acceptance_matches:
        acceptance_mappings.append(
            {
                "acceptance_id": acceptance_id.strip(),
                "implementation_unit": implementation_unit.strip(),
                "evidence_ref": evidence_ref.strip(),
            }
        )

    return {
        "feat_id": parent_id,
        "goal_mapping": goal_mappings,
        "acceptance_mapping": acceptance_mappings,
    }


def _extract_simple_bullets(section_text: str) -> List[str]:
    return [
        line.strip()[1:].strip(" `")
        for line in section_text.splitlines()
        if line.strip().startswith("-")
    ]


def _extract_delivery_handoffs(section_text: str) -> List[Dict[str, Any]]:
    matches = re.findall(
        r"- from: `?([^`\n]+)`?\n\s*to: `?([^`\n]+)`?\n\s*artifacts:\n((?:    - .+\n?)*)",
        section_text,
    )
    handoffs = []
    for from_stage, to_stage, artifacts_block in matches:
        artifacts = [
            line.strip()[1:].strip(" `")
            for line in artifacts_block.splitlines()
            if line.strip().startswith("-")
        ]
        handoffs.append({"from": from_stage.strip(), "to": to_stage.strip(), "artifacts": artifacts})
    return handoffs


def _extract_validation_rules(section_text: str) -> List[Dict[str, Any]]:
    matches = re.findall(
        r"- rule: `?([^`\n]+)`?\n\s*description: (.+?)\n\s*severity: (blocker|major|minor)",
        section_text,
    )
    return [
        {
            "rule": rule.strip(),
            "description": description.strip(),
            "severity": severity.strip(),
        }
        for rule, description, severity in matches
    ]


def parse_tech_markdown(path: str | Path) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)

    architecture_decisions = _extract_architecture_decisions(_section(body, "Architecture Decisions"))
    feat_mapping = _extract_feat_mapping(_section(body, "Feat Mapping"), frontmatter["parent_id"])
    implementation_section = _section(body, "Implementation Rules")
    implementation_rules = {
        "required_inputs": _extract_simple_bullets(_subsection(implementation_section, "Required Inputs")),
        "required_outputs": _extract_simple_bullets(_subsection(implementation_section, "Required Outputs")),
        "forbidden_shortcuts": _extract_simple_bullets(_subsection(implementation_section, "Forbidden Shortcuts")),
    }
    delivery_handoffs = _extract_delivery_handoffs(_section(body, "Delivery Handoffs"))
    validation_rules = _extract_validation_rules(_section(body, "Validation Rules"))

    return {
        "id": frontmatter["id"],
        "ssot_type": frontmatter["ssot_type"],
        "title": frontmatter["title"],
        "parent_id": frontmatter["parent_id"],
        "derived_from_ids": frontmatter.get("derived_from_ids", []),
        "source_refs": frontmatter.get("source_refs", []),
        "architecture_decisions": architecture_decisions,
        "feat_mapping": feat_mapping,
        "implementation_rules": implementation_rules,
        "delivery_handoffs": delivery_handoffs,
        "validation_rules": validation_rules,
    }


def validate_tech_file(tech_path: str | Path, schema_path: str | Path) -> None:
    instance = parse_tech_markdown(tech_path)
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    jsonschema_validate(instance=instance, schema=schema)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate a TECH markdown document.")
    parser.add_argument("tech_path")
    parser.add_argument("schema_path")
    args = parser.parse_args()

    validate_tech_file(args.tech_path, args.schema_path)
    print("TECH schema validation passed")
