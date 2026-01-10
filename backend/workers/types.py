"""
Typed structures for worker communication protocol.

These dataclasses define the data flow between worker phases and
serve as the schema for SQS messages in Phase 2I.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class JobIdentifier:
    """
    Unique identifier for a job within a user's context.

    This is the key used for UPSERT and SQS message routing.
    Combines company + external_id to avoid splitting later.
    """
    company: str
    external_id: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "JobIdentifier":
        return cls(company=data["company"], external_id=data["external_id"])


@dataclass
class JobData:
    """
    Job data from extractor, ready for UPSERT.

    Contains the identifier plus metadata from the career page.
    """
    identifier: JobIdentifier
    url: str
    title: Optional[str] = None
    location: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "company": self.identifier.company,
            "external_id": self.identifier.external_id,
            "url": self.url,
            "title": self.title,
            "location": self.location,
        }

    @classmethod
    def from_extractor_job(cls, company: str, job: dict) -> "JobData":
        """Create from extractor result job dict."""
        return cls(
            identifier=JobIdentifier(company=company, external_id=job["id"]),
            url=job["url"],
            title=job.get("title"),
            location=job.get("location"),
        )


@dataclass
class CrawlMessage:
    """
    SQS message for crawler worker (Phase 2J).

    Contains job URL to avoid extra DB query during crawl.
    """
    user_id: int
    run_id: int
    job: JobIdentifier
    url: str
    use_test_db: bool = False

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "run_id": self.run_id,
            "company": self.job.company,
            "external_id": self.job.external_id,
            "url": self.url,
            "use_test_db": self.use_test_db,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlMessage":
        return cls(
            user_id=data["user_id"],
            run_id=data["run_id"],
            job=JobIdentifier(company=data["company"], external_id=data["external_id"]),
            url=data["url"],
            use_test_db=data.get("use_test_db", False),
        )


@dataclass
class CompanyResult:
    """
    Result of processing jobs for a single company.

    Returned by run_initialization_phase for each company.
    """
    company: str
    status: str  # "success" or "error"
    jobs: list[JobData] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def job_count(self) -> int:
        return len(self.jobs)


@dataclass
class InitializationResult:
    """
    Result of the initialization phase.

    Contains all jobs ready for ingestion, organized by company.
    Used by run_ingestion_phase to create SQS messages.
    """
    user_id: int
    run_id: int
    companies: list[CompanyResult] = field(default_factory=list)
    jobs_expired: int = 0

    @property
    def total_jobs(self) -> int:
        return sum(c.job_count for c in self.companies)

    @property
    def all_jobs(self) -> list[JobData]:
        """Flatten all jobs from all companies."""
        jobs = []
        for company in self.companies:
            jobs.extend(company.jobs)
        return jobs

    def to_crawl_messages(self, use_test_db: bool = False) -> list[CrawlMessage]:
        """Generate SQS messages for all jobs."""
        messages = []
        for company in self.companies:
            if company.status != "success":
                continue
            for job in company.jobs:
                messages.append(CrawlMessage(
                    user_id=self.user_id,
                    run_id=self.run_id,
                    job=job.identifier,
                    url=job.url,
                    use_test_db=use_test_db,
                ))
        return messages


@dataclass
class IngestionResult:
    """
    Result of the ingestion phase.

    Final counts after all jobs are processed.
    """
    jobs_ready: int = 0
    jobs_skipped: int = 0
    jobs_expired: int = 0
    jobs_failed: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
