"""Celery application configuration."""

import os

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "quantforge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.strategy_tasks", "app.tasks.notification_tasks", "app.tasks.reconciliation_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=30,
    result_expires=86400,
    beat_schedule={
        "reconcile-open-broker-orders": {
            "task": "app.tasks.reconciliation_tasks.reconcile_broker_orders",
            "schedule": 30.0,
            "options": {"expires": 25},
        },
        "dispatch-due-strategy-schedules": {
            "task": "app.tasks.strategy_tasks.dispatch_scheduled_strategy_tasks",
            "schedule": 60.0,
            "options": {"expires": 55},
        },
    },
)

if os.getenv("CELERY_ALWAYS_EAGER", "").lower() in ("1", "true", "yes"):
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
