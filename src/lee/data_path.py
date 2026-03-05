"""
LEE 框架路径解析模块

提供统一的资源路径访问接口，支持：
- 包内资源（builtin）访问
- 工作区发现
- Spec 解析优先级控制
- dev/prod 模式切换

使用 importlib.resources 访问包内资源，确保：
- zip 安装时正常工作
- 资源不会因 as_file 临时目录被清理而失效
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files, as_file
from pathlib import Path
from typing import Callable, TypeVar, Literal, Optional
from datetime import datetime

T = TypeVar("T")

# ==================== 核心 API ====================

def get_builtin_spec_traversable():
    """
    获取包内 spec-global Traversable（不落盘）

    Returns:
        Traversable: 可用于读取 YAML/MD 等资源
    """
    return files("lee").joinpath("data/spec-global")


def get_builtin_config_traversable():
    """
    获取包内 config Traversable

    Returns:
        Traversable: 可用于读取配置文件
    """
    return files("lee").joinpath("config")


def with_builtin_spec_root(fn: Callable[[Path], T]) -> T:
    """
    在真实 spec-root 路径上执行回调

    使用 as_file 将 Traversable 展开为真实文件系统路径，
    确保回调执行期间路径有效。

    Args:
        fn: 接受 Path 参数的回调函数

    Returns:
        回调函数的返回值
    """
    t = get_builtin_spec_traversable()
    with as_file(t) as p:
        return fn(p)


def with_builtin_config_dir(fn: Callable[[Path], T]) -> T:
    """
    在真实 config 目录上执行回调

    Args:
        fn: 接受 Path 参数的回调函数

    Returns:
        回调函数的返回值
    """
    t = get_builtin_config_traversable()
    with as_file(t) as p:
        return fn(p)


# ==================== 统一 Resolver ====================

@dataclass
class SpecResolveInput:
    """
    Spec 解析输入

    Attributes:
        workspace_root: 工作区根目录
        cli_spec_root: CLI 参数 --spec-root
        env_spec_root: 环境变量 LEE_SPEC_ROOT
        config_spec_root: .lee/config.yaml 中的 spec_root
        lock_mode: .lee/lee.lock 中的 mode
        lock_lee_src: .lee/lee.lock 中的 lee_src
    """
    workspace_root: Path
    cli_spec_root: Optional[str] = None
    env_spec_root: Optional[str] = None
    config_spec_root: Optional[str] = None
    lock_mode: Optional[str] = None
    lock_lee_src: Optional[str] = None


@dataclass
class SpecResolveResult:
    """
    Spec 解析结果

    Attributes:
        source: 命中来源 (cli/env/config/builtin/dev)
        kind: 资源类型 (builtin/filesystem)
        value: 原始值
        resolved: 解析后的路径（仅 kind=filesystem 时有效）
    """
    source: Literal["cli", "env", "config", "builtin", "dev"]
    kind: Literal["builtin", "filesystem"]
    value: str
    resolved: Optional[Path] = None

    def with_path(self, fn: Callable[[Path], T]) -> T:
        """
        如果需要真实 Path，使用此回调

        - builtin: 使用 with_builtin_spec_root 展开
        - filesystem: 使用 resolved 路径

        Args:
            fn: 接受 Path 参数的回调函数

        Returns:
            回调函数的返回值

        Raises:
            ValueError: 当 filesystem 类型但 resolved 为空时
        """
        if self.kind == "builtin":
            return with_builtin_spec_root(fn)
        elif self.resolved:
            return fn(self.resolved)
        else:
            raise ValueError("Resolved filesystem path is missing")


def resolve_spec(input: SpecResolveInput) -> SpecResolveResult:
    """
    统一 Spec 解析算法

    优先级（从高到低）：
    1. CLI 参数 --spec-root
    2. 环境变量 LEE_SPEC_ROOT
    3. .lee/config.yaml 的 spec_root
    4. dev 模式（mode=dev 且未指定 spec_root 时）
    5. builtin（包内默认）

    ⚠️ 重要：mode=dev 时，path_base 会切换为 lee_src，
    因此 CLI/ENV/config 的相对路径也会相对于 lee_src 解析。

    Args:
        input: 解析输入参数

    Returns:
        SpecResolveResult: 解析结果
    """
    # 0. 确定 path_base（相对路径解析基准）
    path_base = input.workspace_root
    if input.lock_mode == "dev" and input.lock_lee_src:
        path_base = Path(input.lock_lee_src)

    # 1. CLI
    if input.cli_spec_root:
        return _resolve_value(input.cli_spec_root, path_base, "cli")

    # 2. ENV
    if input.env_spec_root:
        return _resolve_value(input.env_spec_root, path_base, "env")

    # 3. config
    if input.config_spec_root:
        return _resolve_value(input.config_spec_root, path_base, "config")

    # 4. dev 模式：默认使用 <lee_src>/spec-global
    if input.lock_mode == "dev" and input.lock_lee_src:
        dev_spec = Path(input.lock_lee_src) / "spec-global"
        return SpecResolveResult(
            source="dev",
            kind="filesystem",
            value=str(dev_spec),
            resolved=dev_spec.resolve()
        )

    # 5. builtin
    return SpecResolveResult(
        source="builtin",
        kind="builtin",
        value="builtin"
    )


def _resolve_value(value: str, path_base: Path, source: str) -> SpecResolveResult:
    """
    解析单个 spec_root 值（相对路径基准可配置）

    Args:
        value: spec_root 配置值
        path_base: 相对路径解析基准目录
        source: 来源标识

    Returns:
        SpecResolveResult: 解析结果
    """
    # builtin 语义
    if value in ("", "builtin", "@builtin"):
        return SpecResolveResult(source=source, kind="builtin", value="builtin")

    # 相对路径 → 相对于 path_base
    p = Path(value)
    if not p.is_absolute():
        resolved = (path_base / p).resolve()
        return SpecResolveResult(
            source=source,
            kind="filesystem",
            value=value,
            resolved=resolved
        )

    # 绝对路径
    return SpecResolveResult(
        source=source,
        kind="filesystem",
        value=value,
        resolved=p.resolve()
    )


# ==================== Workspace 发现 ====================

def discover_workspace_root(
    cwd: Path,
    cli_project_dir: Optional[str] = None
) -> Path:
    """
    发现 workspace 根目录

    规则：
    1. CLI 参数 --project-dir（最高优先级）
    2. 向上查找 .lee/ 目录（含当前层）
    3. 退回 cwd（CLI 层应在 run 时检测无 .lee 并报错）

    Args:
        cwd: 当前工作目录
        cli_project_dir: CLI 参数 --project-dir

    Returns:
        Path: 工作区根目录
    """
    # 1. CLI 参数
    if cli_project_dir:
        return Path(cli_project_dir).resolve()

    # 2. 向上查找 .lee/ 目录（含当前层）
    current = cwd.resolve()
    for p in [current, *current.parents]:
        if (p / ".lee").is_dir():
            return p

    # 3. 退回 cwd（CLI 层应在 run 时检测无 .lee 并报错）
    return current


# ==================== Lee Lock 操作 ====================

@dataclass
class LeeLock:
    """Lee Lock 文件结构"""
    schema_version: int
    lee_version: str
    lee_install: Literal["pypi", "editable", "wheel"]
    mode: Literal["prod", "dev"]
    lee_src: Optional[str] = None
    initialized_at: Optional[str] = None


def load_lee_lock(workspace_root: Path) -> Optional[LeeLock]:
    """
    加载 .lee/lee.lock 文件

    Args:
        workspace_root: 工作区根目录

    Returns:
        LeeLock 对象或 None（文件不存在时）
    """
    import json

    lock_path = workspace_root / ".lee" / "lee.lock"
    if not lock_path.exists():
        return None

    with open(lock_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return LeeLock(
        schema_version=data.get("schema_version", 1),
        lee_version=data.get("lee_version", "unknown"),
        lee_install=data.get("lee_install", "pypi"),
        mode=data.get("mode", "prod"),
        lee_src=data.get("lee_src"),
        initialized_at=data.get("initialized_at")
    )


def create_lee_lock(
    workspace_root: Path,
    lee_version: str,
    mode: str = "prod",
    lee_src: Optional[str] = None,
    lee_install: str = "pypi"
) -> LeeLock:
    """
    创建 .lee/lee.lock 文件

    Args:
        workspace_root: 工作区根目录
        lee_version: LEE 版本号
        mode: 运行模式 (prod/dev)
        lee_src: 开发模式源码路径
        lee_install: 安装方式 (pypi/editable/wheel)

    Returns:
        LeeLock: 创建的 lock 对象
    """
    import json

    lock = LeeLock(
        schema_version=1,
        lee_version=lee_version,
        lee_install=lee_install,
        mode=mode,
        lee_src=lee_src,
        initialized_at=datetime.utcnow().isoformat() + "Z"
    )

    lock_path = workspace_root / ".lee" / "lee.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": lock.schema_version,
            "lee_version": lock.lee_version,
            "lee_install": lock.lee_install,
            "mode": lock.mode,
            "lee_src": lock.lee_src,
            "initialized_at": lock.initialized_at
        }, f, indent=2, ensure_ascii=False)

    return lock
