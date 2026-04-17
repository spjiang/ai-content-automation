from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.v1.deps import get_db
from src.api.v1.schemas.content import AssetOut, JobDetail, JobSummary, PackageSummary
from src.infrastructure.db.models import ContentJob, JobStatus, PublishPackage
from src.workers.tasks.generation import run_content_generation
from src.workers.tasks.packaging import build_publish_package

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSummary])
async def list_jobs(
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
) -> list[JobSummary]:
    stmt = select(ContentJob).order_by(ContentJob.created_at.desc()).limit(200)
    if status_filter:
        stmt = stmt.where(ContentJob.status == status_filter)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        JobSummary(
            id=j.id,
            status=j.status,
            canonical_title=j.canonical_title,
            topic_fingerprint=j.topic_fingerprint,
            asset_version=j.asset_version,
            created_at=j.created_at,
        )
        for j in rows
    ]


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(job_id: int, session: AsyncSession = Depends(get_db)) -> JobDetail:
    stmt = (
        select(ContentJob)
        .options(selectinload(ContentJob.assets))
        .where(ContentJob.id == job_id)
    )
    job = (await session.execute(stmt)).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    assets = [
        a
        for a in job.assets
        if a.version == job.asset_version
    ]
    return JobDetail(
        id=job.id,
        status=job.status,
        canonical_title=job.canonical_title,
        topic_fingerprint=job.topic_fingerprint,
        asset_version=job.asset_version,
        created_at=job.created_at,
        prompt_version=job.prompt_version,
        template_version=job.template_version,
        rule_version=job.rule_version,
        failure_code=job.failure_code,
        failure_reason=job.failure_reason,
        assets=[
            AssetOut(
                publish_target=a.publish_target,
                version=a.version,
                title=a.title,
                body=a.body,
                tags=list(a.tags or []),
                cover_text=a.cover_text,
                image_suggestions=list(a.image_suggestions or []),
            )
            for a in sorted(assets, key=lambda x: x.publish_target)
        ],
    )


@router.get("/{job_id}/packages", response_model=list[PackageSummary])
async def list_job_packages(
    job_id: int,
    session: AsyncSession = Depends(get_db),
) -> list[PackageSummary]:
    job = await session.get(ContentJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    stmt = (
        select(PublishPackage)
        .where(PublishPackage.content_job_id == job_id)
        .order_by(PublishPackage.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        PackageSummary(id=p.id, package_version=p.package_version, created_at=p.created_at) for p in rows
    ]


@router.post("/{job_id}/requeue", status_code=status.HTTP_202_ACCEPTED)
async def requeue_job(
    job_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    async with session.begin():
        job = (
            await session.execute(
                select(ContentJob).where(ContentJob.id == job_id).with_for_update()
            )
        ).scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        if job.status != JobStatus.REVISE_REQUIRED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="only REVISE_REQUIRED jobs can be requeued",
            )
        job.asset_version += 1
        job.status = JobStatus.QUEUED.value
        job.failure_code = None
        job.failure_reason = None
    run_content_generation.delay(job_id)
    return {"job_id": job_id, "status": "QUEUED"}


@router.post("/{job_id}/package", status_code=status.HTTP_202_ACCEPTED)
async def trigger_package(job_id: int, session: AsyncSession = Depends(get_db)) -> dict[str, int | str]:
    job = await session.get(ContentJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    if job.status != JobStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job must be APPROVED to build package",
        )
    build_publish_package.delay(job_id)
    return {"job_id": job_id, "queued": "packaging"}
