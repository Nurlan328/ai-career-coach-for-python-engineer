"""Celery application. Worker: `celery -A app.core.celery_app worker --loglevel=info`."""
from celery import Celery

from app.core.config import settings

_broker = settings.celery_broker_url or settings.redis_url
_backend = settings.celery_result_backend or settings.redis_url

celery_app = Celery(
    "ai_career_coach",
    broker=_broker,
    backend=_backend,
    include=["app.worker.tasks"],  # lazily import tasks when the worker starts
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # In tests this is True so tasks run inline without a broker.
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
)
