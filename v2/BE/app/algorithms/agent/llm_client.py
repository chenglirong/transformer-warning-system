"""OpenAI 兼容 Chat Completions 客户端(stdlib,无强制 langchain 依赖)。

环境变量:
  LLM_API_KEY   必填才启用 LLM
  LLM_BASE_URL  默认 https://api.openai.com/v1
  LLM_MODEL     默认 gpt-4o-mini

部分阿里云 MaaS 网关回包不是标准 choices[].message.content,
而是扁平 {finish_reason, text};本客户端两种都认。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional


def llm_enabled() -> bool:
    return bool(os.environ.get("LLM_API_KEY", "").strip())


def _extract_content(payload: Any) -> str:
    """从多种兼容回包中取出 assistant 正文。"""
    if not isinstance(payload, dict):
        raise RuntimeError(f"LLM 响应非对象: {payload!r}"[:400])

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        c0 = choices[0]
        if isinstance(c0, dict):
            msg = c0.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if content is not None and str(content).strip():
                    return str(content)
            # 少数兼容层把正文放在 choice 上
            for key in ("text", "content"):
                val = c0.get(key)
                if val is not None and str(val).strip():
                    return str(val)

    # 阿里云 MaaS 等扁平结构: {finish_reason, text}
    for key in ("text", "content", "output_text"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, dict):
            nested = val.get("text") or val.get("content")
            if nested is not None and str(nested).strip():
                return str(nested)

    output = payload.get("output")
    if isinstance(output, dict):
        for key in ("text", "content"):
            val = output.get(key)
            if val is not None and str(val).strip():
                return str(val)
    if isinstance(output, str) and output.strip():
        return output

    raise RuntimeError(f"LLM 响应格式异常: {payload!r}"[:400])


def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout_s: float = 60.0,
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
        "max_tokens": max_tokens,
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

    content = _extract_content(payload)
    if not content or not str(content).strip():
        raise RuntimeError("LLM 返回空内容")
    return str(content).strip()
