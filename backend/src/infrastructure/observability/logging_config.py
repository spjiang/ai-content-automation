"""Structlog 配置：支持 LOG_FORMAT=json 与统一时间戳。"""

from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging(service: str) -> None:
    """在 API 进程与 Celery worker 启动时各调用一次。"""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = os.environ.get("LOG_FORMAT", "").lower()

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared: list[object] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        _add_service_name(service),
    ]

    if log_format == "json":
        shared.append(structlog.processors.format_exc_info)
        shared.append(structlog.processors.JSONRenderer())
    else:
        shared.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=shared,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def _add_service_name(service: str) -> object:
    def processor(logger: object, method_name: str, event_dict: dict[str, object]) -> dict[str, object]:
        event_dict["service"] = service
        return event_dict

    return processor
