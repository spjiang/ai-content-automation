"""抓取连续失败计数（Redis），供 health 聚合；无 Redis 时用进程内字典兜底。"""

from __future__ import annotations

import os

import redis

_local_failures: dict[str, int] = {}


def _client() -> redis.Redis | None:
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    try:
        return redis.Redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def incr_collector_failure(platform: str) -> int:
    c = _client()
    if c is not None:
        key = f"collector:failures:{platform}"
        n = int(c.incr(key))
        c.expire(key, 86400 * 7)
        return n
    _local_failures[platform] = _local_failures.get(platform, 0) + 1
    return _local_failures[platform]


def reset_collector_failure(platform: str) -> None:
    c = _client()
    if c is not None:
        c.delete(f"collector:failures:{platform}")
    _local_failures[platform] = 0


def get_all_collector_failures() -> dict[str, int]:
    out: dict[str, int] = {}
    c = _client()
    if c is not None:
        for plat in ("weibo", "zhihu", "douyin"):
            key = f"collector:failures:{plat}"
            v = c.get(key)
            if v is not None:
                out[plat] = int(v)
    for plat, n in _local_failures.items():
        if n > 0:
            out[plat] = max(out.get(plat, 0), n)
    return out


async def get_all_collector_failures_async() -> dict[str, int]:
    """FastAPI 侧异步读取（与 sync 实现共享 key）。"""
    import redis.asyncio as aioredis

    url = os.environ.get("REDIS_URL")
    if not url:
        return {}
    try:
        client = aioredis.from_url(url, decode_responses=True)
    except Exception:
        return {}
    try:
        out: dict[str, int] = {}
        for plat in ("weibo", "zhihu", "douyin"):
            key = f"collector:failures:{plat}"
            v = await client.get(key)
            if v is not None:
                out[plat] = int(v)
        return out
    finally:
        await client.aclose()
