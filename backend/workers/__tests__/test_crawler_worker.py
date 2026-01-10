"""
Unit tests for crawler worker.

Tests worker logic with mocked external dependencies (DB, S3, HTTP crawling).
All tests use unittest.mock.patch to avoid real DB/network/S3 calls.

Run: python3 -m pytest workers/__tests__/test_crawler_worker.py -v
"""

from unittest.mock import MagicMock, patch

from workers.crawler_worker import (
    process_crawl_message,
    build_s3_key,
    CIRCUIT_BREAKER_THRESHOLD,
)
from workers.types import CrawlMessage, JobIdentifier
from models.ingestion_run import RunStatus
from models.job import JobStatus


def make_crawl_message(
    user_id: int = 1,
    run_id: int = 10,
    company: str = "google",
    external_id: str = "jobs/123",
    url: str = "https://careers.google.com/jobs/123",
    use_test_db: bool = False,
) -> CrawlMessage:
    """Create a test CrawlMessage."""
    return CrawlMessage(
        user_id=user_id,
        run_id=run_id,
        job=JobIdentifier(company=company, external_id=external_id),
        url=url,
        use_test_db=use_test_db,
    )


def make_mock_run(
    run_id: int = 10,
    status: str = RunStatus.INGESTING,
    run_metadata: dict | None = None,
) -> MagicMock:
    """Create a mock IngestionRun."""
    mock_run = MagicMock()
    mock_run.id = run_id
    mock_run.status = status
    mock_run.run_metadata = run_metadata or {}
    return mock_run


def make_mock_job(
    user_id: int = 1,
    company: str = "google",
    external_id: str = "jobs/123",
    status: str = JobStatus.PENDING,
    simhash: int | None = None,
) -> MagicMock:
    """Create a mock Job."""
    mock_job = MagicMock()
    mock_job.user_id = user_id
    mock_job.company = company
    mock_job.external_id = external_id
    mock_job.status = status
    mock_job.simhash = simhash
    return mock_job


class TestBuildS3Key:
    """Tests for S3 key building."""

    def test_simple_external_id(self):
        """Should build key with company and external_id."""
        key = build_s3_key("google", "abc123")
        assert key == "raw/google/abc123.html"

    def test_external_id_with_slashes(self):
        """Should replace slashes with underscores."""
        key = build_s3_key("google", "jobs/results/123456")
        assert key == "raw/google/jobs_results_123456.html"


class TestProcessCrawlMessage:
    """Tests for process_crawl_message with mocked dependencies."""

    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_run_not_found(self, mock_get_run):
        """Should return error if run doesn't exist."""
        mock_db = MagicMock()
        mock_get_run.return_value = None
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "error"
        assert result["reason"] == "run_not_found"

    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_run_aborted(self, mock_get_run):
        """Should skip processing if run was aborted."""
        mock_db = MagicMock()
        mock_get_run.return_value = make_mock_run(status=RunStatus.ABORTED)
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "skipped"
        assert result["reason"] == "run_aborted"

    @patch("workers.crawler_worker.update_job_status")
    @patch("workers.crawler_worker.get_job")
    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_circuit_breaker_triggered(self, mock_get_run, mock_get_job, mock_update_job):
        """Should skip and mark error when circuit breaker is open."""
        mock_db = MagicMock()
        # Circuit breaker threshold is 5
        mock_get_run.return_value = make_mock_run(
            run_metadata={"google_failures": CIRCUIT_BREAKER_THRESHOLD}
        )
        mock_job = make_mock_job()
        mock_get_job.return_value = mock_job
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "error"
        assert result["reason"] == "circuit_breaker"
        # Should mark job as error
        mock_update_job.assert_called_once()
        call_args = mock_update_job.call_args
        assert call_args[0][2] == JobStatus.ERROR  # status arg
        assert "Circuit breaker" in call_args[1]["error_message"]

    @patch("workers.crawler_worker.update_job_status")
    @patch("workers.crawler_worker.get_job")
    @patch("workers.crawler_worker.increment_failure_count")
    @patch("workers.crawler_worker.crawl_with_retry")
    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_crawl_failure(
        self, mock_get_run, mock_crawl, mock_inc_failure, mock_get_job, mock_update_job
    ):
        """Should increment failure count and mark job error on crawl failure."""
        mock_db = MagicMock()
        mock_get_run.return_value = make_mock_run()
        mock_crawl.side_effect = Exception("Connection timeout")
        mock_inc_failure.return_value = 1
        mock_job = make_mock_job()
        mock_get_job.return_value = mock_job
        message = make_crawl_message()

        # Mock asyncio.run to actually call the async function
        with patch("workers.crawler_worker.asyncio.run", side_effect=Exception("Connection timeout")):
            result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "error"
        assert result["reason"] == "crawl_failed"
        assert "Connection timeout" in result["error"]
        mock_inc_failure.assert_called_once()
        mock_update_job.assert_called_once()

    @patch("workers.crawler_worker.get_job")
    @patch("workers.crawler_worker.asyncio.run")
    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_job_not_found_in_db(self, mock_get_run, mock_asyncio_run, mock_get_job):
        """Should return error if job record doesn't exist."""
        mock_db = MagicMock()
        mock_get_run.return_value = make_mock_run()
        mock_asyncio_run.return_value = "<html>content</html>"
        mock_get_job.return_value = None  # Job not found
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "error"
        assert result["reason"] == "job_not_found"

    @patch("workers.crawler_worker.update_job_status")
    @patch("workers.crawler_worker.is_similar")
    @patch("workers.crawler_worker.compute_simhash")
    @patch("workers.crawler_worker.get_job")
    @patch("workers.crawler_worker.asyncio.run")
    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_content_similar_skipped(
        self,
        mock_get_run,
        mock_asyncio_run,
        mock_get_job,
        mock_compute_simhash,
        mock_is_similar,
        mock_update_job,
    ):
        """Should mark job SKIPPED when content is similar (SimHash match)."""
        mock_db = MagicMock()
        mock_get_run.return_value = make_mock_run()
        mock_asyncio_run.return_value = "<html>similar content</html>"
        mock_job = make_mock_job(simhash=12345)
        mock_get_job.return_value = mock_job
        mock_compute_simhash.return_value = 12346  # Similar hash
        mock_is_similar.return_value = True  # Content is similar
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "skipped"
        assert result["reason"] == "content_similar"
        mock_update_job.assert_called_once()
        call_args = mock_update_job.call_args
        assert call_args[0][2] == JobStatus.SKIPPED

    @patch("workers.crawler_worker.update_job_status")
    @patch("workers.crawler_worker.increment_failure_count")
    @patch("workers.crawler_worker.save_to_s3")
    @patch("workers.crawler_worker.is_similar")
    @patch("workers.crawler_worker.compute_simhash")
    @patch("workers.crawler_worker.get_job")
    @patch("workers.crawler_worker.asyncio.run")
    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_s3_save_failure(
        self,
        mock_get_run,
        mock_asyncio_run,
        mock_get_job,
        mock_compute_simhash,
        mock_is_similar,
        mock_save_s3,
        mock_inc_failure,
        mock_update_job,
    ):
        """Should increment failure and mark error on S3 save failure."""
        mock_db = MagicMock()
        mock_get_run.return_value = make_mock_run()
        mock_asyncio_run.return_value = "<html>new content</html>"
        mock_job = make_mock_job(simhash=12345)
        mock_get_job.return_value = mock_job
        mock_compute_simhash.return_value = 99999  # Different hash
        mock_is_similar.return_value = False  # Content changed
        mock_save_s3.side_effect = Exception("S3 access denied")
        mock_inc_failure.return_value = 1
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "error"
        assert result["reason"] == "s3_failed"
        assert "S3 access denied" in result["error"]
        mock_inc_failure.assert_called_once()
        mock_update_job.assert_called_once()
        call_args = mock_update_job.call_args
        assert call_args[0][2] == JobStatus.ERROR

    @patch("workers.crawler_worker.update_job_status")
    @patch("workers.crawler_worker.save_to_s3")
    @patch("workers.crawler_worker.is_similar")
    @patch("workers.crawler_worker.compute_simhash")
    @patch("workers.crawler_worker.get_job")
    @patch("workers.crawler_worker.asyncio.run")
    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_happy_path_new_content(
        self,
        mock_get_run,
        mock_asyncio_run,
        mock_get_job,
        mock_compute_simhash,
        mock_is_similar,
        mock_save_s3,
        mock_update_job,
    ):
        """Should crawl, save to S3, and mark READY for new content."""
        mock_db = MagicMock()
        mock_get_run.return_value = make_mock_run()
        mock_asyncio_run.return_value = "<html>brand new content</html>"
        mock_job = make_mock_job(simhash=None)  # No previous simhash
        mock_get_job.return_value = mock_job
        mock_compute_simhash.return_value = 12345
        mock_is_similar.return_value = False  # Content is new
        mock_save_s3.return_value = "s3://test-bucket/raw/google/jobs_123.html"
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "ready"
        assert result["s3_url"] == "s3://test-bucket/raw/google/jobs_123.html"
        mock_save_s3.assert_called_once()
        mock_update_job.assert_called_once()
        call_args = mock_update_job.call_args
        assert call_args[0][2] == JobStatus.READY
        assert call_args[1]["simhash"] == 12345
        assert call_args[1]["raw_s3_url"] == "s3://test-bucket/raw/google/jobs_123.html"

    @patch("workers.crawler_worker.update_job_status")
    @patch("workers.crawler_worker.save_to_s3")
    @patch("workers.crawler_worker.is_similar")
    @patch("workers.crawler_worker.compute_simhash")
    @patch("workers.crawler_worker.get_job")
    @patch("workers.crawler_worker.asyncio.run")
    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_happy_path_content_changed(
        self,
        mock_get_run,
        mock_asyncio_run,
        mock_get_job,
        mock_compute_simhash,
        mock_is_similar,
        mock_save_s3,
        mock_update_job,
    ):
        """Should update job when content has changed significantly."""
        mock_db = MagicMock()
        mock_get_run.return_value = make_mock_run()
        mock_asyncio_run.return_value = "<html>updated content</html>"
        mock_job = make_mock_job(simhash=11111)  # Has previous simhash
        mock_get_job.return_value = mock_job
        mock_compute_simhash.return_value = 99999  # Very different
        mock_is_similar.return_value = False  # Content changed
        mock_save_s3.return_value = "s3://test-bucket/raw/google/jobs_123.html"
        message = make_crawl_message()

        result = process_crawl_message(mock_db, message, "test-bucket")

        assert result["status"] == "ready"
        mock_is_similar.assert_called_once_with(11111, 99999, threshold=3)

    @patch("workers.crawler_worker.get_run_with_metadata")
    def test_circuit_breaker_below_threshold(self, mock_get_run):
        """Should continue processing when failures below threshold."""
        mock_db = MagicMock()
        # 4 failures is below threshold of 5
        mock_get_run.return_value = make_mock_run(
            run_metadata={"google_failures": CIRCUIT_BREAKER_THRESHOLD - 1}
        )
        message = make_crawl_message()

        # Will continue and fail on next step (asyncio.run not mocked)
        # This verifies circuit breaker didn't trigger
        with patch("workers.crawler_worker.asyncio.run") as mock_asyncio:
            mock_asyncio.side_effect = Exception("Expected - testing circuit breaker didn't trigger")
            with patch("workers.crawler_worker.increment_failure_count"):
                with patch("workers.crawler_worker.get_job", return_value=make_mock_job()):
                    with patch("workers.crawler_worker.update_job_status"):
                        result = process_crawl_message(mock_db, message, "test-bucket")

        # Should have tried to crawl (not blocked by circuit breaker)
        assert result["reason"] == "crawl_failed"


class TestCrawlMessageParsing:
    """Tests for CrawlMessage serialization/deserialization."""

    def test_round_trip(self):
        """Should serialize and deserialize correctly."""
        original = make_crawl_message(
            user_id=42,
            run_id=100,
            company="amazon",
            external_id="jobs/456",
            url="https://amazon.jobs/456",
            use_test_db=True,
        )

        # Serialize
        data = original.to_dict()
        assert data["user_id"] == 42
        assert data["run_id"] == 100
        assert data["company"] == "amazon"
        assert data["external_id"] == "jobs/456"
        assert data["url"] == "https://amazon.jobs/456"
        assert data["use_test_db"] is True

        # Deserialize
        restored = CrawlMessage.from_dict(data)
        assert restored.user_id == original.user_id
        assert restored.run_id == original.run_id
        assert restored.job.company == original.job.company
        assert restored.job.external_id == original.job.external_id
        assert restored.url == original.url
        assert restored.use_test_db == original.use_test_db

    def test_use_test_db_defaults_false(self):
        """Should default use_test_db to False if not present."""
        data = {
            "user_id": 1,
            "run_id": 10,
            "company": "google",
            "external_id": "123",
            "url": "https://example.com",
            # use_test_db not present
        }

        message = CrawlMessage.from_dict(data)
        assert message.use_test_db is False
