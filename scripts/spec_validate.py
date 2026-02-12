#!/usr/bin/env python3
"""
Spec 引用完整性验证器（三分法版本）
──────────────────────────────────
校验规则:
  E001: workflow → agent 引用：对应 agent.yaml 必须存在
  E002: agent tools: → skill spec：必须有 spec 文件且 spec 有 runtime: 块
  E003: agent specs: → skill spec：必须有 spec 文件（runtime 可选）
  W001: agent capabilities: 中有 spec 文件的 skill → 建议移到 tools/specs
  W002: tool skill spec 无 runtime: 块
  (capabilities: 不做存在性校验)

用法:
  python scripts/spec_validate.py              # 检查所有
  python scripts/spec_validate.py --strict     # 严格模式: warnings 也算失败
"""

import argparse
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "spec-global"


def build_spec_index():
    """Build {spec_id: {file, has_runtime}} index for all spec types."""
    index = {
        "agent": {},     # {agent_id: file_path}
        "skill": {},     # {skill_id: {file, has_runtime}}
    }

    for f in BASE.rglob("agent.yaml"):
        content = f.read_text()
        m = re.search(r"^\s*id:\s*(agent\.[\w\.]+)", content, re.M)
        if m:
            index["agent"][m.group(1)] = str(f)

    for f in BASE.rglob("skill.yaml"):
        content = f.read_text()
        m = re.search(r"^\s*id:\s*(skill\.[\w\.]+)", content, re.M)
        if m:
            has_runtime = bool(re.search(r"^runtime:", content, re.M))
            index["skill"][m.group(1)] = {
                "file": str(f),
                "has_runtime": has_runtime,
            }

    return index


def validate_workflow_agent_refs(index):
    """E001: workflow → agent references must have agent.yaml files."""
    errors = []
    for wf in sorted(BASE.rglob("workflow.yaml")):
        content = wf.read_text()
        rel = str(wf.relative_to(BASE))
        agents = set(re.findall(r"agent\.[a-z_\.]+", content))
        agents.discard("agent.yaml")

        for agent_id in sorted(agents):
            if agent_id not in index["agent"]:
                errors.append(
                    f"[E001] {rel}: agent '{agent_id}' referenced but no agent.yaml found"
                )
    return errors, []


def validate_agent_three_categories(index):
    """
    E002: agent tools: → skill must have spec + runtime
    E003: agent specs: → skill must have spec (runtime optional)
    W001: capabilities: entry has a spec file → suggest moving
    """
    errors = []
    warnings = []

    for af in sorted(BASE.rglob("agent.yaml")):
        if "gates/" in str(af):
            continue
        content = af.read_text()
        rel = str(af.relative_to(BASE))

        m = re.search(r"^\s*id:\s*(agent\.[\w\.]+)", content, re.M)
        if not m:
            continue

        # --- Check tools: section ---
        tools_block = re.search(
            r"^tools:\s*\n((?:\s+-\s+ref:\s+skill\.[\w\.]+\s*\n)*)",
            content, re.M,
        )
        if tools_block:
            tool_refs = re.findall(r"ref:\s+(skill\.[\w\.]+)", tools_block.group(1))
            for skill_id in tool_refs:
                if skill_id not in index["skill"]:
                    errors.append(
                        f"[E002] {rel}: tool '{skill_id}' in tools: but no skill.yaml found"
                    )
                elif not index["skill"][skill_id]["has_runtime"]:
                    warnings.append(
                        f"[W002] {rel}: tool '{skill_id}' in tools: but spec has no runtime: block — "
                        f"consider moving to specs: or adding runtime:"
                    )

        # --- Check legacy skills: section (should be migrated) ---
        legacy_block = re.search(
            r"^skills:\s*\n((?:\s+-\s+ref:\s+skill\.[\w\.]+\s*\n)*)",
            content, re.M,
        )
        if legacy_block:
            legacy_refs = re.findall(r"ref:\s+(skill\.[\w\.]+)", legacy_block.group(1))
            for skill_id in legacy_refs:
                warnings.append(
                    f"[W003] {rel}: '{skill_id}' still uses legacy skills: field — "
                    f"migrate to tools: or specs: per three-category taxonomy"
                )

        # --- Check specs: section ---
        specs_block = re.search(
            r"^specs:\s*\n((?:\s+-\s+ref:\s+skill\.[\w\.]+\s*\n)*)",
            content, re.M,
        )
        if specs_block:
            spec_refs = re.findall(r"ref:\s+(skill\.[\w\.]+)", specs_block.group(1))
            for skill_id in spec_refs:
                if skill_id not in index["skill"]:
                    errors.append(
                        f"[E003] {rel}: spec skill '{skill_id}' in specs: but no skill.yaml found"
                    )

        # --- Check capabilities: section ---
        cap_block = re.search(
            r"^capabilities:\s*\n((?:\s+-\s+skill\.[\w\.]+\s*\n)*)",
            content, re.M,
        )
        if cap_block:
            cap_refs = re.findall(r"-\s+(skill\.[\w\.]+)", cap_block.group(1))
            for cap_id in cap_refs:
                if cap_id in index["skill"]:
                    target = "tools:" if index["skill"][cap_id]["has_runtime"] else "specs:"
                    warnings.append(
                        f"[W001] {rel}: '{cap_id}' in capabilities: but has spec file — "
                        f"consider moving to {target}"
                    )

    return errors, warnings


def validate_skill_runtime(index):
    """W002: standalone check — skill specs in tools: should have runtime."""
    # Already handled inline in validate_agent_three_categories
    return [], []


def main():
    parser = argparse.ArgumentParser(description="Spec 引用完整性验证（三分法）")
    parser.add_argument("--strict", action="store_true", help="Warnings also cause failure")
    args = parser.parse_args()

    if not BASE.exists():
        print(f"ERROR: spec-global directory not found at {BASE}")
        sys.exit(2)

    print("🔍 Building spec index...")
    index = build_spec_index()
    print(f"   Agents:    {len(index['agent'])}")
    print(f"   Skills:    {len(index['skill'])} "
          f"(tool: {sum(1 for s in index['skill'].values() if s['has_runtime'])}, "
          f"spec: {sum(1 for s in index['skill'].values() if not s['has_runtime'])})")

    all_errors = []
    all_warnings = []

    print("\n📋 [E001] Checking workflow → agent references...")
    e, w = validate_workflow_agent_refs(index)
    all_errors.extend(e)
    all_warnings.extend(w)

    print("📋 [E002/E003/W001-3] Checking agent tools:/specs:/capabilities:...")
    e, w = validate_agent_three_categories(index)
    all_errors.extend(e)
    all_warnings.extend(w)

    # Print results
    print(f"\n{'='*60}")
    if all_errors:
        print(f"❌ ERRORS ({len(all_errors)}):")
        for err in all_errors:
            print(f"   {err}")
    if all_warnings:
        print(f"⚠️  WARNINGS ({len(all_warnings)}):")
        for warn in all_warnings:
            print(f"   {warn}")
    if not all_errors and not all_warnings:
        print("✅ All spec references are valid! (Three-Category Taxonomy)")

    print(f"{'='*60}")
    print(f"Errors: {len(all_errors)}, Warnings: {len(all_warnings)}")

    if all_errors:
        sys.exit(1)
    if args.strict and all_warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
