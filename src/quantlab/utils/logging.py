from contextlib import contextmanager
import logging


@contextmanager
def run_logging(path):
    logger = logging.getLogger("quantlab")
    old_level = logger.level
    old_propagate = logger.propagate
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handlers = [logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()]
    # Detailed decision/order logs stay in the archive; console focuses on milestones.
    handlers[0].setLevel(logging.INFO)
    handlers[1].setLevel(logging.INFO)
    handlers[1].addFilter(
        lambda record: (
            record.levelno >= logging.WARNING
            or not record.getMessage().startswith(
                ("Decision ", "Order ", "Resolved config:")
            )
        )
    )
    for handler in handlers:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    try:
        yield logger
    finally:
        for handler in handlers:
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(old_level)
        logger.propagate = old_propagate
