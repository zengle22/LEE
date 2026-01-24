# LEE Slash Commands

This directory contains **slash commands** that users can type directly in Claude Code.

## What are Slash Commands?

Slash commands are user-invocable commands that you type directly into Claude Code:
- `/gate-review` - Review and approve gates
- `/gate-approval` - Gate approval tools
- `/pm-workflow` - PM workflow management

## Difference from Function Tools

| Feature | Slash Commands | Function Tools |
|---------|---------------|----------------|
| Location | `.claude/commands/*.md` | `.claude/tools/*.json` |
| Format | Markdown | JSON |
| Invocation | User types `/name` | AI calls automatically |
| Purpose | Interactive operations | Programmatic integration |

## Available Commands

### `/gate-review`
Review and approve pending human gates in the LEE workflow system.

**File**: `gate-review.md`

**Features**:
- List all pending gates
- Show gate details with upstream analysis
- Submit approve/reject/revise decisions

### `/gate-approval`
Gate approval tools for the LEE workflow.

**File**: `gate-approval.md`

**Features**:
- List pending gates
- Show gate details and checklist
- Submit decisions

### `/pm-workflow`
PM workflow management tools.

**File**: `pm-workflow.md`

**Features**:
- Get workflow state
- List ready steps
- Run workflow steps
- Execute next step

## Creating New Commands

To create a new slash command:

1. Create a new Markdown file in this directory
2. Name it after the command (e.g., `my-command.md` → `/my-command`)
3. Add optional frontmatter with description
4. Write the prompt/instructions for Claude to execute

### Example Template

```markdown
---
description: Brief description of what this command does
---

# Command Name

Instructions for Claude to execute when this command is invoked.

## Usage

```python
tool_name(action="...", param="...")
```

## Steps

1. First step description
2. Second step description
3. etc.
```

## Related Documentation

- [Slash Commands Guide](../../docs/SLASH-COMMANDS-GUIDE.md) - Complete guide to LEE slash commands
- [Tools README](../tools/README.md) - Function tools documentation
