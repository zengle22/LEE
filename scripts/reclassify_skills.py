"""
Batch reclassify agent skill references.
- skills with spec files → stay in skills:
- skills without spec files → move to capabilities:
- skills only in non-workflow agents → remove entirely

Agent format is:
  skills:
    - ref: skill.xxx
    - ref: skill.yyy
"""

import re
from pathlib import Path

BASE = Path("spec-global")

# 1. Build set of skills that have spec files
skill_specs = set()
for f in BASE.rglob("skill.yaml"):
    content = f.read_text()
    m = re.search(r"^\s*id:\s*(skill\.[\w\.]+)", content, re.M)
    if m:
        skill_specs.add(m.group(1))

print(f"Skills with spec files ({len(skill_specs)}):")
for s in sorted(skill_specs):
    print(f"  ✓ {s}")

# 2. Build workflow-referenced agent set
wf_agents = set()
for f in BASE.rglob("workflow.yaml"):
    content = f.read_text()
    wf_agents.update(re.findall(r"agent\.[a-z_\.]+", content))
wf_agents.discard("agent.yaml")

# 3. Process each agent file
total_reclassified = 0
total_removed = 0
modified_agents = []

for f in sorted(BASE.rglob("agent.yaml")):
    content = f.read_text()
    m = re.search(r"^\s*id:\s*(agent\.[\w\.]+)", content, re.M)
    if not m:
        continue
    agent_id = m.group(1)
    is_wf_active = agent_id in wf_agents

    # Find skills: section with "- ref: skill.xxx" entries
    # Match the whole skills block
    skills_block_match = re.search(
        r"^(skills:\s*\n)((?:\s+-\s+ref:\s+skill\.[\w\.]+\s*\n)+)",
        content, re.M
    )
    if not skills_block_match:
        continue

    full_block = skills_block_match.group(0)
    skill_refs = re.findall(r"ref:\s+(skill\.[\w\.]+)", full_block)

    if not skill_refs:
        continue

    keep = [s for s in skill_refs if s in skill_specs]
    move_to_cap = [s for s in skill_refs if s not in skill_specs and is_wf_active]
    remove = [s for s in skill_refs if s not in skill_specs and not is_wf_active]

    if not move_to_cap and not remove:
        continue

    # Build replacement
    parts = []
    if keep:
        parts.append("skills:\n" + "".join(f"  - ref: {s}\n" for s in keep))
    
    if move_to_cap:
        parts.append("capabilities:\n" + "".join(f"  - {s}\n" for s in move_to_cap))
    
    replacement = "\n".join(parts)
    if not replacement:
        replacement = ""

    new_content = content.replace(full_block, replacement + ("\n" if replacement else ""))
    
    # Clean up any double blank lines
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)
    
    f.write_text(new_content)

    total_reclassified += len(move_to_cap)
    total_removed += len(remove)
    modified_agents.append({
        "id": agent_id,
        "file": str(f),
        "wf_active": is_wf_active,
        "keep": keep,
        "cap": move_to_cap,
        "remove": remove,
    })

print(f"\n{'='*60}")
print(f"Agents modified: {len(modified_agents)}")
print(f"Skills kept in skills:: {sum(len(a['keep']) for a in modified_agents)}")
print(f"Skills → capabilities:: {total_reclassified}")
print(f"Skills removed entirely: {total_removed}")
print(f"{'='*60}")

for a in modified_agents:
    tag = "WF" if a["wf_active"] else "NON-WF"
    print(f"\n  [{tag}] {a['id']} ({a['file']})")
    if a["keep"]:
        print(f"    keep:   {a['keep']}")
    if a["cap"]:
        print(f"    → cap:  {a['cap']}")
    if a["remove"]:
        print(f"    ✗ del:  {a['remove']}")
