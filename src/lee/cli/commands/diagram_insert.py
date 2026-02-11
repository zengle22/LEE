"""
Diagram Insertion CLI — 在 Markdown 中插入图表占位提示
lee diagram-insert insert
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import click


# ── 占位模板 ──

TEMPLATES = {
    "standard": """<!-- DIAGRAM:{asset_id} -->
【结构图：{caption}】

> 📎 发布前操作：
> 1. 打开文件：`{png_path}`
> 2. 上传到公众号素材库
> 3. 删除本占位提示，插入图片""",

    "minimal": "【图：{caption}】({png_path})",

    "detailed": """---
**图表占位：{caption}**

- 文件位置：`{png_path}`
- Mermaid 源码：`{mmd_path}`
- 建议宽度：800px

发布后请删除此区块。
---""",
}


def _format_placeholder(asset: dict, template_name: str = "standard") -> str:
    """Format a single placeholder from an asset dict."""
    template = TEMPLATES.get(template_name, TEMPLATES["standard"])
    files = asset.get("files", {})
    return template.format(
        asset_id=asset.get("id", "unknown"),
        caption=asset.get("caption", "图表"),
        png_path=files.get("png", {}).get("path", "images/unknown.png"),
        mmd_path=files.get("mmd", {}).get("path", "images/unknown.mmd"),
    )


def _split_paragraphs(text: str):
    """Split markdown into paragraphs (by double newline)."""
    return re.split(r"\n\n+", text)


def insert_diagrams(article_md: str, assets: list, template: str = "standard") -> tuple:
    """
    Insert diagram placeholders into article markdown.
    Returns (modified_article, insertion_report).
    """
    paragraphs = _split_paragraphs(article_md)
    insertions = []  # (paragraph_index, placeholder_text, asset_id)

    for asset in assets:
        guide = asset.get("insertion_guide", {})
        position = guide.get("suggested_position", {})
        placeholder = _format_placeholder(asset, template)

        after_paragraph = position.get("after_paragraph")
        after_heading = position.get("after_heading")

        if after_paragraph is not None:
            idx = min(after_paragraph, len(paragraphs))
            insertions.append((idx, placeholder, asset.get("id"), position))
        elif after_heading is not None:
            # Find the heading by fuzzy match
            found = False
            for i, para in enumerate(paragraphs):
                if para.strip().startswith("#") and after_heading.lower() in para.lower():
                    insertions.append((i + 1, placeholder, asset.get("id"), position))
                    found = True
                    break
            if not found:
                # Fallback: append at end
                insertions.append((len(paragraphs), placeholder, asset.get("id"), position))
        else:
            # Default: append at end
            insertions.append((len(paragraphs), placeholder, asset.get("id"), position))

    # Sort by position descending to avoid index shifts
    insertions.sort(key=lambda x: x[0], reverse=True)

    for idx, placeholder, _, _ in insertions:
        paragraphs.insert(idx, placeholder)

    result_article = "\n\n".join(paragraphs)

    # Build report
    report = {
        "total_placeholders": len(insertions),
        "placeholders": [
            {
                "position": pos,
                "placeholder_text": f"【结构图：{assets[i].get('caption', '图表')}】" if i < len(assets) else "",
                "asset_id": aid,
            }
            for i, (_, _, aid, pos) in enumerate(sorted(insertions, key=lambda x: x[0]))
        ],
    }

    return result_article, report


# ── CLI ──

@click.group("diagram-insert")
def diagram_insert():
    """图表插入工具 — 在 Markdown 中插入占位提示"""
    pass


@diagram_insert.command()
@click.option("--article", "-a", required=True, help="输入的 Markdown 文件路径")
@click.option("--assets", "-s", required=True, help="图表资产清单 JSON 文件")
@click.option("--output", "-o", "output_file", default=None,
              help="输出 Markdown 文件路径，默认覆写原文件")
@click.option("--template", "-t", default="standard",
              type=click.Choice(["standard", "minimal", "detailed"]),
              help="占位提示模板")
@click.option("--report", "-r", "report_file", default=None,
              help="输出插入报告 JSON 文件路径")
def insert(article: str, assets: str, output_file: Optional[str],
           template: str, report_file: Optional[str]):
    """将图表占位提示插入 Markdown 文章中"""
    article_path = Path(article)
    assets_path = Path(assets)

    if not article_path.exists():
        click.echo(json.dumps({"ok": False, "error": f"Article not found: {article}"}))
        sys.exit(3)
    if not assets_path.exists():
        click.echo(json.dumps({"ok": False, "error": f"Assets file not found: {assets}"}))
        sys.exit(3)

    article_md = article_path.read_text(encoding="utf-8")

    try:
        assets_data = json.loads(assets_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        click.echo(json.dumps({"ok": False, "error": f"Invalid assets JSON: {e}"}))
        sys.exit(3)

    # Support both {"diagram_assets": [...]} and direct array
    if isinstance(assets_data, dict):
        asset_list = assets_data.get("diagram_assets", assets_data.get("assets", []))
    elif isinstance(assets_data, list):
        asset_list = assets_data
    else:
        click.echo(json.dumps({"ok": False, "error": "Assets must be array or {diagram_assets:[...]}"}))
        sys.exit(3)

    result_md, report = insert_diagrams(article_md, asset_list, template)

    # Write output
    out_path = Path(output_file) if output_file else article_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result_md, encoding="utf-8")

    # Write report
    if report_file:
        rp = Path(report_file)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "ok": True,
        "output_file": str(out_path),
        "total_placeholders": report["total_placeholders"],
    }
    click.echo(json.dumps(result, ensure_ascii=False))
    sys.exit(0)
