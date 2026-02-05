"""
LEE Orchestrator - Migration Tool

将旧格式工作流模板迁移到 spec-global 格式。

功能：
1. 读取旧格式模板（examples/templates.yaml）
2. 转换为 spec-global 格式
3. 添加 legacy 头注释
4. 更新 README
"""

import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List

from lee.orchestrator.ir.converter import TemplateToIRConverter


# Legacy 头注释
LEGACY_HEADER = """# status: legacy
# format: orchestrator-legacy-template
# NOTE:
#   - New workflows MUST use spec-global format.
#   - This file exists only for backward compatibility and migration.
#   - Use 'lee migrate-workflow <template_id>' to migrate to spec-global.
#
"""


class WorkflowMigrator:
    """
    工作流迁移工具

    将 Orchestrator 的旧格式模板迁移到 spec-global 格式。
    """

    def __init__(self, input_dir: str, output_dir: str):
        """
        初始化迁移工具

        Args:
            input_dir: 输入目录（包含旧格式模板）
            output_dir: 输出目录（保存 spec-global 格式模板）
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.converter = TemplateToIRConverter()

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def migrate_template_file(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        add_legacy_header: bool = True
    ) -> str:
        """
        迁移单个模板文件

        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径（可选）
            add_legacy_header: 是否在原文件添加 legacy 头注释

        Returns:
            输出文件路径
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # 读取旧格式模板
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 YAML（支持多文档）
        docs = list(yaml.safe_load_all(content))
        templates = [doc for doc in docs if doc]

        # 迁移每个模板
        migrated_files = []
        for template in templates:
            # 提取模板 ID
            template_id = template.get("name", template.get("id", ""))
            if not template_id:
                continue

            # 转换为 IR
            ir = self._legacy_to_ir(template)

            # 确定输出文件
            if output_file:
                output_path = Path(output_file)
            else:
                # 自动生成输出路径
                filename = f"{template_id}.yaml"
                output_path = self.output_dir / filename

            # 导出为 spec-global 格式
            self.converter.ir_to_spec_global_yaml(ir, str(output_path))
            migrated_files.append(str(output_path))

            # 在原文件添加 legacy 头注释
            if add_legacy_header:
                self._add_legacy_header(input_path)

        return migrated_files[0] if len(migrated_files) == 1 else migrated_files

    def migrate_all_templates(self, input_file: str = None) -> List[str]:
        """
        迁移所有模板

        Args:
            input_file: 输入文件路径（默认为 examples/templates.yaml）

        Returns:
            迁移的文件列表
        """
        if input_file is None:
            input_file = self.input_dir / "templates.yaml"

        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Template file not found: {input_file}")

        # 读取模板
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        docs = list(yaml.safe_load_all(content))
        templates = [doc for doc in docs if doc]

        migrated = []
        for template in templates:
            template_id = template.get("name", template.get("id", ""))
            if not template_id:
                continue

            # 转换并导出
            ir = self._legacy_to_ir(template)
            output_path = self.output_dir / f"{template_id}.yaml"
            self.converter.ir_to_spec_global_yaml(ir, str(output_path))
            migrated.append(str(output_path))

        # 在原文件添加 legacy 头注释
        self._add_legacy_header(input_path)

        return migrated

    def _legacy_to_ir(self, template: Dict[str, Any]):
        """
        将旧格式模板转换为 IR

        Args:
            template: 旧格式模板字典

        Returns:
            WorkflowIR 对象
        """
        # 提取基本信息
        level = template.get("level", "task")
        name = template.get("name", "")
        description = template.get("description", "")

        # 转换步骤
        steps_data = template.get("steps", [])

        # 构建基本的 IR 结构
        ir = self.converter.template_to_ir(
            template=None,  # 占位符
            kind="workflow"
        )

        # 手动设置字段
        ir.id = name
        ir.name = name
        ir.description = description

        # 转换步骤
        from lee.orchestrator.ir.models import StepIR, StepKind
        ir.steps = []
        for step in steps_data:
            step_ir = StepIR(
                id=step.get("id", step.get("name", "")),
                kind=StepKind.AGENT,
                name=step.get("name", ""),
                description=step.get("description", ""),
                agent_id=step.get("agent"),
                skill_id=step.get("skill"),
                depends_on=step.get("depends_on", []),
            )
            ir.steps.append(step_ir)

        return ir

    def _add_legacy_header(self, file_path: Path) -> None:
        """
        在文件开头添加 legacy 头注释

        Args:
            file_path: 文件路径
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已经有 legacy 头注释
        if content.startswith("# status: legacy"):
            return

        # 添加头注释
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(LEGACY_HEADER)
            f.write(content)

    def update_readme(self) -> None:
        """更新 README 添加格式统一规则"""
        readme_path = self.input_dir / "README.md"

        if not readme_path.exists():
            # 尝试项目根目录的 README
            readme_path = Path(__file__).parent.parent.parent.parent / "README.md"

        if not readme_path.exists():
            print("README not found, skipping update")
            return

        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已经添加过
        if "## 工作流定义规范" in content:
            return

        # 添加格式规范章节
        workflow_section = """

## 工作流定义规范

**重要**: LEE 框架统一使用 spec-global 格式定义工作流。

### 规范说明

- **唯一格式**: 所有新工作流必须使用 `spec-global` 格式
- **工作流文件**: 存放在 `spec-global/departments/{department}/workflows/{name}/v1/workflow.yaml`
- **格式标识**: 文件必须以 `kind: workflow` 开头
- **版本管理**: 使用 `version: 1.0` 标识格式版本

### 旧格式状态

`examples/templates.yaml` 中的模板为 **legacy 格式**，仅用于：
- 向后兼容已有项目
- 迁移参考
- 学习 spec-global 格式

**禁止新增** 旧格式工作流定义。

### 迁移工具

使用迁移工具将旧格式转换为 spec-global：

```bash
# 迁移单个模板
lee migrate-workflow <template_id> --output spec-global/workflows/

# 迁移所有模板
lee migrate-workflow --all
```

详细迁移指南请参考：[Orchestrator 迁移指南](../docs/orchestrator-migration-guide.md)
"""

        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content + workflow_section)


# ========================================================================
# CLI 命令
# ========================================================================

def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="LEE 工作流迁移工具 - 将旧格式模板迁移到 spec-global 格式"
    )
    parser.add_argument(
        "template_id",
        nargs="?",
        help="模板 ID（如果不提供则迁移所有模板）"
    )
    parser.add_argument(
        "--input",
        default="examples/templates.yaml",
        help="输入文件路径（默认: examples/templates.yaml）"
    )
    parser.add_argument(
        "--output",
        default="spec-global/migrated-workflows",
        help="输出目录路径（默认: spec-global/migrated-workflows）"
    )
    parser.add_argument(
        "--no-legacy-header",
        action="store_true",
        help="不在原文件添加 legacy 头注释"
    )
    parser.add_argument(
        "--update-readme",
        action="store_true",
        help="更新 README 添加格式规范"
    )

    args = parser.parse_args()

    # 创建迁移工具
    migrator = WorkflowMigrator(
        input_dir=Path(args.input).parent,
        output_dir=args.output
    )

    if args.template_id:
        # 迁移单个模板
        print(f"Migrating template: {args.template_id}")
        output_file = migrator.migrate_template_file(
            args.input,
            output_file=f"{args.output}/{args.template_id}.yaml",
            add_legacy_header=not args.no_legacy_header
        )
        print(f"  → Migrated to: {output_file}")
    else:
        # 迁移所有模板
        print("Migrating all templates...")
        migrated = migrator.migrate_all_templates(args.input)
        for f in migrated:
            print(f"  → {f}")

    # 更新 README
    if args.update_readme:
        print("Updating README...")
        migrator.update_readme()
        print("  → README updated")

    print("\nMigration completed!")


if __name__ == "__main__":
    main()
