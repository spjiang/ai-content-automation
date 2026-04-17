"""消费生成队列：DeepSeek 双平台资产写入 + 状态迁移。"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from celery import Task
from sqlalchemy import select, update

from src.infrastructure.db.celery_async import run_async
from src.infrastructure.db.models import ContentAsset, ContentJob, JobStatus, PublishTarget
from src.infrastructure.db.session import AsyncSessionLocal
from src.infrastructure.external.deepseek import DeepSeekError, generate_dual_platform_copy
from src.infrastructure.observability.alerting import emit_alert
from src.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

_PROMPT_VERSION_DEFAULT = "prompt-v1"
_TEMPLATE_VERSION_DEFAULT = "template-v1"


async def _claim_job(
    job_id: int,
) -> tuple[int, str, int, str | None, str | None, dict | None] | None:
    """QUEUED → GENERATING，成功则返回生成所需快照字段。"""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            job = (
                await session.execute(
                    select(ContentJob)
                    .where(
                        ContentJob.id == job_id,
                        ContentJob.status == JobStatus.QUEUED.value,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if job is None:
                return None
            job.status = JobStatus.GENERATING.value
            return (
                job.id,
                job.canonical_title,
                job.asset_version,
                job.prompt_version,
                job.template_version,
                job.input_snapshot,
            )


async def _fail_job(job_id: int, code: str, message: str) -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(ContentJob)
                .where(ContentJob.id == job_id)
                .values(
                    status=JobStatus.FAILED.value,
                    failure_code=code,
                    failure_reason=message[:4000],
                )
            )
    emit_alert(
        "content_job_generation_failed",
        job_id=job_id,
        failure_code=code,
        message_preview=message[:500],
    )


async def _complete_job(
    job_id: int,
    asset_version: int,
    prompt_version: str | None,
    template_version: str | None,
    douyin: dict[str, Any],
    xhs: dict[str, Any],
) -> None:
    prompt_v = prompt_version or _PROMPT_VERSION_DEFAULT
    template_v = template_version or _TEMPLATE_VERSION_DEFAULT
    async with AsyncSessionLocal() as session:
        async with session.begin():
            job_row = (
                await session.execute(
                    select(ContentJob).where(ContentJob.id == job_id).with_for_update()
                )
            ).scalar_one_or_none()
            if job_row is not None:
                if job_row.prompt_version is None:
                    job_row.prompt_version = prompt_v
                if job_row.template_version is None:
                    job_row.template_version = template_v
            await session.execute(
                update(ContentJob)
                .where(ContentJob.id == job_id)
                .values(status=JobStatus.GENERATED.value)
            )
            session.add_all(
                [
                    ContentAsset(
                        content_job_id=job_id,
                        publish_target=PublishTarget.DOUYIN_GRAPHIC.value,
                        version=asset_version,
                        title=str(douyin["title"]),
                        body=str(douyin["body"]),
                        tags=list(douyin.get("tags") or []),
                        cover_text=douyin.get("cover_text"),
                        image_suggestions=list(douyin.get("image_suggestions") or []),
                    ),
                    ContentAsset(
                        content_job_id=job_id,
                        publish_target=PublishTarget.XIAOHONGSHU.value,
                        version=asset_version,
                        title=str(xhs["title"]),
                        body=str(xhs["body"]),
                        tags=list(xhs.get("tags") or []),
                        cover_text=xhs.get("cover_text"),
                        image_suggestions=list(xhs.get("image_suggestions") or []),
                    ),
                ]
            )
            await session.execute(
                update(ContentJob)
                .where(ContentJob.id == job_id)
                .values(status=JobStatus.IN_REVIEW.value)
            )


async def _run_generation(job_id: int) -> dict[str, Any]:
    claimed = await _claim_job(job_id)
    if claimed is None:
        return {"skipped": True, "reason": "not_queued_or_already_claimed"}

    _jid, canonical_title, asset_version, prompt_v, template_v, input_snapshot = claimed
    ctx = json.dumps(input_snapshot, ensure_ascii=False)[:2000] if input_snapshot else None

    t_llm = time.perf_counter()
    try:
        douyin, xhs = await generate_dual_platform_copy(canonical_title, topic_context=ctx)
    except DeepSeekError as exc:
        await _fail_job(job_id, exc.code.value, exc.message)
        logger.warning(
            "generation.phase.deepseek_failed",
            job_id=job_id,
            duration_ms=round((time.perf_counter() - t_llm) * 1000, 2),
            error_code=exc.code.value,
        )
        return {"ok": False, "error": exc.code.value}

    logger.info(
        "generation.phase.deepseek",
        job_id=job_id,
        duration_ms=round((time.perf_counter() - t_llm) * 1000, 2),
    )

    await _complete_job(job_id, asset_version, prompt_v, template_v, douyin, xhs)
    logger.info("generation.done", job_id=job_id)
    return {"ok": True, "job_id": job_id}


@celery_app.task(
    name="src.workers.tasks.generation.run_content_generation",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def run_content_generation(self: Task, job_id: int) -> dict[str, Any]:
    try:
        return run_async(_run_generation(job_id))
    except Exception as exc:  # pragma: no cover
        logger.exception("generation.task.error", job_id=job_id)
        raise self.retry(exc=exc) from exc
