"""审核通过后生成版本化发布包文件并落库。"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from celery import Task
from sqlalchemy import func, select, update

from src.infrastructure.db.celery_async import run_async
from src.infrastructure.db.models import ContentAsset, ContentJob, JobStatus, PublishPackage
from src.infrastructure.db.session import AsyncSessionLocal
from src.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


def _storage_dir() -> Path:
    return Path(os.environ.get("PACKAGE_STORAGE_DIR", "data/packages")).resolve()


async def _run_packaging(job_id: int) -> dict[str, str | int | bool]:
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as session:
        job = await session.get(ContentJob, job_id)
        if job is None:
            return {"skipped": True, "reason": "job_not_found"}  # type: ignore[return-value]
        if job.status != JobStatus.APPROVED.value:
            return {"skipped": True, "reason": f"invalid_status:{job.status}"}  # type: ignore[return-value]

        n = await session.scalar(
            select(func.count()).select_from(PublishPackage).where(PublishPackage.content_job_id == job_id)
        )
        ver_num = int(n or 0) + 1
        package_version = f"v{ver_num}"

        canonical_title = job.canonical_title
        asset_version = job.asset_version
        asset_rows = (
            await session.execute(
                select(ContentAsset).where(
                    ContentAsset.content_job_id == job_id,
                    ContentAsset.version == asset_version,
                )
            )
        ).scalars().all()
        asset_dicts = [
            {
                "publish_target": a.publish_target,
                "version": a.version,
                "title": a.title,
                "body": a.body,
                "tags": a.tags,
                "cover_text": a.cover_text,
                "image_suggestions": a.image_suggestions,
            }
            for a in asset_rows
        ]

    payload: dict[str, object] = {
        "job_id": job_id,
        "package_version": package_version,
        "canonical_title": canonical_title,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "assets": asset_dicts,
        "metrics": {"impressions": None, "plays": None, "interactions": None},
    }

    base = _storage_dir()
    job_dir = base / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    file_path = job_dir / f"{package_version}.json"
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=7)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add(
                PublishPackage(
                    content_job_id=job_id,
                    package_version=package_version,
                    storage_path=str(file_path),
                    download_url=None,
                    payload_json=payload,
                    expires_at=expires_at,
                )
            )
            await session.execute(
                update(ContentJob)
                .where(ContentJob.id == job_id)
                .values(status=JobStatus.PACKAGED.value)
            )

    logger.info(
        "packaging.done",
        job_id=job_id,
        package_version=package_version,
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    )
    return {"ok": True, "job_id": job_id, "package_version": package_version}


@celery_app.task(
    name="src.workers.tasks.packaging.build_publish_package",
    bind=True,
    max_retries=3,
    default_retry_delay=20,
)
def build_publish_package(self: Task, job_id: int) -> dict[str, str | int | bool]:
    try:
        return run_async(_run_packaging(job_id))
    except Exception as exc:  # pragma: no cover
        logger.exception("packaging.task.error", job_id=job_id)
        raise self.retry(exc=exc) from exc
