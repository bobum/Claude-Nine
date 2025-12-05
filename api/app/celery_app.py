"""
Celery application configuration for Claude-Nine task queue.

This module configures Celery with Redis as the message broker and result backend.
The worker process consumes tasks from the queue and executes orchestrator jobs.
"""

from celery import Celery
from .config import settings

# Create Celery application
celery_app = Celery(
    "claude_nine",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.orchestrator_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes (more reliable)
    task_reject_on_worker_lost=True,  # Requeue if worker dies

    # Result settings
    result_expires=86400,  # Results expire after 24 hours

    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch one task at a time (for long-running tasks)
    worker_concurrency=4,  # Number of concurrent workers

    # Task routing (optional, for future scaling)
    task_routes={
        "app.tasks.orchestrator_tasks.run_orchestrator": {"queue": "orchestrator"},
    },

    # Default queue
    task_default_queue="orchestrator",
)
