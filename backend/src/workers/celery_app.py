"""Celery 应用实例与全局配置。"""

import os

from celery import Celery

celery_app = Celery(
    "ai_content",
    broker=os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672/"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    include=[
        "src.workers.tasks.ingestion",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.workers.tasks.ingestion.*": {"queue": "ingestion"},
    },
)
