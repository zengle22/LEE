"""
安全边界工具

提供文件路径安全验证，防止路径穿越攻击。
"""

import os
import pathlib
from typing import List, Optional, Tuple
from fnmatch import fnmatch


def safe_join(root: str, rel_path: str) -> Optional[str]:
    """
    安全地拼接路径，防止路径穿越攻击

    Args:
        root: 根目录（绝对路径）
        rel_path: 相对路径

    Returns:
        拼接后的绝对路径，如果路径穿越则返回 None

    Example:
        >>> safe_join("/workspace", "src/main.py")
        '/workspace/src/main.py'
        >>> safe_join("/workspace", "../../../etc/passwd")
        None
    """
    try:
        root_path = pathlib.Path(root).resolve()
        joined_path = (root_path / rel_path).resolve()

        # 检查结果路径是否在 root 之下
        if str(joined_path).startswith(str(root_path)):
            return str(joined_path)
        else:
            return None
    except (ValueError, OSError):
        return None


def validate_path_allowed(
    path: str,
    workspace_root: str,
    allowed_patterns: List[str],
) -> bool:
    """
    验证路径是否在允许的范围内

    Args:
        path: 待验证的路径
        workspace_root: 工作区根目录
        allowed_patterns: 允许的路径模式列表（支持通配符）

    Returns:
        是否允许
    """
    # 首先检查是否在工作区内
    safe_path = safe_join(workspace_root, path)
    if safe_path is None:
        return False

    # 计算相对于工作区的路径
    rel_path = os.path.relpath(safe_path, workspace_root)

    # 检查是否匹配允许的模式
    for pattern in allowed_patterns:
        if fnmatch(rel_path, pattern):
            return True

    return False


def validate_write_operation(
    abs_path: str,
    workspace_root: str,
    allowed_patterns: List[str],
) -> Tuple[bool, Optional[str]]:
    """
    验证写入操作是否安全

    Args:
        abs_path: 绝对路径
        workspace_root: 工作区根目录
        allowed_patterns: 允许的路径模式列表

    Returns:
        (是否允许, 错误信息)
    """
    # 检查是否在工作区内
    root_path = pathlib.Path(workspace_root).resolve()
    path_obj = pathlib.Path(abs_path).resolve()

    if not str(path_obj).startswith(str(root_path)):
        return False, f"Path outside workspace: {abs_path}"

    # 计算相对路径
    try:
        rel_path = path_obj.relative_to(root_path)
    except ValueError:
        return False, f"Cannot compute relative path: {abs_path}"

    # 如果没有模式限制，只检查是否在工作区内
    if not allowed_patterns:
        return True, None

    # 检查是否匹配允许的模式
    rel_path_str = str(rel_path).replace("\\", "/")

    for pattern in allowed_patterns:
        if fnmatch(rel_path_str, pattern):
            return True, None

    return False, f"Path not in allowed patterns: {rel_path_str}"
