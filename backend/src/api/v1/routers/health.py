"""健康检查与依赖聚合（M3）。"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps import get_db
from src.infrastructure.db.models import ContentJob, JobStatus
from src.infrastructure.observability.redis_counters import get_all_collector_failures_async

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"

QUEUE_DEPTH_WARN = int(os.environ.get("CELERY_QUEUE_BACKLOG_WARN", "80"))
GEN_FAIL_RATE_WARN = float(os.environ.get("GENERATION_FAILURE_RATE_WARN", "0.25"))


class CheckResult(BaseModel):
    ok: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(description="ok | degraded | unhealthy")
    version: str
    checks: dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_db)) -> HealthResponse:
    checks: dict[str, Any] = {}
    degraded = False
    unhealthy = False

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = CheckResult(ok=True, detail="connected").model_dump()
    except Exception as exc:
        checks["database"] = CheckResult(ok=False, detail=str(exc)[:200]).model_dump()
        unhealthy = True

    if not unhealthy:
        backlog = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(ContentJob)
                    .where(
                        ContentJob.status.in_(
                            [JobStatus.QUEUED.value, JobStatus.GENERATING.value],
                        ),
                    )
                )
            ).scalar_one()
        )
        q_ok = backlog < QUEUE_DEPTH_WARN
        checks["queue_backlog"] = {
            "ok": q_ok,
            "queued_or_generating": backlog,
            "warn_threshold": QUEUE_DEPTH_WARN,
        }
        if not q_ok:
            degraded = True

        fail_sql = text(
            """
            SELECT COUNT(*)::int FROM content_job
            WHERE status = 'FAILED'
              AND updated_at > NOW() - INTERVAL '24 hours'
            """
        )
        ok_sql = text(
            """
            SELECT COUNT(*)::int FROM content_job
            WHERE status IN ('GENERATED','IN_REVIEW','APPROVED','PACKAGED')
              AND updated_at > NOW() - INTERVAL '24 hours'
            """
        )
        n_fail = int((await session.execute(fail_sql)).scalar_one())
        n_ok = int((await session.execute(ok_sql)).scalar_one())
        denom = n_fail + n_ok
        rate = (n_fail / denom) if denom else 0.0
        rate_ok = rate < GEN_FAIL_RATE_WARN
        checks["generation_failure_rate_24h"] = {
            "ok": rate_ok,
            "failed_jobs": n_fail,
            "terminal_ok_jobs": n_ok,
            "rate": round(rate, 4),
            "warn_threshold": GEN_FAIL_RATE_WARN,
        }
        if not rate_ok:
            degraded = True

    try:
        collector_failures = await get_all_collector_failures_async()
        checks["collectors"] = {"failures_by_platform": collector_failures, "ok": True}
    except Exception as exc:
        checks["collectors"] = {"ok": False, "detail": str(exc)[:200]}
        degraded = True

    if unhealthy:
        overall = "unhealthy"
    elif degraded:
        overall = "degraded"
    else:
        overall = "ok"

    return HealthResponse(status=overall, version=APP_VERSION, checks=checks)
