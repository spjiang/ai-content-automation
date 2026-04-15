"""微博热搜 collector（占位实现，返回 mock 数据，真实抓取逻辑待补充）。"""

import structlog

from src.infrastructure.external.collectors.base import BaseCollector, RawTopic

logger = structlog.get_logger(__name__)

_MOCK_TOPICS = [
    {"title": "微博热搜话题1", "heat": 9800000.0, "url": "https://s.weibo.com/weibo?q=%231"},
    {"title": "微博热搜话题2", "heat": 7500000.0, "url": "https://s.weibo.com/weibo?q=%232"},
    {"title": "微博热搜话题3", "heat": 6200000.0, "url": "https://s.weibo.com/weibo?q=%233"},
]


class WeiboCollector(BaseCollector):
    platform = "weibo"

    async def fetch(self) -> list[RawTopic]:
        logger.info("weibo.collector.fetch.start")
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
        logger.info("weibo.collector.fetch.done", count=len(topics))
        return topics
