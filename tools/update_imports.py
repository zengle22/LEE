#!/usr/bin/env python3
"""
Import 路径批量更新脚本

在 LEE 框架迁移后，批量更新所有 Python 文件中的 import 语句。

使用方式：
    python update_imports.py --dry-run  # 预览模式（不实际修改）
    python update_imports.py            # 执行更新
    python update_imports.py --path lee  # 只处理特定目录
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict

# Import 映射规则
IMPORT_MAPPINGS: List[Tuple[str, str]] = [
    # orchestrator → lee.orchestrator
    (r'from orchestrator\.core\.', 'from lee.orchestrator.'),
    (r'from orchestrator\.', 'from lee.cli.'),
    (r'import orchestrator\.core\.', 'import lee.orchestrator.'),
    (r'import orchestrator\.', 'import lee.cli.'),

    # orchestrator.core 内部模块扁平化
    (r'from lee\.orchestrator\.agent_context', 'from lee.orchestrator.agent_context'),
    (r'from lee\.orchestrator\.agent_loader', 'from lee.orchestrator.agent_loader'),
    (r'from lee\.orchestrator\.agent_resolver', 'from lee.orchestrator.agent_resolver'),
    (r'from lee\.orchestrator\.event_bus', 'from lee.utils.event_bus'),
    (r'from lee\.orchestrator\.template_resolver', 'from lee.utils.template_resolver'),
    (r'from lee\.orchestrator\.session_log', 'from lee.orchestrator.session_log'),

    # MetaGPT 适配层
    (r'from metagpt\.lee\.', 'from lee.engines.metagpt.'),
    (r'import metagpt\.lee\.', 'import lee.engines.metagpt.'),

    # 其他常见路径
    (r'from ai-spec\.', 'from lee.spec_global.'),
]


def find_python_files(root_path: Path) -> List[Path]:
    """查找所有 Python 文件"""
    python_files = []
    for path in root_path.rglob('*.py'):
        # 跳过虚拟环境和缓存目录
        if any(skip in path.parts for skip in ['venv', '__pycache__', '.tox', 'build']):
            continue
        python_files.append(path)
    return python_files


def update_imports_in_file(file_path: Path, dry_run: bool = False) -> Dict[str, int]:
    """更新单个文件中的 import 语句"""
    changes = {'total': 0, 'modified': 0}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes['total'] += 1

        # 应用所有映射规则
        for pattern, replacement in IMPORT_MAPPINGS:
            content = re.sub(pattern, replacement, content)

        # 如果内容发生变化
        if content != original_content:
            changes['modified'] += 1
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ 已更新: {file_path}")
            else:
                print(f"• 需要更新: {file_path}")

    except Exception as e:
        print(f"✗ 错误处理文件 {file_path}: {e}", file=sys.stderr)

    return changes


def show_summary(total_files: int, modified_files: int, dry_run: bool):
    """显示更新摘要"""
    print("\n" + "=" * 60)
    if dry_run:
        print("预览模式摘要（DRY RUN）")
    else:
        print("更新完成摘要")
    print("=" * 60)
    print(f"扫描文件总数: {total_files}")
    print(f"需要更新的文件: {modified_files}")
    print(f"更新率: {modified_files/total_files*100:.1f}%" if total_files > 0 else "更新率: 0%")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='批量更新 Python 文件中的 import 路径',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    # 预览模式（查看哪些文件需要更新）
    python update_imports.py --dry-run

    # 执行更新
    python update_imports.py

    # 只处理特定目录
    python update_imports.py --path lee/orchestrator

    # 显示详细的映射规则
    python update_imports.py --show-rules
        """
    )

    parser.add_argument(
        '--path',
        type=Path,
        default=Path('.'),
        help='要处理的根目录（默认：当前目录）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，不实际修改文件'
    )

    parser.add_argument(
        '--show-rules',
        action='store_true',
        help='显示所有 import 映射规则'
    )

    args = parser.parse_args()

    # 显示映射规则
    if args.show_rules:
        print("Import 映射规则：")
        print("-" * 60)
        for i, (pattern, replacement) in enumerate(IMPORT_MAPPINGS, 1):
            print(f"{i}. {pattern} → {replacement}")
        print("-" * 60)
        return

    # 查找所有 Python 文件
    print(f"扫描目录: {args.path.absolute()}")
    python_files = find_python_files(args.path)
    print(f"找到 {len(python_files)} 个 Python 文件\n")

    # 更新文件
    total_modified = 0
    for file_path in python_files:
        changes = update_imports_in_file(file_path, args.dry_run)
        total_modified += changes['modified']

    # 显示摘要
    show_summary(len(python_files), total_modified, args.dry_run)

    # 提示下一步操作
    if args.dry_run and total_modified > 0:
        print("\n执行以下命令应用更新：")
        print("  python update_imports.py")
    elif not args.dry_run and total_modified > 0:
        print("\n建议执行以下操作验证更新：")
        print("  1. python -m py_compile lee/**/*.py  # 检查语法")
        print("  2. pytest tests/  # 运行测试（如果有）")


if __name__ == '__main__':
    main()
