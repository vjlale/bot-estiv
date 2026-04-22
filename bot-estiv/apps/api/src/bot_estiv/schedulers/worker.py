"""Worker ARQ: cron + jobs async de Bot Estiv."""
from __future__ import annotations

from arq.connections import RedisSettings
from arq.cron import cron

from ..config import settings
from . import jobs


async def startup(ctx):
    import logging

    logging.basicConfig(level=settings.log_level)


async def shutdown(ctx):
    pass


class WorkerSettings:
    functions = [
        jobs.weekly_plan_reminder,
        jobs.pre_publish_reminder,
        jobs.publish_scheduled,
        jobs.refresh_analytics_snapshot,
    ]
    cron_jobs = [
        cron(jobs.weekly_plan_reminder, weekday="mon", hour=9, minute=0),
        cron(jobs.pre_publish_reminder, hour=10, minute=0),
        cron(jobs.publish_scheduled, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        cron(jobs.refresh_analytics_snapshot, hour=2, minute=0),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
