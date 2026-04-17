"""
M1/M2/M3 ingestion pipeline:
  抓取 → 入库 topic_raw → 归一化 → upsert topic_canonical → 规则引擎
  → 持久化 topic_rule_evaluation → ContentJob（QUEUED）→ 投递生成任务
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone

import structlog
from celery import Task
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from tenacity import retry, stop_after_attempt, wait_exponential

from src.application.services.normalizer import CanonicalTopic, normalize
from src.application.services.rule_engine import RuleConfig, RuleResult, apply_rules, serialize_hit_details
from src.infrastructure.db.models import ContentJob, JobStatus, Platform, TopicCanonical, TopicRaw, TopicRuleEvaluation
from src.infrastructure.db.session import AsyncSessionLocal
from src.infrastructure.external.collectors.base import BaseCollector, RawTopic
from src.infrastructure.external.collectors.douyin import DouyinCollector
from src.infrastructure.external.collectors.weibo import WeiboCollector
from src.infrastructure.external.collectors.zhihu import ZhihuCollector
from src.infrastructure.observability.alerting import emit_alert
from src.infrastructure.observability.redis_counters import (
    get_all_collector_failures,
    incr_collector_failure,
    reset_collector_failure,
)
from src.workers.celery_app import celery_app
from src.workers.tasks.generation import run_content_generation

logger = structlog.get_logger(__name__)

RETRY_MAX = int(os.environ.get("COLLECTOR_RETRY_MAX", "3"))
RETRY_BACKOFF_BASE = int(os.environ.get("COLLECTOR_RETRY_BACKOFF_BASE", "2"))
FAILURE_ALERT_THRESHOLD = int(os.environ.get("COLLECTOR_FAILURE_ALERT_THRESHOLD", "5"))
QUEUE_BACKLOG_WARN = int(os.environ.get("CELERY_QUEUE_BACKLOG_WARN", "80"))

_TERMINAL_JOB_STATUSES = frozenset({JobStatus.FAILED.value, JobStatus.PACKAGED.value})


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _alert(platform: str, message: str) -> None:
    emit_alert(
        "collector_consecutive_failures",
        platform=platform,
        message=message,
        failure_count=get_all_collector_failures().get(platform, 0),
    )


async def _fetch_with_retry(collector: BaseCollector) -> list[RawTopic]:
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
        reset_collector_failure(platform)
        return topics
    except Exception as exc:
        count = incr_collector_failure(platform)
        logger.warning(
            "ingestion.collector.fetch_failed",
            platform=platform,
            error=str(exc),
            failure_count=count,
        )
        if count >= FAILURE_ALERT_THRESHOLD:
            _alert(platform, f"Consecutive failures reached threshold {FAILURE_ALERT_THRESHOLD}")
        return []


async def _persist_raw_topics(session: AsyncSession, raw_topics: list[RawTopic]) -> int:
    if not raw_topics:
        return 0
    rows = [
        {
            "platform": Platform(r.platform),
            "title": (r.title or "")[:512],
            "heat": r.heat,
            "url": r.url,
            "raw_payload": dict(r.raw_payload or {}),
            "crawled_at": _utc(r.crawled_at),
        }
        for r in raw_topics
    ]
    await session.execute(insert(TopicRaw), rows)
    return len(rows)


async def _upsert_canonical_ids(session: AsyncSession, topics: list[CanonicalTopic]) -> dict[str, int]:
    fp_to_id: dict[str, int] = {}
    for t in topics:
        ins = pg_insert(TopicCanonical).values(
            canonical_title=t.canonical_title[:512],
            cluster_key=t.cluster_key[:256],
            dedup_fingerprint=t.dedup_fingerprint[:128],
            combined_heat=t.combined_heat,
            source_platforms=list(t.source_platforms),
            heat_score=t.heat_score,
            first_seen_at=_utc(t.first_seen_at),
            last_seen_at=_utc(t.last_seen_at),
        )
        stmt_ok = ins.on_conflict_do_update(
            index_elements=[TopicCanonical.dedup_fingerprint],
            set_={
                "canonical_title": ins.excluded.canonical_title,
                "cluster_key": ins.excluded.cluster_key,
                "combined_heat": ins.excluded.combined_heat,
                "source_platforms": ins.excluded.source_platforms,
                "heat_score": ins.excluded.heat_score,
                "last_seen_at": ins.excluded.last_seen_at,
            },
        ).returning(TopicCanonical.id, TopicCanonical.dedup_fingerprint)
        row = (await session.execute(stmt_ok)).one()
        fp_to_id[str(row.dedup_fingerprint)] = int(row.id)
    return fp_to_id


async def _persist_rule_evaluations(
    session: AsyncSession,
    fp_to_id: dict[str, int],
    all_results: list[RuleResult],
    rule_version: str,
) -> int:
    n = 0
    for r in all_results:
        tc_id = fp_to_id.get(r.topic.dedup_fingerprint)
        if tc_id is None:
            continue
        session.add(
            TopicRuleEvaluation(
                topic_canonical_id=tc_id,
                rule_version=rule_version,
                passed=bool(r.passed),
                hit_details=serialize_hit_details(r.hit_details),
            )
        )
        n += 1
    return n


async def _persist_jobs_for_topics(
    passed_topics: list[CanonicalTopic],
    rule_version: str,
) -> list[int]:
    """为通过规则的话题创建 QUEUED 任务；同一指纹若已有未终态任务则跳过。"""
    job_ids: list[int] = []
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for topic in passed_topics:
                exists = (
                    await session.execute(
                        select(ContentJob.id)
                        .where(
                            ContentJob.topic_fingerprint == topic.dedup_fingerprint,
                            ContentJob.status.not_in(_TERMINAL_JOB_STATUSES),
                        )
                        .limit(1)
                    )
                ).first()
                if exists is not None:
                    continue
                job = ContentJob(
                    status=JobStatus.QUEUED.value,
                    topic_fingerprint=topic.dedup_fingerprint,
                    canonical_title=topic.canonical_title,
                    rule_version=rule_version,
                    input_snapshot={
                        "heat_score": topic.heat_score,
                        "source_platforms": topic.source_platforms,
                    },
                )
                session.add(job)
                await session.flush()
                job_ids.append(job.id)
    return job_ids


async def _count_queue_backlog() -> int:
    async with AsyncSessionLocal() as session:
        n = await session.scalar(
            select(func.count())
            .select_from(ContentJob)
            .where(
                ContentJob.status.in_([JobStatus.QUEUED.value, JobStatus.GENERATING.value]),
            )
        )
        return int(n or 0)


async def _run_db_pipeline(
    all_raw: list[RawTopic],
    canonical_topics: list[CanonicalTopic],
    all_results: list[RuleResult],
    rule_version: str,
) -> tuple[int, dict[str, int]]:
    """持久化 raw、canonical、规则审计；返回 (rule_eval_rows, fp_to_id)。"""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            t0 = time.perf_counter()
            inserted_raw = await _persist_raw_topics(session, all_raw)
            logger.info(
                "ingestion.persist.topic_raw",
                rows=inserted_raw,
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

            t1 = time.perf_counter()
            fp_to_id = await _upsert_canonical_ids(session, canonical_topics)
            logger.info(
                "ingestion.persist.topic_canonical",
                rows=len(fp_to_id),
                duration_ms=round((time.perf_counter() - t1) * 1000, 2),
            )

            t2 = time.perf_counter()
            n_eval = await _persist_rule_evaluations(session, fp_to_id, all_results, rule_version)
            logger.info(
                "ingestion.persist.topic_rule_evaluation",
                rows=n_eval,
                duration_ms=round((time.perf_counter() - t2) * 1000, 2),
            )
    return n_eval, fp_to_id


@celery_app.task(
    name="src.workers.tasks.ingestion.run_ingestion_pipeline",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def run_ingestion_pipeline(self: Task, rule_config_dict: dict[str, object] | None = None) -> dict[str, object]:
    t_pipeline = time.perf_counter()
    logger.info("ingestion.pipeline.start")

    collectors: list[BaseCollector] = [WeiboCollector(), ZhihuCollector(), DouyinCollector()]

    async def _collect() -> list[RawTopic]:
        t0 = time.perf_counter()
        results = await asyncio.gather(
            *[_fetch_with_retry(c) for c in collectors],
            return_exceptions=False,
        )
        topics = [topic for batch in results for topic in batch]
        logger.info(
            "ingestion.phase.collect",
            total_raw=len(topics),
            duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        return topics

    try:
        all_raw = asyncio.run(_collect())
    except Exception as exc:
        logger.error("ingestion.pipeline.fetch_fatal", error=str(exc))
        raise self.retry(exc=exc) from exc

    t_norm = time.perf_counter()
    cfg = RuleConfig(**rule_config_dict) if rule_config_dict else RuleConfig()
    canonical_topics = normalize(all_raw)
    logger.info(
        "ingestion.phase.normalize",
        canonical=len(canonical_topics),
        duration_ms=round((time.perf_counter() - t_norm) * 1000, 2),
    )

    t_rule = time.perf_counter()
    passed_topics, all_results = apply_rules(canonical_topics, cfg)
    logger.info(
        "ingestion.phase.rules",
        passed=len(passed_topics),
        duration_ms=round((time.perf_counter() - t_rule) * 1000, 2),
    )

    t_db = time.perf_counter()
    n_eval, _ = asyncio.run(_run_db_pipeline(all_raw, canonical_topics, all_results, cfg.version))
    logger.info(
        "ingestion.phase.persist",
        rule_evaluations=n_eval,
        duration_ms=round((time.perf_counter() - t_db) * 1000, 2),
    )

    backlog = asyncio.run(_count_queue_backlog())
    if backlog >= QUEUE_BACKLOG_WARN:
        emit_alert(
            "queue_backlog_high",
            depth=backlog,
            threshold=QUEUE_BACKLOG_WARN,
        )

    job_ids = asyncio.run(_persist_jobs_for_topics(passed_topics, cfg.version))
    for jid in job_ids:
        run_content_generation.delay(jid)

    logger.info(
        "ingestion.pipeline.done",
        total_raw=len(all_raw),
        canonical=len(canonical_topics),
        passed=len(passed_topics),
        jobs_created=len(job_ids),
        duration_ms=round((time.perf_counter() - t_pipeline) * 1000, 2),
    )

    return {
        "total_raw": len(all_raw),
        "canonical_count": len(canonical_topics),
        "passed_count": len(passed_topics),
        "job_ids": job_ids,
        "rule_evaluations_persisted": n_eval,
    }
