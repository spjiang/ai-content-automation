"""基础告警钩子：统一结构化日志出口，便于接入外部告警系统。"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def emit_alert(alert_type: str, **fields: Any) -> None:
    """
    MVP：以结构化 ERROR 日志表示告警事件。
    后续可在此处接入 Webhook / Sentry / 企业微信等。
    """
    logger.error("ops.alert", alert_type=alert_type, **fields)
