"""Normalizer service: 清洗 RawTopic → TopicCanonical，含去重指纹与热度排序。"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import structlog

from src.infrastructure.external.collectors.base import RawTopic

logger = structlog.get_logger(__name__)

# 平台热度归一化权重（可通过配置覆盖）
PLATFORM_WEIGHT: dict[str, float] = {
    "weibo": 1.0,
    "zhihu": 2.5,
    "douyin": 1.5,
}
FRESHNESS_HALF_LIFE_HOURS: float = 6.0


@dataclass
class CanonicalTopic:
    """归一化话题，供规则引擎与持久化使用。"""

    canonical_title: str
    cluster_key: str
    dedup_fingerprint: str
    combined_heat: float
    source_platforms: list[str]
    heat_score: float
    first_seen_at: datetime
    last_seen_at: datetime
    source_raws: list[RawTopic] = field(default_factory=list)


def _normalize_title(title: str) -> str:
    """去除标点、空白，转小写，用于指纹计算。"""
    title = re.sub(r"[^\w\u4e00-\u9fff]", "", title)
    return title.lower().strip()


def _make_fingerprint(title: str, window_start: datetime) -> str:
    """基于规范化标题 + 时间窗（精确到小时）生成去重指纹。"""
    normalized = _normalize_title(title)
    window_key = window_start.strftime("%Y%m%d%H")
    raw = f"{normalized}::{window_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _freshness_decay(crawled_at: datetime, now: datetime) -> float:
    """指数衰减：半衰期 FRESHNESS_HALF_LIFE_HOURS 小时。"""
    age_hours = max((now - crawled_at).total_seconds() / 3600, 0)
    return 0.5 ** (age_hours / FRESHNESS_HALF_LIFE_HOURS)


def normalize(
    raw_topics: list[RawTopic],
    *,
    top_n: int = 50,
    time_window_hours: float = 2.0,
    platform_weights: dict[str, float] | None = None,
) -> list[CanonicalTopic]:
    """
    将多源 RawTopic 列表归一、去重、排序，返回 top_n 条 CanonicalTopic。

    Args:
        raw_topics: 所有来源的原始热点列表。
        top_n: 输出上限。
        time_window_hours: 同一时间窗内才参与指纹去重。
        platform_weights: 各平台权重覆盖，默认使用 PLATFORM_WEIGHT。
    """
    weights = platform_weights or PLATFORM_WEIGHT
    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(hours=time_window_hours)

    # 按指纹分组合并
    groups: dict[str, list[RawTopic]] = {}
    for raw in raw_topics:
        fp = _make_fingerprint(raw.title, window_start)
        groups.setdefault(fp, []).append(raw)

    canonical_list: list[CanonicalTopic] = []
    for fingerprint, raws in groups.items():
        platforms = list({r.platform for r in raws})
        combined_heat = sum((r.heat or 0) * weights.get(r.platform, 1.0) for r in raws)
        first_seen = min(r.crawled_at for r in raws)
        last_seen = max(r.crawled_at for r in raws)
        representative = max(raws, key=lambda r: r.heat or 0)
        freshness = _freshness_decay(last_seen, now)
        heat_score = combined_heat * freshness

        canonical_list.append(
            CanonicalTopic(
                canonical_title=representative.title,
                cluster_key=_normalize_title(representative.title)[:64],
                dedup_fingerprint=fingerprint,
                combined_heat=combined_heat,
                source_platforms=platforms,
                heat_score=heat_score,
                first_seen_at=first_seen,
                last_seen_at=last_seen,
                source_raws=raws,
            )
        )

    sorted_topics = sorted(canonical_list, key=lambda t: t.heat_score, reverse=True)
    result = sorted_topics[:top_n]
    logger.info(
        "normalizer.done",
        input_count=len(raw_topics),
        groups=len(canonical_list),
        output_count=len(result),
    )
    return result
