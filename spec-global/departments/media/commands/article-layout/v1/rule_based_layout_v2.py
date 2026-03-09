#!/usr/bin/env python3
"""
Rule-based Article Layout Processor V2
基于规则的文章排版处理器 V2

支持 LLM 识别的重点标注，在规则排版基础上应用重点强调。
"""

import re
from typing import List, Optional, Set, Dict


class RuleBasedLayoutProcessorV2:
    """基于规则的排版处理器 V2（支持 LLM 重点标注）"""

    def __init__(self, highlight_phrases: Set[str] = None, highlight_blocks: Set[str] = None):
        """初始化处理器

        Args:
            highlight_phrases: 需要行内强调的短语集合
            highlight_blocks: 需要高亮引用块的段落集合
        """
        self.highlight_phrases = highlight_phrases or set()
        self.highlight_blocks = highlight_blocks or set()
        self.lines: List[str] = []
        self.result: List[str] = []
        self.line_index = 0
        self.code_block_placeholders: dict = {}
        # 层级编号计数器
        self.chapter_counter = 0
        self.subsection_counter = 0
        self.subsubsection_counter = 0
        self.last_chapter = 0
        self.last_subsection = 0
        self.has_parent_h1 = False

    def process(self, markdown_content: str) -> str:
        """处理 Markdown 内容，返回格式化的 HTML"""
        # 首先处理代码块
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
        """提取代码块并用占位符替换"""
        self.code_block_placeholders = {}

        def replace_code_block(match):
            language = match.group(1) or 'text'
            code_content = match.group(2)
            # 转义 HTML 特殊字符
            code_content = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_block = f'<pre><code class="language-{language}">{code_content}</code></pre>'

            placeholder = f'__CODE_BLOCK_{len(self.code_block_placeholders)}__'
            self.code_block_placeholders[placeholder] = html_block
            return placeholder

        pattern = r'```(\w*)\n(.*?)```'
        return re.sub(pattern, replace_code_block, content, flags=re.DOTALL)

    def _restore_code_blocks(self, content: str) -> str:
        """还原代码块占位符"""
        for placeholder, html_block in self.code_block_placeholders.items():
            content = content.replace(placeholder, html_block)
        return content

    def _apply_highlight_phrase(self, text: str) -> str:
        """
        对文本应用行内重点标注

        检查文本中是否包含需要强调的短语，如果包含则用红色加粗标注
        """
        if not self.highlight_phrases:
            return text

        # 按长度降序排序，优先匹配长文本
        sorted_phrases = sorted(self.highlight_phrases, key=len, reverse=True)

        for phrase in sorted_phrases:
            if phrase in text:
                # 用红色加粗替换短语
                highlighted = f'<strong style="color:#cf1322;">{phrase}</strong>'
                text = text.replace(phrase, highlighted)

        return text

    def _is_highlight_block(self, text: str) -> bool:
        """检查是否应该作为高亮引用块"""
        # 检查是否完全匹配某个 highlight_block
        if text in self.highlight_blocks:
            return True

        # 检查是否包含某个 highlight_block 的核心内容
        for block in self.highlight_blocks:
            if block in text or block.replace(' ', '') in text.replace(' ', ''):
                return True

        return False

    def _process_line(self, line: str, index: int) -> tuple:
        """处理单行内容"""
        stripped = line.strip()

        # 空行
        if not stripped:
            return '', 1

        # 代码块占位符
        if stripped.startswith('__CODE_BLOCK_') and stripped.endswith('__'):
            return stripped, 1

        # 分隔线
        if stripped in ('---', '***'):
            return '<hr>', 1

        # H1 标题
        if stripped.startswith('# '):
            content = self._clean_markdown(stripped[2:].strip())
            numbered_content, has_number = self._convert_chapter_number(content, 1)
            # 如果已有编号，只返回原始内容（不重复添加编号）
            if not has_number:
                return f'<h1 style="color:#cf1322;font-size:22px;font-weight:700;margin:24px 0 16px 0;">{numbered_content}</h1><hr>', 1
            else:
                return f'<h1 style="color:#cf1322;font-size:22px;font-weight:700;margin:24px 0 16px 0;">{content}</h1><hr>', 1

        # H2 标题
        if stripped.startswith('## '):
            content = self._clean_markdown(stripped[3:].strip())
            numbered_content, has_number = self._convert_chapter_number(content, 2)
            # H2 标题总是用红色，不管有没有编号
            if has_number:
                return f'<h2 style="color:#cf1322;font-size:18px;font-weight:600;margin:20px 0 12px 0;">{numbered_content}</h2><hr>', 1
            else:
                return f'<h2 style="color:#cf1322;font-size:17px;font-weight:600;margin:20px 0 12px 0;">{numbered_content}</h2><hr>', 1

        # H3 标题
        if stripped.startswith('### '):
            content = self._clean_markdown(stripped[4:].strip())
            numbered_content, has_number = self._convert_chapter_number(content, 3)
            # H3 标题总是用红色，不管有没有编号
            if has_number:
                return f'<h3 style="color:#cf1322;font-size:16px;font-weight:600;margin:16px 0 8px 0;">{numbered_content}</h3><hr>', 1
            else:
                return f'<h3 style="color:#cf1322;font-size:15px;font-weight:600;margin:16px 0 8px 0;">{numbered_content}</h3><hr>', 1

        # 引用块
        if stripped.startswith('>'):
            result, lines_consumed = self._process_blockquote(index)
            return result, lines_consumed

        # 检查是否为重点标题 + 列表组合
        list_block, lines_consumed = self._process_list_block(index)
        if list_block:
            return list_block, lines_consumed

        # 检查是否为编号列表
        numbered_list, lines_consumed = self._process_numbered_list(index)
        if numbered_list:
            return numbered_list, lines_consumed

        # 检查是否为简单列表
        simple_list, lines_consumed = self._process_simple_list(index)
        if simple_list:
            return simple_list, lines_consumed

        # 检查是否为重点标题（独立）
        if self._is_highlight_title(stripped):
            return f'<p style="color:#cf1322;font-weight:bold;font-size:16px;margin:16px 0;">{stripped}</p>', 1

        # 普通段落 - 应用行内重点标注
        processed_text = self._apply_highlight_phrase(self._process_inline_formatting(stripped))
        return f'<p>{processed_text}</p>', 1

    def _process_list_block(self, start_index: int) -> tuple:
        """处理重点标题 + 列表组合"""
        i = start_index

        first_line = self.lines[i].strip()
        if not self._is_highlight_title(first_line):
            return None, 0

        title = first_line
        i += 1

        list_items = []
        while i < len(self.lines):
            line = self.lines[i].strip()
            if not line:
                break
            if self._is_list_item(line):
                list_items.append(line)
                i += 1
            else:
                break

        if not list_items:
            return None, 0

        result_lines = [f'<blockquote class="highlight">']
        result_lines.append(f'<strong style="color:#cf1322;">{title}</strong><br>')

        for item in list_items:
            processed = self._process_list_item(item)
            result_lines.append(f'{processed}<br>')

        result_lines.append('</blockquote>')

        return '\n'.join(result_lines), 1 + len(list_items)

    def _is_list_item(self, text: str) -> bool:
        """检查是否为列表项"""
        if text.startswith('●') or text.startswith('-'):
            return True
        if re.match(r'^\d+[.、]\s*', text):
            return True
        if re.match(r'^[第零一二三四五六七八九十百]+[，,、]\s*', text):
            return True
        return False

    def _process_list_item(self, text: str) -> str:
        """处理单个列表项"""
        if text.startswith('●'):
            content = text[1:].strip()
            return f'● <span class="text">{self._process_inline_formatting(content)}</span>'
        if text.startswith('-'):
            content = text[1:].strip()
            return f'● <span class="text">{self._process_inline_formatting(content)}</span>'

        num_match = re.match(r'^(\d+)[.、]\s*(.+)$', text)
        if num_match:
            num, content = num_match.groups()
            return f'{num}. <span class="text">{self._process_inline_formatting(content)}</span>'

        chinese_match = re.match(r'^([第零一二三四五六七八九十百]+)[，,]\s*(.+)$', text)
        if chinese_match:
            num, content = chinese_match.groups()
            return f'{num}，<span class="text">{self._process_inline_formatting(content)}</span>'

        return text

    def _process_numbered_list(self, start_index: int) -> tuple:
        """处理编号列表"""
        lines = []
        i = start_index
        lines_consumed = 0

        while i < len(self.lines):
            line = self.lines[i].strip()
            if not line:
                if lines:
                    i += 1
                    lines_consumed += 1
                    continue
                else:
                    break
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
        """处理简单的 - 列表"""
        lines = []
        i = start_index
        lines_consumed = 0

        while i < len(self.lines):
            line = self.lines[i].strip()
            if not line:
                if lines:
                    i += 1
                    lines_consumed += 1
                    continue
                else:
                    break
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
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return text

    def _clean_markdown(self, text: str) -> str:
        """清理 Markdown 标记"""
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        return text

    def _is_real_chapter(self, text: str, level: int) -> bool:
        """判断是否为真正的"章节"（需要重新编号）"""
        circle_nums = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮'
        emoji_nums = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

        # 如果已有编号（中文、圆圈、emoji、阿拉伯数字），不需要重新编号
        for char in circle_nums:
            if char in text:
                return False  # 已有编号，不重复添加
        for emoji in emoji_nums:
            if emoji in text:
                return False

        chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        for ch in chinese_nums:
            if re.match(rf'^{ch}[、.．]\s*', text):
                return False  # 已有中文编号，不重复添加

        if re.match(r'^\d+[.、．)\s]', text):
            return False  # 已有阿拉伯数字编号，不重复添加

        if re.match(r'^[\d]+\）', text):
            return False  # 已有 "1）" 格式编号，不重复添加

        # 没有编号的章节，根据关键词判断是否需要添加编号
        if level in (1, 2):
            chapter_keywords = ['真实', '事故', '为什么', '怎么', '解决', '治理', '启示',
                              '错误', '修复', '效果', '定义', '标准', '机制', '规则']
            for kw in chapter_keywords:
                if kw in text:
                    return True
            if len(text) > 10:
                return True

        return False

    def _convert_chapter_number(self, text: str, level: int) -> tuple:
        """转换章节编号为分层阿拉伯数字"""
        circle_nums = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮'
        emoji_nums = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

        needs_number = self._is_real_chapter(text, level)

        # 如果不需要编号，检查原文是否有已有编号，有则保留
        if not needs_number:
            # 检查原文是否已有编号
            has_existing_number = False
            for char in circle_nums:
                if char in text:
                    has_existing_number = True
                    break
            if not has_existing_number:
                for emoji in emoji_nums:
                    if emoji in text:
                        has_existing_number = True
                        break
            if not has_existing_number:
                chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
                for ch in chinese_nums:
                    if re.match(rf'^{ch}[、.．]\s*', text):
                        has_existing_number = True
                        break
            if not has_existing_number:
                if re.match(r'^\d+[.、．)\s]', text):
                    has_existing_number = True

            # 如果有已有编号，返回原文（保留编号）
            if has_existing_number:
                return text, True
            # 如果没有已有编号，返回清理后的文本
            cleaned_text = text
            for char in circle_nums:
                cleaned_text = cleaned_text.replace(char, '')
            for emoji in emoji_nums:
                cleaned_text = cleaned_text.replace(emoji, '')
            chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
            for ch in chinese_nums:
                cleaned_text = re.sub(rf'^{ch}[、.．]\s*', '', cleaned_text)
            cleaned_text = re.sub(r'^\d+[.、．)\s]', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
            return cleaned_text, False

        cleaned_text = text
        for char in circle_nums:
            cleaned_text = cleaned_text.replace(char, '')
        for emoji in emoji_nums:
            cleaned_text = cleaned_text.replace(emoji, '')

        chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        for ch in chinese_nums:
            cleaned_text = re.sub(rf'^{ch}[、.．]\s*', '', cleaned_text)

        cleaned_text = re.sub(r'^\d+[.、．]\s*', '', cleaned_text)
        cleaned_text = cleaned_text.strip()

        if level == 1:
            self.chapter_counter += 1
            self.subsection_counter = 0
            self.subsubsection_counter = 0
            self.last_chapter = self.chapter_counter
            self.has_parent_h1 = True
            number = f"{self.chapter_counter}"
        elif level == 2:
            if self.has_parent_h1:
                self.subsection_counter += 1
                self.subsubsection_counter = 0
                self.last_subsection = self.subsection_counter
                number = f"{self.last_chapter}.{self.subsection_counter}"
            else:
                self.chapter_counter += 1
                self.subsection_counter = 0
                self.subsubsection_counter = 0
                self.last_chapter = self.chapter_counter
                number = f"{self.chapter_counter}"
        else:
            self.subsubsection_counter += 1
            if self.last_subsection > 0:
                number = f"{self.last_chapter}.{self.last_subsection}.{self.subsubsection_counter}"
            else:
                number = f"{self.last_chapter}.{self.subsubsection_counter}"

        return f"{number}. {cleaned_text}", True

    def _process_blockquote(self, start_index: int) -> tuple:
        """处理引用块（可能是多行）"""
        lines = []
        i = start_index
        while i < len(self.lines):
            line = self.lines[i].rstrip()
            if line.strip().startswith('>'):
                content = line.strip()[1:].strip()
                lines.append(content)
                i += 1
            else:
                break

        combined_text = ' '.join(lines)

        # 检查是否是 LLM 标记的高亮段落
        is_highlight = self._is_highlight_block(combined_text)

        # 如果 LLM 没有标记，使用关键词判断
        if not is_highlight:
            is_highlight = any(keyword in combined_text for keyword in [
                '结论', '关键', '重要', '核心', '本质', '没有展示',
                '更像是', '而不是', '才关键', '不会', '没有', '无法',
                '完成', '验证', '证据', '定义', '人类', 'Agent',
                '责任', '结果', '语言', '治理', '结构', '文化'
            ])

        content = '<br>'.join(lines)

        if is_highlight:
            return f'<blockquote class="highlight">{content}</blockquote>', len(lines)
        else:
            return f'<blockquote>{content}</blockquote>', len(lines)


def apply_rule_based_layout_with_highlights(
    markdown_content: str,
    highlight_phrases: Set[str],
    highlight_blocks: Set[str]
) -> str:
    """
    应用基于规则的排版（带 LLM 识别的重点标注）

    Args:
        markdown_content: 原始 Markdown 内容
        highlight_phrases: 需要行内强调的短语集合
        highlight_blocks: 需要高亮引用块的段落集合

    Returns:
        格式化后的 HTML 内容
    """
    processor = RuleBasedLayoutProcessorV2(highlight_phrases, highlight_blocks)
    return processor.process(markdown_content)


def apply_rule_based_layout(markdown_content: str) -> str:
    """
    应用基于规则的排版（不带重点标注）

    Args:
        markdown_content: 原始 Markdown 内容

    Returns:
        格式化后的 HTML 内容
    """
    processor = RuleBasedLayoutProcessorV2()
    return processor.process(markdown_content)
