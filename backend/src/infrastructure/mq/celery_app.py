import os

from celery import Celery

BROKER_URL: str = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//")
RESULT_BACKEND: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "ai_content",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["src.workers.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
