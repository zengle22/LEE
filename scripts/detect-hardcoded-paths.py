"""
Hardcoded Path Detector - CI Gate

扫描代码库中的硬编码路径（.artifacts, .workflow），
用于 CI 门禁，防止新增硬编码绕过统一路径管理。

用法:
    python scripts/detect-hardcoded-paths.py [--fix] [paths...]

默认扫描 src/ 目录。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import FrozenSet, List, Tuple


# 允许的路径前缀（工具目录）
ALLOWED_PREFIXES: FrozenSet[str] = frozenset({
    ".artifacts",
    ".workflow",
})

# 允许出现这些字符串的文件/目录（不视为硬编码）
ALLOWED_FILES: FrozenSet[str] = frozenset({
    "path_policy.py",       # 策略定义文件本身
    "path_config.py",       # 路径配置服务
    "io_guard.py",          # 守卫实现文件本身
    "detect-hardcoded-paths.py",  # CI 门禁脚本本身
    "__init__.py",          # 模块导入
    "test_",                # 测试文件
    ".pyc",
})

# 豁免的目录（这些目录中的路径不视为硬编码）
EXCLUDED_DIRS: FrozenSet[str] = frozenset({
    "evidence",             # 历史运行产物
    "spec-global",           # 规范定义目录（声明期望的目录结构）
    "tech-debt",             # 技术债务记录
    ".workflow",             # 工作流运行态（输出目录）
    ".artifacts",           # 产出物目录
})

# 允许的上下文模式（不算硬编码）
ALLOWED_CONTEXTS: List[re.Pattern] = [
    # 注释中的路径
    re.compile(r'#.*["\'](\.artifacts|/\.artifacts)'),
    re.compile(r'#.*["\'](\.workflow|/\.workflow)'),
    # 字符串字面量中的路径（可能是配置值）
    re.compile(r'["\'](\.artifacts/)["\']'),  # ".artifacts/" 作为值
    re.compile(r'["\'](\.workflow/)["\']'),   # ".workflow/" 作为值
    # 文档字符串
    re.compile(r'""".*\.artifacts.*"""', re.DOTALL),
    re.compile(r'""".*\.workflow.*"""', re.DOTALL),
    re.compile(r"'''.*\.artifacts.*'''", re.DOTALL),
    re.compile(r"'''.*\.workflow.*'''", re.DOTALL),
    # 模块级常量定义（不算硬编码）- 如 TOKENS_DIR = ".workflow/tokens"
    re.compile(r'^[A-Z_]+ = [".\'](\.artifacts|\.workflow)/'),  # CONST = ".workflow/xxx"
    # 类属性定义（不算硬编码）- 如 self.TOKENS_DIR = ".workflow/tokens"
    re.compile(r'self\.[A-Z_]+ = [".\'](\.artifacts|\.workflow)/'),  # self.CONST = ".workflow/xxx"
    # 类属性定义 - 如 TOKENS_DIR = ".workflow/tokens" (在类里面)
    re.compile(r'^\s+TOKENS?_[A-Z_]+ = [".\'](\.artifacts|\.workflow)/'),  # class attribute
    re.compile(r'^\s+LOG_[A-Z_]+ = [".\'](\.artifacts|\.workflow)/'),  # LOG_FILE
    re.compile(r'^\s+SECRET_[A-Z_]+ = [".\'](\.artifacts|\.workflow)/'),  # SECRET_FILE
    # 类属性列表中的路径（不算硬编码）- 如 DEFAULT_..._PATHS = ["..."]
    re.compile(r'^\s+["\'][^"\']*["\'],?\s*$'),  # 列表项（配合下面的列表上下文检测）
    re.compile(r'=\s*\['),  # 列表开始
    # dataclass 默认值（不算硬编码）- 如 output_dir: str = ".workflow/traces"
    re.compile(r':\s*(str|Optional\[str\])\s*=\s*["\'](\.artifacts|\.workflow)/'),  # field default
    re.compile(r'data\.get\([^)]+,\s*["\'](\.artifacts|\.workflow)/'),  # data.get() fallback
    # f-string 动态路径拼接（如 prompt 生成）- 如 f".workflow/workspace/{workflow_id}/"
    re.compile(r'f["\'].*\.workflow/.*\{.*\}.*["\']'),  # f-string with .workflow/ and {}
    re.compile(r'f["\'].*\.artifacts/.*\{.*\}.*["\']'),  # f-string with .artifacts/ and {}
    # 字典键中的路径（文档说明）- 如 ".workflow/runs": "description"
    re.compile(r'["\'](\.artifacts|\.workflow)/[^"\'\s]+["\']:\s*["\']'),  # dict key with description
    # JSON/字典中的路径描述（如 docstring 说明输出路径）
    re.compile(r'"outputs":\s*\[[^]]*(\.workflow|\.artifacts)[^]]*\]'),  # "outputs": [".workflow/..."]
]

# 豁免的配置列表模式（列表中的路径字符串不算硬编码）
ALLOWED_LIST_CONTEXTS: List[re.Pattern] = [
    re.compile(r'[A-Z_]+_DIRS?\s*[:=]\s*\{'),  # _DIRS = { 或 _DIRS: Set = {
    re.compile(r'[A-Z_]+_PATHS?\s*[:=]\s*\['),  # _PATHS = [
    re.compile(r'[A-Z_]+_LISTS?\s*[:=]\s*\['),  # _LISTS = [
]


def is_allowed_file(file_path: Path) -> bool:
    """检查文件是否在允许列表中"""
    filename = file_path.name
    for allowed in ALLOWED_FILES:
        if allowed in filename:
            return True
    return False


def is_in_excluded_dir(file_path: Path) -> bool:
    """检查文件是否在豁免目录中"""
    path_str = str(file_path)
    for excluded in EXCLUDED_DIRS:
        if excluded in path_str:
            return True
    return False


def is_allowed_context(line: str, in_list_context: bool = False) -> bool:
    """检查行是否在允许的上下文中"""
    for pattern in ALLOWED_CONTEXTS:
        if pattern.search(line):
            return True

    # 如果在列表上下文中（配置列表），豁免路径字符串
    if in_list_context:
        # 匹配列表项中的路径字符串，如 "path/to/dir",
        if re.search(r'^\s*["\'][^"\']+["\']', line):
            return True

    return False


def detect_hardcoded_paths(
    root_dir: Path,
    extensions: Tuple[str, ...] = (".py", ".yaml", ".yml"),
) -> List[Tuple[Path, int, str]]:
    """
    检测硬编码路径

    Returns:
        List of (file_path, line_number, line_content) tuples
    """
    findings = []

    # 正则：匹配 .artifacts 或 .workflow 作为路径的一部分
    # 排除注释和允许的上下文
    patterns = [
        # 匹配字符串中的路径（如 ".artifacts/..." 或 '.workflow/...'）
        re.compile(r'["\'](\.artifacts/[^"\']*)["\']'),
        re.compile(r'["\'](\.workflow/[^"\']*)["\']'),
        # 匹配路径拼接（如 Path(".artifacts") 或 Path(".workflow")）
        re.compile(r'Path\(["\'](\.artifacts)["\']'),
        re.compile(r'Path\(["\'](\.workflow)["\']'),
        # 匹配目录字面量（如 /".artifacts/" 或 /'.workflow/'）
        re.compile(r'/\.artifacts/'),
        re.compile(r'/\.workflow/'),
    ]

    for file_path in root_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if not file_path.name.endswith(extensions):
            continue
        if is_allowed_file(file_path):
            continue
        if is_in_excluded_dir(file_path):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        lines = content.splitlines()
        in_list_context = False
        for line_num, line in enumerate(lines, start=1):
            # 跳过注释行
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # 检查是否进入/退出列表上下文
            for list_pattern in ALLOWED_LIST_CONTEXTS:
                if list_pattern.search(line):
                    in_list_context = True
                    break
            # 空行或右括号结束列表上下文
            if in_list_context and (not stripped.strip() or stripped.startswith("]") or stripped.startswith("}")):
                in_list_context = False

            # 检查是否在允许的上下文中
            if is_allowed_context(line, in_list_context):
                continue

            # 检查是否匹配硬编码模式
            for pattern in patterns:
                if pattern.search(line):
                    findings.append((
                        file_path.relative_to(root_dir),
                        line_num,
                        line.strip(),
                    ))
                    break

    return findings


def detect_hardcoded_paths_for_file(file_path: Path) -> List[Tuple[Path, int, str]]:
    """
    检测单个文件中的硬编码路径。

    返回值中的 Path 仍然是相对于该文件父目录的相对路径，
    便于与目录模式的输出结构保持一致。
    """
    file_path = Path(file_path)
    findings = detect_hardcoded_paths(file_path.parent)
    target_name = file_path.name
    return [
        (relative_path, line_num, content)
        for relative_path, line_num, content in findings
        if relative_path.name == target_name
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Detect hardcoded .artifacts/.workflow paths in code"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["src"],
        help="Paths to scan (default: src)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Suggest fixes (not implemented yet)",
    )
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Exit with code 1 if findings exist",
    )

    args = parser.parse_args()

    root = Path(".")
    all_findings = []

    for path in args.paths:
        p = Path(path)
        if p.is_dir():
            findings = detect_hardcoded_paths(p)
            all_findings.extend(findings)
        elif p.is_file():
            all_findings.extend(detect_hardcoded_paths_for_file(p))

    if all_findings:
        print("=" * 70)
        print("⚠️  硬编码路径检测 - 发现问题")
        print("=" * 70)
        print()

        # 按文件分组显示
        by_file: dict = {}
        for f, ln, content in all_findings:
            if f not in by_file:
                by_file[f] = []
            by_file[f].append((ln, content))

        for file_path, lines in sorted(by_file.items()):
            print(f"📁 {file_path}")
            for ln, content in lines[:3]:  # 每个文件最多显示3行
                print(f"   {ln:4d}: {content[:80]}")
            if len(lines) > 3:
                print(f"   ... (共 {len(lines)} 处)")
            print()

        print("=" * 70)
        print(f"总计: {len(all_findings)} 处硬编码路径")
        print()
        print("建议: 使用 PathConfig 或 path_policy.py 中的常量")
        print("      from src.lee.orchestrator.core.path_policy import ALLOWED_WRITE_PREFIXES")
        print("=" * 70)

        if args.fail:
            sys.exit(1)
    else:
        print("✅ 未检测到硬编码路径")
        print("   (path_policy.py 和 io_guard.py 已豁免)")


if __name__ == "__main__":
    main()
