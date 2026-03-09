"""
LEE Executor - LLM Profile 加载器

管理 LLM 配置和客户端实例。

支持:
- 内置 Profile（Anthropic）
- YAML 配置文件（config/llm_config.yaml）
- 环境变量配置
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


def _get_package_config_path() -> Optional[Path]:
    """获取包内 config 目录路径"""
    from lee.data_path import with_builtin_config_dir

    try:
        return with_builtin_config_dir(lambda p: p)
    except Exception:
        return None


# 配置文件路径
_CONFIG_FILE_PATHS = []

# 首先尝试包内配置
pkg_config = _get_package_config_path()
if pkg_config:
    _CONFIG_FILE_PATHS.append(pkg_config / "llm_config.yaml")

# 然后尝试项目配置
_CONFIG_FILE_PATHS.append(Path.cwd() / "config" / "llm_config.yaml")


@dataclass
class LLMProfile:
    """LLM Profile 配置"""
    name: str
    provider: str  # "anthropic" | "openai"
    model: str
    api_key: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    base_url: Optional[str] = None
    timeout: int = 120


# 内置 Profile 定义
_BUILTIN_PROFILES: Dict[str, Dict[str, Any]] = {
    "default": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "claudebot": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "claude-sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "claude-opus": {
        "provider": "anthropic",
        "model": "claude-opus-4-20250514",
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    "claude-haiku": {
        "provider": "anthropic",
        "model": "claude-haiku-4-20250514",
        "temperature": 0.5,
        "max_tokens": 2048,
    },
    # 智谱 GLM Profile
    "zhipu": {
        "provider": "openai",  # GLM uses OpenAI-compatible API
        "model": "glm-4-flash",
        "temperature": 0.7,
        "max_tokens": 8000,
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",  # 或从配置文件读取
    },
    "glm": {
        "provider": "openai",
        "model": "glm-4-flash",
        "temperature": 0.7,
        "max_tokens": 8000,
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
    },
}

# 从配置文件加载的 Profile 缓存
_CONFIG_PROFILES: Optional[Dict[str, Dict[str, Any]]] = None


def _load_config_profiles() -> Dict[str, Dict[str, Any]]:
    """从配置文件加载 Profile"""
    global _CONFIG_PROFILES
    if _CONFIG_PROFILES is not None:
        return _CONFIG_PROFILES

    _CONFIG_PROFILES = {}

    for config_path in _CONFIG_FILE_PATHS:
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}

                for name, profile_config in config.items():
                    if isinstance(profile_config, dict) and profile_config.get("type") == "llm":
                        # 转换配置格式
                        provider = profile_config.get("provider", "custom")
                        # 所有使用 OpenAI 兼容 API 的 provider 统一为 openai
                        openai_compatible = {
                            "custom", "zhipu", "ollama", "deepseek",
                            "huawei_deepseek", "minimax", "azure",
                        }
                        if provider in openai_compatible:
                            provider = "openai"

                        _CONFIG_PROFILES[name] = {
                            "provider": provider,
                            "model": profile_config.get("model", ""),
                            "temperature": profile_config.get("temperature", 0.7),
                            "max_tokens": profile_config.get("max_tokens", 4096),
                            "base_url": profile_config.get("base_url"),
                            "api_key": profile_config.get("api_key"),  # 直接存储 API Key
                        }

                logger.debug(f"Loaded {len(_CONFIG_PROFILES)} profiles from {config_path}")
                break  # 只加载第一个找到的配置文件

            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

    return _CONFIG_PROFILES

# 缓存的客户端
_CLIENT_CACHE: Dict[str, Any] = {}


def load_profile(name: str) -> LLMProfile:
    """
    加载 LLM Profile

    优先级:
    1. 内置 Profile
    2. 配置文件 Profile (config/llm_config.yaml)
    3. 环境变量自定义 Profile

    Args:
        name: Profile 名称

    Returns:
        LLMProfile 实例

    Raises:
        ValueError: Profile 不存在或 API Key 未设置
    """
    config = None

    # 1. 首先尝试从配置文件加载（优先，因为包含实际的 API Key）
    config_profiles = _load_config_profiles()
    if name in config_profiles:
        config = config_profiles[name].copy()

    # 2. 尝试从内置 Profile 加载
    if config is None and name in _BUILTIN_PROFILES:
        config = _BUILTIN_PROFILES[name].copy()

    # 3. 尝试从环境变量构建自定义 Profile
    if config is None:
        prefix = f"LEE_LLM_{name.upper().replace('-', '_')}_"
        provider = os.environ.get(f"{prefix}PROVIDER")
        model = os.environ.get(f"{prefix}MODEL")

        if provider and model:
            config = {
                "provider": provider,
                "model": model,
                "temperature": float(os.environ.get(f"{prefix}TEMPERATURE", "0.3")),
                "max_tokens": int(os.environ.get(f"{prefix}MAX_TOKENS", "4096")),
            }

    if config is None:
        available = list(_BUILTIN_PROFILES.keys()) + list(_load_config_profiles().keys())
        raise ValueError(
            f"Unknown profile: {name}. "
            f"Available profiles: {available}"
        )

    # 获取 API Key（优先使用配置中直接提供的 key）
    api_key = config.get("api_key")
    if not api_key:
        # 尝试从指定的环境变量获取
        api_key_env = config.get("api_key_env")
        if api_key_env:
            api_key = os.environ.get(api_key_env, "")

        # 回退到默认的 provider 环境变量
        if not api_key:
            api_key = _get_api_key(config["provider"], required=False)

        if not api_key:
            env_var = api_key_env or _get_default_api_key_env(config["provider"])
            raise ValueError(
                f"API key not found for profile '{name}'. "
                f"Set {env_var} environment variable or configure api_key in config file."
            )

    return LLMProfile(
        name=name,
        provider=config["provider"],
        model=config["model"],
        api_key=api_key,
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        base_url=config.get("base_url"),
        timeout=config.get("timeout", 120),
    )


def _get_default_api_key_env(provider: str) -> str:
    """获取 provider 对应的默认 API Key 环境变量名"""
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    return env_map.get(provider, f"{provider.upper()}_API_KEY")


def _get_api_key(provider: str, required: bool = True) -> str:
    """
    获取 API Key

    Args:
        provider: 提供商名称
        required: 是否必须存在，为 False 时不抛异常

    Returns:
        API Key（可能为空字符串如果 required=False）

    Raises:
        ValueError: API Key 未设置（仅当 required=True）
    """
    env_var = _get_default_api_key_env(provider)
    api_key = os.environ.get(env_var, "")

    if not api_key and required:
        raise ValueError(
            f"{env_var} environment variable not set. "
            f"Please set it with: export {env_var}='your-key'"
        )

    return api_key


def get_client(profile: LLMProfile) -> Any:
    """
    获取 LLM Client（带缓存）

    Args:
        profile: LLM Profile

    Returns:
        LLM Client 实例

    Raises:
        ValueError: 不支持的 provider
        ImportError: 依赖未安装
    """
    cache_key = f"{profile.provider}:{profile.api_key[:8]}"

    if cache_key in _CLIENT_CACHE:
        return _CLIENT_CACHE[cache_key]

    if profile.provider == "anthropic":
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Run: pip install anthropic"
            )

        client = Anthropic(
            api_key=profile.api_key,
            base_url=profile.base_url,
            timeout=profile.timeout,
        )
        _CLIENT_CACHE[cache_key] = client
        return client

    elif profile.provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Run: pip install openai"
            )

        client = OpenAI(
            api_key=profile.api_key,
            base_url=profile.base_url,
            timeout=profile.timeout,
        )
        _CLIENT_CACHE[cache_key] = client
        return client

    else:
        raise ValueError(f"Unsupported provider: {profile.provider}")


def clear_client_cache() -> None:
    """清除客户端缓存"""
    _CLIENT_CACHE.clear()


def list_profiles() -> list[str]:
    """列出所有可用的 Profile（内置 + 配置文件）"""
    profiles = set(_BUILTIN_PROFILES.keys())
    profiles.update(_load_config_profiles().keys())
    return sorted(profiles)
