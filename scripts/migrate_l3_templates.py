#!/usr/bin/env python
"""
Migrate L3 Workflow Templates to new format

This script migrates old L3 templates that use root-level 'steps' 
to the new format that uses 'stages' with nested 'steps'.

Old format:
  steps:
    - id: step1
      ...

New format:
  stages:
    - id: execution
      kind: stage
      steps:
        - id: step1
          ...
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load YAML file and return parsed content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml_file(file_path: Path, data: Dict[str, Any]) -> None:
    """Save data to YAML file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        # Preserve some formatting
        f.write(f"# Migrated by lint_l3_templates.py on {datetime.now().isoformat()}\n")
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=100
        )


def migrate_template(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate a single L3 template to new format.
    
    Returns:
        Migrated data dictionary
    """
    # Skip if already migrated (has stages but no root-level steps)
    if 'stages' in data and 'steps' not in data:
        # Check if stages have proper kind field
        needs_stage_kind_fix = False
        for stage in data.get('stages', []):
            if stage.get('kind') != 'stage':
                needs_stage_kind_fix = True
                break
        
        if not needs_stage_kind_fix:
            return data  # Already in correct format
    
    migrated = data.copy()
    
    # Remove old steps field and migrate to stages
    if 'steps' in migrated:
        old_steps = migrated.pop('steps')
        
        # Create a single execution stage containing all steps
        execution_stage = {
            'id': 'execution',
            'name': 'Execution Pipeline',
            'kind': 'stage',
            'description': 'Auto-migrated from root-level steps',
            'steps': old_steps
        }
        
        # Preserve execution_order if present
        if 'execution_order' in migrated:
            execution_stage['step_order'] = migrated.pop('execution_order')
        
        # Add to stages
        if 'stages' not in migrated:
            migrated['stages'] = []
        
        migrated['stages'].append(execution_stage)
    
    # Fix stage kind field if needed
    for stage in migrated.get('stages', []):
        if stage.get('kind') != 'stage':
            stage['kind'] = 'stage'
    
    return migrated


def find_l3_templates(paths: List[Path]) -> List[Path]:
    """Find all L3 workflow template files in given paths."""
    templates = []
    
    for path in paths:
        if path.is_file() and path.suffix in ('.yaml', '.yml'):
            try:
                data = load_yaml_file(path)
                if data and data.get('kind') == 'l3_workflow_template':
                    templates.append(path)
            except Exception:
                continue
        elif path.is_dir():
            for yaml_file in path.rglob("*.yaml"):
                try:
                    data = load_yaml_file(yaml_file)
                    if data and data.get('kind') == 'l3_workflow_template':
                        templates.append(yaml_file)
                except Exception:
                    continue
    
    return sorted(set(templates))


def needs_migration(file_path: Path) -> bool:
    """Check if a template needs migration."""
    try:
        data = load_yaml_file(file_path)
        
        # Has root-level steps = needs migration
        if 'steps' in data:
            return True
        
        # Has stages but kind != 'stage' = needs migration
        for stage in data.get('stages', []):
            if stage.get('kind') != 'stage':
                return True
        
        return False
    except Exception:
        return False


def migrate_templates(paths: List[Path], dry_run: bool = True, backup: bool = True) -> int:
    """
    Migrate all L3 templates in given paths.
    
    Returns:
        Number of templates migrated
    """
    templates = find_l3_templates(paths)
    migrated_count = 0
    
    print(f"📋 Found {len(templates)} L3 template(s)\n")
    
    for template_path in templates:
        try:
            rel_path = template_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = template_path
        
        if not needs_migration(template_path):
            print(f"⏭️  {rel_path} (already migrated)")
            continue
        
        print(f"🔄 {rel_path}")
        
        try:
            data = load_yaml_file(template_path)
            migrated_data = migrate_template(data)
            
            if dry_run:
                print(f"   📝 Would migrate (dry run)")
            else:
                # Backup original
                if backup:
                    backup_path = template_path.with_suffix('.yaml.bak')
                    shutil.copy2(template_path, backup_path)
                    print(f"   💾 Backed up to {backup_path.name}")
                
                # Save migrated version
                save_yaml_file(template_path, migrated_data)
                print(f"   ✅ Migrated successfully")
            
            migrated_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    return migrated_count


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate L3 Workflow Templates to new format"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("spec-global/departments")],
        help="Paths to migrate (default: spec-global/departments)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually perform migration (default: dry run)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup files"
    )
    
    args = parser.parse_args()
    
    # Validate paths exist
    for path in args.paths:
        if not path.exists():
            print(f"❌ Path not found: {path}")
            sys.exit(1)
    
    # Run migration
    dry_run = not args.no_dry_run
    backup = not args.no_backup
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")
        print("=" * 60)
    
    migrated_count = migrate_templates(args.paths, dry_run=dry_run, backup=backup)
    
    print("=" * 60)
    if dry_run:
        print(f"\n📊 {migrated_count} template(s) would be migrated")
        print("   Run with --no-dry-run to apply changes")
    else:
        print(f"\n✅ {migrated_count} template(s) migrated successfully")
    
    sys.exit(0 if migrated_count == 0 else 1)


if __name__ == "__main__":
    main()
