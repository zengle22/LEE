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

    def process(self, markdown_content: str) -> str:
        """
        处理 Markdown 内容，返回格式化的 HTML
        """
        self.lines = markdown_content.split('\n')
        self.result = []
        self.line_index = 0

        while self.line_index < len(self.lines):
            line = self.lines[self.line_index].rstrip()
            processed, skip = self._process_line(line, self.line_index)
            if processed:
                self.result.append(processed)
            self.line_index += skip if skip else 1

        return '\n'.join(self.result)

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
            return self._process_blockquote(index), 0

        # 检查是否为重点标题 + 列表组合
        list_block = self._process_list_block(index)
        if list_block:
            return list_block, 0

        # 检查是否为重点标题（独立）
        if self._is_highlight_title(stripped):
            return f'<p style="color:#cf1322;font-weight:bold;font-size:16px;margin:16px 0;">{stripped}</p>', 1

        # 检查是否为编号列表（使用 ul/li 格式）
        numbered_list = self._process_numbered_list(index)
        if numbered_list:
            return numbered_list, 0

        # 普通段落
        return f'<p>{self._process_inline_formatting(stripped)}</p>', 1

    def _process_list_block(self, start_index: int) -> Optional[str]:
        """
        处理重点标题 + 列表组合（如"核心特点"后面的列表）

        格式：
        <blockquote class="highlight">
        <strong style="color:#cf1322;">核心特点</strong><br>
        ● <span class="text">内容1</span><br>
        ● <span class="text">内容2</span>
        </blockquote>
        """
        lines = []
        i = start_index

        # 检查第一行是否为重点标题
        first_line = self.lines[i].strip()
        if not self._is_highlight_title(first_line):
            return None

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
            return None

        # 构建引用块
        result_lines = [f'<blockquote class="highlight">']
        result_lines.append(f'<strong style="color:#cf1322;">{title}</strong><br>')

        for item in list_items:
            # 处理列表项
            processed = self._process_list_item(item)
            result_lines.append(f'{processed}<br>')

        result_lines.append('</blockquote>')

        # 更新跳过的行数
        # 注意：这里需要在调用方处理

        return '\n'.join(result_lines)

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

    def _process_numbered_list(self, start_index: int) -> Optional[str]:
        """
        处理编号列表（使用 ul/li 格式）

        格式：
        <ul>
        <li><strong>定期拉取平台上的新内容</strong></li>
        <li><strong>把帖子和评论作为上下文</strong></li>
        </ul>
        """
        lines = []
        i = start_index

        # 收集连续的编号列表项
        while i < len(self.lines):
            line = self.lines[i].strip()
            if not line:
                break
            # 检查是否为编号列表项
            match = re.match(r'^(\d+)[.、]\s*(.+)$', line)
            if match:
                num, content = match.groups()
                lines.append(f'<li><strong>{self._process_inline_formatting(content)}</strong></li>')
                i += 1
            else:
                break

        if not lines:
            return None

        result = '<ul>\n' + '\n'.join(lines) + '\n</ul>'

        # 更新跳过的行数
        # 注意：这里需要在调用方处理

        return result

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

    def _process_blockquote(self, start_index: int) -> str:
        """处理引用块（可能是多行）"""
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
            return f'<blockquote class="highlight">{content}</blockquote>'
        else:
            return f'<blockquote>{content}</blockquote>'


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
