"""
Worker logging utilities with Protocol + Mixin pattern.

Provides trait-like logging functionality for Lambda workers.
Each worker defines its type and context format, the mixin provides
consistent log_info/log_warning/log_error methods.

Usage:
    class CrawlerContext(WorkerLoggerMixin):
        worker_type = WorkerType.CRAWLER

        def __init__(self, run_id: int, job_key: str):
            self.run_id = run_id
            self.job_key = job_key

        def _log_context(self) -> str:
            return f"run_id={self.run_id}:job={self.job_key}"

    ctx = CrawlerContext(123, "google/abc")
    ctx.log_info("Processing")  # [CrawlerWorker:run_id=123:job=google/abc] Processing
"""

import logging
from enum import Enum
from typing import Protocol

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class WorkerType(Enum):
    """Worker type enum for log prefix identification."""
    INGESTION = "IngestionWorker"
    CRAWLER = "CrawlerWorker"
    EXTRACTOR = "ExtractorWorker"  # Phase 2K


class WorkerLoggerProtocol(Protocol):
    """
    Protocol defining what classes using WorkerLoggerMixin must provide.

    This enables type checking - mypy will error if a class uses the mixin
    but doesn't define worker_type or _log_context().
    """
    worker_type: WorkerType

    def _log_context(self) -> str:
        """Return context string like 'run_id=5' or 'run_id=5:job=google/123'."""
        ...


class WorkerLoggerMixin:
    """
    Mixin providing log_info/log_warning/log_error methods.

    Classes using this mixin must satisfy WorkerLoggerProtocol:
    - Define worker_type: WorkerType class attribute
    - Implement _log_context() -> str method

    Log format: [WorkerType:context] message
    With test DB: [TEST][WorkerType:context] message

    Examples:
    - [IngestionWorker:run_id=123] Starting initialization
    - [TEST][CrawlerWorker:run_id=123:job=google/abc] Crawling URL
    """

    # Set by subclass __init__ to add [TEST] prefix
    use_test_db: bool = False

    def _log_prefix(self: WorkerLoggerProtocol) -> str:
        """Build log prefix from worker type and context."""
        test_prefix = "[TEST]" if getattr(self, 'use_test_db', False) else ""
        return f"{test_prefix}[{self.worker_type.value}:{self._log_context()}]"

    def log_info(self: WorkerLoggerProtocol, message: str) -> None:
        """Log info message with worker prefix."""
        logger.info(f"{self._log_prefix()} {message}")

    def log_warning(self: WorkerLoggerProtocol, message: str) -> None:
        """Log warning message with worker prefix."""
        logger.warning(f"{self._log_prefix()} {message}")

    def log_error(self: WorkerLoggerProtocol, message: str) -> None:
        """Log error message with worker prefix."""
        logger.error(f"{self._log_prefix()} {message}")


# =============================================================================
# Concrete Context Classes
# =============================================================================

class IngestionLogContext(WorkerLoggerMixin):
    """
    Logging context for IngestionWorker.

    Log format: [IngestionWorker:run_id=X] message
    With test DB: [TEST][IngestionWorker:run_id=X] message
    """
    worker_type = WorkerType.INGESTION

    def __init__(self, run_id: int, use_test_db: bool = False):
        self.run_id = run_id
        self.use_test_db = use_test_db

    def _log_context(self) -> str:
        return f"run_id={self.run_id}"


class CrawlerLogContext(WorkerLoggerMixin):
    """
    Logging context for CrawlerWorker.

    Log format: [CrawlerWorker:run_id=X:job=company/external_id] message
    With test DB: [TEST][CrawlerWorker:run_id=X:job=company/external_id] message
    """
    worker_type = WorkerType.CRAWLER

    def __init__(self, run_id: int, job_key: str, use_test_db: bool = False):
        self.run_id = run_id
        self.job_key = job_key
        self.use_test_db = use_test_db

    def _log_context(self) -> str:
        return f"run_id={self.run_id}:job={self.job_key}"


class ExtractorLogContext(WorkerLoggerMixin):
    """
    Logging context for ExtractorWorker (Phase 2K).

    Log format: [ExtractorWorker:run_id=X:job=company/external_id] message
    With test DB: [TEST][ExtractorWorker:run_id=X:job=company/external_id] message
    """
    worker_type = WorkerType.EXTRACTOR

    def __init__(self, run_id: int, job_key: str, use_test_db: bool = False):
        self.run_id = run_id
        self.job_key = job_key
        self.use_test_db = use_test_db

    def _log_context(self) -> str:
        return f"run_id={self.run_id}:job={self.job_key}"
