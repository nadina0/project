import logging.config

import structlog
from structlog.processors import JSONRenderer, TimeStamper, StackInfoRenderer, format_exc_info
from structlog.stdlib import add_log_level, filter_by_level, add_logger_name


def configure_stdout_logging(level=None):
    structlog.configure(
        processors=[
            filter_by_level,
            add_log_level,
            add_logger_name,
            TimeStamper(fmt="iso", key="time"),
            StackInfoRenderer(),
            format_exc_info,
            JSONRenderer(sort_keys=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "plain": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=False),
            },
            "access-json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": [
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.add_logger_name,
                    TimeStamper(fmt="iso", key="time"),
                    StackInfoRenderer(),
                    format_exc_info,
                ],
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "plain",
            },
            "access": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "access-json",
            },
        },
        "loggers": {
            "": {
                "handlers": ["stdout"],
                "level": level,
                "propagate": False,
            }
        }
    })  # yapf: disable
