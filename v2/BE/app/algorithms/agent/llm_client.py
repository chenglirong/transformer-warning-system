"""OpenAI 兼容 Chat Completions 客户端(stdlib,无强制 langchain 依赖)。

环境变量:
  LLM_API_KEY   必填才启用 LLM
  LLM_BASE_URL  默认 https://api.openai.com/v1
  LLM_MODEL     默认 gpt-4o-mini
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional


def llm_enabled() -> bool:
    return bool(os.environ.get("LLM_API_KEY", "").strip())


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    timeout_s: float = 45.0,
) -> str:
    """返回 assistant content;失败抛 RuntimeError。"""
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未配置 LLM_API_KEY")

    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    url = f"{base}/chat/completions"
    body = json.dumps({
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"LLM HTTP {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"LLM 调用失败: {e}") from e

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"LLM 响应格式异常: {payload!r}"[:400]) from e
    if not content or not str(content).strip():
        raise RuntimeError("LLM 返回空内容")
    return str(content).strip()
