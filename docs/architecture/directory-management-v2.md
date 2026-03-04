# 目录管理统一方案 v2.0 (第八修订版 - 最终版)

## 1. 问题定义

### 1.1 现状

- `dirs.yaml` 定义了目录结构，但未被实际使用
- `.artifacts` 和 `.workflow` 在代码中硬编码 (共 43 处)
- 统一入口存在，但团队没有被强制走入口

### 1.2 根因分析

| 根因 | 描述 |
|------|------|
| 路径是"随手可写"的字符串 | 业务层可以拿到裸字符串路径，随意拼接 |
| 统一模块"可选用" | `DirectoryStructureConfig` 存在但未被调用 |
| 缺乏违例检测 | 没有工程护栏阻止硬编码 |
| 单例设计导致状态污染 | 多项目/多工作区/测试并行时会出问题 |

---

## 2. 方案架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     方案架构 - 三道门                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│   │  扫描止血   │ →  │  静态门禁   │ →  │  运行时门禁 │     │
│   │  (债务清单) │    │    (CI)     │    │  (I/O Guard)│     │
│   └─────────────┘    └─────────────┘    └─────────────┘     │
│                            │                  │               │
│                            ↓                  ↓               │
│   ┌─────────────────────────────────────────────────────┐     │
│   │           统一路径服务层 (PathConfig)                │     │
│   │   - 可注入设计（不依赖单例）                         │     │
│   │   - WorkflowContext 集成                            │     │
│   │   - 类型化路径对象                                  │     │
│   └─────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心修订点（第八修订 - 最终版）

> **第八修订说明**：修复了 3 个潜在翻车点（P0×1 + P1×2），最小改动但显著提升稳定性。

### 3.1 修订 1: path_policy.py - 统一规则 + Windows 兼容

**修订方案**:
```python
# src/lee/orchestrator/core/path_policy.py

"""
目录策略定义 - SSOT

PathConfig 和 PathGuard 共用此策略定义
"""

from typing import FrozenSet

# 工具目录定义
TOOL_DIRECTORIES: FrozenSet[str] = frozenset({
    ".artifacts",
    ".workflow",
    ".project",
})

# 允许写入的路径前缀集合 (统一使用正斜杠，兼容 Windows)
ALLOWED_WRITE_PREFIXES: FrozenSet[str] = frozenset({
    ".artifacts/",
    ".workflow/",
    "outputs/",
})

# 冻结目录前缀集合 (禁止写入/删除)
FROZEN_PREFIXES: FrozenSet[str] = frozenset({
    "contracts/",
    "src/",
    "specs/",
})


def normalize_path(path: str) -> str:
    """
    规范化路径为 POSIX 格式（正斜杠）

    确保跨平台一致性：Windows 反斜杠 → 正斜杠
    """
    return path.replace("\\", "/")


def is_allowed_write_path(rel_path: str) -> bool:
    """
    判断相对路径是否允许写入

    判定逻辑:
    1. 先规范化路径（兼容 Windows）
    2. 统一检查：前缀匹配 或 根目录本身匹配
    """
    # 规范化路径（兼容 Windows）
    normalized = normalize_path(rel_path)

    # 统一检查：前缀匹配 + 根目录本身匹配
    for prefix in ALLOWED_WRITE_PREFIXES:
        root = prefix.rstrip("/")  # 去掉末尾斜杠得到根目录名
        # 检查前缀匹配 或 根目录本身匹配
        if normalized.startswith(prefix) or normalized == root:
            return True

    return False


def is_frozen_path(rel_path: str) -> bool:
    """
    判断路径是否在冻结目录

    判定逻辑:
    1. 先规范化路径（兼容 Windows）
    2. 统一检查：前缀匹配 或 根目录本身匹配
    """
    # 规范化路径（兼容 Windows）
    normalized = normalize_path(rel_path)

    # 统一检查：前缀匹配 + 根目录本身匹配
    for prefix in FROZEN_PREFIXES:
        root = prefix.rstrip("/")  # 去掉末尾斜杠得到根目录名
        # 检查前缀匹配 或 根目录本身匹配
        if normalized.startswith(prefix) or normalized == root:
            return True

    return False


def is_dev_mode() -> bool:
    """判断是否在 dev 模式"""
    import os
    value = os.getenv("LEE_DEV_MODE", "").lower()
    return value in ("1", "true")


def is_ci_mode() -> bool:
    """判断是否在 CI 模式"""
    import os
    value = os.getenv("CI", "").lower()
    return value in ("1", "true")


def is_path_guard_enabled() -> bool:
    """判断是否启用 PathGuard"""
    return is_dev_mode() or is_ci_mode()
```

### 3.2 修订 2: PathGuard - Windows 兼容 + kwargs 增强

```python
# src/lee/orchestrator/core/io_guard.py

import os
import sys
from pathlib import Path
from functools import wraps
from typing import Optional

# 导入统一目录策略
from .path_policy import (
    ALLOWED_WRITE_PREFIXES,
    FROZEN_PREFIXES,
    is_allowed_write_path,
    is_frozen_path,
    is_path_guard_enabled,
    normalize_path,
)


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

    _enabled = False
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
        """启用路径守卫"""
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
        """禁用路径守卫 - 恢复原始操作并清空引用"""
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
    def _resolve_path(cls, path: Path) -> Path:
        """
        解析路径为绝对路径

        关键: 相对路径按 project_root 解析，而不是 CWD
        """
        if path.is_absolute():
            return path.resolve()
        return (cls._project_root / path).resolve()

    @classmethod
    def _patch_io_operations(cls):
        """Patch 所有 I/O 操作"""
        cls._original_open = builtins.open
        builtins.open = cls._guarded_open

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
    def _normalize_path(cls, path) -> Path:
        """标准化路径为 Path 对象，支持 str/Path/os.PathLike"""
        if isinstance(path, Path):
            return path
        if isinstance(path, os.PathLike):
            return Path(path)
        return Path(path)

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

    @classmethod
    def _guarded_write_text(cls, self, *args, **kwargs):
        cls._check_path(self, "write_text")
        return cls._original_write_text(self, *args, **kwargs)

    @classmethod
    def _guarded_write_bytes(cls, self, *args, **kwargs):
        cls._check_path(self, "write_bytes")
        return cls._original_write_bytes(self, *args, **kwargs)

    @classmethod
    def _guarded_mkdir(cls, self, *args, **kwargs):
        cls._check_path(self, "mkdir")
        return cls._original_mkdir(self, *args, **kwargs)

    @classmethod
    def _guarded_touch(cls, self, *args, **kwargs):
        cls._check_path(self, "touch")
        return cls._original_touch(self, *args, **kwargs)

    @classmethod
    def _guarded_unlink(cls, self, *args, **kwargs):
        cls._check_path(self, "unlink")
        return cls._original_unlink(self, *args, **kwargs)

    @classmethod
    def _guarded_rename(cls, self, *args, **kwargs):
        """rename 双向校验: 源路径 + 目标路径"""
        cls._check_path(self, "rename(source)")

        if args:
            target = args[0]
            if target is not None:
                target_path = cls._normalize_path(target)
                # 直接传 target_path 给 _check_path，让其内部统一解析
                # 不要传提前 resolve 过的 target_abs，保持路径解析逻辑一致性
                cls._check_path(target_path, "rename(target)")

        return cls._original_rename(self, *args, **kwargs)

    @classmethod
    def _guarded_replace(cls, self, *args, **kwargs):
        """replace 双向校验: 源路径 + 目标路径"""
        cls._check_path(self, "replace(source)")

        if args:
            target = args[0]
            if target is not None:
                target_path = cls._normalize_path(target)
                # 直接传 target_path 给 _check_path，让其内部统一解析
                # 不要传提前 resolve 过的 target_abs，保持路径解析逻辑一致性
                cls._check_path(target_path, "replace(target)")

        return cls._original_replace(self, *args, **kwargs)


class SecurityError(Exception):
    """安全异常 - 路径守卫触发"""
    pass


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


import builtins
import os
```

---

## 4. 分阶段实施

| Phase | 内容 | 工期 | 优先级 |
|-------|------|-----|--------|
| Phase 0 | 扫描止血 - 输出债务清单 | 0.5天 | 必选 |
| Phase 1 | CI 门禁 - regex + 白名单 | 0.5天 | 必选 |
| Phase 2 | PathConfig - 可注入设计 + 去除 dirs.yaml 依赖 | 1天 | 必选 |
| Phase 3 | 硬编码替换 - 核心模块 | 1天 | 必选 |
| Phase 4 | I/O Guard - 运行时门禁 + patch 扩展 | 0.5天 | 必选 |
| Phase 5 | 顺滑 API + 测试 | 1天 | 推荐 |
| Phase 6 | 黑产物扫描 (可选) | 1天 | 可选 |

---

## 5. 验收标准

### 5.1 基础验收

- [ ] 硬编码位置清单输出
- [ ] CI 门禁规则生效
- [ ] PathConfig 可正常导入使用
- [ ] 硬编码替换完成
- [ ] 现有测试通过

### 5.2 反复发验收

- [ ] **CI 门禁**: 新增硬编码路径 CI 必 fail
- [ ] **运行时门禁**: 绕过 PathConfig 写文件运行时必 fail

### 5.3 稳定性验收

- [ ] 多项目并行运行不串路径
- [ ] 测试并行执行无状态污染
- [ ] 重复启用检查正常工作
- [ ] disable 后 original 引用已清空
- [ ] **Windows 路径兼容** (`outputs\temp.txt` 正确识别为允许)

### 5.4 负向用例验收

- [ ] `open("src/test.py", "w")` 必须抛 `SecurityError`
- [ ] `open("contracts/xxx.yaml", "r")` 必须允许
- [ ] `open("contracts/xxx.yaml", "w")` 必须抛 `SecurityError`
- [ ] `Path("outputs/temp.txt").write_text("x")` 必须允许
- [ ] 写入项目外部路径必须抛 `SecurityError`
- [ ] 写入项目根目录必须抛 `SecurityError`
- [ ] `Path("src/file").touch()` 必须抛 `SecurityError`
- [ ] `Path("src/file").unlink()` 必须抛 `SecurityError`
- [ ] `Path("outputs/a.txt").rename("src/a.txt")` 必须抛 `SecurityError`
- [ ] `Path("outputs/a.txt").replace("src/a.txt")` 必须抛 `SecurityError`
- [ ] `Path("outputs/a.txt").rename("/tmp/a.txt")` 必须抛 `SecurityError`
- [ ] **CWD != project_root** 时: `Path("outputs/a.txt").write_text("x")` 仍然允许
- [ ] **os.PathLike** 自定义路径写入也会被拦截
- [ ] **Windows 路径**: `Path(r"outputs\file.txt").write_text()` 允许
- [ ] **Windows 路径**: `Path(r"src\file.txt").write_text()` 禁止

---

## 6. 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 测试并行状态污染 | P0 | 使用 `lru_cache` 按 root 缓存，PathConfig 内部状态不可变 |
| 相对路径按 CWD 解析 | P0 | 改为按 project_root 解析 |
| rename/replace 绕过 | P0 | 双向校验 + 显式目标路径解析 |
| 项目根目录写入未明确 | P0 | 明确禁止，写入抛 SecurityError |
| 第一层目录判定限制扩展 | P0 | 升级为"允许前缀集合" |
| Windows 路径兼容 | P0 | 路径规范化 (normalize_path: 反斜杠 → 正斜杠) |
| 目录常量重复漂移 | P1 | 统一 path_policy.py，共用常量 |
| Env 变量校验过宽 | P1 | 只接受 "1"/"true"/"True" |
| unlink 语义不清 | P1 | 明确禁止删除冻结目录 |
| monkey patch 副作用 | P1 | 文档明确：仅 CLI worker 入口启用 |
| open 低层 fd 漏拦 | P2 | 文档说明 PathGuard 非安全沙箱 |

---

## 7. 最终合并 checklist

- [ ] `_check_path` 使用 `normalize_path()` 规范化路径
- [ ] 在 Windows + Linux 各跑一遍核心负向用例
- [ ] path_policy 的"单一权威规则"已收敛（只保留 prefix 集合）
- [x] **P0**: `rename/replace(target)` 传 `target_path` 而非 `target_abs` 给 `_check_path`
- [x] **P1-1**: `_restore_io_operations` 使用 `is not None` 判定
- [x] **P1-2**: `path_policy.py` 根目录匹配逻辑收敛为统一检查（单次循环）

---

## 8. 附录

### 8.1 启用边界约束

```
PathGuard 启用约束:
- 仅在 CLI worker 入口启用
- 进程结束自动失效
- 禁止在长生命周期进程内来回切换 project_root
- 如需多项目隔离，使用多进程
```

### 8.2 目录策略 SSOT

```
src/lee/orchestrator/core/path_policy.py
    ↓
PathConfig + PathGuard 共用
```

### 8.3 清理策略

- 冻结目录 (`contracts`, `src`, `specs`) 禁止删除
- 如需清理，走专用 `cleanup workflow`（带 gate/白名单）
- 临时产物 (`outputs`) 由用户自行管理
