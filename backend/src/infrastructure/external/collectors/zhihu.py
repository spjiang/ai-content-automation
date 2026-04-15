"""知乎热榜 collector（占位实现，返回 mock 数据）。"""

import structlog

from src.infrastructure.external.collectors.base import BaseCollector, RawTopic

logger = structlog.get_logger(__name__)

_MOCK_TOPICS = [
    {"title": "知乎热榜话题1", "heat": 500000.0, "url": "https://www.zhihu.com/hot"},
    {"title": "知乎热榜话题2", "heat": 420000.0, "url": "https://www.zhihu.com/hot"},
    {"title": "知乎热榜话题3", "heat": 380000.0, "url": "https://www.zhihu.com/hot"},
]


class ZhihuCollector(BaseCollector):
    platform = "zhihu"

    async def fetch(self) -> list[RawTopic]:
        logger.info("zhihu.collector.fetch.start")
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
        logger.info("zhihu.collector.fetch.done", count=len(topics))
        return topics
