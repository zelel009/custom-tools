from rq import Worker

from app.core.db import init_db
from app.worker.queue import get_redis_conn


def main() -> None:
    init_db()
    conn = get_redis_conn()
    worker = Worker(["youtube"], connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
