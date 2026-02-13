#!/usr/bin/env python3
"""
Rule-based Article Layout Processor
基于规则的文章排版处理器

确保稳定的排版输出，与昨天的排版效果完全一致。
"""

import re
from typing import List, Optional


class RuleBasedLayoutProcessor:
    """基于规则的排版处理器"""

    def __init__(self):
        """初始化处理器"""
        self.lines: List[str] = []
        self.result: List[str] = []
        self.line_index = 0
        self.code_block_placeholders: dict = {}  # 存储代码块的占位符映射

    def process(self, markdown_content: str) -> str:
        """
        处理 Markdown 内容，返回格式化的 HTML
        """
        # 首先处理代码块，用占位符替换，避免被其他规则干扰
        markdown_content = self._extract_code_blocks(markdown_content)

        self.lines = markdown_content.split('\n')
        self.result = []
        self.line_index = 0

        while self.line_index < len(self.lines):
            line = self.lines[self.line_index].rstrip()
            processed, skip = self._process_line(line, self.line_index)
            if processed:
                self.result.append(processed)
            self.line_index += skip if skip else 1

        # 还原代码块
        result = '\n'.join(self.result)
        result = self._restore_code_blocks(result)

        return result

    def _extract_code_blocks(self, content: str) -> str:
        """
        提取代码块并用占位符替换，避免被其他规则干扰
        """
        self.code_block_placeholders = {}

        def replace_code_block(match):
            language = match.group(1) or 'text'
            code_content = match.group(2)
            # 转义 HTML 特殊字符
            code_content = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_block = f'<pre><code class="language-{language}">{code_content}</code></pre>'

            # 生成唯一占位符
            placeholder = f'__CODE_BLOCK_{len(self.code_block_placeholders)}__'
            self.code_block_placeholders[placeholder] = html_block
            return placeholder

        # 使用正则匹配代码块
        pattern = r'```(\w*)\n(.*?)```'
        return re.sub(pattern, replace_code_block, content, flags=re.DOTALL)

    def _restore_code_blocks(self, content: str) -> str:
        """
        还原代码块占位符
        """
        for placeholder, html_block in self.code_block_placeholders.items():
            content = content.replace(placeholder, html_block)
        return content

    def _process_line(self, line: str, index: int) -> tuple:
        """
        处理单行内容

        Returns:
            (处理后的内容, 跳过的行数)
        """
        stripped = line.strip()

        # 空行
        if not stripped:
            return '', 1

        # 代码块占位符 - 直接返回，不包裹 <p>
        if stripped.startswith('__CODE_BLOCK_') and stripped.endswith('__'):
            return stripped, 1

        # 分隔线
        if stripped in ('---', '***'):
            return '<hr>', 1

        # H1 标题
        if stripped.startswith('# '):
            content = self._clean_markdown(stripped[2:].strip())
            return f'<h1>{content}</h1>', 1

        # H2 标题
        if stripped.startswith('## '):
            content = self._clean_markdown(stripped[3:].strip())
            return f'<h2>{content}</h2>', 1

        # H3 标题
        if stripped.startswith('### '):
            content = self._clean_markdown(stripped[4:].strip())
            return f'<h3>{content}</h3>', 1

        # 引用块
        if stripped.startswith('>'):
            result, lines_consumed = self._process_blockquote(index)
            return result, lines_consumed

        # 检查是否为重点标题 + 列表组合
        list_block, lines_consumed = self._process_list_block(index)
        if list_block:
            return list_block, lines_consumed

        # 检查是否为编号列表（使用 ul/li 格式）
        numbered_list, lines_consumed = self._process_numbered_list(index)
        if numbered_list:
            return numbered_list, lines_consumed

        # 检查是否为简单 - 列表
        simple_list, lines_consumed = self._process_simple_list(index)
        if simple_list:
            return simple_list, lines_consumed

        # 检查是否为重点标题（独立）
        if self._is_highlight_title(stripped):
            return f'<p style="color:#cf1322;font-weight:bold;font-size:16px;margin:16px 0;">{stripped}</p>', 1

        # 普通段落
        return f'<p>{self._process_inline_formatting(stripped)}</p>', 1

    def _process_list_block(self, start_index: int) -> tuple:
        """
        处理重点标题 + 列表组合（如"核心特点"后面的列表）

        格式：
        <blockquote class="highlight">
        <strong style="color:#cf1322;">核心特点</strong><br>
        ● <span class="text">内容1</span><br>
        ● <span class="text">内容2</span>
        </blockquote>

        Returns:
            (处理后的内容, 消耗的行数) 或 (None, 0)
        """
        i = start_index

        # 检查第一行是否为重点标题
        first_line = self.lines[i].strip()
        if not self._is_highlight_title(first_line):
            return None, 0

        # 收集标题和后续列表项
        title = first_line
        i += 1

        list_items = []
        while i < len(self.lines):
            line = self.lines[i].strip()
            if not line:
                break
            # 检查是否为列表项（圆点、数字、中文数字）
            if self._is_list_item(line):
                list_items.append(line)
                i += 1
            else:
                break

        # 如果没有列表项，返回 None
        if not list_items:
            return None, 0

        # 构建引用块
        result_lines = [f'<blockquote class="highlight">']
        result_lines.append(f'<strong style="color:#cf1322;">{title}</strong><br>')

        for item in list_items:
            # 处理列表项
            processed = self._process_list_item(item)
            result_lines.append(f'{processed}<br>')

        result_lines.append('</blockquote>')

        # 返回内容和消耗的行数 (1 标题 + len(list_items) 列表项)
        return '\n'.join(result_lines), 1 + len(list_items)

    def _is_list_item(self, text: str) -> bool:
        """检查是否为列表项"""
        # 圆点列表
        if text.startswith('●') or text.startswith('-'):
            return True
        # 数字列表
        if re.match(r'^\d+[.、]\s*', text):
            return True
        # 中文数字列表
        if re.match(r'^[第零一二三四五六七八九十百]+[，,、]\s*', text):
            return True
        return False

    def _process_list_item(self, text: str) -> str:
        """处理单个列表项"""
        # 圆点列表
        if text.startswith('●'):
            content = text[1:].strip()
            return f'● <span class="text">{self._process_inline_formatting(content)}</span>'
        if text.startswith('-'):
            content = text[1:].strip()
            return f'● <span class="text">{self._process_inline_formatting(content)}</span>'

        # 数字列表
        num_match = re.match(r'^(\d+)[.、]\s*(.+)$', text)
        if num_match:
            num, content = num_match.groups()
            return f'{num}. <span class="text">{self._process_inline_formatting(content)}</span>'

        # 中文数字列表
        chinese_match = re.match(r'^([第零一二三四五六七八九十百]+)[，,]\s*(.+)$', text)
        if chinese_match:
            num, content = chinese_match.groups()
            return f'{num}，<span class="text">{self._process_inline_formatting(content)}</span>'

        return text

    def _process_numbered_list(self, start_index: int) -> tuple:
        """
        处理编号列表（使用 ol/li 格式）

        格式：
        <ol>
        <li>内容1</li>
        <li>内容2</li>
        </ol>

        Returns:
            (处理后的内容, 消耗的行数) 或 (None, 0)
        """
        lines = []
        i = start_index
        lines_consumed = 0

        # 收集连续的编号列表项（允许中间有空行）
        while i < len(self.lines):
            line = self.lines[i].strip()
            # 跳过空行（列表项之间的空行）
            if not line:
                if lines:
                    i += 1
                    lines_consumed += 1
                    continue
                else:
                    break
            # 检查是否为编号列表项
            match = re.match(r'^(\d+)[.、]\s*(.+)$', line)
            if match:
                num, content = match.groups()
                lines.append(f'<li>{self._process_inline_formatting(content)}</li>')
                i += 1
                lines_consumed += 1
            else:
                break

        if not lines:
            return None, 0

        result = '<ol>\n' + '\n'.join(lines) + '\n</ol>'

        return result, lines_consumed

    def _process_simple_list(self, start_index: int) -> tuple:
        """
        处理简单的 - 列表

        格式：
        <ul>
        <li>内容1</li>
        <li>内容2</li>
        </ul>

        Returns:
            (处理后的内容, 消耗的行数) 或 (None, 0)
        """
        lines = []
        i = start_index
        lines_consumed = 0

        # 收集连续的 - 列表项（允许中间有空行）
        while i < len(self.lines):
            line = self.lines[i].strip()
            # 跳过空行（列表项之间的空行）
            if not line:
                # 如果已经收集了列表项，继续查找下一个列表项
                if lines:
                    i += 1
                    lines_consumed += 1
                    continue
                else:
                    break
            # 检查是否为 - 列表项（以 - 开头，后面跟空格）
            if re.match(r'^-\s+.+$', line):
                content = line[1:].strip()
                lines.append(f'<li>{self._process_inline_formatting(content)}</li>')
                i += 1
                lines_consumed += 1
            else:
                break

        if not lines:
            return None, 0

        result = '<ul>\n' + '\n'.join(lines) + '\n</ul>'

        return result, lines_consumed

    def _is_highlight_title(self, text: str) -> bool:
        """检查是否为重点标题"""
        # 短文本且包含特定关键词
        if len(text) <= 15:
            keywords = ['核心', '关键', '特点', '因素', '要点', '本质', '基础', '重点',
                       '问题', '效果', '结论', '真正', '而不是', '这其实', '换句话说',
                       '含义', '特征', '风险', 'Meltbook 上的', '认知风险']
            for keyword in keywords:
                if keyword in text:
                    return True
        return False

    def _process_inline_formatting(self, text: str) -> str:
        """处理行内格式化"""
        # 处理 **粗体**
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return text

    def _clean_markdown(self, text: str) -> str:
        """清理 Markdown 标记"""
        # 移除 **粗体** 标记
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        return text

    def _process_blockquote(self, start_index: int) -> tuple:
        """
        处理引用块（可能是多行）

        Returns:
            (处理后的内容, 消耗的行数)
        """
        # 收集所有连续的引用行
        lines = []
        i = start_index
        while i < len(self.lines):
            line = self.lines[i].rstrip()
            if line.strip().startswith('>'):
                # 移除 > 符号
                content = line.strip()[1:].strip()
                lines.append(content)
                i += 1
            else:
                break

        # 检查是否为高亮引用
        combined_text = ' '.join(lines)
        is_highlight = any(keyword in combined_text for keyword in [
            '结论', '关键', '重要', '核心', '本质', '没有展示',
            '更像是', '而不是', '才关键'
        ])

        # 构建引用块内容（使用 <br> 连接多行）
        content = '<br>'.join(lines)

        if is_highlight:
            return f'<blockquote class="highlight">{content}</blockquote>', len(lines)
        else:
            return f'<blockquote>{content}</blockquote>', len(lines)


def apply_rule_based_layout(markdown_content: str) -> str:
    """
    应用基于规则的排版

    Args:
        markdown_content: 原始 Markdown 内容

    Returns:
        格式化后的 HTML 内容
    """
    processor = RuleBasedLayoutProcessor()
    return processor.process(markdown_content)
