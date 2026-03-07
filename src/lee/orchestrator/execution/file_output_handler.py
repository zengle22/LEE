"""
LEE Orchestrator v3.0 - File Output Handler

本模块负责将 LLM 输出保存到文件系统。

核心职责：
1. 解析 LLM 输出（分离多个文件）
2. 根据 outputs.spec 保存文件
3. 格式校验（YAML/JSON）
4. 创建必要的目录结构
"""

import os
import re
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ParsedOutput:
    """解析后的输出文件"""
    filename: str
    content: str
    format: str


class FileOutputHandler:
    """
    文件输出处理器

    负责将 LLM 返回的文本解析并保存为多个文件
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化

        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()

    async def handle(
        self,
        llm_output: str,
        outputs_spec: List[Any],
        workflow_context: Dict[str, Any] = None
    ) -> List[str]:
        """
        处理 LLM 输出，保存文件

        Args:
            llm_output: LLM 返回的原始文本
            outputs_spec: OutputSpec 列表
            workflow_context: 工作流上下文（用于路径解析）

        Returns:
            成功写入的文件路径列表
        """
        if workflow_context is None:
            workflow_context = {}

        # 1. 解析 LLM 输出为多个文件
        parsed_outputs = self._parse_llm_output(llm_output)

        # 2. 根据 outputs_spec 匹配和保存文件
        written_files = []

        for spec in outputs_spec:
            # 解析路径
            output_path = self._resolve_path(spec.path, workflow_context)

            # 处理目录类型输出
            if spec.type == "dir":
                # 对于目录类型，查找所有应放入该目录的文件
                dir_files = self._find_files_for_directory(
                    parsed_outputs,
                    spec.path,
                    llm_output
                )

                if not dir_files:
                    if spec.required:
                        # 如果没有找到文件但有目录类型输出，尝试创建空目录
                        os.makedirs(output_path, exist_ok=True)
                        written_files.append(output_path)
                    continue

                # 写入目录中的所有文件
                for file_info in dir_files:
                    file_path = os.path.join(output_path, file_info["filename"])
                    await self._write_file(file_path, file_info["content"])
                    written_files.append(file_path)

                continue

            # 处理文件类型输出
            # 查找匹配的输出内容
            content = self._find_content_for_spec(
                parsed_outputs,
                spec,
                llm_output
            )

            if content is None:
                if spec.required:
                    raise ValueError(f"Required output not found: {spec.path}")
                continue

            # 格式校验（仅警告，不阻止）
            # if spec.format:
            #     try:
            #         self._validate_format(content, spec.format)
            #     except ValueError as e:
            #         print(f"[FileOutputHandler] Warning: {e}")
            #         # 继续处理，不阻止写入

            # 创建目录并写入文件
            await self._write_file(output_path, content)
            written_files.append(output_path)

        return written_files

    def _parse_llm_output(self, llm_output: str) -> List[ParsedOutput]:
        """
        解析 LLM 输出，提取多个文件内容

        支持的格式：
        1. Markdown 代码块：```yaml ... ```, ```json ... ```
        2. 文件分隔符：=== filename.ext ===
        3. 单文件模式：整个输出作为单个文件

        Args:
            llm_output: LLM 原始输出

        Returns:
            解析后的文件列表
        """
        outputs = []

        # 方法1: 尝试解析 Markdown 代码块
        code_blocks = self._extract_code_blocks(llm_output)
        if len(code_blocks) > 1:
            return code_blocks

        # 方法2: 尝试解析文件分隔符格式
        separator_outputs = self._extract_by_separator(llm_output)
        if separator_outputs:
            return separator_outputs

        # 方法3: 单文件模式
        # 根据内容推断格式
        format_hint = self._infer_format_from_content(llm_output)
        outputs.append(ParsedOutput(
            filename="output",
            content=llm_output,
            format=format_hint
        ))

        return outputs

    def _extract_code_blocks(self, text: str) -> List[ParsedOutput]:
        """
        提取 Markdown 代码块

        支持格式：
        - ```yaml ... ```
        - ```yaml filename: docker-compose.yml\n ... ```
        - ```yaml\n # File: docker-compose.yml\n ... ```
        - ## filename.yaml\n```yaml\n ... ``` (Markdown heading before code block)
        """
        outputs = []

        # 首先尝试提取带 Markdown heading 的格式
        # 模式: ## filename.yaml (或其他级别的 heading) 后跟代码块
        heading_pattern = r"^(#{1,6})\s*([^\n#]+?)\s*\n\s*```(yaml|yml|json|markdown|md|text|bash|sh|shell)(?:\n?[^\n]*)?\n(.*?)```"

        heading_matches = list(re.finditer(heading_pattern, text, re.MULTILINE | re.DOTALL))

        if heading_matches:
            # 使用 heading 格式提取
            for match in heading_matches:
                heading_level = match.group(1)
                heading_text = match.group(2).strip()
                lang = match.group(3)
                content = match.group(4).strip()

                # 尝试从 heading 文本中提取文件路径
                # 支持格式：
                # - "devops/infra/docker-compose.yml"
                # - "1. Docker Compose (devops/infra/docker-compose.yml)"
                # - "Docker Compose File - devops/infra/docker-compose.yml"
                filename = None

                # 优先级顺序：
                # 1. 括号中的完整路径（最高优先级）- 例如: (devops/infra/docker-compose.yml)
                # 2. 直接就是路径（包含 /）- 例如: devops/infra/docker-compose.yml
                # 3. 破折号后的路径
                # 4. 其他路径匹配
                # 5. heading 文本（最后备选）

                filename = None

                # 模式1: 括号中的完整路径（支持包含 / 和 . 的路径）
                bracket_match = re.search(r'\(([\w/\-\.]+\.(ya?ml|json|md|txt|sh))\)', heading_text)
                if bracket_match:
                    filename = bracket_match.group(1)

                # 模式2: 直接就是路径（包含 / 的完整路径）
                if not filename and '/' in heading_text and re.search(r'\.(ya?ml|json|md|txt|sh)$', heading_text):
                    filename = heading_text.strip()

                # 模式3: 破折号后的路径
                if not filename:
                    dash_match = re.search(r'[-–]\s*([\w/\-\.]+\.(ya?ml|json|md|txt|sh))\s*$', heading_text)
                    if dash_match:
                        filename = dash_match.group(1)

                # 模式4: 查找任何类似文件路径的模式
                if not filename:
                    path_match = re.search(r'[\w/]+/[\w\-\.]+\.(ya?ml|json|md|txt|sh)', heading_text)
                    if path_match:
                        filename = path_match.group(0)

                # 如果都没找到，使用 heading 文本作为文件名（最后备选）
                if not filename:
                    filename = heading_text

                # 标准化格式名称
                if lang in ["yaml", "yml"]:
                    format_type = "yaml"
                elif lang == "json":
                    format_type = "json"
                elif lang in ["markdown", "md"]:
                    format_type = "markdown"
                elif lang in ["bash", "sh", "shell"]:
                    format_type = "text"
                    # 如果文件名没有扩展名，添加 .sh
                    if not filename.endswith('.sh'):
                        filename = f"{filename}.sh"
                else:
                    format_type = "text"

                outputs.append(ParsedOutput(
                    filename=filename,
                    content=content,
                    format=format_type
                ))

            return outputs

        # 如果没有找到 heading 格式，使用原来的方法
        # 但首先尝试提取所有 ## 文件路径 模式
        heading_filenames = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('##'):
                # 提取文件路径
                filename_match = re.search(r'##\s*([\w/\-\.]+\.(ya?ml|json|md|txt|sh|ini))\s*', line)
                if filename_match:
                    heading_filenames.append(filename_match.group(1))

        # 更宽松的模式，支持在代码块开始后指定文件名
        pattern = r"```(yaml|yml|json|markdown|md|text|bash|sh|shell|ini)(?:\n?[^\n]*)?\n(.*?)```"

        matches = list(re.finditer(pattern, text, re.DOTALL))

        for i, match in enumerate(matches):
            lang = match.group(1)
            full_content = match.group(2).strip()

            # 尝试从内容开头提取文件名
            filename = self._extract_filename_from_content(full_content, lang)
            content = full_content

            # 如果没有找到文件名，尝试从提取的 heading_filenames 中获取
            if not filename or filename.startswith("file_"):
                if i < len(heading_filenames):
                    filename = heading_filenames[i]
                else:
                    # 最后的备选方案：从第一行提取文件名注释
                    lines = full_content.split('\n')
                    if lines and lines[0].strip().startswith('#'):
                        first_line = lines[0].strip()
                        # 检查是否包含文件名模式
                        if 'file:' in first_line.lower() or 'filename:' in first_line.lower():
                            filename = first_line.split(':', 1)[1].strip()
                            content = '\n'.join(lines[1:]).strip()
                        else:
                            filename = f"file_{i+1}"
                    else:
                        filename = f"file_{i+1}"

            # 标准化格式名称
            if lang in ["yaml", "yml"]:
                format_type = "yaml"
            elif lang == "json":
                format_type = "json"
            elif lang in ["markdown", "md"]:
                format_type = "markdown"
            elif lang in ["bash", "sh", "shell"]:
                format_type = "text"
                # 如果文件名没有扩展名，添加 .sh
                if not filename.endswith('.sh'):
                    filename = f"{filename}.sh"
            elif lang == "ini":
                format_type = "text"
            else:
                format_type = "text"

            outputs.append(ParsedOutput(
                filename=filename,
                content=content,
                format=format_type
            ))

        return outputs

    def _extract_filename_from_content(self, content: str, lang: str) -> Optional[str]:
        """从代码块内容中提取文件名"""
        lines = content.split('\n')
        if not lines:
            return None

        first_line = lines[0].strip()

        # 模式1: # File: docker-compose.yml
        if first_line.lower().startswith('# file:'):
            return first_line.split(':', 1)[1].strip()

        # 模式2: # filename: docker-compose.yml
        if first_line.lower().startswith('# filename:'):
            return first_line.split(':', 1)[1].strip()

        # 模式3: # docker-compose.yml (文件名作为注释)
        if first_line.startswith('# ') and not first_line.startswith('# #'):
            potential_name = first_line[1:].strip()
            # 检查是否看起来像文件名（包含扩展名）
            if '.' in potential_name and len(potential_name) < 100:
                return potential_name

        return None

    def _extract_by_separator(self, text: str) -> List[ParsedOutput]:
        """
        提取使用文件分隔符的输出

        支持格式：
        - === filename.yaml ===
        - ### File: filename.yaml
        - -- filename.yaml --
        """
        outputs = []

        # 模式1: === filename.yaml ===
        pattern1 = r"===\s*(.+?\.\w+)\s*===\n?\n(.*?)(?=\n===\s*.+?\.\w+\s*===|\Z)"
        matches = list(re.finditer(pattern1, text, re.DOTALL))

        # 模式2: ### File: filename.yaml
        if not matches:
            pattern2 = r"#{3,}\s*File:\s*(.+?\.\w+)\s*\n?\n(.*?)(?=\n#{3,}\s*File:|\Z)"
            matches = list(re.finditer(pattern2, text, re.DOTALL))

        # 模式3: -- filename.yaml --
        if not matches:
            pattern3 = r"--\s*(.+?\.\w+)\s*--\n?\n(.*?)(?=\n--\s*.+?\.\w+\s*--|\Z)"
            matches = list(re.finditer(pattern3, text, re.DOTALL))

        for match in matches:
            filename = match.group(1).strip()
            content = match.group(2).strip()
            format_type = self._infer_format_from_filename(filename)

            outputs.append(ParsedOutput(
                filename=filename,
                content=content,
                format=format_type
            ))

        return outputs

    def _infer_format_from_filename(self, filename: str) -> str:
        """从文件名推断格式"""
        if filename.endswith((".yaml", ".yml")):
            return "yaml"
        elif filename.endswith(".json"):
            return "json"
        elif filename.endswith((".md", ".markdown")):
            return "markdown"
        else:
            return "text"

    def _infer_format_from_content(self, content: str) -> str:
        """从内容推断格式"""
        content = content.strip()

        # 尝试解析为 YAML
        try:
            yaml.safe_load(content)
            # 如果成功，可能是 YAML
            if content.startswith(("{{%", "{#)", "#")):
                return "text"  # 模板
            return "yaml"
        except:
            pass

        # 尝试解析为 JSON
        try:
            json.loads(content)
            return "json"
        except:
            pass

        # 默认为 markdown（因为 LLM 常用 markdown 输出）
        return "markdown"

    def _find_content_for_spec(
        self,
        parsed_outputs: List[ParsedOutput],
        spec,
        fallback_content: str
    ) -> Optional[str]:
        """
        根据 outputs.spec 查找匹配的内容

        匹配规则：
        1. 文件名匹配（优先）：从 spec.path 提取文件名，与 parsed_outputs 中的 filename 匹配
        2. 路径后缀匹配：从 spec.path 提取最后部分（如 ansible-inventory.yaml），与 parsed_outputs 匹配
        3. 格式匹配（仅当唯一时）
        4. 顺序匹配（第 N 个输出对应第 N 个 spec）

        Args:
            parsed_outputs: 解析后的输出列表
            spec: OutputSpec
            fallback_content: 备用内容（整个 LLM 输出）

        Returns:
            匹配的内容，或 None
        """
        # 规则1: 直接使用 fallback（如果只有一个输出）
        if len(parsed_outputs) == 1:
            return fallback_content

        # 规则2: 文件名完全匹配（从 spec.path 提取完整文件名）
        spec_filename = os.path.basename(spec.path)
        for o in parsed_outputs:
            if o.filename == spec_filename or o.filename == spec.path:
                return o.content

        # 规则3: 文件名部分匹配（spec.path 的最后部分与 parsed_outputs.filename 匹配）
        # 例如: spec.path="ansible/ansible-inventory.yaml" 匹配 filename="ansible-inventory.yaml"
        for o in parsed_outputs:
            # 检查 spec.path 是否以 filename 结尾
            if spec.path.endswith(o.filename):
                return o.content
            # 检查 filename 是否包含 spec.path 的关键部分
            # 例如: filename="ansible-inventory.yaml" 包含 "ansible-inventory"
            spec_basename = os.path.splitext(spec_filename)[0]
            o_basename = os.path.splitext(o.filename)[0]
            if spec_basename == o_basename or o_basename in spec_filename:
                return o.content

        # 规则4: 按格式匹配（仅当唯一时）
        matching_format = [o for o in parsed_outputs if o.format == spec.format]
        if len(matching_format) == 1:
            return matching_format[0].content

        # 规则5: 按文件扩展名匹配
        ext = self._get_extension(spec.format)
        matching_ext = [o for o in parsed_outputs if o.filename.endswith(ext)]
        if len(matching_ext) == 1:
            return matching_ext[0].content

        # 规则6: 返回第一个匹配格式的内容
        for o in parsed_outputs:
            if o.format == spec.format or self._is_format_compatible(o.format, spec.format):
                return o.content

        return None

    def _find_files_for_directory(
        self,
        parsed_outputs: List[ParsedOutput],
        dir_path: str,
        fallback_content: str
    ) -> List[Dict[str, str]]:
        """
        为目录查找应放入其中的所有文件

        Args:
            parsed_outputs: 解析后的输出列表
            dir_path: 目录路径（相对于项目根目录，如 devops/cicd/）
            fallback_content: 备用内容（整个 LLM 输出）

        Returns:
            文件信息列表：[{"filename": "...", "content": "..."}]
        """
        files = []

        # 预处理：获取目录路径的各个组成部分
        dir_parts = dir_path.rstrip('/').split('/')
        # 例如 devops/cicd/ -> ['devops', 'cicd']

        for output in parsed_outputs:
            if output.filename and output.filename != "output" and output.filename != "file_1":
                extracted_filename = output.filename

                # 核心逻辑：提取相对于 dir_path 的文件名
                if dir_path:
                    normalized_dir = dir_path.rstrip('/') + '/'

                    # 尝试多种模式

                    # 模式1: 直接匹配 - 文件名以目录路径开头
                    # devops/cicd/infra/xxx.yml -> infra/xxx.yml
                    if extracted_filename.startswith(normalized_dir):
                        extracted_filename = extracted_filename[len(normalized_dir):]

                    # 模式2: 去掉 devops/ 前缀，然后重新匹配
                    # devops/infra/xxx.yml -> infra/xxx.yml (对于 dir_path=devops/)
                    # devops/cicd/infra/xxx.yml -> infra/xxx.yml (对于 dir_path=devops/cicd/)
                    elif extracted_filename.startswith('devops/'):
                        after_devops = extracted_filename[7:]  # 去掉 devops/ (7个字符: d e v o p s /)
                        # 重新匹配
                        if after_devops.startswith(normalized_dir):
                            extracted_filename = after_devops[len(normalized_dir):]
                        else:
                            extracted_filename = after_devops

                    # 模式3: 处理重复的目录前缀
                    # devops/cicd/devops/infra/xxx.yml -> infra/xxx.yml
                    # 检查是否有 dir_parts 的重复
                    else:
                        # 构建可能的重复前缀
                        # 例如 ['devops', 'cicd'] -> 'devops/cicd/devops/cicd/'
                        for i in range(len(dir_parts), 0, -1):
                            prefix = '/'.join(dir_parts[:i]) + '/'  # 'devops/' for i=1
                            duplicate = '/'.join(dir_parts) + '/' + prefix  # 'devops/cicd/devops/'
                            if extracted_filename.startswith(duplicate):
                                extracted_filename = extracted_filename[len(duplicate):]
                                break

                # 最终清理：如果文件名仍然以目录部分开头，提取最后的部分
                if '/' in extracted_filename:
                    # 路径中有多个部分，检查是否可以简化
                    parts = extracted_filename.split('/')
                    # 如果第一部分是目录名，可能需要去掉
                    if len(parts) > 1 and parts[0] in dir_parts:
                        # 找到第一个不在 dir_parts 中的部分
                        for i, part in enumerate(parts):
                            if part not in dir_parts:
                                extracted_filename = '/'.join(parts[i:])
                                break

                # 确保文件名是有效的
                if extracted_filename and extracted_filename not in ['.', '/', '']:
                    files.append({
                        "filename": extracted_filename,
                        "content": output.content
                    })
            else:
                # 没有明确文件名，根据内容类型推断
                ext = self._infer_extension_from_content(output.content)
                filename = f"output_{len(files) + 1}{ext}"
                files.append({
                    "filename": filename,
                    "content": output.content
                })

        return files

    def _infer_extension_from_content(self, content: str) -> str:
        """从内容推断文件扩展名"""
        content = content.strip()
        if content.startswith("---") or content.startswith("# "):
            return ".yaml"
        elif content.startswith("{") or content.startswith("["):
            return ".json"
        elif content.startswith("# ") or content.startswith("## "):
            return ".md"
        else:
            return ".txt"

    def _get_extension(self, format_type: str) -> str:
        """获取格式的文件扩展名"""
        mapping = {
            "yaml": ".yaml",
            "json": ".json",
            "markdown": ".md",
            "text": ".txt",
        }
        return mapping.get(format_type, "")

    def _is_format_compatible(self, output_format: str, required_format: str) -> bool:
        """检查格式是否兼容"""
        # text 可以兼容任何格式
        if output_format == "text":
            return True
        # markdown 和 text 可以互换
        if output_format in ["markdown", "text"] and required_format in ["markdown", "text"]:
            return True
        return output_format == required_format

    def _validate_format(self, content: str, format_type: str) -> None:
        """
        校验内容格式

        Args:
            content: 文件内容
            format_type: 期望的格式

        Raises:
            ValueError: 格式不正确
        """
        if format_type == "yaml":
            try:
                # 尝试多文档解析（支持 --- 分隔符）
                docs = list(yaml.safe_load_all(content))
                # 验证至少有一个有效文档
                if not docs or all(d is None for d in docs):
                    raise ValueError("Empty YAML content")
            except yaml.YAMLError as e:
                # 如果多文档解析失败，尝试单文档（向后兼容）
                try:
                    yaml.safe_load(content)
                except Exception as e2:
                    import logging
                    logging.getLogger(__name__).debug(
                        f"Failed to parse YAML in multi-document or single-document mode: {e}, {e2}"
                    )
                    raise ValueError(f"Invalid YAML format: {e}")

        elif format_type == "json":
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {e}")

    def _resolve_path(self, path: str, context: Dict[str, Any]) -> str:
        """
        解析路径变量并转换为绝对路径

        支持两种变量格式：
        1. ${VARIABLE} - 环境变量风格
        2. {{ variable }} - Jinja2 模板风格

        Args:
            path: 原始路径
            context: 工作流上下文

        Returns:
            解析后的绝对路径
        """
        # 构建模板渲染上下文
        template_context = {}

        # 从 context 中提取常用变量
        # 优先使用顶层的 data，如果没有则使用 context 本身
        if "data" in context:
            data = context.get("data", {})
            template_context.update(data)

            # 从 data 中提取 params（模板渲染需要这些变量）
            if "params" in data:
                template_context.update(data.get("params", {}))
        else:
            # 如果没有 data，直接使用 context
            template_context.update(context)

        # 添加其他顶层变量（覆盖 data 中的同名变量）
        for key in ["project_name", "qa_specs_dir", "module"]:
            if key in context:
                template_context[key] = context[key]

        # 渲染 Jinja2 模板变量
        if "{{" in path and "}}" in path:
            from lee.orchestrator.core.template_engine import TemplateEngine
            import logging
            logger = logging.getLogger(__name__)
            engine = TemplateEngine()
            logger.info(f"Rendering path: {path}, context keys: {list(template_context.keys())}")
            try:
                path = engine.render_string(path, template_context)
                logger.info(f"Rendered path: {path}")
            except Exception as e:
                logger.warning(f"Path rendering failed: {e}")
                pass  # 渲染失败时保留原样

        # 变量替换 - ${PROJECT_NAME} 风格
        if "${PROJECT_NAME}" in path:
            project_name = context.get("project_name", context.get("data", {}).get("project_name", "ai-marathon-coach"))
            path = path.replace("${PROJECT_NAME}", project_name)

        # `/reports/...` 这类项目内根路径在 Windows 上会被 Path.join 吃成盘符根目录。
        # 这里统一当作“相对 project_root 的治理路径”处理。
        if isinstance(path, str) and path.startswith(("/", "\\")) and not Path(path).drive:
            path = path.lstrip("/\\")

        # 转换为绝对路径
        if not os.path.isabs(path):
            path = str((self.project_root / path).resolve())

        return path

    async def _write_file(self, path: str, content: str) -> None:
        """
        写入文件

        Args:
            path: 文件路径
            content: 文件内容
        """
        import logging
        import re
        logger = logging.getLogger(__name__)
        
        # 清理 Markdown 格式（如果内容是 YAML/JSON）
        if path.endswith(('.yaml', '.yml', '.json')):
            cleaned_content = self._clean_markdown_format(content)
            if cleaned_content != content:
                logger.info(f"Cleaned Markdown format from: {path}")
                content = cleaned_content
        
        # 创建目录
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # 写入文件
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _clean_markdown_format(self, content: str) -> str:
        """
        清理 Markdown 格式，提取纯 YAML/JSON 内容
        
        Args:
            content: 可能包含 Markdown 格式的内容
        
        Returns:
            清理后的纯内容
        """
        import re
        
        original_content = content
        
        # 移除文件路径标记（如 **spec/qa/test-sets/ts-xxx.yaml**）
        content = re.sub(r'^\*\*[^*]+\*\*\s*\n?', '', content, flags=re.MULTILINE)
        
        # 移除 Markdown 代码块开始标记（```yaml, ```json, ```）
        content = re.sub(r'^```(?:yaml|json)?\s*\n?', '', content, flags=re.MULTILINE)
        
        # 移除 Markdown 代码块结束标记
        content = re.sub(r'\n?\s*```\s*$', '', content, flags=re.MULTILINE)
        
        # 移除 Markdown 标题标记（###, ##, #）
        content = re.sub(r'^#+\s+.*$', '', content, flags=re.MULTILINE)
        
        # 查找第一个 YAML 键的位置
        lines = content.split('\n')
        yaml_start = 0
        yaml_end = len(lines)
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            # 检查是否是 YAML 键的开始（排除注释和空行）
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*:', stripped):
                yaml_start = i
                break
        
        # 从后往前找，找到最后一个有效的 YAML 行
        for i in range(len(lines) - 1, yaml_start, -1):
            stripped = lines[i].strip()
            # 如果是空行或注释，继续
            if not stripped or stripped.startswith('#'):
                continue
            # 如果看起来像说明文字（包含数字列表、冒号解释、中文说明等）
            if re.match(r'^\d+\.', stripped) or \
               re.match(r'^To\s+complete:', stripped, re.IGNORECASE) or \
               re.match(r'^This\s+(template|file|YAML)', stripped, re.IGNORECASE) or \
               re.match(r'^该\s*(YAML|文件|此)', stripped) or \
               re.match(r'^\d+\.?\s*$', stripped):  # 单独的数字行
                yaml_end = i
                break
        
        # 提取 YAML 内容
        yaml_lines = lines[yaml_start:yaml_end]
        
        # 移除末尾的说明文字行
        final_lines = []
        for line in yaml_lines:
            stripped = line.strip()
            # 如果是说明文字的开始，停止
            if re.match(r'^\d+\.\s+', stripped) or \
               re.match(r'^To\s+complete:', stripped, re.IGNORECASE) or \
               re.match(r'^This\s+(template|file|YAML)', stripped, re.IGNORECASE) or \
               re.match(r'^该\s*(YAML|文件|此)', stripped) or \
               re.match(r'^\d+\.?\s*$', stripped):
                break
            final_lines.append(line)
        
        result = '\n'.join(final_lines)
        
        # 如果清理后内容为空，返回原始内容
        if not result.strip():
            return original_content
        
        return result

    async def write_directory(
        self,
        base_path: str,
        files: Dict[str, str],
        workflow_context: Dict[str, Any] = None
    ) -> List[str]:
        """
        写入目录（多个文件）

        Args:
            base_path: 基础目录路径
            files: 文件名到内容的映射
            workflow_context: 工作流上下文

        Returns:
            写入的文件路径列表
        """
        if workflow_context is None:
            workflow_context = {}

        base_path = self._resolve_path(base_path, workflow_context)
        written_files = []

        for filename, content in files.items():
            full_path = os.path.join(base_path, filename)
            await self._write_file(full_path, content)
            written_files.append(full_path)

        return written_files
