"""
LLM Executor - 直接调用大模型 API

支持多种 Provider：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Azure OpenAI
- 其他兼容 OpenAI API 的服务
"""

import os
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import random

from ..base import AbstractExecutor
from ..protocol import StepExecutionRequest, StepExecutionResult, ArtifactReference


class LLMExecutor(AbstractExecutor):
    """
    LLM 执行器 - 直接调用大模型 API

    配置示例（agent.yaml）：
    ```yaml
    engine:
      type: llm
      provider: openai  # openai, anthropic, azure, custom
      model: gpt-4
      api_key: ${OPENAI_API_KEY}  # 或从环境变量读取
      base_url: https://api.openai.com/v1  # 可选
      temperature: 0.7
      max_tokens: 4000
    ```
    """

    async def execute(self, request: StepExecutionRequest) -> StepExecutionResult:
        """执行步骤"""
        started_at = datetime.now().isoformat()

        try:
            # 1. 验证请求
            valid, error = self.validate_request(request)
            if not valid:
                return StepExecutionResult(
                    status="failed",
                    error=f"Invalid request: {error}",
                    started_at=started_at,
                    engine_type="llm"
                )

            # 2. 获取工作目录
            workspace = request.get_working_dir()

            # 3. 构建 Prompt
            system_prompt = self._build_system_prompt(request)
            user_message = self._build_user_message(request)

            # 4. 调用 LLM API (with retry for transient errors)
            provider = self.engine_config.get("provider", "openai")

            if provider == "openai":
                response = await self._call_with_retry(self._call_openai, system_prompt, user_message)
            elif provider == "anthropic":
                response = await self._call_with_retry(self._call_anthropic, system_prompt, user_message)
            elif provider == "azure":
                response = await self._call_with_retry(self._call_azure_openai, system_prompt, user_message)
            else:
                response = await self._call_with_retry(self._call_custom, system_prompt, user_message)

            # 5. 保存响应到工作目录
            output_file = workspace / "response.txt"
            # Only write if response is not empty
            if response and len(response.strip()) > 0:
                output_file.write_text(response, encoding="utf-8")
            else:
                raise ValueError("LLM returned empty response")

            # 6. 构建结果
            completed_at = datetime.now().isoformat()
            duration = (
                datetime.fromisoformat(completed_at) -
                datetime.fromisoformat(started_at)
            ).total_seconds()

            return StepExecutionResult(
                status="completed",
                outputs=[
                    ArtifactReference(
                        id="response",
                        path=str(output_file.relative_to(request.project_dir)),
                        content_type="text/plain",
                        summary="LLM response"
                    )
                ],
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_message
                    },
                    {
                        "role": "assistant",
                        "content": response
                    }
                ],
                raw=response,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                engine_type="llm"
            )

        except Exception as e:
            completed_at = datetime.now().isoformat()
            return StepExecutionResult(
                status="failed",
                error=str(e),
                error_details={
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                },
                started_at=started_at,
                completed_at=completed_at,
                engine_type="llm"
            )

    async def _call_with_retry(
        self,
        call_func,
        system_prompt: str,
        user_message: str,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> str:
        """
        Call LLM API with retry logic for transient errors

        Handles:
        - HTTP 429 (Too Many Requests) - rate limiting
        - HTTP 500/502/503/504 - server errors
        - Network timeouts

        Args:
            call_func: The API call function to retry
            system_prompt: System prompt
            user_message: User message
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds (exponential backoff)

        Returns:
            API response string

        Raises:
            ValueError: If all retries are exhausted
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await call_func(system_prompt, user_message)

            except aiohttp.ClientResponseError as e:
                last_error = e

                # Check if it's a transient error that we should retry
                if e.status in [429, 500, 502, 503, 504]:
                    if attempt < max_retries - 1:
                        # Calculate delay with exponential backoff + jitter
                        delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                        delay = min(delay, 30)  # Cap at 30 seconds

                        print(
                            f"[LLM Executor] API error {e.status} (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {delay:.1f}s..."
                        )

                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise ValueError(
                            f"LLM API failed after {max_retries} attempts. "
                            f"Last error: {e.status} {e.message}"
                        )
                else:
                    # Non-transient error, don't retry
                    raise ValueError(f"LLM API error: {e.status} {e.message}")

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e

                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                    delay = min(delay, 30)

                    print(
                        f"[LLM Executor] Network error (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {delay:.1f}s..."
                    )

                    await asyncio.sleep(delay)
                else:
                    raise ValueError(
                        f"LLM API network error after {max_retries} attempts: {str(e)}"
                    )

        # Should not reach here, but just in case
        raise ValueError(f"LLM API call failed: {str(last_error)}")

    async def _call_openai(
        self,
        system_prompt: str,
        user_message: str
    ) -> str:
        """调用 OpenAI API"""
        api_key = self._get_api_key()
        base_url = self.engine_config.get("base_url", "https://api.openai.com/v1")
        model = self.engine_config.get("model", "gpt-4")
        temperature = self.engine_config.get("temperature", 0.7)
        max_tokens = self.engine_config.get("max_tokens", 4000)

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

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_message: str
    ) -> str:
        """调用 Anthropic Claude API"""
        api_key = self._get_api_key()
        base_url = self.engine_config.get("base_url", "https://api.anthropic.com/v1")
        model = self.engine_config.get("model", "claude-3-opus-20240229")
        max_tokens = self.engine_config.get("max_tokens", 4000)

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/messages",
                headers=headers,
                json=payload
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["content"][0]["text"]

    async def _call_azure_openai(
        self,
        system_prompt: str,
        user_message: str
    ) -> str:
        """调用 Azure OpenAI API"""
        # Azure OpenAI 兼容 OpenAI API 格式
        return await self._call_openai(system_prompt, user_message)

    async def _call_custom(
        self,
        system_prompt: str,
        user_message: str
    ) -> str:
        """调用自定义兼容 OpenAI API 的服务"""
        return await self._call_openai(system_prompt, user_message)

    def _get_api_key(self) -> str:
        """获取 API Key"""
        # 1. 从 engine 配置读取
        api_key = self.engine_config.get("api_key")

        # 2. 支持环境变量替换
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var)

        # 3. 如果没有，尝试从环境变量直接读取
        if not api_key:
            provider = self.engine_config.get("provider", "openai")
            if provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
            elif provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
            elif provider == "azure":
                api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                f"API key not found for provider '{self.engine_config.get('provider')}'. "
                f"Please set engine.api_key or environment variable."
            )

        return api_key


# 注册到 EngineRegistry
def create_executor(agent_spec: Dict, project_dir: str) -> LLMExecutor:
    """工厂函数：创建 LLMExecutor 实例"""
    return LLMExecutor(project_dir, agent_spec)
