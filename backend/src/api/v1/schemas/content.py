from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    job_id: int
    decision: Literal["approve", "reject"]
    reviewer_id: str = Field(..., min_length=1, max_length=128)
    reject_reason: str | None = None
    revision_notes: str | None = None


class RequeueRequest(BaseModel):
    """修订后重新入队（可选备注）。"""

    notes: str | None = None


class JobSummary(BaseModel):
    id: int
    status: str
    canonical_title: str
    topic_fingerprint: str
    asset_version: int
    created_at: datetime


class AssetOut(BaseModel):
    publish_target: str
    version: int
    title: str
    body: str
    tags: list[str]
    cover_text: str | None
    image_suggestions: list[str]


class JobDetail(JobSummary):
    prompt_version: str | None
    template_version: str | None
    rule_version: str | None
    failure_code: str | None
    failure_reason: str | None
    assets: list[AssetOut]


class PackageSummary(BaseModel):
    id: int
    package_version: str
    created_at: datetime
