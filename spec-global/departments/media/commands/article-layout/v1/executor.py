#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Article Layout Splash Command Executor V2
文章排版命令执行器 V2

两阶段排版方案：
1. 第一阶段：LLM 识别文章重点（词句、段落）
2. 第二阶段：基于规则排版，应用重点标注

执行 /layout 命令，将文章转换为格式化的平台就绪内容。

Usage:
    python article_layout_command.py <file_path> [options]

Options:
    --theme <theme>         主题选择 (wechat_red_safe, blue, minimal)
    --platform <platform>   目标平台 (wechat, xhs, notion, feishu, generic)
    --format <format>       输出格式 (md, html, both)
    --no-proofread          跳过自动校对
    --no-llm                不使用 LLM，使用基于规则的排版
"""

import argparse
import json
import os
import sys
import asyncio
import re
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent.parent.parent  # 到 E:/ai/lee (7 级向上)
spec_global_root = project_root / "spec-global"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 导入 LLM 执行器
LLM_AVAILABLE = False
try:
    from lee.orchestrator.execution.llm_executor import LLMExecutor
    LLM_AVAILABLE = True
    print(f"   ✓ LLM 执行器导入成功")
except ImportError as e:
    print(f"   ⚠ LLM 执行器导入失败：{e}")
    print(f"   将使用基于规则的排版")


class ArticleLayoutCommand:
    """文章排版命令执行器 V2 - 两阶段方案"""

    def __init__(self, file_path: str, theme: str = "wechat_red_safe",
                 platform: str = "wechat", output_format: str = "both",
                 proofread: bool = True, use_llm: bool = True):
        self.file_path = Path(file_path)
        self.theme = theme
        self.platform = platform
        self.output_format = output_format
        self.proofread = proofread
        # 默认使用 LLM 识别重点，但用规则排版保证内容完整性
        self.use_llm = use_llm and LLM_AVAILABLE
        self.highlights = {"highlight_phrases": [], "highlight_blocks": [], "highlight_titles": []}

        # LLM 执行器
        self.llm_executor = None
        if self.use_llm:
            try:
                try:
                    self.llm_executor = LLMExecutor(profile="deepseek")
                    print(f"   ✓ DeepSeek-Chat LLM 初始化成功")
                except Exception:
                    self.llm_executor = LLMExecutor(profile="huawei_deepseek")
                    print(f"   ✓ Huawei DeepSeek LLM 初始化成功")
            except Exception as e:
                print(f"   ⚠ LLM 初始化失败：{e}，使用基于规则的排版")
                self.use_llm = False
        else:
            print(f"   ℹ LLM 已禁用，使用基于规则的排版")

        # 输出目录
        self.output_dir = self.file_path.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        # 输出文件名
        base_name = self.file_path.stem
        self.output_md = self.output_dir / f"{base_name}_final.md"
        self.output_html = self.output_dir / f"{base_name}_final.html"
        self.report_file = self.output_dir / f"{base_name}_report.json"

    def validate_input(self):
        """验证输入文件"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"找不到文件：{self.file_path}")

        supported_extensions = {".md", ".txt", ".markdown"}
        if self.file_path.suffix.lower() not in supported_extensions:
            raise ValueError(
                f"不支持的文件格式：{self.file_path.suffix}。"
                f"支持的格式：{', '.join(supported_extensions)}"
            )

    def load_theme_config(self):
        """加载主题配置"""
        theme_names = [self.theme, "wechat-red-theme", "red-theme"]
        base_paths = [
            spec_global_root / "departments" / "media" / "themes",
            spec_global_root / "themes",
        ]

        for base_path in base_paths:
            for theme_name in theme_names:
                theme_path = base_path / theme_name / "v1" / "theme.yaml"
                if theme_path.exists():
                    import yaml
                    with open(theme_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f)
                        print(f"   加载主题：{theme_name}")
                        return config

        print(f"   ⚠ 主题配置未找到，使用默认配置")
        return {
            "colors": {
                "red_primary": "#ff4d4f",
                "red_dark": "#cf1322",
                "red_bg": "#fff1f0",
                "text_main": "#555555",
                "text_muted": "#666666",
                "text_deep": "#4a4a4a",
            }
        }

    def read_article(self):
        """读取文章内容"""
        with open(self.file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _validate_output_completeness(self, original: str, formatted: str) -> bool:
        """验证输出是否完整"""
        orig_len = len(original.strip())
        fmt_len = len(formatted.strip())

        # 如果输出长度小于原文的 30%，肯定有问题
        if fmt_len < orig_len * 0.3:
            print(f"   ⚠ 输出长度异常：原文 {orig_len} 字符，输出 {fmt_len} 字符 ({fmt_len*100//orig_len}%)")
            return False

        # 检查主要章节标题是否保留
        orig_headers = set(re.findall(r'^#{1,2}\s+(.+)$', original, re.MULTILINE))

        if orig_headers:
            found_count = 0
            clean_formatted = re.sub(r'<[^>]+>', '', formatted)

            for header in orig_headers:
                if header in formatted or header in clean_formatted:
                    found_count += 1
                    continue

                if header.replace(' ', '') in formatted.replace(' ', '') or header.replace(' ', '') in clean_formatted.replace(' ', ''):
                    found_count += 1
                    continue

                core_header = re.sub(r'^[零一二三四五六七八九十百]+[、..]\s*', '', header)
                core_header = re.sub(r'^\d+[、..]\s*', '', core_header)
                core_header = re.sub(r'^[1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣8️⃣9️⃣🔟]+\s*', '', core_header)
                core_header = core_header.strip()

                if len(core_header) >= 4 and core_header in clean_formatted:
                    found_count += 1
                    continue

                if len(core_header) >= 4:
                    if re.search(rf'\d+\.\s*{re.escape(core_header)}', formatted):
                        found_count += 1
                        continue

            retention_rate = found_count / len(orig_headers)
            if retention_rate < 0.5:
                print(f"   ⚠ 标题保留率异常：{retention_rate*100:.0f}% ({found_count}/{len(orig_headers)})")
                return False

        return True

    async def _llm_extract_highlights(self, article_content: str) -> dict:
        """
        第一阶段：使用 LLM 识别文章中的重点内容
        返回一个字典，包含需要强调的词句和段落
        """
        os.environ["LLM_TIMEOUT_SECONDS"] = "180"

        system_prompt = """你是一个文章重点识别专家。你的任务是分析文章，识别出需要强调的重点内容。

【重要原则】
- 你只需要识别重点，不需要排版或改写
- 所有识别出的文本必须是原文中的 exact 文本，不能修改
- 输出必须是合法的 JSON 格式

**输出格式（必须是合法的 JSON）**：
```json
{
    "highlight_phrases": [
        {"text": "原文中的 exact 文本", "type": "core_concept|contrast|conclusion|data"}
    ],
    "highlight_blocks": [
        {"text": "需要放入高亮引用块的完整段落或句子", "type": "conclusion|key_insight"}
    ]
}
```

**识别规则**：

1. **highlight_phrases（行内强调 - 用红色加粗）**：
   - 核心概念/关键结论 → type="core_concept"
   - 对比句中的重点部分（"不是 A，而是 B"中的 B）→ type="contrast"
   - 重要数据/数字 → type="data"
   - 每个章节的核心观点

2. **highlight_blocks（高亮引用块）**：
   - 文章的核心结论段落
   - 关键洞察
   - 总结性陈述
   - 重要引言

**重要要求**：
- 只识别重点，不要改写或总结
- 所有 text 字段必须是原文中的 exact 文本
- 不要遗漏任何重要内容
- 输出纯 JSON，不要包裹在代码块中"""

        user_prompt = f"""请分析以下文章，识别需要强调的重点内容：

```markdown
{article_content}
```

按以下标准识别：
1. 核心观点、关键结论
2. 对比句（"不是 A，而是 B"格式）
3. 重要数据、百分比
4. 总结性陈述

输出 JSON 格式结果。"""

        result = await self.llm_executor.execute({
            "prompt": user_prompt,
            "system_message": system_prompt,
            "temperature": 0.1,
            "max_tokens": 4096
        })

        if result.get("status") == "completed":
            llm_output = result.get("generated_text", "").strip()

            # 处理可能的代码块包裹
            if llm_output.startswith("```json"):
                llm_output = llm_output[7:]
            if llm_output.endswith("```"):
                llm_output = llm_output[:-3]
            llm_output = llm_output.strip()

            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
            if json_match:
                llm_output = json_match.group()

            try:
                highlights = json.loads(llm_output)
                print(f"   LLM 识别：{len(highlights.get('highlight_phrases', []))} 个重点短语，"
                      f"{len(highlights.get('highlight_blocks', []))} 个重点段落")
                return highlights
            except json.JSONDecodeError as e:
                print(f"   ⚠ JSON 解析失败：{e}，返回空字典")
                return {"highlight_phrases": [], "highlight_blocks": []}
        else:
            print(f"   ⚠ LLM 调用失败：{result.get('error', '未知错误')}")
            return {"highlight_phrases": [], "highlight_blocks": []}

    async def _llm_layout(self, article_content: str, theme_config: dict) -> str:
        """
        两阶段排版方案：
        第一阶段：LLM 识别重点
        第二阶段：基于规则排版，应用重点标注
        """
        os.environ["LLM_TIMEOUT_SECONDS"] = "300"

        # 第一阶段：提取重点
        print("   第一阶段：LLM 识别文章重点...")
        self.highlights = await self._llm_extract_highlights(article_content)

        # 将重点信息传递给规则排版器
        print("   第二阶段：基于规则排版，应用重点标注...")
        return self._apply_layout_with_highlights(article_content, self.highlights, theme_config)

    def _apply_layout_with_highlights(self, article_content: str, highlights: dict, theme_config: dict) -> str:
        """
        基于规则排版，并应用 LLM 识别的重点标注
        """
        # 构建重点查找表
        highlight_phrases = set()
        for item in highlights.get("highlight_phrases", []):
            text = item.get("text", "").strip()
            if text:
                highlight_phrases.add(text)

        highlight_blocks = set()
        for item in highlights.get("highlight_blocks", []):
            text = item.get("text", "").strip()
            if text:
                highlight_blocks.add(text)

        # 调用 rule_based_layout_v2 模块
        try:
            import importlib.util
            rule_based_path = Path(__file__).parent / "rule_based_layout_v2.py"
            spec = importlib.util.spec_from_file_location("rule_based_layout_v2", rule_based_path)
            rule_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rule_module)

            # 使用带重点信息的排版函数
            if hasattr(rule_module, 'apply_rule_based_layout_with_highlights'):
                return rule_module.apply_rule_based_layout_with_highlights(
                    article_content, highlight_phrases, highlight_blocks
                )
            else:
                # 回退到普通规则排版
                return rule_module.apply_rule_based_layout(article_content)

        except Exception as e:
            print(f"   ⚠ 规则排版失败：{e}，使用基础排版")
            return self._simple_markdown_to_html(article_content, {})

    def _fallback_rule_based_layout(self, article_content: str) -> str:
        """回退到基于规则的排版"""
        try:
            import importlib.util
            rule_based_path = Path(__file__).parent / "rule_based_layout.py"
            spec = importlib.util.spec_from_file_location("rule_based_layout", rule_based_path)
            rule_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rule_module)
            return rule_module.apply_rule_based_layout(article_content)
        except Exception as e:
            print(f"   ⚠ 基于规则的排版失败：{e}")
            return self._simple_markdown_to_html(article_content, {})

    def _simple_markdown_to_html(self, article_content: str, theme_config: dict) -> str:
        """Simple Markdown to HTML converter"""
        colors = theme_config.get("colors", {})
        lines = article_content.split("\n")
        result = []
        in_paragraph = False
        in_list = False
        in_blockquote = False

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                if in_list:
                    result.append("</ul>")
                    in_list = False
                if in_blockquote:
                    result.append("</blockquote>")
                    in_blockquote = False
                i += 1
                continue

            if stripped.startswith("# "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                content = stripped[2:].strip()
                result.append(f'<h1>{content}</h1>')

            elif stripped.startswith("## "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                content = stripped[3:].strip()
                result.append(f'<h2>{content}</h2>')

            elif stripped.startswith("### "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                content = stripped[4:].strip()
                result.append(f'<h3>{content}</h3>')

            elif stripped.startswith(">"):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                if not in_blockquote:
                    in_blockquote = True
                    is_highlight = "核心" in stripped or "重点" in stripped or "关键" in stripped
                    result.append(f'<blockquote class="highlight">' if is_highlight else '<blockquote>')
                content = stripped[1:].strip()
                result.append(f'<p>{content}</p>' if content else '<br>')

            elif stripped.startswith("- ") or stripped.startswith("* "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                if not in_list:
                    in_list = True
                    result.append("<ul>")
                content = stripped[2:].strip()
                result.append(f'<li>{content}</li>')

            elif stripped == "---" or stripped == "***":
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                result.append("<hr>")

            else:
                if not in_paragraph:
                    result.append("<p>")
                    in_paragraph = True
                else:
                    result.append("<br>")
                result.append(stripped)

            i += 1

        if in_paragraph:
            result.append("</p>")
        if in_list:
            result.append("</ul>")
        if in_blockquote:
            result.append("</blockquote>")

        return "\n".join(result)

    def proofread_content(self, content: str) -> tuple:
        """Proofread content, fix dark text colors"""
        issues_found = []

        dark_colors = {
            "#333333": "#555555",
            "#8c8c8c": "#666666",
        }

        for dark, light in dark_colors.items():
            if dark in content:
                count = content.count(dark)
                issues_found.append({
                    "type": "dark_text",
                    "color": dark,
                    "replacement": light,
                    "count": count
                })
                content = content.replace(dark, light)

        if '<blockquote style="color:#666666;">' in content:
            content = content.replace(
                '<blockquote style="color:#666666;">',
                '<blockquote style="color:#4a4a4a;">'
            )
            issues_found.append({
                "type": "quote_block_color",
                "original": "#666666",
                "replacement": "#4a4a4a",
                "reason": "Use deeper color for quote blocks to ensure contrast"
            })

        return content, issues_found

    def generate_html(self, markdown_content: str) -> str:
        """Generate standalone HTML file"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.file_path.stem}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            color: #555555;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }}
        h1 {{
            color: #ff4d4f;
            font-weight: 700;
            font-size: 24px;
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #cf1322;
            font-weight: 600;
            font-size: 18px;
            margin-top: 24px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #ff4d4f;
        }}
        h3 {{
            color: #cf1322;
            font-weight: 600;
            font-size: 16px;
            margin-top: 16px;
            margin-bottom: 8px;
        }}
        p {{
            color: #555555;
            font-size: 15px;
            margin: 8px 0;
            line-height: 1.8;
        }}
        blockquote {{
            color: #4a4a4a;
            padding: 12px 16px;
            margin: 16px 0;
            border-left: 4px solid #d9d9d9;
            background: #f5f5f5;
        }}
        blockquote.highlight {{
            background: #fff1f0;
            border-left: 4px solid #ff4d4f;
        }}
        strong {{
            font-weight: 600;
        }}
        ul {{
            padding-left: 20px;
        }}
        ol {{
            padding-left: 24px;
        }}
        li {{
            margin: 4px 0;
        }}
        span.emphasis {{
            color: #ff4d4f;
            font-weight: 600;
        }}
        span.text {{
            color: #555555;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e8e8e8;
            margin: 20px 0;
        }}
        pre {{
            background: #282c34;
            border-radius: 8px;
            padding: 0;
            margin: 16px 0;
            overflow: hidden;
            position: relative;
        }}
        .code-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            background: #21252b;
            border-bottom: 1px solid #181a1f;
        }}
        .code-language {{
            color: #61afef;
            font-size: 12px;
            font-weight: 500;
            text-transform: uppercase;
        }}
        .code-copy {{
            color: #abb2bf;
            font-size: 12px;
            cursor: pointer;
            padding: 4px 12px;
            border: 1px solid #4b5263;
            border-radius: 4px;
            background: transparent;
            transition: all 0.2s;
        }}
        .code-copy:hover {{
            background: #3e4451;
            color: #fff;
        }}
        .code-copy.copied {{
            background: #98c379;
            border-color: #98c379;
            color: #fff;
        }}
        pre > code {{
            display: block;
            padding: 16px;
            overflow-x: auto;
            font-family: "Consolas", "Monaco", "Courier New", monospace;
            font-size: 14px;
            line-height: 1.6;
            background: transparent;
        }}
        p > code, li > code, span > code {{
            background: #f5f5f5;
            color: #cf1322;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Consolas", "Monaco", monospace;
            font-size: 13px;
        }}
        .hljs {{
            background: #282c34;
            color: #abb2bf;
        }}
    </style>
</head>
<body>
{markdown_content}
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        hljs.highlightAll();

        document.querySelectorAll('pre > code').forEach(function(block) {{
            const pre = block.parentElement;
            if (pre.querySelector('.code-header')) return;

            const languageClass = Array.from(block.classList).find(c => c.startsWith('language-'));
            const language = languageClass ? languageClass.replace('language-', '') : 'text';

            const header = document.createElement('div');
            header.className = 'code-header';
            header.innerHTML = `
                <span class="code-language">${{language}}</span>
                <button class="code-copy" onclick="copyCode(this)">复制代码</button>
            `;

            pre.insertBefore(header, block);
        }});
    }});

    function copyCode(button) {{
        const pre = button.closest('pre');
        const code = pre.querySelector('code');
        const text = code.textContent;

        if (navigator.clipboard && window.isSecureContext) {{
            navigator.clipboard.writeText(text).then(function() {{
                showCopySuccess(button);
            }}).catch(function() {{
                fallbackCopy(text, button);
            }});
        }} else {{
            fallbackCopy(text, button);
        }}
    }}

    function fallbackCopy(text, button) {{
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {{
            const successful = document.execCommand('copy');
            if (successful) {{
                showCopySuccess(button);
            }} else {{
                button.textContent = '复制失败';
                setTimeout(function() {{
                    button.textContent = '复制代码';
                }}, 2000);
            }}
        }} catch (err) {{
            button.textContent = '复制失败';
            setTimeout(function() {{
                button.textContent = '复制代码';
            }}, 2000);
        }}

        document.body.removeChild(textarea);
    }}

    function showCopySuccess(button) {{
        button.textContent = '已复制';
        button.classList.add('copied');
        setTimeout(function() {{
            button.textContent = '复制代码';
            button.classList.remove('copied');
        }}, 2000);
    }}
</script>
</body>
</html>"""

    def run(self):
        """执行排版命令"""
        print(f"📝 文章排版命令执行器 V2（两阶段方案）")
        print(f"=" * 50)
        print(f"输入文件：{self.file_path}")
        print(f"主题：{self.theme}")
        print(f"平台：{self.platform}")
        print(f"输出格式：{self.output_format}")
        print(f"自动校对：{'是' if self.proofread else '否'}")
        print()

        self.validate_input()

        print("📖 读取文章...")
        article_content = self.read_article()

        print("🎨 加载主题配置...")
        theme_config = self.load_theme_config()

        print("✨ 应用排版样式...")
        if self.use_llm:
            # 两阶段方案：LLM 识别重点 + 规则排版
            formatted_content = asyncio.run(self._llm_layout(article_content, theme_config))

            # 验证输出完整性
            if not self._validate_output_completeness(article_content, formatted_content):
                print("   ⚠ LLM 排版输出不完整，回退到纯规则排版...")
                formatted_content = self._fallback_rule_based_layout(article_content)
        else:
            # 纯规则排版
            print("   使用基于规则的排版处理器...")
            formatted_content = self._fallback_rule_based_layout(article_content)

        # 检测是否为完整的 HTML
        is_full_html = formatted_content.strip().startswith("<!DOCTYPE html>") or formatted_content.strip().startswith("<html")

        report = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(self.file_path),
            "theme": self.theme,
            "platform": self.platform,
            "output_format": self.output_format,
            "proofread_issues": [],
            "output_files": [],
            "use_llm": self.use_llm,
            "is_full_html": is_full_html,
            "highlights": self.highlights
        }

        proofread_issues = []
        if self.proofread:
            print("🔍 自动校对...")
            formatted_content, proofread_issues = self.proofread_content(formatted_content)
            if proofread_issues:
                print(f"   发现 {len(proofread_issues)} 个问题，已自动修复")
            report["proofread_issues"] = proofread_issues

        print("💾 保存输出文件...")

        if self.output_format in ["md", "both"]:
            with open(self.output_md, "w", encoding="utf-8") as f:
                f.write(formatted_content)
            report["output_files"].append(str(self.output_md))
            print(f"   ✓ {self.output_md}")

        if self.output_format in ["html", "both"]:
            if is_full_html:
                html_content = formatted_content
            else:
                html_content = self.generate_html(formatted_content)
            with open(self.output_html, "w", encoding="utf-8") as f:
                f.write(html_content)
            report["output_files"].append(str(self.output_html))
            print(f"   ✓ {self.output_html}")

        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"   ✓ {self.report_file}")

        print()
        print("✅ 排版完成！")
        print(f"📂 输出目录：{self.output_dir}")

        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="文章排版命令 - 将文章转换为格式化的平台就绪内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s articles/my-post.md
  %(prog)s articles/my-post.md --theme blue
  %(prog)s articles/my-post.md --platform xhs --format html
  %(prog)s articles/my-post.md --theme minimal --platform notion
        """
    )

    parser.add_argument(
        "file_path",
        help="输入文章的文件路径（.md 或 .txt）"
    )

    parser.add_argument(
        "--theme",
        choices=["wechat_red_safe", "blue", "minimal"],
        default="wechat_red_safe",
        help="排版主题（默认：wechat_red_safe）"
    )

    parser.add_argument(
        "--platform",
        choices=["wechat", "xhs", "notion", "feishu", "generic"],
        default="wechat",
        help="目标平台（默认：wechat）"
    )

    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["md", "html", "both"],
        default="both",
        help="输出格式（默认：both）"
    )

    parser.add_argument(
        "--no-proofread",
        action="store_true",
        help="跳过自动校对"
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="不使用 LLM，使用基于规则的排版"
    )

    args = parser.parse_args()

    try:
        command = ArticleLayoutCommand(
            file_path=args.file_path,
            theme=args.theme,
            platform=args.platform,
            output_format=args.output_format,
            proofread=not args.no_proofread,
            use_llm=not args.no_llm
        )
        command.run()

    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        print("请检查文件路径是否正确", file=sys.stderr)
        sys.exit(1)

    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"❌ 执行出错：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
