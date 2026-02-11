"""
Diagram Generation CLI — 将结构 DSL 转换为 Mermaid 文本
lee diagram-gen render
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click


# ── Mermaid 生成核心 ──

CHART_TYPE_MAP = {
    "governance_loop": "flowchart",
    "execution_pipeline": "flowchart",
    "system_architecture": "flowchart",
    "decision_tree": "flowchart",
    "hierarchy": "flowchart",
    "workflow": "flowchart",
    "state_machine": "stateDiagram-v2",
    "data_flow": "flowchart",
    "concept_map": "flowchart",
    "comparison_matrix": "flowchart",
}

NODE_TEMPLATES = {
    "actor": '{id}["{label}"]',
    "decision": '{id}{{"{label}"}}',
    "terminator": '{id}(["{label}"])',
    "process": '{id}["{label}"]',
    "default": '{id}["{label}"]',
}


def _sanitize_id(node_id: str) -> str:
    """Replace illegal characters in node IDs."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in node_id)


def _escape_label(label: str) -> str:
    """Escape quotes in labels for Mermaid syntax."""
    return label.replace('"', "#quot;")


def _render_node(node: dict) -> str:
    node_type = node.get("type", "default")
    template = NODE_TEMPLATES.get(node_type, NODE_TEMPLATES["default"])
    return template.format(
        id=_sanitize_id(node["id"]),
        label=_escape_label(node.get("label", node["id"])),
    )


def _render_edge(edge: dict) -> str:
    src = _sanitize_id(edge["from"])
    dst = _sanitize_id(edge["to"])
    label = edge.get("label")
    if label:
        return f'{src} -->|"{_escape_label(label)}"| {dst}'
    return f"{src} --> {dst}"


def generate_mermaid(diagram: dict) -> str:
    """Convert a structure DSL dict to Mermaid source text."""
    diagram_type = diagram.get("type", "flowchart")
    chart_type = CHART_TYPE_MAP.get(diagram_type, "flowchart")

    dsl = diagram.get("structure_dsl", diagram)
    direction = dsl.get("direction", "TD")
    nodes = dsl.get("nodes", [])
    edges = dsl.get("edges", [])

    lines = [f"{chart_type} {direction}"]
    for node in nodes:
        lines.append(f"    {_render_node(node)}")

    if nodes and edges:
        lines.append("")

    for edge in edges:
        lines.append(f"    {_render_edge(edge)}")

    return "\n".join(lines)


# ── CLI ──

@click.group("diagram-gen")
def diagram_gen():
    """图表生成工具 — 结构 DSL 转 Mermaid"""
    pass


@diagram_gen.command()
@click.option("--input", "-i", "input_file", required=True,
              help="输入的结构 DSL JSON 文件")
@click.option("--output", "-o", "output_file", default=None,
              help="输出 Mermaid 文件路径 (.mmd)，默认 stdout")
@click.option("--wrap-fences", is_flag=True, default=False,
              help="是否用 ```mermaid ``` 包裹输出")
def render(input_file: str, output_file: Optional[str], wrap_fences: bool):
    """将结构 DSL JSON 渲染为 Mermaid 文本"""
    input_path = Path(input_file)
    if not input_path.exists():
        click.echo(json.dumps({"ok": False, "error": f"File not found: {input_file}"}))
        sys.exit(3)

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        click.echo(json.dumps({"ok": False, "error": f"Invalid JSON: {e}"}))
        sys.exit(3)

    # Support both {"diagram": {...}} and direct diagram object
    diagram = data.get("diagram", data)

    try:
        mermaid_source = generate_mermaid(diagram)
    except Exception as e:
        click.echo(json.dumps({"ok": False, "error": f"Generation failed: {e}"}))
        sys.exit(1)

    if wrap_fences:
        mermaid_source = f"```mermaid\n{mermaid_source}\n```"

    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(mermaid_source, encoding="utf-8")
        result = {
            "ok": True,
            "output_file": str(out_path),
            "diagram_id": diagram.get("id", "unknown"),
            "chart_type": CHART_TYPE_MAP.get(diagram.get("type", ""), "flowchart"),
        }
        click.echo(json.dumps(result))
    else:
        click.echo(mermaid_source)

    sys.exit(0)
