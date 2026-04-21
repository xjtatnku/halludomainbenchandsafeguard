from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable, Mapping

import requests

from .models import ModelSpec


PROVIDER_ALIASES = {
    "siliconflow": "siliconflow",
    "qianfan": "baidu_qianfan",
    "baidu": "baidu_qianfan",
    "baidu_qianfan": "baidu_qianfan",
    "volcengine": "volcengine_ark",
    "ark": "volcengine_ark",
    "doubao": "volcengine_ark",
    "volcengine_ark": "volcengine_ark",
}

DEFAULT_API_KEY_NAMES = {
    "siliconflow": "SILICONFLOW_API_KEY",
    "baidu_qianfan": "BAIDU_QIANFAN_API_KEY",
    "volcengine_ark": "VOLCENGINE_ARK_API_KEY",
}


def normalize_provider_name(provider: str) -> str:
    normalized = provider.strip().lower().replace("-", "_")
    return PROVIDER_ALIASES.get(normalized, normalized)


def provider_default_api_key_name(provider: str) -> str:
    normalized = normalize_provider_name(provider)
    return DEFAULT_API_KEY_NAMES.get(normalized, DEFAULT_API_KEY_NAMES["siliconflow"])


def resolve_api_key_name(model_name: str | ModelSpec) -> str:
    if isinstance(model_name, ModelSpec):
        if model_name.api_key_name.strip():
            return model_name.api_key_name.strip()
        if model_name.provider.strip():
            return provider_default_api_key_name(model_name.provider)
        return DEFAULT_API_KEY_NAMES["siliconflow"]
    return DEFAULT_API_KEY_NAMES["siliconflow"]


def required_api_key_names(model_specs: Iterable[ModelSpec], extra_names: Iterable[str] | None = None) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for name in [resolve_api_key_name(spec) for spec in model_specs] + list(extra_names or []):
        normalized = str(name).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            names.append(normalized)
    return names


class BaseLLMClient(ABC):
    def __init__(self, api_key: str, *, base_url: str, default_headers: Mapping[str, str] | None = None):
        if not api_key:
            raise ValueError("Missing API key for LLM provider")
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if default_headers:
            headers.update(default_headers)
        self.session.headers.update(headers)

    @abstractmethod
    def chat_completion(
        self,
        model: str,
        user_text: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        max_tokens: int = 512,
        timeout_sec: float = 90.0,
        request_overrides: Mapping[str, Any] | None = None,
    ) -> dict:
        raise NotImplementedError


class OpenAICompatibleClient(BaseLLMClient):
    CONNECT_TIMEOUT_SEC = 30.0

    def chat_completion(
        self,
        model: str,
        user_text: str,
        system_prompt: str = "",
        temperature: float = 0.2,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        max_tokens: int = 512,
        timeout_sec: float = 90.0,
        request_overrides: Mapping[str, Any] | None = None,
    ) -> dict:
        overrides = dict(request_overrides or {})
        payload = self._build_payload(
            model=model,
            user_text=user_text,
            system_prompt=system_prompt,
            temperature=temperature,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            max_tokens=max_tokens,
            request_overrides=overrides,
        )

        try:
            with self.session.post(
                url=self.base_url,
                json=payload,
                stream=bool(payload.get("stream", True)),
                timeout=(min(self.CONNECT_TIMEOUT_SEC, timeout_sec), timeout_sec),
            ) as response:
                response.raise_for_status()
                if bool(payload.get("stream", True)):
                    return self._parse_streaming_response(response)
                return self._parse_non_stream_response(response.json())
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Request failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"Invalid response payload: {exc}") from exc

    def _build_payload(
        self,
        *,
        model: str,
        user_text: str,
        system_prompt: str,
        temperature: float,
        top_p: float | None,
        presence_penalty: float | None,
        frequency_penalty: float | None,
        max_tokens: int,
        request_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        messages = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": user_text})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": bool(request_overrides.pop("stream", True)),
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty

        self.apply_provider_payload(payload, model, request_overrides)

        extra_body = request_overrides.pop("extra_body", {})
        if isinstance(extra_body, dict):
            payload.update(extra_body)
        payload.update(request_overrides)
        return payload

    def apply_provider_payload(self, payload: dict[str, Any], model: str, overrides: dict[str, Any]) -> None:
        del payload, model, overrides

    @staticmethod
    def _coerce_message_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            chunks: list[str] = []
            for item in value:
                if isinstance(item, str):
                    chunks.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
            return "".join(chunks)
        return ""

    def _extract_choice_fields(self, choice: Mapping[str, Any]) -> tuple[str, str, str]:
        delta = choice.get("delta", {})
        message = choice.get("message", {})
        content = self._coerce_message_text(delta.get("content")) or self._coerce_message_text(message.get("content"))
        reasoning = self._coerce_message_text(delta.get("reasoning_content")) or self._coerce_message_text(
            message.get("reasoning_content")
        )
        finish_reason = str(choice.get("finish_reason") or "").strip()
        return content, reasoning, finish_reason

    def _parse_streaming_response(self, response: requests.Response) -> dict[str, Any]:
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/event-stream" not in content_type:
            return self._parse_non_stream_response(response.json())

        content_chunks: list[str] = []
        reasoning_chunks: list[str] = []
        finish_reason = ""
        usage: dict[str, Any] = {}

        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8", errors="ignore").strip()
            if not decoded.startswith("data:"):
                continue
            data_str = decoded[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            choices = chunk.get("choices", [])
            if choices:
                content, reasoning, chunk_finish_reason = self._extract_choice_fields(choices[0])
                if content:
                    content_chunks.append(content)
                if reasoning:
                    reasoning_chunks.append(reasoning)
                if chunk_finish_reason:
                    finish_reason = chunk_finish_reason
            if isinstance(chunk.get("usage"), dict):
                usage = dict(chunk["usage"])

        return {
            "content": "".join(content_chunks).strip(),
            "reasoning_content": "".join(reasoning_chunks).strip(),
            "finish_reason": finish_reason,
            "usage": usage,
            "raw_response": "streamed",
        }

    def _parse_non_stream_response(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        choices = payload.get("choices", [])
        content = ""
        reasoning = ""
        finish_reason = ""
        if choices:
            content, reasoning, finish_reason = self._extract_choice_fields(choices[0])
        usage = dict(payload.get("usage") or {})
        return {
            "content": content.strip(),
            "reasoning_content": reasoning.strip(),
            "finish_reason": finish_reason,
            "usage": usage,
            "raw_response": "non_stream",
        }


class SiliconFlowClient(OpenAICompatibleClient):
    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
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

    def __init__(self, api_key: str, *, base_url: str = ""):
        super().__init__(api_key, base_url=base_url or self.DEFAULT_BASE_URL)

    def apply_provider_payload(self, payload: dict[str, Any], model: str, overrides: dict[str, Any]) -> None:
        enable_thinking = overrides.pop("enable_thinking", model in self.THINKING_SUPPORTED_MODELS)
        if enable_thinking:
            payload["enable_thinking"] = True


class BaiduQianfanClient(OpenAICompatibleClient):
    DEFAULT_BASE_URL = "https://qianfan.baidubce.com/v2/chat/completions"

    def __init__(self, api_key: str, *, base_url: str = ""):
        super().__init__(api_key, base_url=base_url or self.DEFAULT_BASE_URL)


class VolcengineArkClient(OpenAICompatibleClient):
    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    def __init__(self, api_key: str, *, base_url: str = ""):
        super().__init__(api_key, base_url=base_url or self.DEFAULT_BASE_URL)


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
    def get_client(model_name: str | ModelSpec, api_keys: Mapping[str, str]) -> BaseLLMClient:
        if isinstance(model_name, ModelSpec):
            provider = normalize_provider_name(model_name.provider or "siliconflow")
            resolved_model = model_name.model_id
            api_key_name = resolve_api_key_name(model_name)
            base_url = model_name.base_url.strip()
        else:
            provider = "siliconflow"
            resolved_model = model_name
            api_key_name = DEFAULT_API_KEY_NAMES["siliconflow"]
            base_url = ""

        api_key = api_keys.get(api_key_name, "")
        if provider == "siliconflow":
            return SiliconFlowClient(api_key=api_key, base_url=base_url)
        if provider == "baidu_qianfan":
            return BaiduQianfanClient(api_key=api_key, base_url=base_url)
        if provider == "volcengine_ark":
            return VolcengineArkClient(api_key=api_key, base_url=base_url)
        if isinstance(model_name, str) and resolved_model.startswith(LLMFactory.VALID_PREFIXES):
            return SiliconFlowClient(api_key=api_key, base_url=base_url)
        raise ValueError(f"Unsupported model routing: {resolved_model}")


def _normalize_env_var_names(env_vars: str | Iterable[str] | None) -> list[str]:
    if env_vars is None:
        raw_names: list[str] = [DEFAULT_API_KEY_NAMES["siliconflow"]]
    elif isinstance(env_vars, str):
        raw_names = [env_vars]
    else:
        raw_names = list(env_vars)

    names: list[str] = []
    seen: set[str] = set()
    for name in raw_names:
        normalized = str(name).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            names.append(normalized)
    return names or [DEFAULT_API_KEY_NAMES["siliconflow"]]


def load_api_keys(env_vars: str | Iterable[str] | None, api_key_file: str | Path | None = None) -> dict[str, str]:
    requested_keys = _normalize_env_var_names(env_vars)
    secret_payload: Mapping[str, Any] = {}

    if api_key_file:
        path = Path(api_key_file)
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                secret_payload = loaded

    resolved: dict[str, str] = {}
    for key_name in requested_keys:
        env_value = os.getenv(key_name, "").strip()
        if env_value:
            resolved[key_name] = env_value
            continue
        file_value = str(secret_payload.get(key_name, "")).strip()
        resolved[key_name] = file_value
    return resolved
