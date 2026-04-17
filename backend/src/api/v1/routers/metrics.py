"""M3：运营指标聚合（窗口内 SQL 统计）。"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])


class ReviewMetrics(BaseModel):
    jobs_with_first_review: int = 0
    first_review_approve_count: int = 0
    first_review_approve_rate: float | None = Field(
        default=None, description="首次审核即通过占比（首次记录维度）"
    )


class IngestionGenerationMetrics(BaseModel):
    topic_raw_rows_in_window: int = 0
    content_jobs_created_in_window: int = 0
    generation_failed_in_window: int = 0
    generation_terminal_ok_in_window: int = 0
    generation_success_rate: float | None = None


class LatencyMetrics(BaseModel):
    """首条 asset 落库相对 job 创建的耗时（秒），近似生成链路延迟。"""

    p50_seconds: float | None = None
    p90_seconds: float | None = None
    sample_jobs: int = 0


class MetricsResponse(BaseModel):
    window_days: int
    review: ReviewMetrics
    pipeline: IngestionGenerationMetrics
    latency: LatencyMetrics


def _window_days() -> int:
    return max(1, min(90, int(os.environ.get("METRICS_WINDOW_DAYS", "7"))))


@router.get("", response_model=MetricsResponse)
async def get_metrics(session: AsyncSession = Depends(get_db)) -> MetricsResponse:
    d = _window_days()

    review_sql = text(
        """
        WITH first_rev AS (
            SELECT DISTINCT ON (content_job_id)
                content_job_id,
                decision,
                created_at
            FROM review_record
            ORDER BY content_job_id, created_at ASC
        )
        SELECT
            COUNT(*)::int AS jobs_with_first_review,
            COUNT(*) FILTER (WHERE decision = 'approve')::int AS first_approve
        FROM first_rev
        WHERE created_at > NOW() - (INTERVAL '1 day' * :days)
        """
    )
    pipe_sql = text(
        """
        SELECT
            (SELECT COUNT(*)::int FROM topic_raw
             WHERE created_at > NOW() - (INTERVAL '1 day' * :days)) AS raw_n,
            (SELECT COUNT(*)::int FROM content_job
             WHERE created_at > NOW() - (INTERVAL '1 day' * :days)) AS jobs_n,
            (SELECT COUNT(*)::int FROM content_job
             WHERE status = 'FAILED'
               AND updated_at > NOW() - (INTERVAL '1 day' * :days)) AS gen_fail,
            (SELECT COUNT(*)::int FROM content_job
             WHERE status IN ('GENERATED','IN_REVIEW','APPROVED','PACKAGED')
               AND updated_at > NOW() - (INTERVAL '1 day' * :days)) AS gen_ok
        """
    )
    lat_sql = text(
        """
        WITH lat AS (
            SELECT
                cj.id,
                EXTRACT(EPOCH FROM (MIN(ca.created_at) - cj.created_at))::float AS sec
            FROM content_job cj
            INNER JOIN content_asset ca ON ca.content_job_id = cj.id
            WHERE cj.created_at > NOW() - (INTERVAL '1 day' * :days)
            GROUP BY cj.id, cj.created_at
        )
        SELECT
            COUNT(*)::int AS n,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY sec) AS p50,
            percentile_cont(0.9) WITHIN GROUP (ORDER BY sec) AS p90
        FROM lat
        WHERE sec IS NOT NULL AND sec >= 0
        """
    )

    bind = {"days": d}
    rev_row = (await session.execute(review_sql, bind)).one()
    pipe_row = (await session.execute(pipe_sql, bind)).one()
    lat_row = (await session.execute(lat_sql, bind)).one()

    jobs_fr = int(rev_row.jobs_with_first_review or 0)
    first_apr = int(rev_row.first_approve or 0)
    apr_rate = (first_apr / jobs_fr) if jobs_fr else None

    raw_n = int(pipe_row.raw_n or 0)
    jobs_n = int(pipe_row.jobs_n or 0)
    gen_fail = int(pipe_row.gen_fail or 0)
    gen_ok = int(pipe_row.gen_ok or 0)
    denom = gen_fail + gen_ok
    gen_rate = (gen_ok / denom) if denom else None

    lat_n = int(lat_row.n or 0)
    p50 = float(lat_row.p50) if lat_row.p50 is not None else None
    p90 = float(lat_row.p90) if lat_row.p90 is not None else None

    return MetricsResponse(
        window_days=d,
        review=ReviewMetrics(
            jobs_with_first_review=jobs_fr,
            first_review_approve_count=first_apr,
            first_review_approve_rate=apr_rate,
        ),
        pipeline=IngestionGenerationMetrics(
            topic_raw_rows_in_window=raw_n,
            content_jobs_created_in_window=jobs_n,
            generation_failed_in_window=gen_fail,
            generation_terminal_ok_in_window=gen_ok,
            generation_success_rate=gen_rate,
        ),
        latency=LatencyMetrics(p50_seconds=p50, p90_seconds=p90, sample_jobs=lat_n),
    )


@router.get("/export", response_model=dict[str, Any])
async def export_metrics_json(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """与 GET /metrics 相同数据，以 JSON 对象导出（便于采集器抓取）。"""
    m = await get_metrics(session)
    return m.model_dump()
