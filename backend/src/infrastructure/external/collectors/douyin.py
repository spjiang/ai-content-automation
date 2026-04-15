"""抖音热榜 collector（占位实现，返回 mock 数据）。"""

import structlog

from src.infrastructure.external.collectors.base import BaseCollector, RawTopic

logger = structlog.get_logger(__name__)

_MOCK_TOPICS = [
    {"title": "抖音热榜话题1", "heat": 1200000.0, "url": "https://www.douyin.com/hot"},
    {"title": "抖音热榜话题2", "heat": 980000.0, "url": "https://www.douyin.com/hot"},
    {"title": "抖音热榜话题3", "heat": 750000.0, "url": "https://www.douyin.com/hot"},
]


class DouyinCollector(BaseCollector):
    platform = "douyin"

    async def fetch(self) -> list[RawTopic]:
        logger.info("douyin.collector.fetch.start")
        topics = [
            RawTopic(
                platform=self.platform,
                title=t["title"],
                heat=t["heat"],
                url=t["url"],
                raw_payload=t,
            )
            for t in _MOCK_TOPICS
        ]
        logger.info("douyin.collector.fetch.done", count=len(topics))
        return topics
