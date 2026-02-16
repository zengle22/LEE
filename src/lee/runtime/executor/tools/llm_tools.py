"""
LLM 调用工具

统一的 LLM 调用接口，支持 Anthropic 和 OpenAI。
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import time
import logging

from ..profiles.loader import load_profile, get_client

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    profile: str
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0
    raw_response: Optional[Dict] = None
    stop_reason: Optional[str] = None


def call_llm(
    profile: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLMResponse:
    """
    调用 LLM

    Args:
        profile: LLM Profile 名称
        messages: 消息列表（格式: [{"role": "user", "content": "..."}]）
        system: 系统提示（可选）
        temperature: 温度（覆盖 profile）
        max_tokens: 最大 token（覆盖 profile）

    Returns:
        LLM 响应

    Raises:
        ValueError: Profile 不存在或不支持的 provider
        Exception: LLM 调用失败
    """
    start_time = time.time()

    # 加载 Profile
    profile_config = load_profile(profile)

    # 获取 Client
    client = get_client(profile_config)

    # 根据 provider 调用不同的 API
    if profile_config.provider == "anthropic":
        return _call_anthropic(
            client=client,
            profile_config=profile_config,
            profile_name=profile,
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            start_time=start_time,
        )
    elif profile_config.provider == "openai":
        return _call_openai(
            client=client,
            profile_config=profile_config,
            profile_name=profile,
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            start_time=start_time,
        )
    else:
        raise ValueError(f"Unsupported provider: {profile_config.provider}")


def _call_anthropic(
    client: Any,
    profile_config: Any,
    profile_name: str,
    messages: List[Dict[str, str]],
    system: Optional[str],
    temperature: Optional[float],
    max_tokens: Optional[int],
    start_time: float,
) -> LLMResponse:
    """调用 Anthropic API"""
    # 过滤 system 消息，Anthropic 使用独立的 system 参数
    filtered_messages = []
    extracted_system = system

    for msg in messages:
        if msg.get("role") == "system":
            if extracted_system is None:
                extracted_system = msg.get("content", "")
        else:
            filtered_messages.append(msg)

    # 准备参数
    params: Dict[str, Any] = {
        "model": profile_config.model,
        "messages": filtered_messages,
        "max_tokens": max_tokens or profile_config.max_tokens or 4096,
    }

    if extracted_system:
        params["system"] = extracted_system

    if temperature is not None:
        params["temperature"] = temperature
    elif profile_config.temperature is not None:
        params["temperature"] = profile_config.temperature

    logger.debug(f"Calling Anthropic API with model: {profile_config.model}")

    # 调用 API
    response = client.messages.create(**params)

    # 解析响应
    input_tokens = 0
    output_tokens = 0
    if hasattr(response, "usage"):
        usage = response.usage
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)

    # 提取内容
    content = ""
    if hasattr(response, "content") and len(response.content) > 0:
        content = response.content[0].text

    # 停止原因
    stop_reason = getattr(response, "stop_reason", None)

    duration = time.time() - start_time

    logger.debug(
        f"Anthropic response: tokens={input_tokens}+{output_tokens}, "
        f"duration={duration:.2f}s"
    )

    return LLMResponse(
        content=content,
        model=profile_config.model,
        profile=profile_name,
        tokens_used=input_tokens + output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_seconds=duration,
        raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        stop_reason=stop_reason,
    )


def _call_openai(
    client: Any,
    profile_config: Any,
    profile_name: str,
    messages: List[Dict[str, str]],
    system: Optional[str],
    temperature: Optional[float],
    max_tokens: Optional[int],
    start_time: float,
) -> LLMResponse:
    """调用 OpenAI API"""
    # OpenAI 使用 messages 中的 system role
    final_messages = []

    if system:
        final_messages.append({"role": "system", "content": system})

    for msg in messages:
        final_messages.append(msg)

    # 准备参数
    params: Dict[str, Any] = {
        "model": profile_config.model,
        "messages": final_messages,
    }

    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    elif profile_config.max_tokens is not None:
        params["max_tokens"] = profile_config.max_tokens

    if temperature is not None:
        params["temperature"] = temperature
    elif profile_config.temperature is not None:
        params["temperature"] = profile_config.temperature

    logger.debug(f"Calling OpenAI API with model: {profile_config.model}")

    # 调用 API
    response = client.chat.completions.create(**params)

    # 解析响应
    input_tokens = 0
    output_tokens = 0
    if hasattr(response, "usage") and response.usage:
        input_tokens = getattr(response.usage, "prompt_tokens", 0)
        output_tokens = getattr(response.usage, "completion_tokens", 0)

    # 提取内容（兼容推理模型如 glm-5, DeepSeek-R1 等）
    content = ""
    if response.choices and len(response.choices) > 0:
        msg = response.choices[0].message
        content = msg.content or ""
        # 推理模型可能将回答放在 reasoning_content 中
        if not content:
            reasoning = getattr(msg, "reasoning_content", None)
            if not reasoning and hasattr(msg, "model_extra") and msg.model_extra:
                reasoning = msg.model_extra.get("reasoning_content", "")
            if reasoning:
                content = reasoning

    # 停止原因
    stop_reason = None
    if response.choices and len(response.choices) > 0:
        stop_reason = response.choices[0].finish_reason

    duration = time.time() - start_time

    logger.debug(
        f"OpenAI response: tokens={input_tokens}+{output_tokens}, "
        f"duration={duration:.2f}s"
    )

    return LLMResponse(
        content=content,
        model=profile_config.model,
        profile=profile_name,
        tokens_used=input_tokens + output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_seconds=duration,
        raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        stop_reason=stop_reason,
    )


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量（粗略估计）

    Args:
        text: 文本内容

    Returns:
        估算的 token 数量
    """
    # 粗略估计：英文约 4 字符/token，中文约 1.5 字符/token
    # 这里用一个简单的平均值
    return len(text) // 3
