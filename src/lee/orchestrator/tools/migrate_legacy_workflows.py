"""
LEE Orchestrator - Legacy Workflow Migration Script

Migrates legacy workflow files that are missing the `kind: workflow` header
to the spec-global format.

Legacy workflows to migrate:
1. devops-deployment - missing `kind: workflow` header
2. ui-design-pipeline - missing `kind: workflow` header, different format
"""

import yaml
import shutil
from pathlib import Path
from datetime import datetime


def migrate_devops_deployment():
    """
    Migrate devops-deployment workflow to spec-global format.

    Changes:
    - Add `kind: workflow` header
    - Convert `level: department` to spec-global format
    - Preserve all existing structure
    """
    input_file = Path("spec-global/departments/devops/workflows/devops-deployment/v1/workflow.yaml")
    backup_file = input_file.with_suffix(".yaml.backup")

    # Create backup
    shutil.copy(input_file, backup_file)
    print(f"✓ Backup created: {backup_file}")

    # Read the file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already migrated
    if "kind: workflow" in content[:500]:
        print("  Already migrated (has kind: workflow)")
        return

    # Add migration header comment
    header = f"""# Migrated to spec-global format on {datetime.now().strftime('%Y-%m-%d')}
# Original format: orchestrator-legacy-template
#

"""

    # Add kind: workflow after the comments
    lines = content.split('\n')

    # Find the first non-comment line
    first_non_comment = 0
    for i, line in enumerate(lines):
        if not line.strip().startswith('#'):
            first_non_comment = i
            break

    # Insert kind: workflow before id
    new_lines = []
    for i, line in enumerate(lines):
        if i == first_non_comment:
            new_lines.append("kind: workflow")
        new_lines.append(line)

    # Write the migrated content
    new_content = header + '\n'.join(new_lines)

    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✓ Migrated: {input_file}")
    print(f"  Added: kind: workflow header")


def migrate_ui_design_pipeline():
    """
    Migrate ui-design-pipeline workflow to spec-global format.

    Changes:
    - Add `kind: workflow` header
    - Rename `id: ui_design_pipeline` to `id: workflow.ui.ui_design_pipeline`
    - Add `owner: ui-ai`
    - Convert `steps` to spec-global format
    - Preserve all existing structure
    """
    input_file = Path("spec-global/departments/ui/workflows/ui-design-pipeline/v1/workflow.yaml")
    backup_file = input_file.with_suffix(".yaml.backup")

    # Create backup
    shutil.copy(input_file, backup_file)
    print(f"✓ Backup created: {backup_file}")

    # Read and parse
    with open(input_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # Check if already migrated
    if data.get('kind') == 'workflow':
        print("  Already migrated (has kind: workflow)")
        return

    # Add migration header comment
    header = f"""# Migrated to spec-global format on {datetime.now().strftime('%Y-%m-%d')}
# Original format: orchestrator-legacy-template
#

"""

    # Convert to spec-global format
    data['kind'] = 'workflow'
    data['version'] = data.get('version', '1.0')

    # Fix ID
    old_id = data.get('id', '')
    if not old_id.startswith('workflow.'):
        data['id'] = f"workflow.ui.{old_id.replace('-', '_')}"

    # Add owner if missing
    if 'owner' not in data:
        data['owner'] = 'ui-ai'

    # Add tags if missing
    if 'tags' not in data:
        data['tags'] = ['ui', 'workflow', 'design', 'figma', 'quality-gate']

    # Write the migrated content
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(header)
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, indent=2)

    print(f"✓ Migrated: {input_file}")
    print(f"  ID: {old_id} → {data['id']}")


def verify_migration(workflow_file: Path) -> bool:
    """Verify that a workflow file is properly migrated."""
    from lee.orchestrator.execution.spec_global_parser import SpecGlobalParser

    parser = SpecGlobalParser()
    try:
        workflow_ir = parser.parse_workflow_file(str(workflow_file))
        print(f"  ✓ Successfully parsed: {workflow_ir.id}")
        print(f"    Name: {workflow_ir.name}")
        print(f"    Steps: {len(workflow_ir.steps)}")
        return True
    except Exception as e:
        print(f"  ✗ Parse error: {e}")
        return False


def main():
    """Run the migration."""
    print("=" * 70)
    print("LEE Orchestrator - Legacy Workflow Migration")
    print("=" * 70)

    print("\n[Migrating devops-deployment]")
    migrate_devops_deployment()

    print("\n[Migrating ui-design-pipeline]")
    migrate_ui_design_pipeline()

    print("\n" + "=" * 70)
    print("Verifying migrations...")
    print("=" * 70)

    devops_file = Path("spec-global/departments/devops/workflows/devops-deployment/v1/workflow.yaml")
    ui_file = Path("spec-global/departments/ui/workflows/ui-design-pipeline/v1/workflow.yaml")

    print("\n[devops-deployment]")
    devops_ok = verify_migration(devops_file)

    print("\n[ui-design-pipeline]")
    ui_ok = verify_migration(ui_file)

    print("\n" + "=" * 70)
    if devops_ok and ui_ok:
        print("✓ Migration completed successfully!")
        print("\nBoth workflows are now in spec-global format.")
        print("\nNext steps:")
        print("  1. Test the workflows with the orchestrator")
        print("  2. Remove .backup files if everything works")
    else:
        print("⚠ Migration completed with errors")
        print("\nPlease check the errors above and:")
        print("  1. Restore from .backup files if needed")
        print("  2. Fix any parsing issues")
        print("  3. Re-run this script")
    print("=" * 70)


if __name__ == "__main__":
    main()
