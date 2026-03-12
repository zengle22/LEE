"""
LLM Executor - 直接调用大模型 API

支持多种 Provider：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Azure OpenAI
- 其他兼容 OpenAI API 的服务
- 自定义反代服务（如 antigravity, 智谱 GLM）
- MiniMax (通过 Anthropic 兼容 API）
"""
import os
import asyncio
import aiohttp
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


def _get_package_config_path() -> Optional[Path]:
    """获取包内 config 目录路径（使用回调确保生命周期）"""
    from lee.data_path import with_builtin_config_dir

    try:
        return with_builtin_config_dir(lambda p: p)
    except Exception:
        return None


# 自动加载 .env 文件
# 注意：这里仍然需要 project_root 来加载 .env，这是用户项目相关的配置
# 不应该从包内读取
try:
    from dotenv import load_dotenv
    # .env 文件应该从项目根目录加载，由调用方传入 project_root
    # 这里不自动加载，改为在调用时由外部传入
except ImportError:
    pass  # 没有安装 python-dotenv 时忽略


class LLMConfig:
    """LLM 配置管理"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 LLM 配置

        Args:
            config_path: 配置文件路径，默认为包内 config/llm_config.yaml
        """
        self.config_path = self._resolve_config_path(config_path)
        self._load_project_env(self.config_path)
        self.configs = self._load_config() if self.config_path else {}

    def _resolve_config_path(self, config_path: Optional[str]) -> Optional[Path]:
        """解析实际要读取的 llm_config.yaml 路径。"""
        candidates: List[Path] = []
        if config_path:
            candidates.append(Path(config_path))
        else:
            pkg_config = _get_package_config_path()
            if pkg_config:
                candidates.append(pkg_config / "llm_config.yaml")
            candidates.append(Path.cwd() / "config" / "llm_config.yaml")

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0] if candidates else None

    def _load_project_env(self, config_path: Optional[Path]) -> None:
        """尽量从当前项目加载 .env，避免 profile 解析依赖外部进程预先注入环境变量。"""
        if "load_dotenv" not in globals():
            return

        candidates: List[Path] = [Path.cwd() / ".env"]
        if config_path:
            candidates.append(config_path.parent.parent / ".env")

        seen = set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists():
                load_dotenv(resolved, override=False)
                break

    def _load_config(self) -> Dict[str, Any]:
        """加载 YAML 配置文件"""
        if not self.config_path or not self.config_path.exists():
            return {}

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get_config(self, profile: str = "default") -> Dict[str, Any]:
        """
        获取指定配置

        Args:
            profile: 配置名称（default, antigravity, zhipu, agent.prd, agent.dev）

        Returns:
            配置字典
        """
        config = self.configs.get(profile, {})

        # 环境变量替换
        config = self._resolve_env_vars(config)

        # 通用环境变量覆盖（避免在配置文件中硬编码密钥）
        overrides = {
            "LLM_BASE_URL": "base_url",
            "LLM_API_KEY": "api_key",
            "LLM_MODEL": "model",
            "LLM_TEMPERATURE": "temperature",
            "LLM_MAX_TOKENS": "max_tokens",
            "LLM_PROVIDER": "provider",
        }
        for env_key, cfg_key in overrides.items():
            env_val = os.getenv(env_key)
            if env_val is None:
                continue
            if cfg_key in ("temperature", "max_tokens"):
                try:
                    config[cfg_key] = float(env_val) if cfg_key == "temperature" else int(env_val)
                except ValueError:
                    config[cfg_key] = env_val
            else:
                config[cfg_key] = env_val

        return config

    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解析环境变量"""
        resolved = {}

        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # 格式: ${VAR:-default}
                # 去掉 ${ 和 }
                env_expr = value[2:-1]
                # 检查是否包含默认值（:-）
                if ":-" in env_expr:
                    env_var, default_val = env_expr.split(":-", 1)
                    # 使用环境变量，如果不存在则使用默认值
                    resolved[key] = os.getenv(env_var, default_val)
                else:
                    # 没有默认值，直接使用环境变量
                    env_var = env_expr
                    resolved[key] = os.getenv(env_var, value)
            else:
                resolved[key] = value

        return resolved

    def get_default_profile(self) -> str:
        """读取可用的默认 profile，坏配置会自动回退到首个可用项。"""
        configured = self.configs.get("default_profile")
        if isinstance(configured, str) and configured.strip():
            candidate = configured.strip()
            if self._has_usable_api_key(self.get_config(candidate)):
                return candidate

        for candidate in ("deepseek", "qwen", "default"):
            if self._has_usable_api_key(self.get_config(candidate)):
                return candidate

        return "default"

    @staticmethod
    def _has_usable_api_key(config: Dict[str, Any]) -> bool:
        api_key = str(config.get("api_key") or "").strip()
        return bool(api_key) and not (api_key.startswith("${") and api_key.endswith("}"))


class LLMExecutor:
    """
    LLM 执行器

    执行 LLM 相关任务（如代码生成、文本分析等）

    配置文件: flowcore/engines/llm/config.yaml
    """

    def __init__(self, profile: Optional[str] = None, config_path: Optional[str] = None,
                 fallback_providers: Optional[List[str]] = None):
        """
        初始化 LLM 执行器

        Args:
            profile: 配置文件名称（未指定时读取 config/llm_config.yaml 的 default_profile）
            config_path: 配置文件路径
            fallback_providers: 备用 provider 列表，当主 provider 失败时自动切换
        """
        self.config_manager = LLMConfig(config_path)
        self.profile = (profile or os.getenv("LLM_PROFILE") or self.config_manager.get_default_profile()).strip()
        self.config = self.config_manager.get_config(self.profile)

        # 加载全局 fallback 配置
        self._fallback_providers = fallback_providers or self._load_fallback_providers()

        # 验证必要配置
        if not self.config.get("api_key"):
            raise ValueError(f"LLM config '{profile}' missing api_key")

    def _load_fallback_providers(self) -> List[str]:
        """从配置文件或环境变量加载 fallback providers"""
        # 优先从环境变量读取
        env_fallback = os.getenv("LLM_FALLBACK_PROVIDERS", "")
        if env_fallback:
            return [p.strip() for p in env_fallback.split(",") if p.strip()]

        # 其次从配置文件读取
        global_config = self.config_manager.configs
        fallback = global_config.get("fallback_providers", [])
        if isinstance(fallback, list):
            return [str(p) for p in fallback if p]
        return []

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 LLM 任务，支持 Fallback 机制

        Args:
            input_data: 应包含 prompt, system_message 等字段

        Returns:
            包含 generated_text, tokens_used 等字段
        """
        prompt = input_data.get("prompt", "")
        system_message = input_data.get("system_message", "You are a helpful assistant.")

        # 从 input_data 获取参数（允许覆盖配置）
        temperature = input_data.get("temperature", self.config.get("temperature", 0.7))
        max_tokens = input_data.get("max_tokens", self.config.get("max_tokens", 4000))

        import time as _time
        call_start = _time.monotonic()

        # 收集所有尝试的 provider 信息
        attempts_log = []

        # 主 provider + fallback providers
        all_providers = [self.profile] + [p for p in self._fallback_providers if p != self.profile]

        last_error = None
        for provider_idx, provider_name in enumerate(all_providers):
            try:
                # 如果是 fallback provider，需要重新加载配置
                if provider_idx > 0:
                    print(f"[LLM Executor] Trying fallback provider: {provider_name}")
                    
                    # ⚠️ 特殊告警：使用昂贵的 deepseek 官方 API
                    if provider_name == "deepseek":
                        print(f"\n⚠️ ⚠️ ⚠️ COST ALERT ⚠️ ⚠️ ⚠️")
                        print(f"[LLM Executor] Using EXPENSIVE deepseek official API as fallback!")
                        print(f"[LLM Executor] Huawei deepseek failed, falling back to costly provider.")
                        print(f"⚠️ ⚠️ ⚠️ COST ALERT ⚠️ ⚠️ ⚠️\n")
                    
                    self.profile = provider_name
                    self.config = self.config_manager.get_config(provider_name)
                    # 验证必要配置
                    if not self.config.get("api_key"):
                        print(f"[LLM Executor] Skipping {provider_name}: no api_key")
                        continue

                # 调用 LLM API
                response = await self._call_with_fallback(
                    self._call_llm,
                    system_message,
                    prompt,
                    provider_name
                )

                call_duration = _time.monotonic() - call_start

                # v3.2: 支持增强返回（dict）和旧格式（str）
                if isinstance(response, dict):
                    response_text = response.get("content", "")
                    model_used = response.get("model", self.config.get("model", "unknown"))
                    input_tokens = response.get("input_tokens", 0)
                    output_tokens = response.get("output_tokens", 0)
                    stop_reason = response.get("stop_reason")
                else:
                    response_text = response
                    model_used = self.config.get("model", "unknown")
                    input_tokens = 0
                    output_tokens = 0
                    stop_reason = None

                return {
                    "generated_text": response_text,
                    "model": model_used,
                    "provider": self.config.get("provider", "custom"),
                    "profile": provider_name,
                    "tokens_used": input_tokens + output_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "duration_seconds": round(call_duration, 3),
                    "stop_reason": stop_reason,
                    "status": "completed",
                    "attempts": attempts_log,
                }

            except Exception as e:
                last_error = str(e)
                attempts_log.append({
                    "profile": provider_name,
                    "error": last_error,
                })
                print(f"[LLM Executor] Provider {provider_name} failed: {last_error}")

                # 如果还有 fallback providers，继续尝试
                if provider_idx < len(all_providers) - 1:
                    continue
                # 否则返回错误

        # 所有 provider 都失败了
        return {
            "generated_text": "",
            "error": f"All providers failed. Last error: {last_error}",
            "status": "failed",
            "attempts": attempts_log,
        }

    async def _call_with_retry(
        self,
        call_func,
        system_prompt: str,
        user_message: str,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> str:
        """
        带重试的 LLM API 调用（保留兼容旧代码）

        处理：
        - HTTP 429 (Too Many Requests) - 速率限制
        - HTTP 500/502/503/504 - 服务器错误
        - 网络超时
        """
        return await self._call_with_fallback(call_func, system_prompt, user_message,
                                              provider_name=self.profile,
                                              max_retries=max_retries,
                                              initial_delay=initial_delay)

    async def _call_with_fallback(
        self,
        call_func,
        system_prompt: str,
        user_message: str,
        provider_name: str = "default",
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> str:
        """
        带重试和退避的 LLM API 调用

        处理：
        - HTTP 429 (Too Many Requests) - 速率限制（触发更长的等待时间）
        - HTTP 500/502/503/504 - 服务器错误
        - 网络超时
        """
        import random

        last_error = None

        for attempt in range(max_retries):
            try:
                return await call_func(system_prompt, user_message)

            except aiohttp.ClientResponseError as e:
                last_error = e

                # 检查是否为可重试的瞬态错误
                if e.status in [429, 500, 502, 503, 504]:
                    if attempt < max_retries - 1:
                        # 429 错误需要更长的等待时间
                        if e.status == 429:
                            # 429 错误：等待更长时间（30-60秒）
                            delay = initial_delay * (4 ** attempt) + random.uniform(10, 30)
                            delay = min(delay, 60)  # 最多等待 60 秒
                            print(f"[LLM Executor] Rate limit (429) on {provider_name}, retrying in {delay:.1f}s...")
                        else:
                            # 其他错误：指数退避 + 抖动
                            delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                            delay = min(delay, 30)  # 最多等待 30 秒
                            print(f"[LLM Executor] API error {e.status} on {provider_name} (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")

                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise ValueError(f"LLM API failed after {max_retries} attempts. Last error: {e.status} {e.message}")
                else:
                    # 非瞬态错误，不重试
                    raise ValueError(f"LLM API error: {e.status} {e.message}")

        raise ValueError(f"LLM API call failed: {str(last_error)}")

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str
    ) -> str:
        """调用 LLM API（兼容 OpenAI/Anthropic/MiniMax 格式）"""
        api_key = self.config.get("api_key")
        base_url = self.config.get("base_url", "https://api.openai.com/v1")
        model = self.config.get("model", "gpt-4")
        temperature = self.config.get("temperature", 0.7)
        max_tokens = self.config.get("max_tokens", 4000)
        provider = self.config.get("provider", "custom")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # 处理不同 provider 的 URL 格式
        url = base_url.rstrip("/")
        if provider == "minimax":
            # MiniMax Anthropic 兼容 API 使用 /messages 端点
            if not url.endswith("/messages"):
                url = f"{url}/messages"
        elif not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"

        # 使用配置中的 timeout，环境变量优先
        timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", self.config.get("timeout", "300")))
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                headers=headers,
                json=payload
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

                # v3.2: 返回完整 API 响应元数据
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return {
                    "content": content,
                    "model": data.get("model", model),
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "stop_reason": data["choices"][0].get("finish_reason"),
                }

    def get_info(self) -> Dict[str, Any]:
        """获取执行器信息"""
        return {
            "type": "llm",
            "profile": self.profile,
            "provider": self.config.get("provider", "custom"),
            "base_url": self.config.get("base_url", ""),
            "model": self.config.get("model", ""),
        }
