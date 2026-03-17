#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FEAT2PLAN L2 Workflow Executor - SRC-046 Bundle

This script executes the FEAT2PLAN L2 workflow using the official SRC-046 FEAT bundle
as input, generating RELEASE, DEVPLAN, and TESTPLAN objects.

Usage:
    python scripts/execute_feat2plan_src046.py
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_yaml_with_frontmatter(file_path: Path) -> Dict[str, Any]:
    """Load YAML file with frontmatter support."""
    content = file_path.read_text(encoding='utf-8')

    # Handle YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 2:
            yaml_content = parts[1]
            return yaml.safe_load(yaml_content)

    return yaml.safe_load(content)


def load_md_with_frontmatter(file_path: Path) -> Dict[str, Any]:
    """Load Markdown file with YAML frontmatter."""
    content = file_path.read_text(encoding='utf-8')

    # Handle YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 2:
            yaml_content = parts[1]
            frontmatter = yaml.safe_load(yaml_content)
            return frontmatter

    return {}


def discover_feat_bundle(src_root: str) -> List[Dict[str, Any]]:
    """Discover all FEAT objects under a SRC root."""
    feat_bundle = []
    requirements_dir = project_root / "spec" / "requirements" / src_root

    if not requirements_dir.exists():
        print(f"Warning: Requirements directory not found: {requirements_dir}")
        return feat_bundle

    for file_path in requirements_dir.glob("FEAT-*.md"):
        frontmatter = load_md_with_frontmatter(file_path)
        if frontmatter and frontmatter.get('ssot_type') == 'feat':
            frontmatter['_file_path'] = str(file_path)
            feat_bundle.append(frontmatter)
            print(f"  Found FEAT: {frontmatter.get('id')} - {frontmatter.get('title')}")

    return feat_bundle


def discover_tasks_for_feat(feat_id: str) -> List[Dict[str, Any]]:
    """Discover all TASK objects for a given FEAT."""
    tasks = []
    tasks_dir = project_root / "spec" / "tasks" / "SRC-046"

    # Check if there's a directory for this FEAT
    feat_dir = tasks_dir / feat_id

    if not feat_dir.exists():
        print(f"  Warning: No TASK directory found for {feat_id}")
        return tasks

    for file_path in feat_dir.glob("*.yaml"):
        try:
            task_data = load_yaml_with_frontmatter(file_path)
            if task_data and task_data.get('ssot_type') == 'task':
                task_data['_file_path'] = str(file_path)
                tasks.append(task_data)
                print(f"    Found TASK: {task_data.get('id')}")
        except Exception as e:
            print(f"  Error loading {file_path}: {e}")

    return tasks


def discover_tech_for_feat(feat_id: str) -> Optional[Dict[str, Any]]:
    """Discover TECH object for a given FEAT."""
    tech_dir = project_root / "spec" / "tech" / "SRC-046"

    if not tech_dir.exists():
        print(f"  Warning: TECH directory not found")
        return None

    # Look for TECH file matching the FEAT
    for file_path in tech_dir.glob(f"TECH-{feat_id}*.yaml"):
        try:
            tech_data = load_yaml_with_frontmatter(file_path)
            if tech_data and tech_data.get('ssot_type') == 'tech':
                tech_data['_file_path'] = str(file_path)
                print(f"    Found TECH: {tech_data.get('id')}")
                return tech_data
        except Exception as e:
            print(f"  Error loading {file_path}: {e}")

    return None


def generate_release_id(feat_bundle: List[Dict[str, Any]]) -> str:
    """Generate RELEASE ID based on FEAT bundle."""
    # For SRC-046, we'll generate REL-1.0.0 as the initial release
    return "REL-1.0.0"


def generate_release(
    release_id: str,
    feat_bundle: List[Dict[str, Any]],
    output_dir: Path
) -> Dict[str, Any]:
    """Generate RELEASE object from FEAT bundle."""
    release = {
        'id': release_id,
        'ssot_type': 'release',
        'title': f'SRC-046 交付版本 - {datetime.now().strftime("%Y-%m-%d")}',
        'status': 'draft',
        'version': 'v1',
        'workflow_instance_id': f'wf-release-src-046-{datetime.now().strftime("%Y%m%d")}',
        'derived_from_ids': [
            {'id': feat['id'], 'version': feat.get('version', 'v1'), 'required': True}
            for feat in feat_bundle
        ],
        'source_refs': ['SRC-046'],
        'owner': 'release_manager',
        'tags': ['src-046', 'delivery-chain', 'mvp'],
        'properties': {
            'scope_frozen_at': datetime.now().isoformat(),
            'target_env': 'production',
            'feat_count': len(feat_bundle),
            'priority': 'P0'
        }
    }

    # Write RELEASE object
    output_file = output_dir / f"{release_id}.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('---\n')
        yaml.dump(release, f, default_flow_style=False, allow_unicode=True)
        f.write('---\n\n# RELEASE object generated by FEAT2PLAN workflow\n')

    print(f"\nGenerated RELEASE: {release_id}")
    return release


def generate_devplan(
    release_id: str,
    feat_bundle: List[Dict[str, Any]],
    all_tasks: Dict[str, List[Dict[str, Any]]],
    output_dir: Path
) -> Dict[str, Any]:
    """Generate DEVPLAN object from RELEASE and TASKs."""
    devplan_id = f"DEVPLAN-{release_id}"

    # Build task refs from all tasks
    task_refs = []
    for feat_id, tasks in all_tasks.items():
        for task in tasks:
            task_refs.append({
                'id': task['id'],
                'version': task.get('version', 'v1'),
                'feat_ref': feat_id
            })

    devplan = {
        'id': devplan_id,
        'ssot_type': 'devplan',
        'title': f'SRC-046 开发计划 - {release_id}',
        'status': 'frozen',
        'version': 'v1',
        'workflow_instance_id': f'wf-devplan-src-046-{datetime.now().strftime("%Y%m%d")}',
        'parent_id': release_id,
        'derived_from_ids': [feat['id'] for feat in feat_bundle],
        'source_refs': ['SRC-046'],
        'owner': 'tech_lead',
        'tags': ['src-046', 'delivery-chain', 'dev'],
        'properties': {
            'slices': [
                {
                    'feat_id': feat['id'],
                    'task_count': len(all_tasks.get(feat['id'], [])),
                    'priority': feat.get('properties', {}).get('priority', 'P1')
                }
                for feat in feat_bundle
            ],
            'coverage_summary': {
                'total_feats': len(feat_bundle),
                'total_tasks': sum(len(tasks) for tasks in all_tasks.values()),
                'coverage_rate': '100%' if all(feat['id'] in all_tasks for feat in feat_bundle) else 'partial'
            }
        },
        'task_refs': task_refs
    }

    # Write DEVPLAN object
    output_file = output_dir / f"{devplan_id}.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('---\n')
        yaml.dump(devplan, f, default_flow_style=False, allow_unicode=True)
        f.write('---\n\n# DEVPLAN object generated by FEAT2PLAN workflow\n')

    print(f"Generated DEVPLAN: {devplan_id}")
    return devplan


def generate_testplan(
    release_id: str,
    feat_bundle: List[Dict[str, Any]],
    all_techs: Dict[str, Optional[Dict[str, Any]]],
    output_dir: Path
) -> Dict[str, Any]:
    """Generate TESTPLAN object from RELEASE and FEAT.AC."""
    testplan_id = f"TESTPLAN-{release_id}"

    # Build test set refs from FEAT acceptance criteria
    test_set_refs = []
    for feat in feat_bundle:
        test_set_refs.append({
            'feat_id': feat['id'],
            'ac_count': len(feat.get('Acceptance Checks', [])),
            'test_strategy': 'integration'
        })

    testplan = {
        'id': testplan_id,
        'ssot_type': 'testplan',
        'title': f'SRC-046 测试计划 - {release_id}',
        'status': 'frozen',
        'version': 'v1',
        'workflow_instance_id': f'wf-testplan-src-046-{datetime.now().strftime("%Y%m%d")}',
        'parent_id': release_id,
        'derived_from_ids': [feat['id'] for feat in feat_bundle],
        'source_refs': ['SRC-046'],
        'owner': 'qa_lead',
        'tags': ['src-046', 'delivery-chain', 'qa'],
        'properties': {
            'slices': test_set_refs,
            'environment_matrix': {
                'environments': ['dev', 'staging', 'production'],
                'browsers': ['chrome', 'firefox', 'safari'],
                'os': ['windows', 'macos', 'linux']
            },
            'coverage_summary': {
                'total_feats': len(feat_bundle),
                'total_acs': sum(len(feat.get('Acceptance Checks', [])) for feat in feat_bundle),
                'test_strategy': 'risk-based'
            }
        },
        'test_set_refs': test_set_refs
    }

    # Write TESTPLAN object
    output_file = output_dir / f"{testplan_id}.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('---\n')
        yaml.dump(testplan, f, default_flow_style=False, allow_unicode=True)
        f.write('---\n\n# TESTPLAN object generated by FEAT2PLAN workflow\n')

    print(f"Generated TESTPLAN: {testplan_id}")
    return testplan


def validate_ssot_chain(
    release: Dict[str, Any],
    devplan: Dict[str, Any],
    testplan: Dict[str, Any],
    feat_bundle: List[Dict[str, Any]]
) -> bool:
    """Validate SSOT chain integrity."""
    print("\n" + "=" * 60)
    print("Validating SSOT Chain Integrity")
    print("=" * 60)

    errors = []

    # P0-012: RELEASE must declare derived_from_ids
    if not release.get('derived_from_ids'):
        errors.append("P0-012: RELEASE missing derived_from_ids")

    # P0-013: DEVPLAN.derived_from_ids must include at least one FEAT
    if not devplan.get('derived_from_ids'):
        errors.append("P0-013: DEVPLAN missing derived_from_ids")

    # P0-014: TESTPLAN.derived_from_ids must include FEAT
    if not testplan.get('derived_from_ids'):
        errors.append("P0-014: TESTPLAN missing derived_from_ids")

    # Check parent_id consistency
    if devplan.get('parent_id') != release['id']:
        errors.append(f"P0-008: DEVPLAN.parent_id ({devplan.get('parent_id')}) != RELEASE.id ({release['id']})")

    if testplan.get('parent_id') != release['id']:
        errors.append(f"P0-008: TESTPLAN.parent_id ({testplan.get('parent_id')}) != RELEASE.id ({release['id']})")

    # Check FEAT coverage
    release_feat_ids = set(f['id'] for f in release.get('derived_from_ids', []))
    devplan_feat_ids = set(devplan.get('derived_from_ids', []))
    testplan_feat_ids = set(testplan.get('derived_from_ids', []))

    if release_feat_ids != devplan_feat_ids:
        errors.append("P0-017: DEVPLAN does not cover all FEATs in RELEASE")

    if release_feat_ids != testplan_feat_ids:
        errors.append("P0-018: TESTPLAN does not cover all FEATs in RELEASE")

    if errors:
        print("VALIDATION FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("VALIDATION PASSED:")
    print(f"  - RELEASE covers {len(release_feat_ids)} FEATs")
    print(f"  - DEVPLAN covers {len(devplan_feat_ids)} FEATs")
    print(f"  - TESTPLAN covers {len(testplan_feat_ids)} FEATs")
    print(f"  - Parent-child relationships are consistent")

    return True


def main():
    """Main entry point for FEAT2PLAN execution."""
    print("=" * 60)
    print("FEAT2PLAN L2 Workflow Executor - SRC-046 Bundle")
    print("=" * 60)
    print(f"Execution time: {datetime.now().isoformat()}")
    print()

    # Step 1: Discover FEAT bundle
    print("Step 1: Discovering FEAT bundle for SRC-046...")
    feat_bundle = discover_feat_bundle("SRC-046")

    if not feat_bundle:
        print("ERROR: No FEAT objects found for SRC-046")
        return 1

    print(f"Discovered {len(feat_bundle)} FEAT objects")

    # Validate all FEATs are frozen
    for feat in feat_bundle:
        if feat.get('status') != 'frozen':
            print(f"WARNING: FEAT {feat['id']} is not frozen (status: {feat.get('status')})")

    # Step 2: Discover TASK and TECH for each FEAT
    print("\nStep 2: Discovering TASK and TECH objects...")
    all_tasks: Dict[str, List[Dict[str, Any]]] = {}
    all_techs: Dict[str, Optional[Dict[str, Any]]] = {}

    for feat in feat_bundle:
        feat_id = feat['id']
        print(f"  Processing {feat_id}:")

        # Discover TASKs
        tasks = discover_tasks_for_feat(feat_id)
        all_tasks[feat_id] = tasks

        # Discover TECH
        tech = discover_tech_for_feat(feat_id)
        all_techs[feat_id] = tech

    # Step 3: Generate RELEASE
    print("\nStep 3: Generating RELEASE object...")
    release_id = generate_release_id(feat_bundle)
    release = generate_release(release_id, feat_bundle, project_root / "spec" / "releases")

    # Step 4: Generate DEVPLAN
    print("\nStep 4: Generating DEVPLAN object...")
    devplan = generate_devplan(release_id, feat_bundle, all_tasks, project_root / "spec" / "devplans")

    # Step 5: Generate TESTPLAN
    print("\nStep 5: Generating TESTPLAN object...")
    testplan = generate_testplan(release_id, feat_bundle, all_techs, project_root / "spec" / "testplans")

    # Step 6: Validate SSOT chain
    print("\nStep 6: Validating SSOT chain...")
    is_valid = validate_ssot_chain(release, devplan, testplan, feat_bundle)

    # Summary
    print("\n" + "=" * 60)
    print("FEAT2PLAN Execution Summary")
    print("=" * 60)
    print(f"Input FEATs: {len(feat_bundle)}")
    print(f"  - FEAT-SRC-046-001: 交付主链建立与 RELEASE 起点治理")
    print(f"  - FEAT-SRC-046-002: 发布关闭标准统一与治理闭环")
    print(f"  - FEAT-SRC-046-003: QA 与研发执行入口绑定收口")
    print(f"  - FEAT-SRC-046-004: 缺陷回流路径与 bugfix 交付轴闭环")
    print(f"\nGenerated Objects:")
    print(f"  - RELEASE: {release_id}")
    print(f"  - DEVPLAN: {devplan['id']}")
    print(f"  - TESTPLAN: {testplan['id']}")
    print(f"\nValidation: {'PASSED' if is_valid else 'FAILED'}")
    print("=" * 60)

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
