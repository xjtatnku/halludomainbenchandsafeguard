from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Mapping

import requests


class BaseLLMClient(ABC):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Missing API key for LLM provider")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    @abstractmethod
    def chat_completion(
        self,
        model: str,
        user_text: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 512,
        timeout_sec: float = 90.0,
    ) -> dict:
        raise NotImplementedError


class SiliconFlowClient(BaseLLMClient):
    CONNECT_TIMEOUT_SEC = 30.0
    THINKING_SUPPORTED_MODELS = {
        "Pro/zai-org/GLM-5",
        "Pro/zai-org/GLM-4.7",
        "deepseek-ai/DeepSeek-V3.2",
        "Pro/deepseek-ai/DeepSeek-V3.2",
        "zai-org/GLM-4.6",
        "Qwen/Qwen3-8B",
        "Qwen/Qwen3-14B",
        "Qwen/Qwen3-32B",
        "Qwen/Qwen3-30B-A3B",
        "tencent/Hunyuan-A13B-Instruct",
        "zai-org/GLM-4.5V",
        "deepseek-ai/DeepSeek-V3.1-Terminus",
        "Pro/deepseek-ai/DeepSeek-V3.1-Terminus",
        "Qwen/Qwen3.5-397B-A17B",
        "Qwen/Qwen3.5-122B-A10B",
        "Qwen/Qwen3.5-35B-A3B",
        "Qwen/Qwen3.5-27B",
        "Qwen/Qwen3.5-9B",
        "Qwen/Qwen3.5-4B",
    }

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"

    def chat_completion(
        self,
        model: str,
        user_text: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        max_tokens: int = 512,
        timeout_sec: float = 90.0,
    ) -> dict:
        messages = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": user_text})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if model in self.THINKING_SUPPORTED_MODELS:
            payload["enable_thinking"] = True

        content_chunks: list[str] = []
        reasoning_chunks: list[str] = []
        finish_reason = ""
        usage: dict = {}

        try:
            with self.session.post(
                url=self.base_url,
                json=payload,
                stream=True,
                timeout=(min(self.CONNECT_TIMEOUT_SEC, timeout_sec), timeout_sec),
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8", errors="ignore")
                    if not decoded.startswith("data: "):
                        continue
                    data_str = decoded[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        if delta.get("content"):
                            content_chunks.append(delta["content"])
                        if delta.get("reasoning_content"):
                            reasoning_chunks.append(delta["reasoning_content"])
                        if choices[0].get("finish_reason"):
                            finish_reason = choices[0]["finish_reason"]
                    if chunk.get("usage"):
                        usage = chunk["usage"]
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Request failed: {exc}") from exc

        return {
            "content": "".join(content_chunks).strip(),
            "reasoning_content": "".join(reasoning_chunks).strip(),
            "finish_reason": finish_reason,
            "usage": usage,
            "raw_response": "streamed",
        }


class LLMFactory:
    VALID_PREFIXES = (
        "Qwen/",
        "Pro/",
        "deepseek-ai/",
        "zai-org/",
        "tencent/",
        "moonshotai/",
        "PaddlePaddle/",
        "baidu/",
        "internlm/",
        "inclusionAI/",
        "stepfun-ai/",
    )

    @staticmethod
    def get_client(model_name: str, api_keys: Mapping[str, str]) -> BaseLLMClient:
        if model_name.startswith(LLMFactory.VALID_PREFIXES):
            return SiliconFlowClient(api_key=api_keys.get("SILICONFLOW_API_KEY", ""))
        raise ValueError(f"Unsupported model routing: {model_name}")


def load_api_keys(env_var: str, api_key_file: str | Path | None = None) -> dict[str, str]:
    env_key = os.getenv(env_var, "").strip()
    if env_key:
        return {"SILICONFLOW_API_KEY": env_key}

    if api_key_file:
        path = Path(api_key_file)
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            file_key = str(payload.get("SILICONFLOW_API_KEY", "")).strip()
            if file_key:
                return {"SILICONFLOW_API_KEY": file_key}

    return {"SILICONFLOW_API_KEY": ""}
