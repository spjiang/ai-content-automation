from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps import get_db
from src.api.v1.schemas.content import ReviewRequest
from src.infrastructure.db.models import ContentJob, JobStatus, ReviewRecord
from src.workers.tasks.packaging import build_publish_package

router = APIRouter(tags=["review"])
logger = structlog.get_logger(__name__)


@router.post("/review", status_code=status.HTTP_200_OK)
async def submit_review(body: ReviewRequest, session: AsyncSession = Depends(get_db)) -> dict[str, int | str]:
    new_status: str
    async with session.begin():
        job = (
            await session.execute(
                select(ContentJob).where(ContentJob.id == body.job_id).with_for_update()
            )
        ).scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        if job.status != JobStatus.IN_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"job not in IN_REVIEW (current={job.status})",
            )
        if body.decision == "approve":
            job.status = JobStatus.APPROVED.value
        else:
            job.status = JobStatus.REVISE_REQUIRED.value
        new_status = job.status
        session.add(
            ReviewRecord(
                content_job_id=job.id,
                reviewer_id=body.reviewer_id,
                decision=body.decision,
                reject_reason=body.reject_reason,
                revision_notes=body.revision_notes,
                asset_version_at_review=job.asset_version,
            )
        )

    if body.decision == "approve":
        build_publish_package.delay(body.job_id)

    logger.info(
        "review.submitted",
        job_id=body.job_id,
        decision=body.decision,
        new_status=new_status,
        reviewer_id=body.reviewer_id,
    )

    return {"job_id": body.job_id, "decision": body.decision, "new_status": new_status}
