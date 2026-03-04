"""
IO Guard - 运行时路径守卫

通过 monkey patch 拦截非法写入操作，确保文件操作只能在允许的目录下进行。
只在 dev/CI 模式下启用。
"""

from __future__ import annotations

import builtins
import os
from pathlib import Path
from typing import Optional

from .path_policy import (
    ALLOWED_WRITE_PREFIXES,
    FROZEN_PREFIXES,
    is_allowed_write_path,
    is_frozen_path,
    is_path_guard_enabled,
    normalize_path,
)


class SecurityError(Exception):
    """安全异常 - 路径守卫触发"""
    pass


class PathGuard:
    """
    路径守卫 - 运行时拦截非法写入

    工作原理:
    - 只在 dev/CI 模式下启用
    - 通过 monkey patch 拦截写入操作
    - 以 project_root 为基准校验路径是否落在允许目录下

    校验算法:
    1. 相对路径按 project_root 解析（不是 CWD）
    2. 路径规范化（兼容 Windows：反斜杠 → 正斜杠）
    3. 使用"允许前缀集合"判定（支持未来扩展）
    4. rename/replace 双向校验（源 + 目标）
    5. 项目根目录禁止写入
    """

    _enabled: bool = False
    _project_root: Optional[Path] = None
    _original_open = None
    _original_write_text = None
    _original_write_bytes = None
    _original_mkdir = None
    _original_touch = None
    _original_unlink = None
    _original_rename = None
    _original_replace = None

    @classmethod
    def enable(cls, project_root: str = "."):
        """
        启用路径守卫

        Args:
            project_root: 项目根目录路径
        """
        if cls._enabled:
            if cls._project_root and str(cls._project_root) != str(Path(project_root).resolve()):
                raise RuntimeError(
                    f"[PathGuard] 已在不同 project_root 下启用: {cls._project_root}\n"
                    f"新请求: {project_root}\n"
                    f"请先调用 PathGuard.disable() 再重新启用"
                )
            return

        cls._project_root = Path(project_root).resolve()
        cls._enabled = True
        cls._patch_io_operations()
        print(f"[PathGuard] 已启用 - 项目根目录: {cls._project_root}")
        print(f"[PathGuard] 允许写入: {ALLOWED_WRITE_PREFIXES}")
        print(f"[PathGuard] 冻结目录: {FROZEN_PREFIXES}")
        print(f"[PathGuard] 项目根目录: 禁止写入")

    @classmethod
    def disable(cls):
        """
        禁用路径守卫 - 恢复原始操作并清空引用
        """
        if not cls._enabled:
            return

        cls._restore_io_operations()

        # 清空 original 引用，防止误用
        cls._original_open = None
        cls._original_write_text = None
        cls._original_write_bytes = None
        cls._original_mkdir = None
        cls._original_touch = None
        cls._original_unlink = None
        cls._original_rename = None
        cls._original_replace = None

        cls._enabled = False
        cls._project_root = None
        print("[PathGuard] 已禁用")

    @classmethod
    def _resolve_path(cls, path) -> Path:
        """
        解析路径为绝对路径

        关键: 相对路径按 project_root 解析，而不是 CWD
        """
        # 确保 path 是 Path 对象
        if not isinstance(path, Path):
            path = Path(path)

        if path.is_absolute():
            return path.resolve()
        return (cls._project_root / path).resolve()

    @classmethod
    def _patch_io_operations(cls):
        """Patch 所有 I/O 操作"""
        # open 是模块级函数，直接替换
        cls._original_open = builtins.open
        builtins.open = cls._guarded_open

        # Path 实例方法：直接赋值普通函数（Python 会自动传递 self）
        cls._original_write_text = Path.write_text
        Path.write_text = cls._guarded_write_text

        cls._original_write_bytes = Path.write_bytes
        Path.write_bytes = cls._guarded_write_bytes

        cls._original_mkdir = Path.mkdir
        Path.mkdir = cls._guarded_mkdir

        cls._original_touch = Path.touch
        Path.touch = cls._guarded_touch

        cls._original_unlink = Path.unlink
        Path.unlink = cls._guarded_unlink

        cls._original_rename = Path.rename
        Path.rename = cls._guarded_rename

        cls._original_replace = Path.replace
        Path.replace = cls._guarded_replace

    @classmethod
    def _restore_io_operations(cls):
        """恢复原始 I/O 操作"""
        # 使用 is not None 判定，避免对象在布尔上下文下的异常行为
        if cls._original_open is not None:
            builtins.open = cls._original_open
        if cls._original_write_text is not None:
            # 恢复原始方法（去除 staticmethod 包装）
            Path.write_text = cls._original_write_text
        if cls._original_write_bytes is not None:
            Path.write_bytes = cls._original_write_bytes
        if cls._original_mkdir is not None:
            Path.mkdir = cls._original_mkdir
        if cls._original_touch is not None:
            Path.touch = cls._original_touch
        if cls._original_unlink is not None:
            Path.unlink = cls._original_unlink
        if cls._original_rename is not None:
            Path.rename = cls._original_rename
        if cls._original_replace is not None:
            Path.replace = cls._original_replace

    @classmethod
    def _is_write_mode(cls, mode: Optional[str]) -> bool:
        """判断 open 模式是否为写入模式"""
        if mode is None:
            return False
        return any(c in mode for c in ("w", "a", "x", "+"))

    @classmethod
    def _normalize_path(cls, path) -> Path:
        """标准化路径为 Path 对象，支持 str/Path/os.PathLike"""
        if isinstance(path, Path):
            return path
        if isinstance(path, os.PathLike):
            return Path(path)
        return Path(path)

    @classmethod
    def _check_path(cls, path: Path, operation: str):
        """
        检查路径是否允许写入（核心校验算法）

        判定逻辑:
        1. 相对路径按 project_root 解析
        2. 路径规范化（兼容 Windows）
        3. 使用"允许前缀集合"判定
        """
        if not cls._enabled:
            return

        if cls._project_root is None:
            raise RuntimeError(
                "[PathGuard] 未初始化 project_root，请先调用 PathGuard.enable(project_root)"
            )

        # 解析路径
        abs_path = cls._resolve_path(path)

        # 检查是否在 project_root 下
        try:
            rel_path = abs_path.relative_to(cls._project_root)
        except ValueError:
            raise SecurityError(
                f"[PathGuard] 禁止写入项目外部: {abs_path}\n"
                f"项目根目录: {cls._project_root}"
            )

        # 获取相对路径字符串并规范化（兼容 Windows）
        rel_path_str = str(rel_path)
        rel_path_str = normalize_path(rel_path_str)

        # 项目根目录禁止写入
        if not rel_path_str or rel_path_str == ".":
            raise SecurityError(
                f"[PathGuard] 禁止写入项目根目录\n"
                f"操作: {operation}\n"
                f"路径: {abs_path}"
            )

        # 使用允许前缀集合判定
        if is_allowed_write_path(rel_path_str):
            return  # 允许写入

        # 检查冻结目录
        if is_frozen_path(rel_path_str):
            raise SecurityError(
                f"[PathGuard] 禁止写入冻结目录: {rel_path_str}\n"
                f"操作: {operation}\n"
                f"路径: {abs_path}"
            )

        # 其他未授权目录
        raise SecurityError(
            f"[PathGuard] 禁止写入未授权目录: {rel_path_str}\n"
            f"操作: {operation}\n"
            f"路径: {abs_path}\n"
            f"允许写入: {ALLOWED_WRITE_PREFIXES}"
        )

    @classmethod
    def _guarded_open(cls, *args, **kwargs):
        """拦截 open 调用"""
        # 解析 mode
        mode = args[1] if len(args) > 1 else kwargs.get('mode')

        if cls._is_write_mode(mode):
            # 尝试从多个参数名获取路径
            path = None
            if args:
                path = args[0]
            if path is None:
                path = kwargs.get('file')
            if path is None:
                path = kwargs.get('filename')  # 兼容某些封装

            if path is not None:
                path_obj = cls._normalize_path(path)
                cls._check_path(path_obj, f"open(mode='{mode}')")
        return cls._original_open(*args, **kwargs)

    # 当赋值给 Path.write_text 时，这是作为实例方法
    # Python 会自动传递 self (Path 实例) 作为第一个参数
    def _guarded_write_text(self, *args, **kwargs):
        # self 是 Path 实例
        PathGuard._check_path(self, "write_text")
        return PathGuard._original_write_text(self, *args, **kwargs)

    def _guarded_write_bytes(self, *args, **kwargs):
        PathGuard._check_path(self, "write_bytes")
        return PathGuard._original_write_bytes(self, *args, **kwargs)

    def _guarded_mkdir(self, *args, **kwargs):
        PathGuard._check_path(self, "mkdir")
        return PathGuard._original_mkdir(self, *args, **kwargs)

    def _guarded_touch(self, *args, **kwargs):
        PathGuard._check_path(self, "touch")
        return PathGuard._original_touch(self, *args, **kwargs)

    def _guarded_unlink(self, *args, **kwargs):
        PathGuard._check_path(self, "unlink")
        return PathGuard._original_unlink(self, *args, **kwargs)

    def _guarded_rename(self, *args, **kwargs):
        """
        rename 双向校验: 源路径 + 目标路径

        P0 修复: 直接传 target_path 给 _check_path，让其内部统一解析
        """
        # self 是源 Path，args[0] 是目标路径
        PathGuard._check_path(self, "rename(source)")

        if args:
            target = args[0]
            if target is not None:
                target_path = PathGuard._normalize_path(target)
                PathGuard._check_path(target_path, "rename(target)")

        return PathGuard._original_rename(self, *args, **kwargs)

    def _guarded_replace(self, *args, **kwargs):
        """
        replace 双向校验: 源路径 + 目标路径

        P0 修复: 直接传 target_path 给 _check_path，让其内部统一解析
        """
        # self 是源 Path，args[0] 是目标路径
        PathGuard._check_path(self, "replace(source)")

        if args:
            target = args[0]
            if target is not None:
                target_path = PathGuard._normalize_path(target)
                PathGuard._check_path(target_path, "replace(target)")

        return PathGuard._original_replace(self, *args, **kwargs)


def init_path_guard(project_root: str = "."):
    """
    初始化路径守卫

    注意:
    - 只在 CLI worker 入口启用
    - 进程结束自动失效
    - 相对路径按 project_root 解析（不是 CWD）
    - 路径规范化（兼容 Windows）
    - rename/replace 操作双向校验
    - 项目根目录禁止写入
    - 禁止删除冻结目录

    Args:
        project_root: 项目根目录
    """
    if is_path_guard_enabled():
        PathGuard.enable(project_root)
