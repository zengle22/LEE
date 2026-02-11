"""
Markdown to WeChat RichText CLI — 将 Markdown 转换为公众号安全 HTML
lee md-to-wechat convert
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click


# ── WeChat-safe HTML conversion ──

FORBIDDEN_TAGS = {"div", "section", "article", "script", "style", "link", "iframe"}

DEFAULT_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
</head>
<body>
{body}
</body>
</html>
"""


def _find_pandoc() -> Optional[str]:
    """Find pandoc executable."""
    for name in ("pandoc",):
        try:
            result = subprocess.run(
                [name, "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _convert_with_pandoc(md_file: str, html_file: str, template: Optional[str] = None) -> bool:
    """Convert markdown to HTML using pandoc."""
    cmd = [
        "pandoc", md_file,
        "--from", "markdown",
        "--to", "html",
        "--standalone",
        "--no-highlight",
        "-o", html_file,
    ]
    if template and Path(template).exists():
        cmd.extend(["--template", template])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def _convert_fallback(md_file: str, html_file: str) -> bool:
    """Fallback: basic markdown to HTML using Python (no pandoc)."""
    import html as html_mod

    md_text = Path(md_file).read_text(encoding="utf-8")
    lines = md_text.split("\n")
    html_parts = []
    title = "文章"
    in_code_block = False

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                html_parts.append("</code></pre>")
                in_code_block = False
            else:
                html_parts.append("<pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(html_mod.escape(line))
            continue

        stripped = line.strip()

        # Headings
        if stripped.startswith("### "):
            text = html_mod.escape(stripped[4:])
            html_parts.append(
                f'<h3 style="font-size:16px;font-weight:bold;margin:16px 0 8px;">{text}</h3>'
            )
        elif stripped.startswith("## "):
            text = html_mod.escape(stripped[3:])
            html_parts.append(
                f'<h2 style="font-size:18px;font-weight:bold;margin:20px 0 10px;">{text}</h2>'
            )
        elif stripped.startswith("# "):
            text = html_mod.escape(stripped[2:])
            title = stripped[2:]
            html_parts.append(
                f'<h1 style="font-size:20px;font-weight:bold;text-align:center;margin-bottom:16px;">{text}</h1>'
            )
        # Blockquote
        elif stripped.startswith("> "):
            text = html_mod.escape(stripped[2:])
            html_parts.append(
                f'<blockquote style="border-left:3px solid #ccc;padding:8px 12px;color:#666;">{text}</blockquote>'
            )
        # List items
        elif stripped.startswith("- ") or stripped.startswith("* "):
            text = html_mod.escape(stripped[2:])
            html_parts.append(f"<li>{text}</li>")
        # Bold/italic inline
        elif stripped:
            text = html_mod.escape(stripped)
            # Apply inline formatting
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            html_parts.append(f'<p style="margin:8px 0;line-height:1.8;">{text}</p>')
        else:
            html_parts.append("")

    body = "\n".join(html_parts)
    html_output = DEFAULT_TEMPLATE.format(title=html_mod.escape(title), body=body)
    Path(html_file).write_text(html_output, encoding="utf-8")
    return True


def _verify_html(html_file: str) -> list:
    """Verify HTML output for WeChat safety."""
    violations = []
    content = Path(html_file).read_text(encoding="utf-8")

    # Check forbidden tags
    for tag in FORBIDDEN_TAGS:
        if f"<{tag}" in content.lower():
            violations.append(f"Forbidden tag <{tag}> found")

    # Check external CSS
    if '<link rel="stylesheet"' in content:
        violations.append("External CSS link found")

    # Check external resources
    if re.search(r'(href=|src=)"http', content):
        violations.append("External resource reference found")

    return violations


# ── CLI ──

@click.group("md-to-wechat")
def md_to_wechat():
    """Markdown 转公众号富文本工具"""
    pass


@md_to_wechat.command()
@click.option("--input", "-i", "input_file", required=True,
              help="输入的 Markdown 文件路径")
@click.option("--output", "-o", "output_file", default=None,
              help="输出的 HTML 文件路径，默认为 input 同目录下 wechat.html")
@click.option("--theme", "-t", default="red",
              type=click.Choice(["red", "blue", "minimal"]),
              help="主题选择")
@click.option("--template", default=None,
              help="自定义 Pandoc 模板路径")
@click.option("--verify/--no-verify", default=True,
              help="是否验证输出 HTML")
def convert(input_file: str, output_file: Optional[str], theme: str,
            template: Optional[str], verify: bool):
    """将 Markdown 转换为公众号安全 HTML"""
    input_path = Path(input_file)
    if not input_path.exists():
        click.echo(json.dumps({"ok": False, "error": f"File not found: {input_file}"}))
        sys.exit(3)

    if output_file is None:
        output_file = str(input_path.parent / "wechat.html")

    # Try pandoc first, fallback to built-in
    pandoc = _find_pandoc()
    if pandoc:
        success = _convert_with_pandoc(input_file, output_file, template)
        engine = "pandoc"
    else:
        success = _convert_fallback(input_file, output_file)
        engine = "builtin"

    if not success:
        click.echo(json.dumps({"ok": False, "error": "Conversion failed"}))
        sys.exit(1)

    # Verify
    violations = _verify_html(output_file) if verify else []

    # Count words
    md_text = input_path.read_text(encoding="utf-8")
    word_count = len(md_text)

    result = {
        "ok": len(violations) == 0,
        "html_file": output_file,
        "engine": engine,
        "metadata": {
            "title": input_path.stem,
            "word_count": word_count,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "verifier_passed": len(violations) == 0,
            "theme": theme,
        },
    }
    if violations:
        result["violations"] = violations

    click.echo(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if len(violations) == 0 else 1)
