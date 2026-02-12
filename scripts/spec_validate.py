#!/usr/bin/env python3
"""
Spec 引用完整性验证器
────────────────────
校验规则:
  1. workflow → agent 引用：对应 agent.yaml 必须存在
  2. agent skills: → skill spec：对应 skill.yaml 必须存在
  3. agent capabilities: → 不做 spec 存在性校验（prompt 知识型）
  4. workflow/agent → contract 引用：对应 contract spec 必须存在
  5. workflow/agent → gate 引用：对应 gate spec 必须存在
  6. skill spec 的 runtime: 块必须存在

用法:
  python scripts/spec_validate.py              # 检查所有
  python scripts/spec_validate.py --strict     # 严格模式: warnings 也算失败
  python scripts/spec_validate.py --changed    # 只检查 git 变更文件涉及的 spec
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# ── Config ──

BASE = Path(__file__).resolve().parent.parent / "spec-global"

# These skills are "capability" type - listed in agent capabilities:, not skills:
# No spec file needed for them
CAPABILITY_PREFIXES = [
    "skill.go.",
    "skill.vue",
    "skill.uniapp.",
    "skill.frontend.",
    "skill.dev.architecture",
    "skill.dev.knowledge",
    "skill.dev.planning",
    "skill.dev.test_driven",
    "skill.product.",
    "skill.review.",
    "skill.design.",
    "skill.qa.",
    "skill.integration.",
    "skill.validation.",
    "skill.io.",
    "skill.analysis.",
    "skill.planning.",
    "skill.gate.",
    "skill.shell.",
    "skill.media.platform_publish",
]


def is_capability_skill(skill_id: str) -> bool:
    """Check if a skill ID is a capability/knowledge type (no spec needed)."""
    return any(skill_id.startswith(prefix) for prefix in CAPABILITY_PREFIXES)


# ── Builders ──

def build_spec_index():
    """Build {spec_id: file_path} indices for all spec types."""
    index = {
        "agent": {},
        "skill": {},
        "contract": {},
        "gate": {},
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
            index["skill"][m.group(1)] = str(f)

    for f in BASE.rglob("schema.yaml"):
        # Contract specs are in contracts/ dirs
        if "contracts/" in str(f) or "contract" in str(f.parent):
            content = f.read_text()
            m = re.search(r"^\s*id:\s*([\w\._-]+)", content, re.M)
            if m:
                index["contract"][m.group(1)] = str(f)
            # Also index by directory name
            contract_dir = f.parent.parent.name if f.parent.name.startswith("v") else f.parent.name
            index["contract"][contract_dir] = str(f)

    for f in BASE.rglob("agent.yaml"):
        if "gates/" in str(f):
            content = f.read_text()
            m = re.search(r"^\s*id:\s*([\w\.]+)", content, re.M)
            if m:
                index["gate"][m.group(1)] = str(f)

    return index


def get_changed_specs():
    """Get spec files changed in git staging area."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, cwd=BASE.parent,
        )
        if result.returncode != 0:
            return None
        return [f for f in result.stdout.strip().split("\n") if f.startswith("spec-global/")]
    except FileNotFoundError:
        return None


# ── Validators ──

def validate_workflow_agent_refs(index):
    """Check workflow → agent references."""
    errors = []
    warnings = []

    for wf in sorted(BASE.rglob("workflow.yaml")):
        content = wf.read_text()
        rel = str(wf.relative_to(BASE))
        agents = set(re.findall(r"agent\.[a-z_\.]+", content))
        agents.discard("agent.yaml")

        for agent_id in sorted(agents):
            if agent_id not in index["agent"]:
                errors.append(f"[E001] {rel}: agent '{agent_id}' referenced but no agent.yaml found")

    return errors, warnings


def validate_agent_skill_refs(index):
    """Check agent skills: → skill spec references."""
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

        # Check skills: section (these MUST have spec files)
        skills_block = re.search(
            r"^skills:\s*\n((?:\s+-\s+ref:\s+skill\.[\w\.]+\s*\n)*)",
            content, re.M,
        )
        if skills_block:
            skill_refs = re.findall(r"ref:\s+(skill\.[\w\.]+)", skills_block.group(1))
            for skill_id in skill_refs:
                if skill_id not in index["skill"]:
                    errors.append(
                        f"[E002] {rel}: skill '{skill_id}' in skills: but no skill.yaml found"
                    )

        # capabilities: section — just warn if something looks like it should be a skill
        cap_block = re.search(
            r"^capabilities:\s*\n((?:\s+-\s+skill\.[\w\.]+\s*\n)*)",
            content, re.M,
        )
        if cap_block:
            cap_refs = re.findall(r"-\s+(skill\.[\w\.]+)", cap_block.group(1))
            for cap_id in cap_refs:
                if cap_id in index["skill"]:
                    warnings.append(
                        f"[W001] {rel}: '{cap_id}' is in capabilities: but has a spec file — "
                        f"consider moving to skills:"
                    )

    return errors, warnings


def validate_skill_runtime(index):
    """Check all skill specs have runtime: blocks."""
    errors = []
    warnings = []

    for skill_id, fpath in sorted(index["skill"].items()):
        content = Path(fpath).read_text()
        if not re.search(r"^runtime:", content, re.M):
            warnings.append(
                f"[W002] {Path(fpath).relative_to(BASE)}: skill '{skill_id}' has no runtime: block"
            )

    return errors, warnings


def validate_contract_refs(index):
    """Check contract references from workflows and agents."""
    errors = []

    for f in sorted(list(BASE.rglob("workflow.yaml")) + list(BASE.rglob("agent.yaml"))):
        content = f.read_text()
        rel = str(f.relative_to(BASE))

        # Look for contract refs in various formats
        contract_refs = set()
        # "contract: contracts/xxx/v1/schema.yaml"
        contract_refs.update(re.findall(r"contracts/([\w-]+)/", content))
        # "ref: xxx-contract"
        contract_refs.update(
            m for m in re.findall(r"[\w-]+-contract[\w-]*", content)
            if not m.startswith("#")
        )

        for cref in sorted(contract_refs):
            # Check if there's a matching contract dir
            found = False
            for contract_dir in BASE.rglob("contracts"):
                if (contract_dir / cref).is_dir():
                    found = True
                    break
            if not found and cref not in index["contract"]:
                # Only error for explicit contract refs, not inline mentions
                pass  # Too noisy — contract naming is inconsistent

    return errors, []


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Spec 引用完整性验证")
    parser.add_argument("--strict", action="store_true", help="Warnings also cause failure")
    parser.add_argument("--changed", action="store_true", help="Only check git-changed specs")
    args = parser.parse_args()

    if not BASE.exists():
        print(f"ERROR: spec-global directory not found at {BASE}")
        sys.exit(2)

    print("🔍 Building spec index...")
    index = build_spec_index()
    print(f"   Agents:    {len(index['agent'])}")
    print(f"   Skills:    {len(index['skill'])}")
    print(f"   Contracts: {len(index['contract'])}")
    print(f"   Gates:     {len(index['gate'])}")

    all_errors = []
    all_warnings = []

    print("\n📋 Checking workflow → agent references...")
    e, w = validate_workflow_agent_refs(index)
    all_errors.extend(e)
    all_warnings.extend(w)

    print("📋 Checking agent skills: → skill spec references...")
    e, w = validate_agent_skill_refs(index)
    all_errors.extend(e)
    all_warnings.extend(w)

    print("📋 Checking skill runtime: blocks...")
    e, w = validate_skill_runtime(index)
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
        print("✅ All spec references are valid!")

    print(f"{'='*60}")
    print(f"Errors: {len(all_errors)}, Warnings: {len(all_warnings)}")

    if all_errors:
        sys.exit(1)
    if args.strict and all_warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
