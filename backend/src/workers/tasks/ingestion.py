"""
M1 ingestion pipeline task:
  抓取 → 归一化 → 规则引擎 → 为通过话题创建 content_job（QUEUED）
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from celery import Task
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from src.infrastructure.external.collectors.base import BaseCollector, RawTopic
from src.infrastructure.external.collectors.douyin import DouyinCollector
from src.infrastructure.external.collectors.weibo import WeiboCollector
from src.infrastructure.external.collectors.zhihu import ZhihuCollector
from src.application.services.normalizer import normalize
from src.application.services.rule_engine import RuleConfig, apply_rules
from src.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

RETRY_MAX = int(os.environ.get("COLLECTOR_RETRY_MAX", "3"))
RETRY_BACKOFF_BASE = int(os.environ.get("COLLECTOR_RETRY_BACKOFF_BASE", "2"))
FAILURE_ALERT_THRESHOLD = int(os.environ.get("COLLECTOR_FAILURE_ALERT_THRESHOLD", "5"))

_failure_counts: dict[str, int] = {}


def _alert(platform: str, message: str) -> None:
    """告警钩子：当前仅写结构化日志，后续可对接告警平台。"""
    logger.error(
        "collector.alert",
        platform=platform,
        message=message,
        failure_count=_failure_counts.get(platform, 0),
    )


async def _fetch_with_retry(collector: BaseCollector) -> list[RawTopic]:
    """对单个 collector 执行指数退避重试抓取。"""

    @retry(
        stop=stop_after_attempt(RETRY_MAX),
        wait=wait_exponential(multiplier=RETRY_BACKOFF_BASE, min=1, max=30),
        reraise=True,
    )
    async def _inner() -> list[RawTopic]:
        return await collector.fetch()

    platform = collector.platform
    try:
        topics = await _inner()
        _failure_counts[platform] = 0
        return topics
    except Exception as exc:
        _failure_counts[platform] = _failure_counts.get(platform, 0) + 1
        count = _failure_counts[platform]
        logger.warning(
            "collector.fetch.failed",
            platform=platform,
            error=str(exc),
            failure_count=count,
        )
        if count >= FAILURE_ALERT_THRESHOLD:
            _alert(platform, f"Consecutive failures reached threshold {FAILURE_ALERT_THRESHOLD}")
        return []


@celery_app.task(
    name="src.workers.tasks.ingestion.run_ingestion_pipeline",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def run_ingestion_pipeline(self: Task, rule_config_dict: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    全量 ingestion pipeline（三源并行 → 归一 → 规则 → 入队）。
    rule_config_dict: 可选规则配置覆盖，None 则使用默认值。
    """
    logger.info("ingestion_pipeline.start")

    collectors: list[BaseCollector] = [WeiboCollector(), ZhihuCollector(), DouyinCollector()]

    async def _run() -> list[RawTopic]:
        import asyncio
        results = await asyncio.gather(
            *[_fetch_with_retry(c) for c in collectors],
            return_exceptions=False,
        )
        return [topic for batch in results for topic in batch]

    try:
        all_raw = asyncio.run(_run())
    except Exception as exc:
        logger.error("ingestion_pipeline.fetch.error", error=str(exc))
        raise self.retry(exc=exc)

    cfg = RuleConfig(**rule_config_dict) if rule_config_dict else RuleConfig()
    canonical_topics = normalize(all_raw)
    passed_topics, rule_results = apply_rules(canonical_topics, cfg)

    logger.info(
        "ingestion_pipeline.rule_engine.done",
        total_raw=len(all_raw),
        canonical=len(canonical_topics),
        passed=len(passed_topics),
    )

    # 将通过话题入 content_job 队列（M2 实现，此处仅记录）
    queued_ids: list[str] = []
    for topic in passed_topics:
        logger.info(
            "ingestion_pipeline.topic.queued",
            fingerprint=topic.dedup_fingerprint,
            title=topic.canonical_title,
            heat_score=topic.heat_score,
        )
        queued_ids.append(topic.dedup_fingerprint)

    return {
        "total_raw": len(all_raw),
        "canonical_count": len(canonical_topics),
        "passed_count": len(passed_topics),
        "queued_fingerprints": queued_ids,
    }
