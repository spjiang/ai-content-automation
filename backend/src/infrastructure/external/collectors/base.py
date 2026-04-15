"""Collector plugin interface — all platform collectors must implement BaseCollector."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawTopic:
    """标准化的单条热点条目，由各 collector 输出。"""

    platform: str
    title: str
    heat: float | None = None
    url: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    crawled_at: datetime = field(default_factory=datetime.utcnow)


class BaseCollector(ABC):
    """所有平台 collector 的抽象基类。"""

    platform: str  # 子类必须声明

    @abstractmethod
    async def fetch(self) -> list[RawTopic]:
        """抓取热点并返回标准化列表；单次失败应抛出异常由上层处理重试。"""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} platform={self.platform}>"
