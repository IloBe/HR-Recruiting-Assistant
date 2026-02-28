"""Central logging configuration for the Recruitment Assistant stack."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Final, Mapping, TypeAlias, cast

import structlog
from loguru import logger as loguru_logger
from structlog.contextvars import merge_contextvars

if TYPE_CHECKING:
    from loguru import Logger  # type-only import; won't run during pytest/runtime

APP_ENV: Final[str] = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION: Final[bool] = APP_ENV in {"production", "prod", "staging"}
LOG_DIR: Final[Path] = Path(__file__).resolve().parents[1] / "logs"
_initialized = False

_SENSITIVE_FIELDS: Final[set[str]] = {
    "password",
    "token",
    "api_key",
    "authorization",
    "secret",
    "credentials",
}

# Loguru record is "dict-like" with known keys, but stubs are not precise.
#
# Some parts implemented because of VS Code Pylance and Loguru limitations:
# purely a type-stub / overload typing mismatch between Pylance and Loguru’s filter parameter
_RecordDict: TypeAlias = dict[str, Any]
_FilterFunc: TypeAlias = Callable[[_RecordDict], bool]


class InterceptHandler(logging.Handler):
    """Redirect Python logging records into Loguru for unified output."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:  # pragma: no cover - guard for custom levels
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _redact(record: _RecordDict) -> bool:
    """Obfuscate secrets before anything is emitted."""

    extra = record.get("extra")
    if isinstance(extra, Mapping):
        # Make a mutable copy if needed
        extra_mut = dict(extra)
        for field in _SENSITIVE_FIELDS:
            if field in extra_mut:
                extra_mut[field] = "***REDACTED***"
        record["extra"] = extra_mut
    return True


# Cast to satisfy Pylance's overload expectations for loguru_logger.add(filter=...)
_REDACT_FILTER: Final[Callable[[Any], bool]] = cast(Callable[[Any], bool], _redact)


def _console_format() -> str:
    """Return a concise format emphasizing time, level, component, and message."""

    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra.get('component','app')}</cyan> | "
        "<cyan>{extra.get('request_id','')}</cyan> | "
        "{message} "
        "<dim>{extra}</dim>"
    )


def configure_logging() -> Logger:
    """Set up Loguru sinks, rotation, and structlog processors once per process."""

    global _initialized
    if _initialized:
        return loguru_logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    loguru_logger.remove()

    console_level = os.getenv("LOG_LEVEL", "DEBUG" if not IS_PRODUCTION else "INFO")
    file_level = os.getenv("FILE_LOG_LEVEL", "DEBUG")
    error_level = os.getenv("ERROR_LOG_LEVEL", "ERROR")
    diagnose_enabled = not IS_PRODUCTION

    # Console sink
    loguru_logger.add(  # type: ignore[call-overload]
        sys.stderr,
        level=console_level,
        format=_console_format(),
        colorize=True,
        filter=_REDACT_FILTER,
        backtrace=True,
        diagnose=diagnose_enabled,
    )


    # JSON file sink
    log_file = LOG_DIR / "recruitment_assistant.log"
    loguru_logger.add(
        log_file,
        level=file_level,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        serialize=True,
        filter=_REDACT_FILTER,
        backtrace=True,
        diagnose=diagnose_enabled,
    )

    # Error file sink
    error_file = LOG_DIR / "recruitment_assistant.error.log"
    loguru_logger.add(
        error_file,
        level=error_level,
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        serialize=True,
        filter=_REDACT_FILTER,
        backtrace=True,
        diagnose=diagnose_enabled,
    )

    # Intercept stdlib logging
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.DEBUG)

    # Structlog configuration (emits into stdlib logging unless you route differently)
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.KeyValueRenderer(
                key_order=[
                    "timestamp",
                    "level",
                    "event",
                    "logger",
                    "request_id",
                    "trace_id",
                ]
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    _initialized = True
    enable_crewai_tracing()

    # Prefer bind() for extra fields (often better with type checkers)
    loguru_logger.bind(
        directory=str(LOG_DIR),
        level=console_level,
        app_env=APP_ENV,
    ).info("logging_initialized")

    return loguru_logger


def enable_crewai_tracing() -> bool:
    """Mark the CrewAI tracing flow as enabled when credentials are present."""

    account = os.getenv("CREWAI_AOP_ACCOUNT")
    api_key = os.getenv("CREWAI_AOP_API_KEY")
    project = os.getenv("CREWAI_AOP_PROJECT", "recruitment-assistant")

    if not account or not api_key:
        loguru_logger.bind(
            reason="missing credentials",
            account=bool(account),
            project=project,
        ).info("crewai_tracing_skipped")
        return False

    os.environ.setdefault("CREWAI_TRACING_ENABLED", "true")
    loguru_logger.bind(
        account=account,
        project=project,
        dashboard_url=os.getenv(
            "CREWAI_DASHBOARD_URL",
            "https://app.crewai.ai/aop",
        ),
    ).info("crewai_tracing_enabled")
    return True


def get_app_logger() -> Logger:
    """Return the configured Loguru logger with a component binding."""

    configure_logging()
    return loguru_logger.bind(component="recruitment_assistant")