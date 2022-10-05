import os

import structlog
from structlog.processors import TimeStamper, StackInfoRenderer, format_exc_info


level = os.getenv("LOG_LEVEL", "INFO")

logconfig_dict = {
    "version": 1,
    "formatters": {
        "json_formatter": {
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
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json_formatter",
        }
    },
    "loggers": {
        "gunicorn": {
            "handlers": ["console"],
            'formatters': ['json'],
            "propagate": False,
            "level": "ERROR",
        },
        "gunicorn.error": {
            "handlers": ["console"],
            'formatters': ['json'],
            "propagate": False,
            "level": level,
        },
    }
}  # yapf: disable
