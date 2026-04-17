"""DeepSeek HTTP 客户端：超时、重试、错误分类。"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class DeepSeekErrorCode(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CONTENT_SAFETY = "content_safety"
    HTTP_ERROR = "http_error"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


@dataclass
class DeepSeekError(Exception):
    code: DeepSeekErrorCode
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code.value}: {self.message}"


def _classify_http_status(status: int) -> DeepSeekErrorCode:
    if status == 429:
        return DeepSeekErrorCode.RATE_LIMIT
    if status in (408, 504):
        return DeepSeekErrorCode.TIMEOUT
    if status == 400:
        return DeepSeekErrorCode.CONTENT_SAFETY
    return DeepSeekErrorCode.HTTP_ERROR


async def _post_chat(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code >= 400:
        code = _classify_http_status(resp.status_code)
        raise DeepSeekError(code, f"HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


async def generate_dual_platform_copy(
    canonical_title: str,
    *,
    topic_context: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    调用 DeepSeek 生成抖音图文版与小红书版文案结构。
    返回 (douyin_asset_dict, xiaohongshu_asset_dict)，每项含 title, body, tags, cover_text, image_suggestions。
    未配置 DEEPSEEK_API_KEY 时返回确定性 mock，便于本地联调。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key == "sk-your-key-here":
        logger.warning("deepseek.mock_response", reason="missing_or_placeholder_api_key")
        base = f"【{canonical_title}】"
        ctx = topic_context or ""
        douyin = {
            "title": f"{base}｜抖音图文",
            "body": f"这里是面向抖音的图文正文示例。\n\n关联上下文：{ctx[:200]}",
            "tags": ["热点", "资讯"],
            "cover_text": "点击展开全文",
            "image_suggestions": ["城市夜景配图", "数据图表"],
        }
        xhs = {
            "title": f"{base}｜小红书笔记",
            "body": f"这里是面向小红书的笔记正文示例。\n\n{ctx[:200]}",
            "tags": ["今日热点", "干货"],
            "cover_text": "左滑查看更多",
            "image_suggestions": ["封面实拍", "清单截图"],
        }
        return douyin, xhs

    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    timeout = float(os.environ.get("DEEPSEEK_TIMEOUT_SECONDS", "60"))

    system = (
        "你是内容运营助手。请严格输出一个 JSON 对象，键为 douyin_graphic 与 xiaohongshu，"
        "每个值为对象，字段：title, body, tags(字符串数组), cover_text, image_suggestions(字符串数组)。"
        "不要输出 markdown 代码围栏以外的任何文字。"
    )
    user = json.dumps(
        {"canonical_title": canonical_title, "topic_context": topic_context or ""},
        ensure_ascii=False,
    )
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.6,
    }
    url = f"{base_url}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    max_retries = int(os.environ.get("DEEPSEEK_MAX_RETRIES", "3"))
    last_err: Exception | None = None
    data: dict[str, Any] | None = None
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries):
                try:
                    data = await _post_chat(client, url, headers, payload)
                    break
                except DeepSeekError as exc:
                    last_err = exc
                    if exc.code != DeepSeekErrorCode.RATE_LIMIT or attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2**attempt)
    except httpx.TimeoutException as exc:
        raise DeepSeekError(DeepSeekErrorCode.TIMEOUT, str(exc)) from exc
    except DeepSeekError:
        raise
    except httpx.HTTPError as exc:
        raise DeepSeekError(DeepSeekErrorCode.HTTP_ERROR, str(exc)) from exc

    if data is None:
        if isinstance(last_err, DeepSeekError):
            raise last_err
        raise DeepSeekError(DeepSeekErrorCode.UNKNOWN, "empty response from DeepSeek")

    try:
        content = data["choices"][0]["message"]["content"]
        if "```" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        parsed = json.loads(content)
        d = parsed["douyin_graphic"]
        x = parsed["xiaohongshu"]
        return d, x
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise DeepSeekError(
            DeepSeekErrorCode.INVALID_RESPONSE,
            f"无法解析模型输出: {exc}; raw={str(data)[:500]}",
        ) from exc
