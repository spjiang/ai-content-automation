"""M3：话题规则命中回放（只读）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.deps import get_db
from src.infrastructure.db.models import TopicCanonical, TopicRuleEvaluation

router = APIRouter(prefix="/topics", tags=["topics"])


class RuleHitEvaluationOut(BaseModel):
    id: int
    rule_version: str
    passed: bool
    hit_details: list[dict[str, Any]] = Field(default_factory=list)
    evaluated_at: datetime


class TopicRuleHitsResponse(BaseModel):
    topic_id: int
    canonical_title: str
    dedup_fingerprint: str
    evaluations: list[RuleHitEvaluationOut]


@router.get("/{topic_id}/rule-hits", response_model=TopicRuleHitsResponse)
async def get_topic_rule_hits(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
) -> TopicRuleHitsResponse:
    topic = await session.get(TopicCanonical, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="topic not found")

    stmt = (
        select(TopicRuleEvaluation)
        .where(TopicRuleEvaluation.topic_canonical_id == topic_id)
        .order_by(TopicRuleEvaluation.evaluated_at.desc())
        .limit(200)
    )
    rows = (await session.execute(stmt)).scalars().all()

    evaluations = [
        RuleHitEvaluationOut(
            id=r.id,
            rule_version=r.rule_version,
            passed=r.passed,
            hit_details=list(r.hit_details or []),
            evaluated_at=r.evaluated_at,
        )
        for r in rows
    ]

    return TopicRuleHitsResponse(
        topic_id=topic.id,
        canonical_title=topic.canonical_title,
        dedup_fingerprint=topic.dedup_fingerprint,
        evaluations=evaluations,
    )
