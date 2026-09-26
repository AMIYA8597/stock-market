"""
Celery application for background task processing.

Used for scheduled data fetching, ML model training, and alert evaluation.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "quantedge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    # Without this, a worker process started via
    # `celery -A app.core.celery_app worker` never imports any task module,
    # so none of the @shared_task-decorated functions below are registered
    # and the beat schedule's task names below can never resolve.
    include=[
        "app.tasks.autotrade_tasks",
        "app.tasks.backtest_tasks",
        "app.tasks.feature_tasks",
        "app.tasks.market_data_tasks",
        "app.tasks.regime_tasks",
        "app.tasks.retraining_trigger",
        "app.tasks.sentiment_tasks",
    ],
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
    task_always_eager=(settings.ENVIRONMENT == "development"),
    beat_schedule={
        # Scheduled data fetch tasks
        "update-news-sentiment-hourly": {
            "task": "update_news_sentiment",
            "schedule": 3600.0,  # Every hour
        },
        "update-regime-states-daily": {
            "task": "update_regime_states",
            "schedule": 86400.0,  # Every day
        },
        "evaluate-market-alerts-minutely": { "task": "evaluate_market_alerts", "schedule": 60.0 },
        "autotrade-scan-every-5-minutes": { "task": "run_autotrade_scan", "schedule": 300.0 },
        "check-model-drift-daily": {
            "task": "check_drift_for_watchlist",
            "schedule": 86400.0,  # Every day — walk-forward PSI/KS drift check, retrains only if drift exceeds threshold
        },
    },
)

celery_app.autodiscover_tasks(['app.tasks', 'app.tasks.alert_tasks'])
