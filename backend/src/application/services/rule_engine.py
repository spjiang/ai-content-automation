"""Rule engine: 对归一化话题做过滤，记录命中明细，输出通过话题列表。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from src.application.services.normalizer import CanonicalTopic

logger = structlog.get_logger(__name__)

RULE_SCHEMA_VERSION = "1.0"


class RuleAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class RuleHitDetail:
    rule_name: str
    rule_version: str
    action: RuleAction
    reason: str
    matched_value: Any = None


@dataclass
class RuleResult:
    topic: CanonicalTopic
    passed: bool
    hit_details: list[RuleHitDetail] = field(default_factory=list)


@dataclass
class RuleConfig:
    """规则配置，可从 DB 或 YAML 加载；此为默认值。"""

    version: str = RULE_SCHEMA_VERSION
    whitelist_keywords: list[str] = field(default_factory=list)
    blacklist_keywords: list[str] = field(default_factory=list)
    sensitive_words: list[str] = field(default_factory=list)
    min_heat_score: float = 0.0
    top_n: int = 30


def _contains_any(text: str, words: list[str]) -> str | None:
    text_lower = text.lower()
    for w in words:
        if w.lower() in text_lower:
            return w
    return None


def apply_rules(
    topics: list[CanonicalTopic],
    config: RuleConfig | None = None,
) -> tuple[list[CanonicalTopic], list[RuleResult]]:
    """
    对话题列表应用规则，返回 (通过列表, 全部命中明细列表)。

    规则优先级：
    1. 白名单命中 → 直接 ALLOW，跳过后续过滤
    2. 黑名单命中 → DENY
    3. 敏感词命中 → DENY
    4. 热度阈值未达 → DENY
    5. 其余 → ALLOW
    最终按 top_n 截断。
    """
    cfg = config or RuleConfig()
    all_results: list[RuleResult] = []

    for topic in topics:
        title = topic.canonical_title
        hits: list[RuleHitDetail] = []
        passed = True

        # 1. 白名单
        if cfg.whitelist_keywords:
            matched = _contains_any(title, cfg.whitelist_keywords)
            if matched:
                hits.append(RuleHitDetail(
                    rule_name="whitelist",
                    rule_version=cfg.version,
                    action=RuleAction.ALLOW,
                    reason="whitelist keyword matched",
                    matched_value=matched,
                ))
                all_results.append(RuleResult(topic=topic, passed=True, hit_details=hits))
                continue

        # 2. 黑名单
        matched = _contains_any(title, cfg.blacklist_keywords)
        if matched:
            hits.append(RuleHitDetail(
                rule_name="blacklist",
                rule_version=cfg.version,
                action=RuleAction.DENY,
                reason="blacklist keyword matched",
                matched_value=matched,
            ))
            passed = False

        # 3. 敏感词
        if passed:
            matched = _contains_any(title, cfg.sensitive_words)
            if matched:
                hits.append(RuleHitDetail(
                    rule_name="sensitive_word",
                    rule_version=cfg.version,
                    action=RuleAction.DENY,
                    reason="sensitive word matched",
                    matched_value=matched,
                ))
                passed = False

        # 4. 热度阈值
        if passed and topic.heat_score < cfg.min_heat_score:
            hits.append(RuleHitDetail(
                rule_name="min_heat_score",
                rule_version=cfg.version,
                action=RuleAction.DENY,
                reason=f"heat_score {topic.heat_score:.2f} < threshold {cfg.min_heat_score:.2f}",
            ))
            passed = False

        if passed and not hits:
            hits.append(RuleHitDetail(
                rule_name="default_allow",
                rule_version=cfg.version,
                action=RuleAction.ALLOW,
                reason="no rule matched, default allow",
            ))

        all_results.append(RuleResult(topic=topic, passed=passed, hit_details=hits))

    passed_topics = [r.topic for r in all_results if r.passed][: cfg.top_n]
    logger.info(
        "rule_engine.done",
        input_count=len(topics),
        passed_count=len(passed_topics),
        rule_version=cfg.version,
    )
    return passed_topics, all_results
