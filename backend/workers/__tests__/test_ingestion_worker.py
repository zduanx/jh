"""
Unit tests for ingestion worker.

Tests worker logic with mocked external dependencies (DB, extractors).
All tests use dependency injection to avoid real DB/network calls.

Run: python3 -m pytest workers/__tests__/test_ingestion_worker.py -v
"""

import pytest
from unittest.mock import MagicMock

from workers.ingestion_worker import (
    run_initialization_phase,
    process_run,
)
from workers.types import InitializationResult, IngestionResult
from sourcing.extractor_utils import ExtractorResult
from models.ingestion_run import RunStatus


def make_extractor_result(
    company: str,
    status: str = "success",
    jobs: list = None,
    error_message: str = None,
) -> ExtractorResult:
    """Create a mock ExtractorResult."""
    if jobs is None:
        jobs = [
            {"id": "job1", "title": "Engineer", "location": "NYC", "url": "https://example.com/1"},
            {"id": "job2", "title": "Manager", "location": "SF", "url": "https://example.com/2"},
        ]
    return ExtractorResult(
        company=company,
        status=status,
        total_count=len(jobs),
        filtered_count=0,
        urls_count=len(jobs),
        included_jobs=jobs,
        excluded_jobs=[],
        error_message=error_message,
    )


class TestRunInitializationPhase:
    """Tests for run_initialization_phase with mocked dependencies."""

    def test_successful_extraction_and_upsert(self):
        """Should extract jobs, UPSERT them, and mark expired."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10)

        # Mock extractor returns success for one company
        mock_extractor_results = {
            "google": make_extractor_result("google"),
        }
        mock_run_extractors = MagicMock(return_value=mock_extractor_results)
        mock_upsert = MagicMock(return_value={"total": 2})
        mock_mark_expired = MagicMock(return_value=3)

        result = run_initialization_phase(
            db=mock_db,
            run=mock_run,
            settings=[MagicMock(company_name="google")],
            _run_extractors=mock_run_extractors,
            _upsert_jobs=mock_upsert,
            _mark_expired_jobs=mock_mark_expired,
        )

        # Verify result structure
        assert result.user_id == 10
        assert result.run_id == 1
        assert result.total_jobs == 2
        assert result.jobs_expired == 3
        assert len(result.companies) == 1
        assert result.companies[0].company == "google"
        assert result.companies[0].status == "success"
        assert len(result.companies[0].jobs) == 2

        # Verify mocks called correctly
        mock_run_extractors.assert_called_once()
        mock_upsert.assert_called_once()
        mock_mark_expired.assert_called_once_with(db=mock_db, user_id=10, run_id=1)

    def test_multiple_companies_success(self):
        """Should handle multiple companies successfully."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10)

        mock_extractor_results = {
            "google": make_extractor_result("google", jobs=[
                {"id": "g1", "url": "https://google.com/1"},
            ]),
            "amazon": make_extractor_result("amazon", jobs=[
                {"id": "a1", "url": "https://amazon.com/1"},
                {"id": "a2", "url": "https://amazon.com/2"},
            ]),
        }

        result = run_initialization_phase(
            db=mock_db,
            run=mock_run,
            settings=[],
            _run_extractors=MagicMock(return_value=mock_extractor_results),
            _upsert_jobs=MagicMock(return_value={"total": 1}),
            _mark_expired_jobs=MagicMock(return_value=0),
        )

        assert result.total_jobs == 3  # 1 from google + 2 from amazon
        assert len(result.companies) == 2

    def test_extractor_failure_isolated(self):
        """One company failing shouldn't block others."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10)

        mock_extractor_results = {
            "google": make_extractor_result("google", jobs=[
                {"id": "g1", "url": "https://google.com/1"},
            ]),
            "amazon": make_extractor_result(
                "amazon",
                status="error",
                jobs=[],
                error_message="Request timed out",
            ),
        }

        result = run_initialization_phase(
            db=mock_db,
            run=mock_run,
            settings=[],
            _run_extractors=MagicMock(return_value=mock_extractor_results),
            _upsert_jobs=MagicMock(return_value={"total": 1}),
            _mark_expired_jobs=MagicMock(return_value=0),
        )

        # Google should succeed, Amazon should fail
        assert result.total_jobs == 1  # Only google's job
        google_result = next(c for c in result.companies if c.company == "google")
        amazon_result = next(c for c in result.companies if c.company == "amazon")

        assert google_result.status == "success"
        assert amazon_result.status == "error"
        assert amazon_result.error_message == "Request timed out"

    def test_all_extractors_fail(self):
        """Should handle all extractors failing gracefully."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10)

        mock_extractor_results = {
            "google": make_extractor_result("google", status="error", jobs=[], error_message="Error 1"),
            "amazon": make_extractor_result("amazon", status="error", jobs=[], error_message="Error 2"),
        }

        result = run_initialization_phase(
            db=mock_db,
            run=mock_run,
            settings=[],
            _run_extractors=MagicMock(return_value=mock_extractor_results),
            _upsert_jobs=MagicMock(return_value={"total": 0}),
            _mark_expired_jobs=MagicMock(return_value=5),
        )

        assert result.total_jobs == 0
        assert result.jobs_expired == 5
        assert all(c.status == "error" for c in result.companies)

    def test_empty_extractors(self):
        """Should handle no enabled companies."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10)

        result = run_initialization_phase(
            db=mock_db,
            run=mock_run,
            settings=[],
            _run_extractors=MagicMock(return_value={}),
            _upsert_jobs=MagicMock(return_value={"total": 0}),
            _mark_expired_jobs=MagicMock(return_value=0),
        )

        assert result.total_jobs == 0
        assert result.companies == []


class TestProcessRun:
    """Tests for process_run with all DB operations mocked."""

    def test_full_flow_success(self):
        """Should go through all phases and return finished."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10, status=RunStatus.PENDING)

        mock_init_result = InitializationResult(
            user_id=10,
            run_id=1,
            companies=[],
            jobs_expired=0,
        )
        mock_ingestion_result = IngestionResult(
            jobs_ready=5,
            jobs_skipped=0,
            jobs_expired=0,
            jobs_failed=0,
        )

        result = process_run(
            db=mock_db,
            run_id=1,
            user_id=10,
            _get_run=MagicMock(return_value=mock_run),
            _update_run_status=MagicMock(),
            _refresh_run=MagicMock(),  # Doesn't change status
            _get_user_enabled_settings=MagicMock(return_value=[MagicMock()]),
            _run_initialization_phase=MagicMock(return_value=mock_init_result),
            _run_ingestion_phase=MagicMock(return_value=mock_ingestion_result),
        )

        assert result["status"] == RunStatus.FINISHED
        assert result["jobs_ready"] == 5

    def test_run_not_found(self):
        """Should return error if run doesn't exist."""
        mock_db = MagicMock()

        result = process_run(
            db=mock_db,
            run_id=999,
            user_id=10,
            _get_run=MagicMock(return_value=None),
            _update_run_status=MagicMock(),
            _refresh_run=MagicMock(),
            _get_user_enabled_settings=MagicMock(),
            _run_initialization_phase=MagicMock(),
            _run_ingestion_phase=MagicMock(),
        )

        assert "error" in result
        assert "not found" in result["error"]

    def test_already_aborted(self):
        """Should return aborted if run was aborted before start."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10, status=RunStatus.ABORTED)

        result = process_run(
            db=mock_db,
            run_id=1,
            user_id=10,
            _get_run=MagicMock(return_value=mock_run),
            _update_run_status=MagicMock(),
            _refresh_run=MagicMock(),
            _get_user_enabled_settings=MagicMock(),
            _run_initialization_phase=MagicMock(),
            _run_ingestion_phase=MagicMock(),
        )

        assert result["status"] == RunStatus.ABORTED

    def test_no_enabled_companies(self):
        """Should return error if no companies enabled."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10, status=RunStatus.PENDING)
        mock_update = MagicMock()

        result = process_run(
            db=mock_db,
            run_id=1,
            user_id=10,
            _get_run=MagicMock(return_value=mock_run),
            _update_run_status=mock_update,
            _refresh_run=MagicMock(),
            _get_user_enabled_settings=MagicMock(return_value=[]),  # No companies
            _run_initialization_phase=MagicMock(),
            _run_ingestion_phase=MagicMock(),
        )

        assert result["status"] == RunStatus.ERROR
        # Verify error status was written
        mock_update.assert_called()

    def test_abort_during_initialization(self):
        """Should detect abort after init phase."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10, status=RunStatus.PENDING)

        def simulate_abort(db, run):
            """Simulate user aborting the run."""
            run.status = RunStatus.ABORTED

        mock_init_result = InitializationResult(
            user_id=10, run_id=1, companies=[], jobs_expired=0
        )

        result = process_run(
            db=mock_db,
            run_id=1,
            user_id=10,
            _get_run=MagicMock(return_value=mock_run),
            _update_run_status=MagicMock(),
            _refresh_run=simulate_abort,  # Abort on refresh
            _get_user_enabled_settings=MagicMock(return_value=[MagicMock()]),
            _run_initialization_phase=MagicMock(return_value=mock_init_result),
            _run_ingestion_phase=MagicMock(),
        )

        assert result["status"] == RunStatus.ABORTED

    def test_abort_during_ingestion(self):
        """Should detect abort after ingestion phase."""
        mock_db = MagicMock()
        mock_run = MagicMock(id=1, user_id=10, status=RunStatus.PENDING)
        call_count = [0]

        def simulate_abort_on_second_call(db, run):
            """Abort on second refresh (after ingestion)."""
            call_count[0] += 1
            if call_count[0] >= 2:
                run.status = RunStatus.ABORTED

        mock_init_result = InitializationResult(
            user_id=10, run_id=1, companies=[], jobs_expired=0
        )
        mock_ingestion_result = IngestionResult(
            jobs_ready=5, jobs_skipped=0, jobs_expired=0, jobs_failed=0
        )

        result = process_run(
            db=mock_db,
            run_id=1,
            user_id=10,
            _get_run=MagicMock(return_value=mock_run),
            _update_run_status=MagicMock(),
            _refresh_run=simulate_abort_on_second_call,
            _get_user_enabled_settings=MagicMock(return_value=[MagicMock()]),
            _run_initialization_phase=MagicMock(return_value=mock_init_result),
            _run_ingestion_phase=MagicMock(return_value=mock_ingestion_result),
        )

        assert result["status"] == RunStatus.ABORTED


class TestCrawlMessageGeneration:
    """Tests for CrawlMessage generation from InitializationResult."""

    def test_to_crawl_messages(self):
        """Should generate messages for all successful jobs."""
        from workers.types import JobData, JobIdentifier, CompanyResult

        init_result = InitializationResult(
            user_id=10,
            run_id=5,
            companies=[
                CompanyResult(
                    company="google",
                    status="success",
                    jobs=[
                        JobData(
                            identifier=JobIdentifier("google", "g1"),
                            url="https://google.com/1",
                        ),
                        JobData(
                            identifier=JobIdentifier("google", "g2"),
                            url="https://google.com/2",
                        ),
                    ],
                ),
                CompanyResult(
                    company="amazon",
                    status="error",
                    error_message="Failed",
                ),
            ],
            jobs_expired=0,
        )

        messages = init_result.to_crawl_messages()

        # Should only have messages for google (success), not amazon (error)
        assert len(messages) == 2
        assert all(m.user_id == 10 for m in messages)
        assert all(m.run_id == 5 for m in messages)
        assert messages[0].job.company == "google"
        assert messages[0].job.external_id == "g1"
        assert messages[1].job.external_id == "g2"

    def test_to_crawl_messages_empty(self):
        """Should return empty list when no jobs."""
        init_result = InitializationResult(
            user_id=10, run_id=5, companies=[], jobs_expired=0
        )

        messages = init_result.to_crawl_messages()
        assert messages == []
