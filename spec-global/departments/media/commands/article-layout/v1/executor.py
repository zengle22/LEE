#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Article Layout Splash Command Executor
文章排版命令执行器

执行 /layout 命令，将文章转换为格式化的平台就绪内容。

Usage:
    python article_layout_command.py <file_path> [options]

Options:
    --theme <theme>         主题选择 (wechat_red_safe, blue, minimal)
    --platform <platform>   目标平台 (wechat, xhs, notion, feishu, generic)
    --format <format>       输出格式 (md, html, both)
    --no-proofread          跳过自动校对
"""

import argparse
import json
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
# executor.py 位于: E:/ai/lee/spec-global/departments/media/commands/article-layout/v1/
# project_root 应该是: E:/ai/lee/
project_root = Path(__file__).parent.parent.parent.parent.parent.parent.parent  # 到 E:/ai/lee (7级向上)
spec_global_root = project_root / "spec-global"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 导入 LLM 执行器和基于规则的排版处理器
LLM_AVAILABLE = False
try:
    from lee.orchestrator.execution.llm_executor import LLMExecutor
    LLM_AVAILABLE = True
    print(f"   ✓ LLM 执行器导入成功")
except ImportError as e:
    print(f"   ⚠ LLM 执行器导入失败: {e}")
    print(f"   将使用基于规则的排版")

# 导入基于规则的排版处理器（从本地文件导入）
RULE_BASED_LAYOUT_AVAILABLE = False
try:
    import importlib.util
    rule_based_path = Path(__file__).parent / "rule_based_layout.py"
    if rule_based_path.exists():
        spec = importlib.util.spec_from_file_location("rule_based_layout", rule_based_path)
        rule_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rule_module)
        apply_rule_based_layout = rule_module.apply_rule_based_layout
        RULE_BASED_LAYOUT_AVAILABLE = True
except Exception as e:
    if "--no-llm" not in sys.argv:
        print(f"   ⚠ 基于规则的排版处理器导入失败: {e}")


class ArticleLayoutCommand:
    """文章排版命令执行器"""

    def __init__(self, file_path: str, theme: str = "wechat_red_safe",
                 platform: str = "wechat", output_format: str = "both",
                 proofread: bool = True, use_llm: bool = True):
        self.file_path = Path(file_path)
        self.theme = theme
        self.platform = platform
        self.output_format = output_format
        self.proofread = proofread
        # 默认使用 LLM（DeepSeek）进行排版
        self.use_llm = use_llm and LLM_AVAILABLE
        self.use_rule_based = RULE_BASED_LAYOUT_AVAILABLE

        # LLM 执行器 - 使用 deepseek-chat 而不是 DeepSeek-R1
        # R1 是推理模型，不适合直接生成大量 HTML 内容
        self.llm_executor = None
        if self.use_llm:
            try:
                # 优先使用 deepseek-chat，回退到 huawei_deepseek
                try:
                    self.llm_executor = LLMExecutor(profile="deepseek")
                    print(f"   ✓ DeepSeek-Chat LLM 初始化成功")
                except Exception:
                    self.llm_executor = LLMExecutor(profile="huawei_deepseek")
                    print(f"   ✓ Huawei DeepSeek LLM 初始化成功")
            except Exception as e:
                print(f"   ⚠ LLM 初始化失败: {e}，使用基于规则的排版")
                self.use_llm = False
                self.use_rule_based = RULE_BASED_LAYOUT_AVAILABLE
        else:
            print(f"   ℹ LLM 排版已禁用，使用基于规则的排版")

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

        # 支持的文件格式
        supported_extensions = {".md", ".txt", ".markdown"}
        if self.file_path.suffix.lower() not in supported_extensions:
            raise ValueError(
                f"不支持的文件格式：{self.file_path.suffix}。"
                f"支持的格式：{', '.join(supported_extensions)}"
            )

    def load_theme_config(self):
        """加载主题配置"""
        # 尝试多个可能的路径
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
                        print(f"   加载主题: {theme_name}")
                        return config

        # 如果都没找到，使用默认配置
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
        """
        验证输出是否完整

        检查规则：
        1. 输出长度不应小于原文的 50%
        2. 原文的主要章节标题应该出现在输出中

        Returns:
            True 如果输出看起来完整，False 如果可能不完整
        """
        # 计算长度比例（去除空白字符后）
        orig_len = len(original.strip())
        fmt_len = len(formatted.strip())

        # 如果输出长度小于原文的 30%，肯定有问题
        if fmt_len < orig_len * 0.3:
            print(f"   ⚠ 输出长度异常: 原文 {orig_len} 字符, 输出 {fmt_len} 字符 ({fmt_len*100//orig_len}%)")
            return False

        # 检查主要章节标题是否保留
        import re
        # 提取原文中的所有标题
        orig_headers = set(re.findall(r'^#+\s+(.+)$', original, re.MULTILINE))

        # 检查至少 80% 的标题出现在输出中
        if orig_headers:
            found_count = 0
            for header in orig_headers:
                # 标题可能在 HTML 中以不同形式出现
                if header in formatted or header.replace(' ', '') in formatted.replace(' ', ''):
                    found_count += 1

            retention_rate = found_count / len(orig_headers)
            if retention_rate < 0.8:
                print(f"   ⚠ 标题保留率异常: {retention_rate*100:.0f}% ({found_count}/{len(orig_headers)})")
                return False

        return True

    def apply_layout(self, article_content: str, theme_config: dict) -> str:
        """
        应用排版样式

        优先级：
        1. LLM 排版（DeepSeek - 高质量）
        2. 基于规则的排版（稳定输出）
        3. 简单的 Markdown 转换
        """
        # 优先使用 LLM 排版
        if self.use_llm:
            print("   使用 DeepSeek LLM 生成带强调效果的排版...")
            try:
                formatted_content = asyncio.run(self._llm_layout(article_content, theme_config))

                # 验证输出完整性
                if not self._validate_output_completeness(article_content, formatted_content):
                    print("   ⚠ LLM 输出不完整，回退到基于规则的排版...")
                    if self.use_rule_based:
                        return self._fallback_rule_based_layout(article_content)

                return formatted_content
            except Exception as e:
                print(f"   ⚠ LLM 排版失败: {e}，使用基于规则的排版")

        # 回退到基于规则的排版
        if self.use_rule_based:
            print("   使用基于规则的排版处理器（稳定输出）...")
            return self._fallback_rule_based_layout(article_content)

        # 使用 markdown 库进行完整转换
        try:
            import markdown
            md = markdown.Markdown(extensions=['nl2br', 'sane_lists'])
            html_content = md.convert(article_content)
            return html_content
        except ImportError:
            print("   ⚠ markdown 库未安装，使用简化转换")
            return self._simple_markdown_to_html(article_content, theme_config)

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
            print(f"   ⚠ 基于规则的排版失败: {e}")
            # 最终回退到简单转换
            return self._simple_markdown_to_html(article_content, {})

    async def _llm_layout(self, article_content: str, theme_config: dict) -> str:
        """
        使用 DeepSeek LLM 生成带强调效果的排版
        """
        # 设置更长的超时时间（5分钟）
        import os
        os.environ["LLM_TIMEOUT_SECONDS"] = "300"

        system_prompt = """你是一个专业的文章排版专家。你的任务是将 Markdown 文章转换为符合微信公众号安全红色主题的格式化 HTML。

【核心原则 - 最高优先级】
⚠️ **绝对禁止删除、省略、总结、压缩或改写原文的任何内容！**
⚠️ **必须逐字逐句完整转换每一行文字！**
⚠️ **原文有多少行，输出就必须有多少行对应的内容！**
⚠️ **即使是开头的前言、引入部分，也必须完整保留！**

**排版规则（严格遵循）**：

1. **整体结构**：
   - 使用简单的 HTML 标签（`<h1>`, `<h2>`, `<h3>`, `<p>`, `<blockquote>`, `<ul>`, `<li>`）
   - 标题后添加 `<hr>` 分隔线
   - 普通段落使用 `<p>` 标签

2. **标题样式**：
   - H1: `<h1>标题</h1>`
   - H2: `<h2>标题</h2>`
   - H3: `<h3>标题</h3>`

3. **引用块规则（重要）**：
   - 普通引用：`<blockquote>内容</blockquote>`
   - 高亮引用（重要结论、关键点）：`<blockquote class="highlight">内容</blockquote>`
   - 多行引用用 `<br>` 连接
   - **重要**：只有明确的引用内容（如引用某人的话、重要结论）才放入引用块，普通陈述句不要放入引用块

4. **列表样式**：
   - 无序列表（- 开头）：使用 `<ul><li>项目</li></ul>` 格式
   - 有序列表（1. 2. 开头）：使用 `<ol><li>项目</li></ol>` 格式
   - 多个连续的列表项必须放在同一个 `<ul>` 或 `<ol>` 中

5. **重点标题 + 列表组合**（如"核心特点"后面跟列表）：
   ```
   <blockquote class="highlight">
   <strong style="color:#cf1322;">核心特点</strong><br>
   ● <span class="text">内容1</span><br>
   ● <span class="text">内容2</span>
   </blockquote>
   ```

6. **独立的重点标题**（后面不跟列表）：
   - `<p style="color:#cf1322;font-weight:bold;font-size:16px;margin:16px 0;">标题</p>`

7. **代码块处理（非常重要，仔细判断！）**：

   **🚫 以下情况【绝对不要】用 `<pre><code>` 代码块格式：**

   a) **`text` 语言的代码块**：原文中 ```text 包裹的内容通常是：
      - 文件路径/目录结构：如 `backend/service/user.py`、`src/components/`
      - 纯文本说明、流程描述
      - 配置示例（非完整 YAML/JSON）
      - **处理方式**：用 `<blockquote>` 显示，路径可用 `<code>` 行内代码样式

   b) **单行或简单内容**：
      - 单行路径：`backend/service/user.py`
      - 简单命令：`npm install`、`git status`
      - **处理方式**：用 `<blockquote>` 或普通 `<p>` + 行内 `<code>` 显示

   c) **流程图/结构示意图**：
      - 箭头流程：`用户 → API → 数据库`
      - 层级结构：`前端 / 后端 / 数据库`
      - **处理方式**：用 `<blockquote>` 显示

   **✅ 只有以下情况才用 `<pre><code>` 格式：**

   - 有明确的编程语言标识（\`\`\`python, \`\`\`javascript, \`\`\`yaml, \`\`\`json, \`\`\`bash 等）
   - 包含多行真正的代码（函数定义、类定义、完整配置文件等）
   - 代码格式示例：
     ```
     <pre><code class="language-python">
     def hello():
         print("world")
     </code></pre>
     ```
   - 代码内容需要转义 HTML 特殊字符（< 变成 &lt;, > 变成 &gt;, & 变成 &amp;）

   **📝 路径/目录结构的推荐显示方式：**
   ```
   <blockquote>
   <code>backend/service/user.py</code>
   </blockquote>
   ```
   或多行路径：
   ```
   <blockquote>
   <code>backend/service/user.py</code><br>
   <code>backend/service/order.py</code>
   </blockquote>
   ```

8. **行内强调**：
   - 使用 `<span class="emphasis">关键词</span>` 来强调重点词汇
   - 一段话最多使用 1-2 次强调

9. **分隔线**：使用 `<hr>`

**禁止**：
- 不要给普通陈述句添加引用块样式
- 不要给列表项添加额外内容（如解释性文字）
- 不要使用内联样式（除了重点标题和引用块）
- 不要删除或修改代码块内容

**输出要求**：
- 保持原文内容和结构完整
- 识别重点内容并应用相应样式
- 代码块必须保留，并添加正确的 language-xxx 类名
- 输出纯 HTML 格式"""

        user_prompt = f"""请将以下文章按照公众号安全红色主题进行排版：

```markdown
{article_content}
```

🔴🔴🔴 **最高优先级规则** 🔴🔴🔴

**你必须完整保留原文的每一句话！原文的每一行都必须在输出中找到对应！**
**禁止删除开头的任何内容（前言、引入、背景等）！**
**禁止合并、总结或压缩任何段落！**

**格式要求**：

1. **列表处理**：
   - `- ` 开头的列表：使用 `<ul><li>内容</li></ul>`，多个连续项放同一个 `<ul>` 中
   - `1. ` `2. ` 开头的列表：使用 `<ol><li>内容</li></ol>`，多个连续项放同一个 `<ol>` 中

2. **重点标题 + 列表组合**（如"核心特点"后面跟列表）：
   - 必须将标题和列表全部包裹在同一个 `<blockquote class="highlight">` 中

3. **引用块**：
   - 只有 `>` 开头的内容才放入 `<blockquote>`
   - 普通陈述句使用 `<p>` 标签

4. **代码块（非常重要，仔细判断！）**：

   🚫 **以下情况不用 `<pre><code>` 代码块**：
   - `text` 语言的代码块（通常是路径、目录结构、纯文本说明）
   - 单行路径如 `backend/service/user.py`
   - 流程图如 `用户 → API → 数据库`
   - **这些用 `<blockquote>` 显示，路径可用行内 `<code>` 样式**

   ✅ **只有真正的编程代码才用 `<pre><code>` 格式**：
   - 有明确语言标识（python, javascript, yaml, json, bash 等）
   - 多行真正的代码（函数、类、完整配置）
   - 代码必须转义 HTML（< 变 &lt;, > 变 &gt;）

   **路径显示示例**：
   `<blockquote><code>backend/service/user.py</code></blockquote>`

5. **分隔线**：在每个 H1 标题后添加 `<hr>`

**输出纯 HTML 格式，不要包裹在代码块中**
"""

        # 使用更高的 max_tokens 处理长文章（覆盖配置文件的值）
        # 注意：DeepSeek API max_tokens 限制为 8192
        # 对于长文章排版，需要足够的输出空间
        result = await self.llm_executor.execute({
            "prompt": user_prompt,
            "system_message": system_prompt,
            "temperature": 0.1,
            "max_tokens": 8192  # DeepSeek API 限制最大 8192
        })

        if result.get("status") == "completed":
            html_content = result.get("generated_text", "")
            stop_reason = result.get("stop_reason")

            # 调试信息
            print(f"   LLM 返回: 输入 {result.get('input_tokens', 0)} tokens, 输出 {result.get('output_tokens', 0)} tokens, stop_reason={stop_reason}")

            # 检测输出是否被截断
            if stop_reason == "length":
                print(f"   ⚠ 警告: LLM 输出达到 token 限制，内容可能不完整")

            # 处理 DeepSeek-R1 推理模型的特殊输出格式
            # R1 模型可能在输出中包含 <think...</think 标签
            if "<think" in html_content:
                # 移除 <think 标签内的推理过程
                import re
                html_content = re.sub(r'<think[^>]*>.*?</think\s*>', '', html_content, flags=re.DOTALL)
                html_content = html_content.strip()

            # 提取 HTML 内容（如果被包裹在代码块中）
            # 注意：不要使用 split() 方法，因为它会丢失大部分内容
            if "```html" in html_content:
                # 找到 ```html 后的第一个代码块
                start_idx = html_content.find("```html")
                if start_idx != -1:
                    # 找到代码块开始后的内容
                    content_start = html_content.find("\n", start_idx) + 1
                    if content_start > 0:
                        # 找到代码块结束
                        content_end = html_content.find("\n```", content_start)
                        if content_end != -1:
                            html_content = html_content[content_start:content_end].strip()
                        else:
                            # 没有结束标记，取到末尾
                            html_content = html_content[content_start:].strip()
            elif html_content.strip().startswith("```"):
                # 处理以 ``` 开头的输出
                lines = html_content.strip().split("\n")
                if len(lines) > 1:
                    # 第一行是 ```language，去掉
                    # 最后一行是 ```，去掉
                    if lines[-1].strip() == "```":
                        html_content = "\n".join(lines[1:-1])
                    else:
                        html_content = "\n".join(lines[1:])

            return html_content
        else:
            raise Exception(result.get("error", "LLM 调用失败"))

    def _simple_markdown_to_html(self, article_content: str, theme_config: dict) -> str:
        """
        Simplified Markdown to HTML converter (when markdown library is unavailable)
        """
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

            # 空行处理
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

            # H1 标题
            if stripped.startswith("# "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                content = stripped[2:].strip()
                result.append(f'<h1>{content}</h1>')

            # H2 标题
            elif stripped.startswith("## "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                content = stripped[3:].strip()
                result.append(f'<h2>{content}</h2>')

            # H3 标题
            elif stripped.startswith("### "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                content = stripped[4:].strip()
                result.append(f'<h3>{content}</h3>')

            # 引用块
            elif stripped.startswith(">"):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                if not in_blockquote:
                    in_blockquote = True
                    # 检查是否是高亮引用
                    is_highlight = "核心" in stripped or "重点" in stripped or "关键" in stripped
                    result.append(f'<blockquote class="highlight">' if is_highlight else '<blockquote>')
                content = stripped[1:].strip()
                result.append(f'<p>{content}</p>' if content else '<br>')

            # 无序列表
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                if not in_list:
                    in_list = True
                    result.append("<ul>")
                content = stripped[2:].strip()
                result.append(f'<li>{content}</li>')

            # 分隔线
            elif stripped == "---" or stripped == "***":
                if in_paragraph:
                    result.append("</p>")
                    in_paragraph = False
                result.append("<hr>")

            # 普通段落
            else:
                if not in_paragraph:
                    result.append("<p>")
                    in_paragraph = True
                else:
                    result.append("<br>")
                result.append(stripped)

            i += 1

        # 关闭未闭合的标签
        if in_paragraph:
            result.append("</p>")
        if in_list:
            result.append("</ul>")
        if in_blockquote:
            result.append("</blockquote>")

        return "\n".join(result)

    def proofread_content(self, content: str) -> tuple:
        """
        Proofread content, fix dark text colors

        Note: Keep #262626 as deep text color (WeChat-safe color)

        Returns:
            (proofread_content, issues_found)
        """
        issues_found = []

        # 检查并替换过暗的颜色（但不替换 #262626）
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

        # 检查引用块颜色
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
    <!-- Highlight.js for syntax highlighting -->
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
        /* Dark code block style - matches screenshot editor look */
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
        /* Inline code */
        p > code, li > code, span > code {{
            background: #f5f5f5;
            color: #cf1322;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Consolas", "Monaco", monospace;
            font-size: 13px;
        }}
        /* Highlight.js overrides for atom-one-dark theme */
        .hljs {{
            background: #282c34;
            color: #abb2bf;
        }}
    </style>
</head>
<body>
{markdown_content}
<script>
    // Initialize syntax highlighting
    document.addEventListener('DOMContentLoaded', function() {{
        hljs.highlightAll();

        // Add copy button functionality to code blocks
        document.querySelectorAll('pre > code').forEach(function(block) {{
            const pre = block.parentElement;

            // Skip if already has header
            if (pre.querySelector('.code-header')) return;

            // Detect language from class
            const languageClass = Array.from(block.classList).find(c => c.startsWith('language-'));
            const language = languageClass ? languageClass.replace('language-', '') : 'text';

            // Create header with language label and copy button
            const header = document.createElement('div');
            header.className = 'code-header';
            header.innerHTML = `
                <span class="code-language">${{language}}</span>
                <button class="code-copy" onclick="copyCode(this)">复制代码</button>
            `;

            pre.insertBefore(header, block);
        }});

        // Fix spec file blocks (YAML) - convert to proper code blocks
        document.querySelectorAll('blockquote').forEach(function(block) {{
            const content = block.textContent.trim();
            if (content.includes('.yaml:') || content.includes('.yml:') || content.includes('.spec:')) {{
                // This might be a spec reference, style it differently
                block.style.borderLeft = '4px solid #e5c07b';
                block.style.background = '#f9f8f4';
            }}
        }});
    }});

    function copyCode(button) {{
        const pre = button.closest('pre');
        const code = pre.querySelector('code');
        const text = code.textContent;

        // 尝试使用现代 Clipboard API
        if (navigator.clipboard && window.isSecureContext) {{
            navigator.clipboard.writeText(text).then(function() {{
                showCopySuccess(button);
            }}).catch(function() {{
                fallbackCopy(text, button);
            }});
        }} else {{
            // 非安全上下文，使用备用方案
            fallbackCopy(text, button);
        }}
    }}

    function fallbackCopy(text, button) {{
        // 创建临时 textarea 元素
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
        print(f"📝 文章排版命令执行器")
        print(f"=" * 50)
        print(f"输入文件: {self.file_path}")
        print(f"主题: {self.theme}")
        print(f"平台: {self.platform}")
        print(f"输出格式: {self.output_format}")
        print(f"自动校对: {'是' if self.proofread else '否'}")
        print()

        # 验证输入
        self.validate_input()

        # 读取文章
        print("📖 读取文章...")
        article_content = self.read_article()

        # 加载主题配置
        print("🎨 加载主题配置...")
        theme_config = self.load_theme_config()

        # 应用排版
        print("✨ 应用排版样式...")
        formatted_content = self.apply_layout(article_content, theme_config)

        # 检测是否为完整的 HTML（由 LLM 生成）
        is_full_html = formatted_content.strip().startswith("<!DOCTYPE html>") or formatted_content.strip().startswith("<html")

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(self.file_path),
            "theme": self.theme,
            "platform": self.platform,
            "output_format": self.output_format,
            "proofread_issues": [],
            "output_files": [],
            "use_llm": self.use_llm,
            "is_full_html": is_full_html
        }

        # 校对
        proofread_issues = []
        if self.proofread:
            print("🔍 自动校对...")
            formatted_content, proofread_issues = self.proofread_content(formatted_content)
            if proofread_issues:
                print(f"   发现 {len(proofread_issues)} 个问题，已自动修复")
            report["proofread_issues"] = proofread_issues

        # 保存输出
        print("💾 保存输出文件...")

        if self.output_format in ["md", "both"]:
            with open(self.output_md, "w", encoding="utf-8") as f:
                f.write(formatted_content)
            report["output_files"].append(str(self.output_md))
            print(f"   ✓ {self.output_md}")

        if self.output_format in ["html", "both"]:
            # 如果 LLM 已经生成了完整 HTML，直接使用；否则包装
            if is_full_html:
                html_content = formatted_content
            else:
                html_content = self.generate_html(formatted_content)
            with open(self.output_html, "w", encoding="utf-8") as f:
                f.write(html_content)
            report["output_files"].append(str(self.output_html))
            print(f"   ✓ {self.output_html}")

        # 保存报告
        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"   ✓ {self.report_file}")

        print()
        print("✅ 排版完成！")
        print(f"📂 输出目录: {self.output_dir}")

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
        help="排版主题（默认: wechat_red_safe）"
    )

    parser.add_argument(
        "--platform",
        choices=["wechat", "xhs", "notion", "feishu", "generic"],
        default="wechat",
        help="目标平台（默认: wechat）"
    )

    parser.add_argument(
        "--format",
        choices=["md", "html", "both"],
        default="both",
        help="输出格式（默认: both）"
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

    # 执行排版
    try:
        command = ArticleLayoutCommand(
            file_path=args.file_path,
            theme=args.theme,
            platform=args.platform,
            output_format=args.format,
            proofread=not args.no_proofread,
            use_llm=not args.no_llm  # 默认使用 LLM，除非明确指定 --no-llm
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
        print(f"❌ 执行出错: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
