"""Main entrypoint for running the Sherlog Incident Worker daemon."""

import logging
import signal
import sys
import time

from backend.app.config import settings
from backend.app.worker.worker import IncidentWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("sherlog.worker")


import argparse


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the worker daemon."""
    parser = argparse.ArgumentParser(
        description="Sherlog Incident Worker - Consumes incidents from Redis Streams",
    )
    parser.add_argument(
        "--stream",
        default=settings.REDIS_STREAM_NAME,
        help="Redis Stream key to consume from (default: %(default)s)",
    )
    parser.add_argument(
        "--group",
        default=settings.REDIS_CONSUMER_GROUP,
        help="Redis Consumer Group name (default: %(default)s)",
    )
    parser.add_argument(
        "--consumer",
        default=None,
        help="Consumer identifier (default: auto-generated worker-<hostname>-<pid>)",
    )
    parser.add_argument(
        "--dlq",
        default=settings.REDIS_DLQ_STREAM_NAME,
        help="Dead-Letter Queue stream name (default: %(default)s)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=settings.WORKER_MAX_RETRIES,
        help="Max retries before routing to DLQ (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> None:
    """Run the standalone incident worker daemon."""
    args = parse_args()

    logger.info("Initializing Sherlog Incident Worker...")
    logger.info("Stream: %s | Group: %s | DLQ: %s", args.stream, args.group, args.dlq)

    worker = IncidentWorker(
        stream_name=args.stream,
        group_name=args.group,
        consumer_name=args.consumer,
        dlq_stream_name=args.dlq,
        max_retries=args.max_retries,
    )

    def handle_shutdown(signum, frame):
        logger.info("Received termination signal (%s). Initiating graceful shutdown...", signum)
        worker.stop()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        worker.run()
    except Exception as exc:
        logger.critical("Incident worker encountered fatal exception: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
