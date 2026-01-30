"""
文件系统工具

提供安全的文件读写操作。
"""

import pathlib
import hashlib
from typing import Optional, List

from .security import validate_write_operation


def read_file(path: str, encoding: str = "utf-8") -> str:
    """
    读取文件内容

    Args:
        path: 文件路径
        encoding: 文件编码

    Returns:
        文件内容

    Raises:
        FileNotFoundError: 文件不存在
        IOError: 读取失败
    """
    p = pathlib.Path(path)
    return p.read_text(encoding=encoding)


def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = True,
    workspace_root: Optional[str] = None,
    allowed_patterns: Optional[List[str]] = None,
) -> None:
    """
    写入文件内容（带安全边界检查）

    Args:
        path: 文件路径
        content: 文件内容
        encoding: 文件编码
        create_parents: 是否自动创建父目录
        workspace_root: 工作区根目录（用于安全检查）
        allowed_patterns: 允许写入的路径模式

    Raises:
        ValueError: 路径穿越或不在允许范围内
        IOError: 写入失败
    """
    # 如果提供了安全边界参数，进行验证
    if workspace_root is not None:
        allowed = allowed_patterns or []
        is_safe, error_msg = validate_write_operation(
            path, workspace_root, allowed
        )
        if not is_safe:
            raise ValueError(f"Security violation: {error_msg}")

    p = pathlib.Path(path)
    if create_parents:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)


def compute_hash(path: str, algorithm: str = "sha256") -> str:
    """
    计算文件哈希

    Args:
        path: 文件路径
        algorithm: 哈希算法（sha256, md5）

    Returns:
        哈希值（十六进制字符串）
    """
    p = pathlib.Path(path)
    content = p.read_bytes()

    if algorithm == "sha256":
        return hashlib.sha256(content).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(content).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def file_exists(path: str) -> bool:
    """检查文件是否存在"""
    return pathlib.Path(path).exists()


def get_file_size(path: str) -> int:
    """获取文件大小（字节）"""
    return pathlib.Path(path).stat().st_size


def list_files(directory: str, pattern: str = "*") -> List[str]:
    """
    列出目录中的文件

    Args:
        directory: 目录路径
        pattern: 匹配模式

    Returns:
        文件路径列表
    """
    p = pathlib.Path(directory)
    return [str(f) for f in p.glob(pattern) if f.is_file()]
