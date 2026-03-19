from rq import Worker

from app.worker.queue import get_redis_conn


def main() -> None:
    conn = get_redis_conn()
    worker = Worker(["youtube"], connection=conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
