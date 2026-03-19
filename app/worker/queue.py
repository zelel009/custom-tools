from redis import Redis
from rq import Queue

from app.core.config import settings


def get_redis_conn() -> Redis:
    return Redis.from_url(settings.redis_url)


def get_youtube_queue() -> Queue:
    return Queue(
        "youtube",
        connection=get_redis_conn(),
        default_timeout=settings.youtube_job_timeout_seconds,
    )
